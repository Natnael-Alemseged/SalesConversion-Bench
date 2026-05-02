#!/usr/bin/env python3
"""Shared dispatcher for Tenacious-Bench ablation runs."""

from __future__ import annotations

import argparse
import copy
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

ABLATIONS_DIR = ROOT / "ablations"
HELD_OUT_TASKS = ROOT / "tenacious_bench_v0.2" / "held_out" / "tasks.jsonl"
TRAINED_MARGINS = ABLATIONS_DIR / "held_out_preference_margins.jsonl"
PROMPT_BASELINE_MARGINS = ABLATIONS_DIR / "held_out_prompt_baseline_margins.jsonl"
ABLATION_RESULTS = ABLATIONS_DIR / "ablation_results.json"


def require_files(paths: list[Path]) -> bool:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print("ERROR: missing required input file(s):", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return False
    return True


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def deterministic_preference_success(task: dict) -> bool:
    reference = task.get("ground_truth_output") or {}
    candidate = task.get("candidate_output") or {}
    if reference == candidate:
        return True

    candidate_score = score_task(task)["score"]
    reference_task = copy.deepcopy(task)
    reference_task["candidate_output"] = reference
    reference_score = score_task(reference_task)["score"]
    return reference_score > candidate_score


def paired_bootstrap(task_success_pairs: list[tuple[int, int]], bootstrap: int, seed: int) -> tuple[float, float, float, float]:
    random.seed(seed)
    n = len(task_success_pairs)
    observed = sum(right - left for left, right in task_success_pairs) / n

    means: list[float] = []
    for _ in range(bootstrap):
        idx = [random.randrange(n) for _ in range(n)]
        means.append(sum(task_success_pairs[i][1] - task_success_pairs[i][0] for i in idx) / n)
    means.sort()

    lo = means[int(0.025 * bootstrap)]
    hi = means[int(0.975 * bootstrap)]
    p_one_sided = sum(1 for mean in means if mean <= 0) / bootstrap
    return observed, lo, hi, p_one_sided


def run_delta_a(seed: int, bootstrap: int) -> int:
    if not require_files([HELD_OUT_TASKS, TRAINED_MARGINS]):
        return 1
    command = [
        sys.executable,
        str(ABLATIONS_DIR / "paired_bootstrap_delta_a.py"),
        "--seed",
        str(seed),
        "--bootstrap",
        str(bootstrap),
    ]
    completed = subprocess.run(command, cwd=str(ROOT), check=False)
    return completed.returncode


def run_delta_b(seed: int, bootstrap: int) -> int:
    if not require_files([HELD_OUT_TASKS, TRAINED_MARGINS, PROMPT_BASELINE_MARGINS]):
        return 1

    tasks = load_jsonl(HELD_OUT_TASKS)
    trained = {row["task_id"]: row for row in load_jsonl(TRAINED_MARGINS)}
    baseline = {row["task_id"]: row for row in load_jsonl(PROMPT_BASELINE_MARGINS)}

    pairs: list[tuple[int, int]] = []
    for task in tasks:
        task_id = task["task_id"]
        if task_id not in baseline or task_id not in trained:
            print(f"ERROR: missing baseline or trained margin row for task_id={task_id}", file=sys.stderr)
            return 1
        baseline_success = 1 if (baseline[task_id]["prefers_reference"] or baseline[task_id]["same_text"]) else 0
        trained_success = 1 if (trained[task_id]["prefers_reference"] or trained[task_id]["same_text"]) else 0
        pairs.append((baseline_success, trained_success))

    observed, lo, hi, p_one_sided = paired_bootstrap(pairs, bootstrap, seed)
    baseline_n = sum(left for left, _ in pairs)
    trained_n = sum(right for _, right in pairs)
    improvements = sum(1 for left, right in pairs if right > left)
    reversals = sum(1 for left, right in pairs if left > right)

    print("Paired bootstrap — Delta B (trained judge vs prompt-engineered backbone baseline)")
    print("")
    print(f"Command: python3 ablations/run_ablations.py --delta B --seed {seed} --bootstrap {bootstrap}")
    print("")
    print(f"n held-out tasks:     {len(pairs)}")
    print(f"baseline_success:     {baseline_n}")
    print(f"trained_success:      {trained_n}")
    print(f"paired improvements:  {trained_n - baseline_n} tasks (baseline fail → trained success: {improvements}; reverse: {reversals})")
    print("")
    print(f"point estimate (mean paired lift): {observed:.6f}")
    print(f"95% bootstrap CI (percentile):      [{lo:.6f}, {hi:.6f}]")
    print(f"p-value (one-sided, P(mean_bootstrap <= 0)): {p_one_sided:.6f}")
    print("")
    print("Source rows: ablations/held_out_prompt_baseline_margins.jsonl + ablations/held_out_preference_margins.jsonl")
    return 0


def run_delta_c() -> int:
    if not require_files([ABLATION_RESULTS]):
        return 1
    results = load_json(ABLATION_RESULTS)
    delta_c = results.get("delta_c", {})
    print("Delta C — informational τ²-Bench reference")
    print("")
    print(delta_c.get("description", "No description found."))
    print(f"Informational only: {delta_c.get('informational_only', True)}")
    print(f"Comparison scope: {delta_c.get('comparison_scope', 'n/a')}")
    print(f"External method pass@1: {delta_c.get('external_method_pass_at_1', 'n/a')}")
    print(f"Published reference pass@1: {delta_c.get('published_reference_pass_at_1', 'n/a')}")
    print(f"Delta: {delta_c.get('delta', 'n/a')}")
    print("Note: this value is imported from ablation_results.json for context and is not directly re-run from this repo.")
    return 0


def run_pareto() -> int:
    if not require_files([ABLATION_RESULTS]):
        return 1
    results = load_json(ABLATION_RESULTS)
    pareto = results.get("cost_pareto", {})
    print("Cost and latency summary")
    print("")
    print(f"Training wall time (minutes): {pareto.get('training_wall_time_minutes', 'n/a')}")
    print(f"Inference latency p50 (ms): {pareto.get('inference_latency_ms_p50', 'n/a')}")
    print(f"Adapter size: {pareto.get('adapter_size_mb', 'n/a')}")
    print(f"Colab cost (USD): {pareto.get('colab_cost_usd', 'n/a')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tenacious-Bench ablations from a shared dispatcher.")
    parser.add_argument("--delta", required=True, choices=["A", "B", "C", "pareto", "all"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=50_000)
    args = parser.parse_args()

    actions = {
        "A": lambda: run_delta_a(args.seed, args.bootstrap),
        "B": lambda: run_delta_b(args.seed, args.bootstrap),
        "C": run_delta_c,
        "pareto": run_pareto,
    }

    if args.delta == "all":
        for name in ["A", "B", "C", "pareto"]:
            print(f"=== {name} ===")
            rc = actions[name]()
            if rc != 0:
                return rc
            print("")
        return 0

    return actions[args.delta]()


if __name__ == "__main__":
    raise SystemExit(main())
