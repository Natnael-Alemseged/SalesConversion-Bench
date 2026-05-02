#!/usr/bin/env python3
"""Estimate per-task inference token counts and costs for Delta A / Delta B conditions.

Methodology (aligned with ``tenacious_path_b_simpo_colab.ipynb`` Cell 10 — held-out eval):
  - ``build_prompt`` / ``build_user_message`` / ``email_to_text`` match the notebook verbatim.
  - Token counts use ``AutoTokenizer`` for ``unsloth/Qwen2.5-0.5B-Instruct`` (same backbone as
    ``ablations/ablation_results.json``), with the same prefix rule as ``completion_avg_logprob``:
    ``prefix = prompt.rstrip() + "\\n\\n"``, completion = email text (Subject/Body).
  - Per forward pass: **prompt tokens** = len(tokenize(prefix)); **completion tokens** =
    len(tokenize(prefix + completion)) - len(tokenize(prefix)).
  - Two passes per task (candidate + reference), same as the margin computation.

  Actual billed cost in this repo: **$0** (local Unsloth inference).

  Reference **$** columns are *not* the production model: they illustrate what similar token
  volumes would cost at public API list prices (see ``_price_anchor_*`` in the JSON output).

Output: ``inference_cost_estimate.json``

Usage:
  uv run python scripts/estimate_inference_cost.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELD_OUT = ROOT / "tenacious_bench_v0.2" / "held_out" / "tasks.jsonl"
MARGINS = ROOT / "ablations" / "held_out_preference_margins.jsonl"
OUT = ROOT / "inference_cost_estimate.json"
BACKBONE = "unsloth/Qwen2.5-0.5B-Instruct"

# OpenRouter / OpenAI gpt-4o-mini (illustrative API anchor — different model family)
PRICE_GPT4O_MINI_IN = 0.15
PRICE_GPT4O_MINI_OUT = 0.60
GPT4O_MINI_LABEL = "openai/gpt-4o-mini via OpenRouter (list price 2026-05-02)"
GPT4O_MINI_URL = "https://openrouter.ai/openai/gpt-4o-mini"

# ---------------------------------------------------------------------------
# Prompt builders — keep in sync with tenacious_path_b_simpo_colab.ipynb Cell 10
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a Tenacious Intelligence Corporation sales agent writing B2B outreach emails.

Tenacious places managed engineering teams (Python, Go, data, ML, infra) for
B2B SaaS and mid-market companies. You write direct, grounded, honest, professional,
non-condescending outreach anchored to real hiring signals.

Rules:
- Subject: under 60 characters, states intent (Request / Context / Question / Re:)
- Body: cold outreach max 120 words, warm reply max 200 words
- Every claim grounded in the supplied signal brief
- If signal confidence is medium/low, ask rather than assert
- Never commit bench capacity beyond what bench_summary shows
- Never use: world-class, top talent, A-players, rockstar, ninja, skyrocket,
  supercharge, I hope this email finds you well, just following up, circling back,
  quick question, quick chat, synergize, synergy, leverage, ecosystem,
  game-changer, disruptor, paradigm shift, do not miss out, per my last email
- Never use "bench" in prospect-facing copy; use "engineering team" or "available capacity"
- One ask per message

Respond with ONLY a JSON object: {"subject": "...", "body": "..."}
"""


def build_user_message(task: dict) -> str:
    inp = task.get("input", {})
    parts = [f"Company: {inp.get('company_name', 'Unknown')}"]
    parts.append(f"ICP segment: {inp.get('icp_segment', '?')}")
    parts.append(f"Thread stage: {inp.get('thread_stage', 'cold_first_touch')}")

    sig = inp.get("signal_brief", {})
    parts.append(f"Signal: {sig.get('signal_line', 'No signal provided')}")
    parts.append(f"Signal confidence: {sig.get('signal_confidence_tier', 'unknown')}")

    bench = inp.get("bench_summary")
    if bench:
        parts.append(f"Bench summary: {json.dumps(bench, ensure_ascii=False)}")

    cap = inp.get("capacity_request")
    if cap:
        parts.append(f"Capacity request: {json.dumps(cap, ensure_ascii=False)}")

    thread = inp.get("prior_thread")
    if thread:
        parts.append(f"Prior thread: {json.dumps(thread, ensure_ascii=False)}")

    return "\n".join(parts)


def build_prompt(task: dict) -> str:
    return f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n[CONTEXT]\n{build_user_message(task)}"


def email_to_text(email: object) -> str:
    if isinstance(email, dict):
        return f"Subject: {email.get('subject', '')}\n\n{email.get('body', '')}".strip()
    return str(email).strip()


_STUB_REF = re.compile(r"^Ref=tbv02-\d{4}\s", re.IGNORECASE)


def classify_signal_line(task: dict) -> str:
    """empty | stub | substantive — stub matches held-out placeholder pattern in memo."""
    raw = task.get("input", {}).get("signal_brief", {}).get("signal_line", "")
    s = (raw or "").strip()
    if not s:
        return "empty"
    if _STUB_REF.match(s) and len(s) < 120:
        return "stub"
    return "substantive"


def load_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(BACKBONE, trust_remote_code=True)


def pass_token_lengths(tokenizer, prompt: str, completion: str) -> tuple[int, int]:
    """Returns (prompt_token_count, completion_token_count) for one scoring pass."""
    prefix = prompt.rstrip() + "\n\n"
    comp = completion.lstrip()
    full = prefix + comp
    p_ids = tokenizer(prefix, add_special_tokens=True, truncation=False)["input_ids"]
    f_ids = tokenizer(full, add_special_tokens=True, truncation=False)["input_ids"]
    prompt_n = len(p_ids)
    completion_n = max(0, len(f_ids) - prompt_n)
    return prompt_n, completion_n


def ref_cost_usd(input_t: int, output_t: int, pin: float, pout: float) -> float:
    return (input_t * pin + output_t * pout) / 1_000_000


def main() -> int:
    tasks = [json.loads(line) for line in HELD_OUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    margins = {json.loads(line)["task_id"]: json.loads(line) for line in MARGINS.read_text(encoding="utf-8").splitlines() if line.strip()}

    try:
        tokenizer = load_tokenizer()
        tokenizer_mode = f"AutoTokenizer({BACKBONE})"
    except Exception as e:
        print(f"ERROR: could not load tokenizer: {e}", file=sys.stderr)
        return 1

    per_task = []
    sum_lora_in = sum_lora_out = 0
    sum_po_in = sum_po_out = 0

    for task in tasks:
        tid = task["task_id"]
        prompt = build_prompt(task)
        chosen = email_to_text(task.get("ground_truth_output", {}))
        candidate = email_to_text(task.get("candidate_output", {}))

        p1_in, p1_out = pass_token_lengths(tokenizer, prompt, candidate)
        p2_in, p2_out = pass_token_lengths(tokenizer, prompt, chosen)
        lora_in = p1_in + p2_in
        lora_out = p1_out + p2_out

        sum_lora_in += lora_in
        sum_lora_out += lora_out
        sum_po_in += lora_in
        sum_po_out += lora_out

        margin = margins.get(tid, {})
        sig_class = classify_signal_line(task)

        per_task.append(
            {
                "task_id": tid,
                "failure_category": task.get("metadata", {}).get("failure_category", "unknown"),
                "signal_line_class": sig_class,
                "lora_judge": {
                    "prompt_tokens_total_two_passes": lora_in,
                    "completion_tokens_total_two_passes": lora_out,
                    "actual_cost_usd": 0.0,
                    "reference_cost_usd_gpt4o_mini": round(
                        ref_cost_usd(lora_in, lora_out, PRICE_GPT4O_MINI_IN, PRICE_GPT4O_MINI_OUT),
                        8,
                    ),
                    "inference_latency_ms": margin.get("latency_ms"),
                },
                "prompt_only_baseline": {
                    "prompt_tokens_total_two_passes": lora_in,
                    "completion_tokens_total_two_passes": lora_out,
                    "actual_cost_usd": 0.0,
                    "reference_cost_usd_gpt4o_mini": round(
                        ref_cost_usd(lora_in, lora_out, PRICE_GPT4O_MINI_IN, PRICE_GPT4O_MINI_OUT),
                        8,
                    ),
                },
            }
        )

    n = len(tasks)
    total_ref_lora = ref_cost_usd(sum_lora_in, sum_lora_out, PRICE_GPT4O_MINI_IN, PRICE_GPT4O_MINI_OUT)
    per_task_ref = total_ref_lora / n if n else 0.0
    per_task_cents = per_task_ref * 100.0

    summary = {
        "_prompt_source": "tenacious_path_b_simpo_colab.ipynb Cell 10 (build_prompt / email_to_text)",
        "_tokenizer": tokenizer_mode,
        "_methodology": (
            "Per scoring pass: tokenize prompt.rstrip()+'\\n\\n' as prompt tokens; "
            "completion tokens = len(full_ids)-len(prompt_ids) for prefix+email text. "
            "Two passes per task (candidate + reference). "
            "Actual inference cost $0 (local). Reference $ uses list price for gpt-4o-mini — "
            "different model family, for magnitude-only comparison to API-hosted judges."
        ),
        "_price_anchor_model": GPT4O_MINI_LABEL,
        "_price_anchor_url": GPT4O_MINI_URL,
        "_price_input_per_1m_usd": PRICE_GPT4O_MINI_IN,
        "_price_output_per_1m_usd": PRICE_GPT4O_MINI_OUT,
        "held_out_n": n,
        "signal_line_distribution": {k: sum(1 for t in tasks if classify_signal_line(t) == k) for k in ("empty", "stub", "substantive")},
        "lora_judge_aggregate": {
            "total_prompt_tokens_two_passes": sum_lora_in,
            "total_completion_tokens_two_passes": sum_lora_out,
            "mean_prompt_tokens_per_task": round(sum_lora_in / n, 2) if n else 0,
            "mean_completion_tokens_per_task": round(sum_lora_out / n, 2) if n else 0,
            "actual_cost_usd": 0.0,
            "actual_cost_note": "Local inference (cost_log.csv); no API spend.",
            "reference_cost_total_usd_gpt4o_mini": round(total_ref_lora, 6),
            "reference_cost_per_task_usd_gpt4o_mini": round(per_task_ref, 8),
            "reference_cost_per_task_cents_gpt4o_mini": round(per_task_cents, 6),
        },
        "prompt_only_baseline_aggregate": {
            "total_prompt_tokens_two_passes": sum_po_in,
            "total_completion_tokens_two_passes": sum_po_out,
            "mean_prompt_tokens_per_task": round(sum_po_in / n, 2) if n else 0,
            "mean_completion_tokens_per_task": round(sum_po_out / n, 2) if n else 0,
            "actual_cost_usd": 0.0,
            "reference_cost_total_usd_gpt4o_mini": round(total_ref_lora, 6),
            "reference_cost_per_task_usd_gpt4o_mini": round(per_task_ref, 8),
            "reference_cost_per_task_cents_gpt4o_mini": round(per_task_cents, 6),
        },
        "marginal_cost_note": (
            f"LoRA vs prompt-only: $0 marginal on owned hardware (same token shapes). "
            f"Latency tradeoff: ~3.8× p50 (see ablation_results.json). "
            f"Illustrative API anchor ({GPT4O_MINI_LABEL}): ~${per_task_ref:.8f}/task "
            f"(~{per_task_cents:.4f} ¢/task) if both passes were billed at that list price."
        ),
        "per_task": per_task,
    }

    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Inference Cost Estimate")
    print("=======================")
    print(f"Tokenizer: {tokenizer_mode}")
    print(f"Tasks: {n}")
    print(f"Signal line classes: {summary['signal_line_distribution']}")
    print("\nAggregate (two passes / task, LoRA):")
    print(f"  Prompt tokens total:     {sum_lora_in:,}")
    print(f"  Completion tokens total: {sum_lora_out:,}")
    print(f"  Mean prompt tokens / task:     {summary['lora_judge_aggregate']['mean_prompt_tokens_per_task']}")
    print(f"  Mean completion tokens / task: {summary['lora_judge_aggregate']['mean_completion_tokens_per_task']}")
    print(f"  Ref. cost @ gpt-4o-mini list: ${total_ref_lora:.6f} total, ${per_task_ref:.8f}/task (~{per_task_cents:.4f} ¢/task)")
    print(f"\nOutput written to: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
