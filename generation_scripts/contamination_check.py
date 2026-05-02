from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "contamination_check.v0.2.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
NGRAM_N = 8
EMBEDDING_THRESHOLD = 0.85
MIN_TIME_SHIFT_DAYS = 7


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def input_text(task: dict[str, Any]) -> str:
    signal = task.get("input", {}).get("signal_brief", {}).get("signal_line", "")
    prior = " ".join(item.get("content", "") for item in task.get("input", {}).get("prior_thread", []))
    return f"{signal} {prior}".strip().lower()


def ngrams(text: str, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    tokens = [tok for tok in text.split() if tok]
    return {tuple(tokens[i : i + n]) for i in range(max(len(tokens) - n + 1, 0))}


def cosine_from_counter(a: Counter[str], b: Counter[str]) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def token_counter(text: str) -> Counter[str]:
    return Counter(tok for tok in re.findall(r"[A-Za-z0-9]+", text))


def _load_embedding_model() -> tuple[Any | None, str]:
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        return SentenceTransformer(EMBEDDING_MODEL), "sentence_transformers"
    except Exception:  # noqa: BLE001
        return None, "lexical_fallback"


def _embedding_cosine(model: Any | None, texts_a: list[str], texts_b: list[str]) -> list[float]:
    if model is None:
        return [cosine_from_counter(token_counter(a), token_counter(b)) for a, b in zip(texts_a, texts_b, strict=False)]

    import numpy as np  # noqa: PLC0415

    all_texts = texts_a + texts_b
    embs = model.encode(all_texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True)
    split = len(texts_a)
    embs_a, embs_b = embs[:split], embs[split:]
    norms_a = np.linalg.norm(embs_a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(embs_b, axis=1, keepdims=True)
    sims = np.sum(embs_a * embs_b, axis=1) / (norms_a.squeeze() * norms_b.squeeze() + 1e-10)
    return sims.tolist()


def parse_iso_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def task_family(task: dict[str, Any]) -> str:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    scaled_from = str(metadata.get("scaled_from_task_id", "") or "")
    if scaled_from:
        return f"seed::{scaled_from}"
    probe_ids = metadata.get("week10_probe_ids", [])
    if isinstance(probe_ids, list) and probe_ids:
        return "probe::" + "|".join(sorted(str(item) for item in probe_ids))
    failure_category = str(metadata.get("failure_category", "") or "")
    source_mode = str(metadata.get("source_mode", task.get("source_mode", "")) or "")
    return f"fallback::{failure_category}::{source_mode}"


def task_has_public_signal(task: dict[str, Any]) -> bool:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    return bool(metadata.get("signal_source") or metadata.get("signal_date"))


def nearest_overlap(task: dict[str, Any], others: list[dict[str, Any]]) -> dict[str, Any]:
    held_ngrams = ngrams(input_text(task), NGRAM_N)
    max_overlap = 0
    max_pair_id: str | None = None
    for other in others:
        overlap = len(held_ngrams & ngrams(input_text(other), NGRAM_N))
        if overlap > max_overlap:
            max_overlap = overlap
            max_pair_id = str(other.get("task_id"))
    return {
        "task_id": task["task_id"],
        "max_8gram_overlap_count": max_overlap,
        "passes_less_than_8gram_rule": max_overlap == 0,
        "nearest_overlap_task_id": max_pair_id,
    }


def nearest_embedding(task: dict[str, Any], others: list[dict[str, Any]], model: Any | None) -> dict[str, Any]:
    held_text = input_text(task)
    other_texts = [input_text(other) for other in others]
    repeated = [held_text] * len(other_texts)
    sims = _embedding_cosine(model, repeated, other_texts)
    best_idx = int(max(range(len(sims)), key=lambda idx: sims[idx]))
    best_score = sims[best_idx]
    nearest = others[best_idx]
    return {
        "task_id": task["task_id"],
        "max_cosine_similarity": round(best_score, 4),
        "passes_below_0_85_rule": best_score < EMBEDDING_THRESHOLD,
        "nearest_neighbor_task_id": nearest["task_id"],
        "nearest_neighbor_family": task_family(nearest),
        "same_family_as_neighbor": task_family(task) == task_family(nearest),
    }


def time_shift_check(task: dict[str, Any], others: list[dict[str, Any]], partition_name: str) -> dict[str, Any]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    signal_date = parse_iso_date(str(metadata.get("signal_date", "") or ""))
    signal_source = str(metadata.get("signal_source", "") or "")
    family = task_family(task)
    family_matches = [other for other in others if task_family(other) == family]
    nearest_family_task_id = None
    min_gap_days = None
    passes_gap_rule = True

    if family_matches and signal_date is not None:
        gaps: list[int] = []
        for other in family_matches:
            other_meta = other.get("metadata", {}) if isinstance(other.get("metadata"), dict) else {}
            other_date = parse_iso_date(str(other_meta.get("signal_date", "") or ""))
            if other_date is None:
                continue
            gaps.append((signal_date - other_date).days)
        if gaps:
            min_gap_days = min(gaps)
            nearest_family_task_id = family_matches[gaps.index(min_gap_days)]["task_id"]
            passes_gap_rule = min_gap_days >= MIN_TIME_SHIFT_DAYS

    return {
        "task_id": task["task_id"],
        "comparison_partition": partition_name,
        "has_public_signal": task_has_public_signal(task),
        "has_signal_date": signal_date is not None,
        "has_signal_source": bool(signal_source),
        "family_key": family,
        "family_match_count": len(family_matches),
        "nearest_family_task_id": nearest_family_task_id,
        "minimum_family_gap_days": min_gap_days,
        "passes_minimum_family_gap_days_rule": passes_gap_rule if family_matches else True,
    }


def pair_report(
    *,
    held_out: list[dict[str, Any]],
    comparison_partition: list[dict[str, Any]],
    comparison_name: str,
    model: Any | None,
) -> dict[str, Any]:
    ngram_rows = [nearest_overlap(task, comparison_partition) for task in held_out]
    embedding_rows = [nearest_embedding(task, comparison_partition, model) for task in held_out]
    time_shift_rows = [time_shift_check(task, comparison_partition, comparison_name) for task in held_out]

    ngram_failures = sum(not row["passes_less_than_8gram_rule"] for row in ngram_rows)
    embedding_failures = sum(not row["passes_below_0_85_rule"] for row in embedding_rows)
    same_family_embedding_failures = sum((not row["passes_below_0_85_rule"]) and row["same_family_as_neighbor"] for row in embedding_rows)
    time_shift_failures = sum(row["has_public_signal"] and (not row["has_signal_date"] or not row["has_signal_source"] or not row["passes_minimum_family_gap_days_rule"]) for row in time_shift_rows)

    return {
        "comparison_partition": comparison_name,
        "held_out_count": len(held_out),
        "comparison_count": len(comparison_partition),
        "n_gram_results": ngram_rows,
        "embedding_similarity_results": embedding_rows,
        "time_shift_results": time_shift_rows,
        "summary": {
            "n_gram_failures": ngram_failures,
            "embedding_failures": embedding_failures,
            "embedding_failures_same_family": same_family_embedding_failures,
            "time_shift_failures": time_shift_failures,
        },
    }


def build_report(dataset_root: Path) -> dict[str, Any]:
    train = load_jsonl(dataset_root / "train" / "tasks.jsonl")
    dev = load_jsonl(dataset_root / "dev" / "tasks.jsonl")
    held_out = load_jsonl(dataset_root / "held_out" / "tasks.jsonl")
    model, backend = _load_embedding_model()

    held_vs_train = pair_report(held_out=held_out, comparison_partition=train, comparison_name="train", model=model)
    held_vs_dev = pair_report(held_out=held_out, comparison_partition=dev, comparison_name="dev", model=model)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "embedding_model_name": EMBEDDING_MODEL,
        "embedding_backend": backend,
        "dataset_root": str(dataset_root),
        "partition_counts": {"train": len(train), "dev": len(dev), "held_out": len(held_out)},
        "thresholds": {
            "n_gram": {
                "n": NGRAM_N,
                "rule": "held_out must remain below 8-gram overlap on input fields",
            },
            "embedding": {
                "value": EMBEDDING_THRESHOLD,
                "rule": "held_out must remain below cosine similarity 0.85 against both train and dev",
            },
            "time_shift": {
                "minimum_family_gap_days": MIN_TIME_SHIFT_DAYS,
                "rule": "held_out tasks with the same source family should be at least 7 days later than train/dev variants and retain signal_date + signal_source provenance",
            },
        },
        "pair_reports": {
            "held_out_vs_train": held_vs_train,
            "held_out_vs_dev": held_vs_dev,
        },
        "notes": [
            f"Embedding backend: {backend}. Model: {EMBEDDING_MODEL}.",
            "The report is intentionally partition-aware: held_out is compared separately against train and against dev rather than against a merged pool.",
            "High embedding similarity inside the same source family is reported as a real contamination warning, not suppressed by metadata lineage.",
            "The 8-gram and time-shift checks remain valuable because they detect exact "
            "surface overlap and provenance-window leakage even when dense embeddings "
            "are naturally high in a narrow-domain benchmark.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run contamination checks for held_out vs train and held_out vs dev.")
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
    report = build_report(dataset_root)
    Path(args.out).resolve().write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
