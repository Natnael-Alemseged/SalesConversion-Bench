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
        probe_ids = tuple(row.get("metadata", {}).get("week10_probe_ids", []))
        family_key = "|".join(probe_ids) if probe_ids else row["source_mode"]
        families[family_key].append(row)

    family_items = list(families.items())
    rng.shuffle(family_items)

    total = len(rows)
    train_n = round(total * 0.5)
    dev_n = round(total * 0.3)
    held_n = total - train_n - dev_n
    targets = {"train": train_n, "dev": dev_n, "held_out": held_n}
    partitions = {"train": [], "dev": [], "held_out": []}

    def remaining(name: str) -> int:
        return targets[name] - len(partitions[name])

    for _, family_rows in family_items:
        candidates = sorted(targets, key=lambda name: (remaining(name) < len(family_rows), -remaining(name)))
        chosen = candidates[0]
        partitions[chosen].extend(family_rows)

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
        "models_called_for_interim_batch": [],
        "notes": [
            "Interim batch uses trace-derived, programmatic, and hand-authored tasks.",
            "Multi-LLM synthesis and judge-filter logs are deferred for the final benchmark build.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
