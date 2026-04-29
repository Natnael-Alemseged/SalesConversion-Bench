from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _candidate_text(task: dict[str, Any]) -> str:
    candidate = task.get("candidate_output")
    if not isinstance(candidate, dict):
        return ""
    subject = str(candidate.get("subject", "") or "")
    body = str(candidate.get("body", "") or "")
    return f"{subject}\n{body}".strip()


def _token_set(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]+", text)}


def jaccard_similarity(a: str, b: str) -> float:
    left = _token_set(a)
    right = _token_set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


@dataclass(frozen=True)
class NearDuplicatePair:
    left_index: int
    right_index: int
    overlap: float


def near_duplicate_pairs(tasks: list[dict[str, Any]], *, threshold: float) -> list[NearDuplicatePair]:
    pairs: list[NearDuplicatePair] = []
    for i, left in enumerate(tasks):
        left_text = _candidate_text(left)
        if not left_text:
            continue
        for j in range(i + 1, len(tasks)):
            right_text = _candidate_text(tasks[j])
            if not right_text:
                continue
            overlap = jaccard_similarity(left_text, right_text)
            if overlap >= threshold:
                pairs.append(NearDuplicatePair(left_index=i, right_index=j, overlap=round(overlap, 4)))
    return pairs
