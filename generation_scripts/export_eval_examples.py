from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

DEFAULT_SUBSET = [
    "tbv01-007",
    "tbv01-021",
    "tbv01-038",
    "tbv01-042",
    "tbv01-051",
    "tbv01-055",
    "tbv01-059",
    "tbv01-001",
    "tbv01-028",
    "tbv01-043",
]


def _iter_tasks_jsonl(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if not path.exists():
        return tasks
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        tasks.append(json.loads(line))
    return tasks


def _load_task_by_id(task_id: str) -> dict[str, Any] | None:
    base = ROOT / "tenacious_bench_v0.1"
    for partition in ("train", "dev", "held_out"):
        path = base / partition / "tasks.jsonl"
        for task in _iter_tasks_jsonl(path):
            if task.get("task_id") == task_id:
                return task
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Export eval_examples/*.json for the UI.")
    parser.add_argument(
        "--dataset-root",
        default=str(ROOT / "tenacious_bench_v0.1"),
        help="Dataset root containing train/dev/held_out/tasks.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "eval_examples"),
        help="Directory to write tbv*.json files",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        default=DEFAULT_SUBSET,
        help="Task IDs to export (default: 10-task interim subset)",
    )
    args = parser.parse_args()

    global _load_task_by_id  # noqa: PLW0603

    def _load_task_by_id(task_id: str) -> dict[str, Any] | None:
        base = Path(args.dataset_root).resolve()
        for partition in ("train", "dev", "held_out"):
            path = base / partition / "tasks.jsonl"
            for task in _iter_tasks_jsonl(path):
                if task.get("task_id") == task_id:
                    return task
        return None

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    written: list[str] = []
    for task_id in args.ids:
        task = _load_task_by_id(task_id)
        if task is None:
            missing.append(task_id)
            continue

        result = score_task(task)
        payload = {"task": task, "result": result}
        out_path = out_dir / f"{task_id}.json"
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        written.append(task_id)

    print(json.dumps({"written": written, "missing": missing}, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
