#!/usr/bin/env python3
"""Paired bootstrap for Delta A using a comparable preference metric on both sides.

baseline_success: deterministic evaluator prefers ground_truth_output over
candidate_output, or the texts are identical
trained_success: learned judge prefers ground_truth_output over candidate_output,
or the texts are identical

Reproduce:
  uv run python ablations/paired_bootstrap_delta_a.py
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=50_000)
    args = parser.parse_args()
    random.seed(args.seed)

    held = ROOT / "tenacious_bench_v0.2" / "held_out" / "tasks.jsonl"
    margins_path = ROOT / "ablations" / "held_out_preference_margins.jsonl"

    tasks = [json.loads(line) for line in held.read_text(encoding="utf-8").splitlines() if line.strip()]
    margins = {json.loads(line)["task_id"]: json.loads(line) for line in margins_path.read_text(encoding="utf-8").splitlines() if line.strip()}

    pairs: list[tuple[int, int]] = []
    for task in tasks:
        tid = task["task_id"]
        base = 1 if deterministic_preference_success(task) else 0
        margin = margins[tid]
        trained = 1 if (margin["prefers_reference"] or margin["same_text"]) else 0
        pairs.append((base, trained))

    n = len(pairs)
    baseline_n = sum(base for base, _ in pairs)
    trained_n = sum(trained for _, trained in pairs)
    obs = sum(trained - base for base, trained in pairs) / n

    means: list[float] = []
    for _ in range(args.bootstrap):
        idx = [random.randrange(n) for _ in range(n)]
        means.append(sum(pairs[i][1] - pairs[i][0] for i in idx) / n)
    means.sort()
    lo = means[int(0.025 * args.bootstrap)]
    hi = means[int(0.975 * args.bootstrap)]
    p_one_sided = sum(1 for mean in means if mean <= 0) / args.bootstrap

    improvements = sum(1 for base, trained in pairs if trained > base)
    reversals = sum(1 for base, trained in pairs if base > trained)

    lines = [
        "Paired bootstrap — Delta A (Tenacious-Bench held-out)",
        "",
        f"Command: uv run python ablations/paired_bootstrap_delta_a.py --seed {args.seed} --bootstrap {args.bootstrap}",
        "",
        "Definitions:",
        "  baseline_success = deterministic evaluator prefers ground_truth_output over",
        "                     candidate_output OR the texts are identical",
        "  trained_success  = learned judge prefers ground_truth_output over",
        "                     candidate_output OR the texts are identical",
        "",
        f"n held-out tasks:     {n}",
        f"baseline_success:     {baseline_n}",
        f"trained_success:      {trained_n}",
        f"paired improvements:  {trained_n - baseline_n} tasks (baseline fail → trained success: {improvements}; reverse: {reversals})",
        "",
        f"point estimate (mean paired lift): {obs:.6f}",
        f"95% bootstrap CI (percentile):      [{lo:.6f}, {hi:.6f}]",
        f"p-value (one-sided, P(mean_bootstrap <= 0)): {p_one_sided:.6f}",
        "",
        "Source rows: tenacious_bench_v0.2/held_out/tasks.jsonl + ablations/held_out_preference_margins.jsonl",
        "(Do not use held_out_traces_raw.jsonl for these headline numbers.)",
        "",
    ]
    text = "\n".join(lines)
    out = ROOT / "ablations" / "significance_test.txt"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
