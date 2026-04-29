from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "generation_scripts" / "schema_validation_report.json"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path")
    parser.add_argument("--schema", default=str(ROOT / "schema.json"))
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    rows = load_jsonl(Path(args.jsonl_path))

    errors: list[dict] = []
    for index, row in enumerate(rows):
        row_errors = sorted(validator.iter_errors(row), key=lambda err: err.path)
        for error in row_errors[:10]:
            errors.append(
                {
                    "index": index,
                    "task_id": row.get("task_id"),
                    "path": list(error.path),
                    "message": error.message,
                }
            )

    report = {
        "input_path": str(Path(args.jsonl_path)),
        "schema_path": str(Path(args.schema)),
        "record_count": len(rows),
        "invalid_record_count": len({entry["index"] for entry in errors}),
        "valid": not errors,
        "errors": errors[:50],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
