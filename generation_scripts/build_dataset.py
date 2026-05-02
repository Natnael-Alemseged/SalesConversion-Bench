from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generation_scripts.authoring.config import DEFAULT_CONFIG, AuthoringConfig  # noqa: E402
from generation_scripts.authoring.dedup import near_duplicate_pairs  # noqa: E402
from generation_scripts.authoring.io import dump_json, dump_jsonl, load_jsonl  # noqa: E402
from generation_scripts.authoring.judging import (  # noqa: E402
    apply_pointwise_thresholds,
    deterministic_pointwise_stub,
)
from generation_scripts.authoring.rotation import enforce_rotation, model_family  # noqa: E402
from generation_scripts.multi_llm_routing import route_task  # noqa: E402

GEN = ROOT / "generation_scripts"
PROMPTS = GEN / "judge_prompts"


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def _model_pick(models: tuple[str, ...], *, seed: int) -> str:
    # Deterministic pick for reproducibility without importing RNG behavior across versions.
    if not models:
        return "unknown"
    return models[seed % len(models)]


def _judge_pick_different_family(*, judges: tuple[str, ...], generator_model: str, seed: int) -> str:
    """Pick a judge model deterministically, enforcing family != generator family."""

    if not judges:
        return "unknown"
    gen_family = model_family(generator_model)
    start = seed % len(judges)
    for offset in range(len(judges)):
        candidate = judges[(start + offset) % len(judges)]
        if model_family(candidate) != gen_family:
            return candidate
    return judges[start]


def build_manifest(*, config: AuthoringConfig, source_pool_path: Path, task_count: int) -> dict[str, Any]:
    return {
        "seed": config.seed,
        "created_at": datetime.now(UTC).isoformat(),
        "source_pool_path": str(source_pool_path),
        "task_count": task_count,
        "rotation_policy": {
            "rule": "generator model family must differ from judge model family for the same example pool",
            "enforced": True,
        },
        "judge_filter_policy": {
            "dimensions": ["coherence", "verifiability", "rubric_clarity"],
            "scale": [1, 3, 5],
            "thresholds": asdict(config.pointwise_thresholds),
            "default_on_malformed": "reject",
        },
        "routing_policy": {
            "cheap_generator_default_for_multi_llm_synthesis": True,
            "eval_generator_calibration_sample_rate": 0.10,
            "trace_derived_forces_eval_generation": True,
            "judge_tier": "eval_only",
        },
        "pairwise_policy": {
            "near_duplicate_measure": "Jaccard token overlap over candidate subject+body",
            "near_duplicate_threshold": config.near_duplicate_jaccard_threshold,
        },
        "prompt_paths": {
            "pointwise": str(PROMPTS / "pointwise_judge.md"),
            "pairwise": str(PROMPTS / "pairwise_tiebreak.md"),
        },
        "models_declared": asdict(config.models),
        "implemented_with_live_llm_calls": False,
        "note": "This orchestrator enforces rotation and threshold logic in source; live model calls can be integrated later without changing audit structure.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dataset with auditable routing + judge-filter scaffolding.")
    parser.add_argument(
        "--source-pool",
        default=str(ROOT / "tenacious_bench_v0.2" / "source_pool.jsonl"),
        help="Input JSONL pool to filter/dedup/audit.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(GEN / "audit_logs"),
        help="Directory to write audit logs and manifest.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_CONFIG.seed,
        help="Reproducibility seed (affects model picks and tie-break determinism).",
    )
    args = parser.parse_args()

    config = AuthoringConfig(
        seed=args.seed,
        near_duplicate_jaccard_threshold=DEFAULT_CONFIG.near_duplicate_jaccard_threshold,
        pointwise_thresholds=DEFAULT_CONFIG.pointwise_thresholds,
        models=DEFAULT_CONFIG.models,
    )

    source_pool_path = Path(args.source_pool).resolve()
    tasks = load_jsonl(source_pool_path)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = _now_slug()
    manifest_path = out_dir / f"authoring_manifest_{run_id}.json"
    audit_path = out_dir / f"authoring_audit_{run_id}.jsonl"

    manifest = build_manifest(config=config, source_pool_path=source_pool_path, task_count=len(tasks))
    manifest["rotation_policy_note"] = "Rotation is enforced per task after routing chooses the generator tier."
    dump_json(manifest_path, manifest)

    accepted: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    pointwise_rejects = 0
    cheap_generator_usage = 0
    eval_generator_usage = 0
    calibration_sample_count = 0

    for index, task in enumerate(tasks):
        route = route_task(task, calibration_sample_rate=0.10)
        if route.generator_tier == "cheap":
            cheap_generator_usage += 1
            generator_model = _model_pick(config.models.cheap_generators, seed=config.seed + index)
        else:
            eval_generator_usage += 1
            generator_model = _model_pick(config.models.eval_generators, seed=config.seed + index)
        if route.calibration_sample:
            calibration_sample_count += 1

        judge_model = _judge_pick_different_family(
            judges=config.models.eval_judges,
            generator_model=generator_model,
            seed=config.seed + index + 1,
        )
        rotation = enforce_rotation(generator_model=generator_model, judge_model=judge_model)

        pointwise = deterministic_pointwise_stub(task)
        threshold_decision, threshold_reason = apply_pointwise_thresholds(pointwise, config.pointwise_thresholds)
        decision = "accept" if (pointwise.decision == "accept" and threshold_decision == "accept") else "reject"
        if decision == "reject":
            pointwise_rejects += 1
        else:
            accepted.append(task)

        audit_rows.append(
            {
                "task_id": task.get("task_id"),
                "route": route.route,
                "generator_tier": route.generator_tier,
                "judge_tier": route.judge_tier,
                "pairwise_required": route.pairwise_required,
                "calibration_sample": route.calibration_sample,
                "generator_model": generator_model,
                "judge_model": judge_model,
                "rotation": asdict(rotation),
                "pointwise": asdict(pointwise),
                "threshold_decision": threshold_decision,
                "threshold_reason": threshold_reason,
                "final_decision": decision,
            }
        )

    # Pairwise near-duplicate analysis is visible in logs. The interim implementation does
    # not drop rows automatically; it records candidate pairs for manual or future judge resolution.
    pairs = near_duplicate_pairs(accepted, threshold=config.near_duplicate_jaccard_threshold)
    for pair in pairs[:500]:
        audit_rows.append(
            {
                "event": "near_duplicate_pair",
                "left_task_id": accepted[pair.left_index].get("task_id"),
                "right_task_id": accepted[pair.right_index].get("task_id"),
                "overlap": pair.overlap,
                "policy": "pairwise tie-break recommended",
            }
        )

    dump_jsonl(audit_path, audit_rows)

    summary = {
        "source_pool": str(source_pool_path),
        "manifest_path": str(manifest_path),
        "audit_log_path": str(audit_path),
        "input_count": len(tasks),
        "accepted_count": len(accepted),
        "rejected_count": len(tasks) - len(accepted),
        "pointwise_rejects": pointwise_rejects,
        "near_duplicate_pair_count": len(pairs),
        "cheap_generator_usage": cheap_generator_usage,
        "eval_generator_usage": eval_generator_usage,
        "calibration_sample_count": calibration_sample_count,
        "implemented_with_live_llm_calls": False,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
