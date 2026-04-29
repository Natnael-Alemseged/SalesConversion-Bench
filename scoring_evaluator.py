"""Tenacious-Bench deterministic scoring evaluator.

Input/output contract
---------------------
score_task(task: dict) -> dict
    task   : one JSON record conforming to schema.json
    returns: {
        "task_id": str,
        "score": float,          # proportion of requested checks that passed, in [0.0, 1.0]
        "passed": int,           # count of passing checks
        "total": int,            # count of requested checks
        "checks": list[dict],    # per-check {"name", "passed", "detail"}
        "llm_judge_hook": dict,  # Path B stub; always "not_run" until Act III
    }

Score semantics
---------------
1.0   All requested checks pass — output is policy-compliant on the tested dimensions.
0.0   All checks fail — output violates every tested dimension.
Intermediate values are proportional (e.g. 0.667 means 2/3 checks passed).

Calibration per dimension
-------------------------
Each check function carries inline 1/3/5 anchor comments.
The deterministic checks map to binary pass/fail; the 1/3/5 language also describes
how a downstream LLM judge should calibrate continuous scores on the same dimensions
(see llm_judge_hook and generation_scripts/judge_prompts/pointwise_judge.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
WEEK10_ROOT = ROOT / "week_10_data"
if str(WEEK10_ROOT) not in sys.path:
    sys.path.insert(0, str(WEEK10_ROOT))

from agent.enrichment.bench_capacity import check_capacity  # noqa: E402

BANNED_PATTERNS = [
    r"\bworld-class\b",
    r"\btop talent\b",
    r"\bA-players\b",
    r"\brockstar\b",
    r"\bninja\b",
    r"\bwizard\b",
    r"\bskyrocket\b",
    r"\bsupercharge\b",
    r"\b10x\b",
    r"\bI hope this email finds you well\b",
    r"\bjust following up\b",
    r"\bcircling back\b",
    r"\bquick question\b",
    r"\bquick chat\b",
    r"\bsynergize\b",
    r"\bsynergy\b",
    r"\bleverage\b",
    r"\becosystem\b",
    r"\bgame-changer\b",
    r"\bdisruptor\b",
    r"\bparadigm shift\b",
    r"\bdo not miss out\b",
    r"\bper my last email\b",
]
BOOKING_HINTS = ("calendar", "book", "schedule", "gettenacious.com/", "cal.com/")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def load_examples(schema_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    examples = payload.get("examples")
    if not isinstance(examples, list):
        raise ValueError("schema.json does not contain an examples array")
    return examples


def _candidate_output(task: dict[str, Any]) -> dict[str, Any]:
    candidate = task.get("candidate_output", {})
    if not isinstance(candidate, dict):
        return {}
    return candidate


def _candidate_text(task: dict[str, Any]) -> str:
    candidate = _candidate_output(task)
    subject = str(candidate.get("subject", ""))
    body = str(candidate.get("body", ""))
    return f"{subject}\n{body}".strip()


def _subject(task: dict[str, Any]) -> str:
    return str(_candidate_output(task).get("subject", ""))


def _body(task: dict[str, Any]) -> str:
    return str(_candidate_output(task).get("body", ""))


def banned_phrase_check(task: dict[str, Any]) -> CheckResult:
    text = _candidate_text(task)
    hits = []
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    # Calibration note:
    # - score 1 / fail: any banned sales-cliche pattern appears in prospect-facing copy.
    # - score 3 / pass: no banned patterns appear.
    # - score 5 / strong: the draft also sounds natural rather than merely avoiding the list.
    return CheckResult(
        name="banned_phrase_check",
        passed=not hits,
        detail="no banned phrases found" if not hits else f"matched {len(hits)} banned patterns",
    )


def signal_grounding_check(task: dict[str, Any]) -> CheckResult:
    signal_line = str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "")).strip()
    if not signal_line:
        return CheckResult(
            name="signal_grounding_check",
            passed=False,
            detail="task has no signal_line to ground against",
        )

    body = _body(task)
    signal_tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9$]+", signal_line) if len(token) >= 4 or any(ch.isdigit() for ch in token)]
    matched = [token for token in signal_tokens if token in body.lower()]
    # Calibration note:
    # - score 1 / fail: zero or one grounded token, so the draft could have been written
    #   without the task-specific evidence.
    # - score 3 / borderline: two grounded tokens, enough for an interim pass.
    # - score 5 / strong: richer grounding than this check currently measures.
    passed = len(set(matched)) >= 2
    return CheckResult(
        name="signal_grounding_check",
        passed=passed,
        detail=(f"matched grounded tokens: {sorted(set(matched))[:8]}" if passed else "candidate does not reference enough signal-specific content"),
    )


def booking_stage_check(task: dict[str, Any]) -> CheckResult:
    stage = str(task.get("input", {}).get("thread_stage", "")).strip()
    body = _body(task).lower()
    has_booking_cta = any(hint in body for hint in BOOKING_HINTS)
    allowed = stage == "ready_to_schedule"
    # Calibration note:
    # - score 1 / fail: booking CTA appears before the prospect has reached
    #   `ready_to_schedule`.
    # - score 3 / pass: no booking CTA before that stage.
    # - score 5 / strong: CTA is stage-appropriate and phrased with explicit confirmation.
    passed = (not has_booking_cta) or allowed
    if not has_booking_cta:
        detail = "no booking CTA detected"
    elif allowed:
        detail = "booking CTA allowed at ready_to_schedule stage"
    else:
        detail = f"booking CTA detected at disallowed stage={stage}"
    return CheckResult(name="booking_stage_check", passed=passed, detail=detail)


def bench_capacity_check(task: dict[str, Any]) -> CheckResult:
    bench = task.get("input", {}).get("bench_summary")
    requests = task.get("input", {}).get("capacity_request") or []
    if not bench or not requests:
        return CheckResult(
            name="bench_capacity_check",
            passed=True,
            detail="no bench_summary or capacity_request on task",
        )

    body = _body(task).lower()
    affirmative = any(
        phrase in body
        for phrase in (
            "we can",
            "we could",
            "can cover",
            "can support",
            "can deliver",
            "can start",
        )
    )
    failures = []
    for request in requests:
        try:
            stack = str(request["stack"])
            requested_count = int(request["requested_count"])
            seniority = request.get("seniority")
            lead_days = request.get("lead_days")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"malformed capacity_request entry: {exc}")
            continue

        verdict = check_capacity(
            bench,
            stack=stack,
            requested_count=requested_count,
            seniority=seniority,
            lead_days=lead_days,
        )
        if not verdict["feasible"] and affirmative:
            failures.append(verdict["reason"])
    # Calibration note:
    # - score 1 / fail: the draft affirmatively promises staffing that the reused Week 10
    #   bench checker marks infeasible.
    # - score 3 / pass: no infeasible affirmative promise appears.
    # - score 5 / strong: the draft also proactively narrows or qualifies the promise.
    passed = not failures
    return CheckResult(
        name="bench_capacity_check",
        passed=passed,
        detail="bench-compatible output" if passed else " | ".join(failures),
    )


def format_check(task: dict[str, Any]) -> CheckResult:
    subject = _subject(task)
    body = _body(task)
    body_words = re.findall(r"\S+", body)
    subject_ok = len(subject) <= 60
    body_ok = len(body_words) <= 120
    # Calibration note:
    # - score 1 / fail: subject > 60 chars or body > 120 words.
    # - score 3 / pass: both limits are met.
    # - score 5 / strong: concise while still preserving the required evidence.
    passed = subject_ok and body_ok
    detail = f"subject_len={len(subject)}, body_words={len(body_words)}"
    return CheckResult(name="format_check", passed=passed, detail=detail)


CHECKS = {
    "banned_phrase_check": banned_phrase_check,
    "signal_grounding_check": signal_grounding_check,
    "booking_stage_check": booking_stage_check,
    "bench_capacity_check": bench_capacity_check,
    "format_check": format_check,
}


# TODO: Path B integration point.
# Replace or augment deterministic checks with an LLM-based Tenacious critic
# that scores candidate_output against the same task context and returns a
# structured judgment for rejection sampling / rollback.
#
# Calibration anchors for the planned pointwise judge:
# - coherence: 1 = internally inconsistent task/draft, 3 = usable but slightly awkward,
#   5 = fully self-consistent and easy to interpret.
# - verifiability: 1 = cannot be judged from provided context, 3 = mostly checkable with
#   one soft spot, 5 = fully checkable from task fields and rubric.
# - rubric_clarity: 1 = pass/fail boundary vague, 3 = directionally clear, 5 = concrete
#   enough that another evaluator would likely agree.
def llm_judge_hook(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "implemented": False,
        "reason": "Act I stub only; learned critic is planned for Act III/IV.",
        "task_id": task.get("task_id"),
        "planned_dimensions": ["coherence", "verifiability", "rubric_clarity"],
        "prompt_path": str(ROOT / "generation_scripts" / "judge_prompts" / "pointwise_judge.md"),
    }


def score_task(task: dict[str, Any]) -> dict[str, Any]:
    candidate = _candidate_output(task)
    if "subject" not in candidate or "body" not in candidate:
        return {
            "task_id": task.get("task_id"),
            "score": 0.0,
            "passed": 0,
            "total": 0,
            "checks": [],
            "error": "candidate_output must be an object with subject and body keys",
            "llm_judge_hook": llm_judge_hook(task),
        }

    requested_checks = task.get("rubric", {}).get("deterministic_checks", []) if isinstance(task.get("rubric"), dict) else []
    results = []
    for check_name in requested_checks:
        if check_name not in CHECKS:
            results.append(
                CheckResult(
                    name=check_name,
                    passed=False,
                    detail="unknown check requested by rubric",
                )
            )
            continue
        fn = CHECKS[check_name]
        result = fn(task)
        results.append(result)

    passed = sum(1 for result in results if result.passed)
    total = len(results)
    score = (passed / total) if total else 0.0
    return {
        "task_id": task.get("task_id"),
        "score": round(score, 4),
        "passed": passed,
        "total": total,
        "checks": [{"name": result.name, "passed": result.passed, "detail": result.detail} for result in results],
        "llm_judge_hook": llm_judge_hook(task),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Act I deterministic scorer.")
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schema.json"),
        help="Path to schema.json containing examples",
    )
    parser.add_argument(
        "--task-file",
        help="Optional JSON file containing a single task or a list of tasks",
    )
    args = parser.parse_args()

    schema_path = Path(args.schema).resolve()
    if args.task_file:
        raw = Path(args.task_file).read_text(encoding="utf-8").strip()
        if raw.startswith("["):
            payload = json.loads(raw)
            tasks = payload if isinstance(payload, list) else [payload]
        elif raw.startswith("{"):
            try:
                payload = json.loads(raw)
                tasks = payload if isinstance(payload, list) else [payload]
            except json.JSONDecodeError:
                tasks = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            tasks = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        tasks = load_examples(schema_path)

    results = [score_task(task) for task in tasks]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
