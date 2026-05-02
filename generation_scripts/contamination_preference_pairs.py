"""Check preference-pair tasks for input overlap with held_out (leakage guard).

Each line in training_data/preference_pairs.jsonl references a train task_id.
We compare that task's input_text (same definition as contamination_check.py)
to every held_out task using 8-gram overlap on signal + prior_thread, matching
the dynamic-eval rule in contamination_check.v0.2.json.

Usage:
  python3 generation_scripts/contamination_preference_pairs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generation_scripts.contamination_check import (  # noqa: E402
    input_text,
    load_jsonl,
    ngrams,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preference pairs vs held_out contamination")
    parser.add_argument(
        "--pairs",
        default=str(ROOT / "training_data" / "preference_pairs.jsonl"),
    )
    parser.add_argument(
        "--dataset-root",
        default=str(ROOT / "tenacious_bench_v0.2"),
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "training_data" / "contamination_preference_pairs.json"),
    )
    args = parser.parse_args()

    pairs_path = Path(args.pairs)
    dataset_root = Path(args.dataset_root)
    train = {t["task_id"]: t for t in load_jsonl(dataset_root / "train" / "tasks.jsonl")}
    held = load_jsonl(dataset_root / "held_out" / "tasks.jsonl")

    rows: list[dict] = []
    violations: list[dict] = []

    if not pairs_path.exists():
        Path(args.out).write_text(json.dumps({"error": "preference_pairs.jsonl missing"}, indent=2))
        print(json.dumps({"error": "preference_pairs.jsonl missing"}, indent=2))
        return 2

    for line in pairs_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        tid = payload.get("task_id")
        task = train.get(tid) if tid else None
        if task is None:
            violations.append({"task_id": tid, "reason": "task_id not found in train/tasks.jsonl"})
            continue

        tin = input_text(task)
        t_set = ngrams(tin, 8)
        worst = 0
        worst_hid = None
        for h in held:
            overlap = len(t_set & ngrams(input_text(h), 8))
            if overlap > worst:
                worst = overlap
                worst_hid = h.get("task_id")

        row = {
            "task_id": tid,
            "max_8gram_overlap_with_held_out": worst,
            "nearest_held_out_task_id": worst_hid,
            "passes_no_overlap_rule": worst == 0,
        }
        rows.append(row)
        if worst > 0:
            violations.append({"task_id": tid, "overlap_count": worst, "nearest_held_out_task_id": worst_hid})

    report = {
        "description": ("For each preference pair, measure max 8-gram overlap between that train task's input_text and each held_out task's input_text."),
        "pairs_checked": len(rows),
        "violation_count": len(violations),
        "violations": violations,
        "per_pair": rows,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"pairs_checked": len(rows), "violation_count": len(violations)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
