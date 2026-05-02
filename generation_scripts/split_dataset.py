from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _family_key(row: dict) -> str:
    metadata = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
    scaled_from_task_id = str(metadata.get("scaled_from_task_id", "") or "").strip()
    if scaled_from_task_id:
        return f"seed::{scaled_from_task_id}"
    probe_ids = tuple(metadata.get("week10_probe_ids", []))
    if probe_ids:
        return "|".join(str(item) for item in probe_ids)
    source_mode = row.get("source_mode") or metadata.get("source_mode") or "unknown"
    failure_category = metadata.get("failure_category") or "unknown"
    return f"{failure_category}::{source_mode}"


def _failure_category(row: dict) -> str:
    metadata = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
    return str(metadata.get("failure_category", "unknown") or "unknown")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path")
    parser.add_argument("--seed", type=int, default=20260429)
    parser.add_argument(
        "--out-root",
        default=str(ROOT / "tenacious_bench_v0.1"),
        help="Dataset root directory to write train/dev/held_out partitions",
    )
    args = parser.parse_args()

    rows = load_jsonl(Path(args.jsonl_path))
    rng = random.Random(args.seed)

    families: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        families[_family_key(row)].append(row)

    total = len(rows)
    train_n = round(total * 0.5)
    dev_n = round(total * 0.3)
    held_n = total - train_n - dev_n
    targets = {"train": train_n, "dev": dev_n, "held_out": held_n}
    partitions = {"train": [], "dev": [], "held_out": []}

    def remaining(name: str) -> int:
        return targets[name] - len(partitions[name])

    category_totals: dict[str, int] = defaultdict(int)
    families_by_category: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    for family_key, family_rows in families.items():
        category = _failure_category(family_rows[0])
        category_totals[category] += len(family_rows)
        families_by_category[category].append((family_key, family_rows))

    category_targets: dict[str, dict[str, int]] = {}
    for category, category_total in category_totals.items():
        cat_train = round(category_total * 0.5)
        cat_dev = round(category_total * 0.3)
        cat_held = category_total - cat_train - cat_dev
        category_targets[category] = {"train": cat_train, "dev": cat_dev, "held_out": cat_held}

    category_counts: dict[str, dict[str, int]] = {category: {"train": 0, "dev": 0, "held_out": 0} for category in category_targets}

    for category in sorted(families_by_category):
        family_items = families_by_category[category]
        rng.shuffle(family_items)
        for _, family_rows in family_items:
            family_size = len(family_rows)
            cat_target = category_targets[category]
            cat_count = category_counts[category]

            def sort_key(
                name: str,
                *,
                _ct: dict[str, int] = cat_target,
                _cc: dict[str, int] = cat_count,
                _fs: int = family_size,
            ) -> tuple[bool, int, int]:
                cat_remaining = _ct[name] - _cc[name]
                overall_remaining = remaining(name)
                return (cat_remaining < _fs, -cat_remaining, -overall_remaining)

            chosen = sorted(targets, key=sort_key)[0]
            partitions[chosen].extend(family_rows)
            category_counts[category][chosen] += family_size

    train = partitions["train"]
    dev = partitions["dev"]
    held = partitions["held_out"]

    dataset_root = Path(args.out_root).resolve()
    dump_jsonl(dataset_root / "train" / "tasks.jsonl", train)
    dump_jsonl(dataset_root / "dev" / "tasks.jsonl", dev)
    dump_jsonl(dataset_root / "held_out" / "tasks.jsonl", held)

    manifest_path = ROOT / "generation_scripts" / "run_manifest.json"
    manifest = {
        "seed": args.seed,
        "input_pool_path": str(Path(args.jsonl_path)),
        "output_root": str(dataset_root),
        "partition_counts": {
            "train": len(train),
            "dev": len(dev),
            "held_out": len(held),
        },
        "authoring_modes_used": sorted({row["source_mode"] for row in rows}),
        "stratification_policy": {
            "family_key": "metadata.scaled_from_task_id fallback metadata.week10_probe_ids fallback failure_category::source_mode",
            "category_key": "metadata.failure_category",
            "goal": "keep probe families intact while preserving approximate 50/30/20 proportions inside each failure category",
        },
        "models_called_for_interim_batch": [],
        "notes": [
            "Split is family-stratified and failure-category-aware.",
            "Whole probe families are assigned to a single partition to reduce lineage leakage.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
