from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "generation_scripts" / "dedup_report.json"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def canonical_hash(row: dict) -> str:
    normalized = dict(row)
    normalized.pop("task_id", None)
    blob = json.dumps(normalized, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path")
    args = parser.parse_args()
    rows = load_jsonl(Path(args.jsonl_path))
    hashes = [canonical_hash(row) for row in rows]
    counts = Counter(hashes)
    duplicates = [digest for digest, count in counts.items() if count > 1]
    report = {
        "input_path": str(Path(args.jsonl_path)),
        "record_count": len(rows),
        "exact_duplicate_group_count": len(duplicates),
        "duplicate_hashes": duplicates,
        "embedding_near_duplicate_status": "deferred_until_sentence_transformers_available",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
