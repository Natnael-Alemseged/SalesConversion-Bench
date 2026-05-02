from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS_PATH = ROOT / "generation_scripts" / "counts.json"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Summarize dataset counts by partition/mode/failure.")
    parser.add_argument(
        "--dataset-root",
        default=str(ROOT / "tenacious_bench_v0.2"),
        help="Dataset root containing train/dev/held_out/tasks.jsonl",
    )
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root).resolve()
    partitions = {}
    by_mode = Counter()
    by_failure = Counter()
    for name in ("train", "dev", "held_out"):
        rows = load_jsonl(dataset_root / name / "tasks.jsonl")
        partitions[name] = len(rows)
        for row in rows:
            by_mode[row["source_mode"]] += 1
            by_failure[row.get("metadata", {}).get("failure_category", "unknown")] += 1
    report = {
        "dataset_root": str(dataset_root),
        "partition_counts": partitions,
        "source_mode_counts": dict(sorted(by_mode.items())),
        "failure_category_counts": dict(sorted(by_failure.items())),
    }
    COUNTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
