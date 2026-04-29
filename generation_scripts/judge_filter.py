"""Judge-filter pipeline for Tenacious-Bench candidate tasks.

Responsibilities
----------------
1. Enforce the multi-LLM rotation policy: generator model family must differ from
   judge model family.  Raises ValueError at startup if the same family is used for
   both roles — this is the preference-leakage prevention required by routing_policy.md.

2. Score each candidate task on three quality dimensions (coherence, verifiability,
   rubric_clarity) using the pointwise judge prompt.

3. Write accepted tasks to an output JSONL and all per-task decisions to an audit log.

Live vs. stub mode
------------------
When OPENROUTER_API_KEY is set and --judge-model is passed, this script makes real
httpx POST calls to https://openrouter.ai/api/v1/chat/completions.

When the key is absent or --dry-run is passed, the script falls back to the
deterministic heuristic scorer already implemented below.  The audit log records
which mode was used for every run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
POINTWISE_PROMPT_PATH = ROOT / "judge_prompts" / "pointwise_judge.md"
PAIRWISE_PROMPT_PATH = ROOT / "judge_prompts" / "pairwise_tiebreak.md"

# ---------------------------------------------------------------------------
# Multi-LLM rotation config
# ---------------------------------------------------------------------------
# Maps model identifiers (as used on OpenRouter) to {family, tier}.
# generator_family must differ from judge_family — see assert_rotation_policy().
ROUTING_CONFIG: dict[str, dict[str, str]] = {
    # cheap generator tier
    "mistralai/mistral-7b-instruct": {"family": "mistral", "tier": "cheap"},
    "mistralai/mixtral-8x7b-instruct": {"family": "mistral", "tier": "cheap"},
    "google/gemma-7b-it": {"family": "gemma", "tier": "cheap"},
    # eval/judge tier
    "anthropic/claude-3-haiku": {"family": "claude", "tier": "eval"},
    "anthropic/claude-3-sonnet": {"family": "claude", "tier": "eval"},
    "anthropic/claude-3-opus": {"family": "claude", "tier": "eval"},
    "openai/gpt-4o-mini": {"family": "openai", "tier": "eval"},
    "openai/gpt-4o": {"family": "openai", "tier": "eval"},
    "qwen/qwen3-8b-instruct": {"family": "qwen", "tier": "cheap"},
    "qwen/qwen3-72b-instruct": {"family": "qwen", "tier": "eval"},
    "meta-llama/llama-3-8b-instruct": {"family": "llama", "tier": "cheap"},
    "meta-llama/llama-3-70b-instruct": {"family": "llama", "tier": "eval"},
}

ACCEPT_THRESHOLD = 3  # minimum score on every dimension to accept a task


def _model_family(model_id: str) -> str:
    entry = ROUTING_CONFIG.get(model_id)
    if entry:
        return entry["family"]
    # best-effort fallback: use the provider prefix before "/"
    return model_id.split("/")[0].lower() if "/" in model_id else model_id.lower()


def assert_rotation_policy(generator_model: str, judge_model: str) -> None:
    """Raise ValueError if generator and judge share the same model family.

    This enforces preference-leakage prevention: a model should not judge its
    own outputs.
    """
    gen_family = _model_family(generator_model)
    judge_family = _model_family(judge_model)
    if gen_family == judge_family:
        raise ValueError(
            f"Rotation policy violation: generator '{generator_model}' and judge '{judge_model}' are in the same model family ('{gen_family}'). Choose a judge from a different provider family."
        )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _candidate_text(task: dict[str, Any]) -> str:
    candidate = task.get("candidate_output")
    if not isinstance(candidate, dict):
        return ""
    subject = str(candidate.get("subject", "") or "")
    body = str(candidate.get("body", "") or "")
    return f"{subject}\n{body}".strip()


def _token_set(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]+", text)}


# ---------------------------------------------------------------------------
# Deterministic heuristic scorer (fallback when no live LLM call is made)
# ---------------------------------------------------------------------------


def _heuristic_pointwise(task: dict[str, Any]) -> dict[str, Any]:
    text = _candidate_text(task)
    rubric = task.get("rubric", {}) if isinstance(task.get("rubric"), dict) else {}
    checks = rubric.get("deterministic_checks", [])
    signal_line = str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "") or "") if isinstance(task.get("input"), dict) else ""

    coherence = 5 if text and len(text.split()) >= 8 else 1
    if coherence == 5 and not rubric:
        coherence = 3

    verifiability = 5 if signal_line or checks else 1
    if verifiability == 5 and not checks:
        verifiability = 3

    rubric_clarity = 5 if isinstance(checks, list) and checks else 1
    if rubric_clarity == 5 and not rubric.get("notes"):
        rubric_clarity = 3

    minimum = min(coherence, verifiability, rubric_clarity)
    decision = "accept" if minimum >= ACCEPT_THRESHOLD else "reject"

    return {
        "task_id": task.get("task_id"),
        "coherence": coherence,
        "verifiability": verifiability,
        "rubric_clarity": rubric_clarity,
        "decision": decision,
        "mode": "heuristic",
        "reason": ("passes interim pointwise thresholds" if decision == "accept" else "fails one or more minimum quality dimensions"),
    }


# ---------------------------------------------------------------------------
# Live LLM call via OpenRouter
# ---------------------------------------------------------------------------


def call_pointwise_judge(
    task: dict[str, Any],
    judge_model: str,
    api_key: str,
) -> dict[str, Any]:
    """POST to OpenRouter and parse the structured JSON response.

    Falls back to the heuristic scorer if the response cannot be parsed.
    """
    try:
        import httpx
    except ImportError:
        print(
            "httpx is not installed; falling back to heuristic scorer. Run: pip install httpx",
            file=sys.stderr,
        )
        result = _heuristic_pointwise(task)
        result["mode"] = "heuristic_fallback_no_httpx"
        return result

    prompt_template = POINTWISE_PROMPT_PATH.read_text(encoding="utf-8")
    task_json = json.dumps(task, ensure_ascii=False, indent=2)
    user_message = f"{prompt_template}\n\n## Task\n\n```json\n{task_json}\n```"

    payload = {
        "model": judge_model,
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.0,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tenacious-intelligence/SalesConversion-Bench",
        "X-Title": "Tenacious-Bench judge-filter",
    }

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        # Extract JSON block from fenced code block or bare JSON
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        raw_json = match.group(1) if match else content.strip()
        parsed = json.loads(raw_json)
        # Normalise to expected keys
        result: dict[str, Any] = {
            "task_id": task.get("task_id"),
            "coherence": int(parsed.get("coherence", 1)),
            "verifiability": int(parsed.get("verifiability", 1)),
            "rubric_clarity": int(parsed.get("rubric_clarity", 1)),
            "mode": "live_llm",
            "judge_model": judge_model,
        }
        minimum = min(result["coherence"], result["verifiability"], result["rubric_clarity"])
        result["decision"] = "accept" if minimum >= ACCEPT_THRESHOLD else "reject"
        result["reason"] = str(parsed.get("reason", ""))
        return result
    except Exception as exc:  # noqa: BLE001
        fallback = _heuristic_pointwise(task)
        fallback["mode"] = f"heuristic_fallback_api_error:{type(exc).__name__}"
        fallback["judge_model"] = judge_model
        return fallback


# ---------------------------------------------------------------------------
# Filter pipeline
# ---------------------------------------------------------------------------


def filter_task_pool(
    tasks: list[dict[str, Any]],
    judge_model: str | None,
    api_key: str | None,
    output_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    """Score every task, write accepted tasks to output_path, all decisions to audit_path."""
    decisions: list[dict[str, Any]] = []

    for task in tasks:
        if judge_model and api_key:
            decision = call_pointwise_judge(task, judge_model, api_key)
        else:
            decision = _heuristic_pointwise(task)

        decisions.append(decision)

    accepted = [task for task, d in zip(tasks, decisions, strict=True) if d["decision"] == "accept"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for task in accepted:
            fh.write(json.dumps(task, ensure_ascii=False) + "\n")

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as fh:
        for d in decisions:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    return {
        "total": len(tasks),
        "accepted": len(accepted),
        "rejected": len(tasks) - len(accepted),
        "output_path": str(output_path),
        "audit_path": str(audit_path),
    }


# ---------------------------------------------------------------------------
# Pairwise tie-break (unchanged from original scaffold)
# ---------------------------------------------------------------------------


def _pairwise_compare(candidate_a: dict[str, Any], candidate_b: dict[str, Any]) -> dict[str, Any]:
    score_a = _heuristic_pointwise(candidate_a)
    score_b = _heuristic_pointwise(candidate_b)
    total_a = score_a["coherence"] + score_a["verifiability"] + score_a["rubric_clarity"]
    total_b = score_b["coherence"] + score_b["verifiability"] + score_b["rubric_clarity"]

    if total_a > total_b:
        winner = "A"
    elif total_b > total_a:
        winner = "B"
    else:
        len_a = len(_candidate_text(candidate_a))
        len_b = len(_candidate_text(candidate_b))
        winner = "A" if len_a <= len_b else "B"

    return {
        "winner": winner,
        "reason": "higher pointwise total; shorter candidate as deterministic tie-break",
        "candidate_a_task_id": candidate_a.get("task_id"),
        "candidate_b_task_id": candidate_b.get("task_id"),
    }


def _near_duplicate_pairs(tasks: list[dict[str, Any]], threshold: float) -> list[tuple[int, int, float]]:
    pairs: list[tuple[int, int, float]] = []
    for i, left in enumerate(tasks):
        left_tokens = _token_set(_candidate_text(left))
        if not left_tokens:
            continue
        for j in range(i + 1, len(tasks)):
            right_tokens = _token_set(_candidate_text(tasks[j]))
            if not right_tokens:
                continue
            overlap = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
            if overlap >= threshold:
                pairs.append((i, j, round(overlap, 4)))
    return pairs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter benchmark candidates through the pointwise judge pipeline.")
    parser.add_argument("--input", required=True, help="JSONL task file to filter")
    parser.add_argument(
        "--generator-model",
        default="",
        help="Model ID used to generate candidate outputs (for rotation check)",
    )
    parser.add_argument(
        "--judge-model",
        default="",
        help="OpenRouter model ID to use for live LLM judging",
    )
    parser.add_argument(
        "--output",
        default="generation_scripts/judge_filter_accepted.jsonl",
        help="Path to write accepted tasks",
    )
    parser.add_argument(
        "--audit-log",
        default="generation_scripts/judge_filter_audit.jsonl",
        help="Path to write per-task decision audit log",
    )
    parser.add_argument(
        "--near-duplicate-threshold",
        type=float,
        default=0.8,
        help="Jaccard overlap threshold for pairwise tie-break routing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use heuristic scorer even if OPENROUTER_API_KEY is set",
    )
    args = parser.parse_args()

    generator_model = args.generator_model.strip()
    judge_model = args.judge_model.strip()

    # Rotation policy check — only enforced when both models are named
    if generator_model and judge_model:
        try:
            assert_rotation_policy(generator_model, judge_model)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    api_key: str | None = None
    if judge_model and not args.dry_run:
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip() or None
        if not api_key:
            print(
                "WARNING: --judge-model set but OPENROUTER_API_KEY not found. Falling back to heuristic scorer.",
                file=sys.stderr,
            )

    task_path = Path(args.input).resolve()
    tasks = load_jsonl(task_path)

    output_path = Path(args.output).resolve()
    audit_path = Path(args.audit_log).resolve()

    summary = filter_task_pool(tasks, judge_model or None, api_key, output_path, audit_path)

    # Pairwise tie-break report for near-duplicates
    pairs = []
    for left_idx, right_idx, overlap in _near_duplicate_pairs(tasks, args.near_duplicate_threshold):
        result = _pairwise_compare(tasks[left_idx], tasks[right_idx])
        result["overlap"] = overlap
        pairs.append(result)

    payload = {
        "task_file": str(task_path),
        "generator_model": generator_model or None,
        "judge_model": judge_model or None,
        "dry_run": args.dry_run,
        "rotation_policy_enforced": bool(generator_model and judge_model),
        "pointwise_prompt_path": str(POINTWISE_PROMPT_PATH),
        "pairwise_prompt_path": str(PAIRWISE_PROMPT_PATH),
        "routing_policy_path": str(ROOT / "routing_policy.md"),
        "filter_summary": summary,
        "pairwise_tiebreak_results": pairs,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
