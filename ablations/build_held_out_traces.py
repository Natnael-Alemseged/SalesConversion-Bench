#!/usr/bin/env python3
"""Build ablations/held_out_traces.jsonl from comparable baseline + trained outputs.

One JSON line per held-out task:
- raw deterministic pass/fail on candidate_output
- deterministic preference success against ground_truth_output
- trained preference success
- category, margin, latency
"""

from __future__ import annotations

import copy
import json
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
    held = ROOT / "tenacious_bench_v0.2" / "held_out" / "tasks.jsonl"
    margins_path = ROOT / "ablations" / "held_out_preference_margins.jsonl"
    out_path = ROOT / "ablations" / "held_out_traces.jsonl"

    tasks = {
        json.loads(line)["task_id"]: json.loads(line)
        for line in held.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    margin_lines = [line for line in margins_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    rows = []
    for line in margin_lines:
        margin = json.loads(line)
        tid = margin["task_id"]
        task = tasks[tid]
        raw_baseline_ok = score_task(task)["score"] == 1.0
        deterministic_pref_ok = deterministic_preference_success(task)
        trained_ok = bool(margin.get("prefers_reference") or margin.get("same_text"))
        rows.append(
            {
                "task_id": tid,
                "failure_category": margin.get("failure_category"),
                "baseline_all_checks_pass": raw_baseline_ok,
                "baseline_preference_success": deterministic_pref_ok,
                "trained_preference_success": trained_ok,
                "prefers_reference": margin.get("prefers_reference"),
                "same_text": margin.get("same_text"),
                "preference_margin": margin.get("preference_margin"),
                "latency_ms": margin.get("latency_ms"),
                "evidence_source": "ablations/held_out_preference_margins.jsonl",
            }
        )

    out_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
