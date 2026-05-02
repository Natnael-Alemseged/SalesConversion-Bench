from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


@dataclass
class RouteDecision:
    task_id: str
    route: str
    generator_tier: str
    judge_tier: str
    pairwise_required: bool
    calibration_sample: bool
    rationale: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _stable_task_key(task: dict[str, Any]) -> str:
    task_id = str(task.get("task_id", "") or "")
    if task_id:
        return task_id
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    probe_ids = metadata.get("week10_probe_ids", [])
    return "|".join(str(item) for item in probe_ids) or "unknown"


def route_task(
    task: dict[str, Any],
    *,
    rng: random.Random | None = None,
    calibration_sample_rate: float = 0.10,
) -> RouteDecision:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    source_mode = str(metadata.get("source_mode", task.get("source_mode", "")) or "")
    failure_category = str(metadata.get("failure_category", "") or "")
    notes = str(metadata.get("notes", "") or "")
    task_key = _stable_task_key(task)
    local_rng = rng or random.Random(task_key)
    calibration_sample = local_rng.random() < calibration_sample_rate

    nuanced_categories = {
        "gap_overclaiming",
        "tone_drift",
        "dual_control_coordination",
    }

    if source_mode == "trace_derived":
        return RouteDecision(
            task_id=task_key,
            route="trace_preserving_rewrite",
            generator_tier="eval",
            judge_tier="eval",
            pairwise_required=False,
            calibration_sample=False,
            rationale="trace-derived tasks preserve a specific Week 10 failure and should use the higher-fidelity route.",
        )

    if source_mode == "multi_llm_synthesis":
        generator_tier = "eval" if calibration_sample else "cheap"
        route = "synthesis_calibration_sample" if calibration_sample else "cheap_synthesis_batch"
        rationale = (
            "multi-LLM synthesis defaults to the cheap generator tier; a seeded calibration sample is escalated to eval-tier generation for quality checks."
            if calibration_sample
            else "multi-LLM synthesis uses the cheap generator tier by default and relies on eval-tier judging plus pairwise filtering."
        )
        return RouteDecision(
            task_id=task_key,
            route=route,
            generator_tier=generator_tier,
            judge_tier="eval",
            pairwise_required=True,
            calibration_sample=calibration_sample,
            rationale=rationale,
        )

    if failure_category in nuanced_categories or "subtle" in notes.lower():
        return RouteDecision(
            task_id=task_key,
            route="nuanced_business_framing",
            generator_tier="eval",
            judge_tier="eval",
            pairwise_required=True,
            calibration_sample=False,
            rationale="framing-sensitive categories need a stronger generator and pairwise tie-break support.",
        )

    return RouteDecision(
        task_id=task_key,
        route="cheap_paraphrase_expansion",
        generator_tier="cheap",
        judge_tier="eval",
        pairwise_required=True,
        calibration_sample=False,
        rationale="controlled variants can start with the cheaper route but still require eval-tier judging.",
    )


def route_summary(tasks: list[dict[str, Any]], *, seed: int = 20260429, calibration_sample_rate: float = 0.10) -> dict[str, Any]:
    rng = random.Random(seed)
    decisions = [route_task(task, rng=rng, calibration_sample_rate=calibration_sample_rate) for task in tasks]
    summary = {
        "cheap_generator_count": sum(1 for d in decisions if d.generator_tier == "cheap"),
        "eval_generator_count": sum(1 for d in decisions if d.generator_tier == "eval"),
        "pairwise_required_count": sum(1 for d in decisions if d.pairwise_required),
        "calibration_sample_count": sum(1 for d in decisions if d.calibration_sample),
    }
    return {
        "routing_policy_path": str(ROOT / "routing_policy.md"),
        "seed": seed,
        "calibration_sample_rate": calibration_sample_rate,
        "summary": summary,
        "decisions": [asdict(decision) for decision in decisions],
        "note": (
            "Route decisions are consumed by scale_source_pool.py (synthesis) and build_dataset.py (judge-filter)."
            " Pass --synthesize to scale_source_pool.py or set OPENROUTER_API_KEY to enable live LLM calls."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Interim multi-LLM routing scaffold.")
    parser.add_argument("task_file", help="JSONL task file to route")
    parser.add_argument("--seed", type=int, default=20260429, help="Seed for deterministic routing and calibration sampling.")
    parser.add_argument(
        "--calibration-sample-rate",
        type=float,
        default=0.10,
        help="Fraction of multi_llm_synthesis tasks escalated to eval-tier generation.",
    )
    args = parser.parse_args()

    task_path = Path(args.task_file).resolve()
    tasks = load_jsonl(task_path)
    payload = {
        "task_file": str(task_path),
        **route_summary(tasks, seed=args.seed, calibration_sample_rate=args.calibration_sample_rate),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
