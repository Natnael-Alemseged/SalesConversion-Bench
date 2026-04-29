from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .config import PointwiseThresholds

Decision = Literal["accept", "reject"]


@dataclass(frozen=True)
class PointwiseResult:
    coherence: int
    verifiability: int
    rubric_clarity: int
    decision: Decision
    reason: str


@dataclass(frozen=True)
class PairwiseResult:
    winner: Literal["A", "B"]
    reason: str


def load_prompt(prompt_path: Path) -> str:
    return prompt_path.read_text(encoding="utf-8")


def _as_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def parse_pointwise_json(raw: str) -> PointwiseResult:
    """Parse the pointwise judge output.

    Strictness is a feature: malformed judge output defaults to rejection.
    """

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return PointwiseResult(
            coherence=1,
            verifiability=1,
            rubric_clarity=1,
            decision="reject",
            reason="malformed judge JSON",
        )

    coherence = _as_int(payload.get("coherence"))
    verifiability = _as_int(payload.get("verifiability"))
    rubric_clarity = _as_int(payload.get("rubric_clarity"))
    decision = payload.get("decision")
    reason = str(payload.get("reason", "") or "").strip() or "no reason provided"

    if coherence not in (1, 3, 5) or verifiability not in (1, 3, 5) or rubric_clarity not in (1, 3, 5):
        return PointwiseResult(
            coherence=1,
            verifiability=1,
            rubric_clarity=1,
            decision="reject",
            reason="judge output missing required 1/3/5 scores",
        )

    if decision not in ("accept", "reject"):
        decision = "reject"
        reason = "judge output missing valid decision"

    return PointwiseResult(
        coherence=coherence,
        verifiability=verifiability,
        rubric_clarity=rubric_clarity,
        decision=decision,
        reason=reason,
    )


def apply_pointwise_thresholds(result: PointwiseResult, thresholds: PointwiseThresholds) -> tuple[Decision, str]:
    """Convert pointwise scores into an accept/reject decision with explicit thresholds.

    Threshold policy (rubric requirement):
    - reject if any dimension is below its minimum
    - accept only if all are at/above minimum
    """

    failures: list[str] = []
    if result.coherence < thresholds.min_coherence:
        failures.append(f"coherence<{thresholds.min_coherence}")
    if result.verifiability < thresholds.min_verifiability:
        failures.append(f"verifiability<{thresholds.min_verifiability}")
    if result.rubric_clarity < thresholds.min_rubric_clarity:
        failures.append(f"rubric_clarity<{thresholds.min_rubric_clarity}")

    if failures:
        return "reject", "threshold_fail: " + ", ".join(failures)
    return "accept", "threshold_pass"


def parse_pairwise_json(raw: str) -> PairwiseResult:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return PairwiseResult(winner="A", reason="malformed judge JSON; default winner A")
    winner = payload.get("winner")
    reason = str(payload.get("reason", "") or "").strip() or "no reason provided"
    if winner not in ("A", "B"):
        return PairwiseResult(winner="A", reason="invalid winner; default winner A")
    return PairwiseResult(winner=winner, reason=reason)


def deterministic_pointwise_stub(task: dict[str, Any]) -> PointwiseResult:
    """Interim pointwise judge stub.

    This exists so the pipeline is runnable without external model calls, while still
    keeping the judge-filter decomposition and thresholds explicit in source.

    IMPORTANT: This is *not* intended to be the final judge. It is a placeholder
    implementation that can be replaced with live routed model calls while keeping
    the same PointwiseResult contract and audit logging.
    """

    rubric = task.get("rubric", {}) if isinstance(task.get("rubric"), dict) else {}
    checks = rubric.get("deterministic_checks", [])
    candidate = task.get("candidate_output", {}) if isinstance(task.get("candidate_output"), dict) else {}
    body = str(candidate.get("body", "") or "")
    signal_line = str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "") or "") if isinstance(task.get("input"), dict) else ""

    coherence = 5 if len(body.split()) >= 8 else 1
    verifiability = 5 if (signal_line or checks) else 1
    rubric_clarity = 5 if isinstance(checks, list) and len(checks) >= 1 else 1

    decision: Decision = "accept" if min(coherence, verifiability, rubric_clarity) >= 3 else "reject"
    reason = "stub judge: minimum dimension gate"
    return PointwiseResult(
        coherence=coherence,
        verifiability=verifiability,
        rubric_clarity=rubric_clarity,
        decision=decision,
        reason=reason,
    )
