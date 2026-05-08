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
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

GPT_4O_MINI_INPUT_USD_PER_1M_TOKENS = 0.15
GPT_4O_MINI_OUTPUT_USD_PER_1M_TOKENS = 0.60
CHARS_PER_TOKEN_ESTIMATE = 4


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


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + CHARS_PER_TOKEN_ESTIMATE - 1) // CHARS_PER_TOKEN_ESTIMATE)


def exact_paired_binomial_p_value(pairs: list[tuple[int, int]]) -> tuple[int, int, int, float]:
    """One-sided exact paired test over discordant binary outcomes.

    Under the null of no paired advantage, each discordant task is equally likely
    to favor either system. This is McNemar's exact/binomial test with
    alternative="trained greater than baseline".
    """
    baseline_wins = sum(1 for baseline, trained in pairs if baseline > trained)
    trained_wins = sum(1 for baseline, trained in pairs if trained > baseline)
    discordant = baseline_wins + trained_wins
    if discordant == 0:
        return baseline_wins, trained_wins, discordant, 1.0

    tail = sum(math.comb(discordant, k) for k in range(trained_wins, discordant + 1))
    return baseline_wins, trained_wins, discordant, tail / (2**discordant)


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
        signal_line = str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "") or "")
        prior_thread = json.dumps(task.get("input", {}).get("prior_thread", []), ensure_ascii=False)
        candidate_output = task.get("candidate_output") or {}
        candidate_text = f"{candidate_output.get('subject', '')}\n{candidate_output.get('body', '')}".strip()
        input_tokens = estimate_tokens(signal_line + prior_thread)
        output_tokens = estimate_tokens(candidate_text)
        task["_estimated_input_tokens"] = input_tokens
        task["_estimated_output_tokens"] = output_tokens
        task["_estimated_cost_usd"] = (input_tokens / 1_000_000) * GPT_4O_MINI_INPUT_USD_PER_1M_TOKENS + (output_tokens / 1_000_000) * GPT_4O_MINI_OUTPUT_USD_PER_1M_TOKENS
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
    baseline_wins, trained_wins, discordant, p_one_sided = exact_paired_binomial_p_value(pairs)

    total_input_tokens = sum(task.get("_estimated_input_tokens", 0) for task in tasks)
    total_output_tokens = sum(task.get("_estimated_output_tokens", 0) for task in tasks)
    total_estimated_cost = sum(task.get("_estimated_cost_usd", 0.0) for task in tasks)
    cost_per_task = total_estimated_cost / n if n else 0.0

    cost_lines = [
        "Cost-Pareto summary",
        f"  total tasks:               {n}",
        f"  total estimated input:     {total_input_tokens} tokens",
        f"  total estimated output:    {total_output_tokens} tokens",
        f"  total estimated cost:      ${total_estimated_cost:.6f} USD",
        f"  estimated cost per task:   ${cost_per_task:.6f} USD",
        "",
    ]
    print("\n".join(cost_lines))

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
        f"paired improvements:  {trained_n - baseline_n} tasks (baseline fail → trained success: {trained_wins}; reverse: {baseline_wins})",
        f"discordant pairs:     {discordant}",
        "",
        f"point estimate (mean paired lift): {obs:.6f}",
        f"95% bootstrap CI (percentile):      [{lo:.6f}, {hi:.6f}]",
        f"p-value (one-sided exact paired binomial/McNemar): {p_one_sided:.12f}",
        "Null: among discordant paired tasks, baseline and trained judge are equally likely to win.",
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
