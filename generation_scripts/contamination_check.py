from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "contamination_check.v0.2.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def input_text(task: dict) -> str:
    signal = task.get("input", {}).get("signal_brief", {}).get("signal_line", "")
    prior = " ".join(item.get("content", "") for item in task.get("input", {}).get("prior_thread", []))
    return f"{signal} {prior}".strip().lower()


def ngrams(text: str, n: int = 8) -> set[tuple[str, ...]]:
    tokens = [tok for tok in text.split() if tok]
    return {tuple(tokens[i : i + n]) for i in range(max(len(tokens) - n + 1, 0))}


def cosine_from_counter(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def token_counter(text: str) -> Counter:
    return Counter(tok for tok in text.split() if tok)


def parse_date(raw: str) -> bool:
    if not raw:
        return False
    try:
        datetime.fromisoformat(raw)
        return True
    except ValueError:
        return False


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run contamination checks for held_out vs train/dev.")
    parser.add_argument(
        "--dataset-root",
        default=str(ROOT / "tenacious_bench_v0.2"),
        help="Dataset root containing train/dev/held_out/tasks.jsonl",
    )
    parser.add_argument(
        "--out",
        default=str(OUTPUT_PATH),
        help="Output path for contamination report JSON",
    )
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root).resolve()
    train = load_jsonl(dataset_root / "train" / "tasks.jsonl")
    dev = load_jsonl(dataset_root / "dev" / "tasks.jsonl")
    held = load_jsonl(dataset_root / "held_out" / "tasks.jsonl")

    train_dev = train + dev
    held_flags = []
    for task in held:
        held_ngrams = ngrams(input_text(task), 8)
        max_overlap = 0
        max_pair = None
        for other in train_dev:
            overlap = len(held_ngrams & ngrams(input_text(other), 8))
            if overlap > max_overlap:
                max_overlap = overlap
                max_pair = other["task_id"]
        held_flags.append(
            {
                "task_id": task["task_id"],
                "max_8gram_overlap_count": max_overlap,
                "passes_less_than_8gram_rule": max_overlap == 0,
                "nearest_overlap_task_id": max_pair,
            }
        )

    embed_rows = []
    for task in held:
        a = token_counter(input_text(task))
        best = 0.0
        best_id = None
        for other in train_dev:
            score = cosine_from_counter(a, token_counter(input_text(other)))
            if score > best:
                best = score
                best_id = other["task_id"]
        embed_rows.append(
            {
                "task_id": task["task_id"],
                "max_cosine_similarity": round(best, 4),
                "passes_below_0_85_rule": best < 0.85,
                "nearest_neighbor_task_id": best_id,
            }
        )

    time_shift_rows = []
    for partition_name, rows in {"train": train, "dev": dev, "held_out": held}.items():
        for row in rows:
            meta = row.get("metadata", {})
            signal_date = meta.get("signal_date", "")
            signal_source = meta.get("signal_source", "")
            time_shift_rows.append(
                {
                    "partition": partition_name,
                    "task_id": row["task_id"],
                    "has_signal_date": bool(signal_date),
                    "signal_date_valid_iso": parse_date(signal_date),
                    "has_signal_source": bool(signal_source),
                }
            )

    report = {
        "embedding_model_name": EMBEDDING_MODEL,
        "dataset_root": str(dataset_root),
        "partition_counts": {"train": len(train), "dev": len(dev), "held_out": len(held)},
        "n_gram_threshold": {
            "n": 8,
            "rule": "held_out must remain below 8-gram overlap on input fields",
        },
        "embedding_threshold": {
            "rule": "held_out must remain below cosine similarity 0.85",
            "value": 0.85,
        },
        "n_gram_results": held_flags,
        "embedding_similarity_results": embed_rows,
        "time_shift_verification": time_shift_rows,
        "notes": [
            "Interim embedding similarity uses a lexical cosine fallback because sentence-transformers is not installed in the current environment.",
            "Pinned target model remains sentence-transformers/all-MiniLM-L6-v2 and should replace the fallback once available.",
        ],
    }
    Path(args.out).resolve().write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
