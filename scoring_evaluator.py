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


def _candidate_text(task: dict[str, Any]) -> str:
    candidate = task.get("candidate_output", {})
    subject = str(candidate.get("subject", ""))
    body = str(candidate.get("body", ""))
    return f"{subject}\n{body}".strip()


def _subject(task: dict[str, Any]) -> str:
    return str(task.get("candidate_output", {}).get("subject", ""))


def _body(task: dict[str, Any]) -> str:
    return str(task.get("candidate_output", {}).get("body", ""))


def banned_phrase_check(task: dict[str, Any]) -> CheckResult:
    text = _candidate_text(task)
    hits = []
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
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
    signal_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9$]+", signal_line)
        if len(token) >= 4 or any(ch.isdigit() for ch in token)
    ]
    matched = [token for token in signal_tokens if token in body.lower()]
    passed = len(set(matched)) >= 2
    return CheckResult(
        name="signal_grounding_check",
        passed=passed,
        detail=(
            f"matched grounded tokens: {sorted(set(matched))[:8]}"
            if passed
            else "candidate does not reference enough signal-specific content"
        ),
    )


def booking_stage_check(task: dict[str, Any]) -> CheckResult:
    stage = str(task.get("input", {}).get("thread_stage", "")).strip()
    body = _body(task).lower()
    has_booking_cta = any(hint in body for hint in BOOKING_HINTS)
    allowed = stage == "ready_to_schedule"
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
        verdict = check_capacity(
            bench,
            stack=str(request["stack"]),
            requested_count=int(request["requested_count"]),
            seniority=request.get("seniority"),
            lead_days=request.get("lead_days"),
        )
        if not verdict["feasible"] and affirmative:
            failures.append(verdict["reason"])
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
def llm_judge_hook(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "implemented": False,
        "reason": "Act I stub only; learned critic is planned for Act III/IV.",
        "task_id": task.get("task_id"),
    }


def score_task(task: dict[str, Any]) -> dict[str, Any]:
    requested_checks = (
        task.get("rubric", {}).get("deterministic_checks", [])
        if isinstance(task.get("rubric"), dict)
        else []
    )
    results = []
    for check_name in requested_checks:
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
        "checks": [
            {"name": result.name, "passed": result.passed, "detail": result.detail}
            for result in results
        ],
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
        payload = json.loads(Path(args.task_file).read_text(encoding="utf-8"))
        tasks = payload if isinstance(payload, list) else [payload]
    else:
        tasks = load_examples(schema_path)

    results = [score_task(task) for task in tasks]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
