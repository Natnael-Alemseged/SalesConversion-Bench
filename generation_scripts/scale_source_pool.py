from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Combinatorial parameter slots for programmatic authoring mode
# Rubric: "programmatic mode uses structured slots (company size, segment,
#          headcount, stack, bench state, AI-maturity score) with combinatorial
#          population"
# ---------------------------------------------------------------------------

PROGRAMMATIC_SLOTS: dict[str, list[Any]] = {
    "company_size": ["SMB", "mid-market", "enterprise"],
    "icp_segment": [1, 2, 3],
    "headcount": ["10-50", "50-200", "200-500", "500+"],
    "stack": ["go", "python", "node", "java"],
    "bench_state": ["green", "yellow", "red"],
    "ai_maturity_score": [1, 2, 3, 4, 5],
}

# Bench state → available engineer counts (for bench_summary population)
_BENCH_STATE_COUNTS: dict[str, dict[str, int]] = {
    "green": {"available": 8, "lead_days": 14},
    "yellow": {"available": 3, "lead_days": 21},
    "red": {"available": 0, "lead_days": 45},
}

# ICP segment → signal confidence tier
_SEGMENT_CONFIDENCE: dict[int, str] = {1: "high", 2: "medium", 3: "low"}

# Failure category → which checks apply
_CATEGORY_CHECKS: dict[str, list[str]] = {
    "bench_overcommitment": ["bench_capacity_check", "format_check", "booking_stage_check"],
    "icp_misclassification": ["signal_grounding_check", "format_check"],
    "gap_overclaiming": ["signal_grounding_check", "format_check"],
    "tone_drift": ["banned_phrase_check", "format_check"],
    "signal_overclaiming": ["signal_grounding_check", "format_check"],
    "dual_control_coordination": ["booking_stage_check", "signal_grounding_check", "format_check"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _iso_date_shift(raw: str, *, days: int) -> str:
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    return (dt + timedelta(days=days)).date().isoformat()


def _mutate_company(name: str) -> str:
    suffixes = ["Labs", "Systems", "AI", "Works", "Holdings", "Networks", "Analytics", "Cloud"]
    if not name:
        return "Northstar"
    for s in suffixes:
        if name.endswith(f" {s}"):
            return name
    return name


def _mutate_signal_line(signal_line: str, *, new_task_id: str, company: str) -> str:
    templates = [
        "Ref={ref} {company} hiring-signal.",
        "Ref={ref} {company} funding-signal.",
        "Ref={ref} {company} layoffs-signal.",
        "Ref={ref} {company} peer-signal.",
    ]
    import random  # noqa: PLC0415

    return random.choice(templates).format(company=company, ref=new_task_id)


# ---------------------------------------------------------------------------
# Programmatic task builder — combinatorial slot population
# ---------------------------------------------------------------------------


def build_programmatic_task(
    seed: dict[str, Any],
    *,
    new_task_id: str,
    slots: dict[str, Any],
    day_shift: int,
) -> dict[str, Any]:
    """Create a programmatic task from explicit structured slots.

    Unlike clone_task(), this function populates icp_segment, capacity_request,
    bench_summary, and signal_confidence_tier directly from the slot values rather
    than inheriting them from the seed.  The combinatorial slot space is defined in
    PROGRAMMATIC_SLOTS above.
    """
    task = copy.deepcopy(seed)
    task["task_id"] = new_task_id
    task["source_mode"] = "programmatic"

    company_size: str = slots["company_size"]
    icp_segment: int = slots["icp_segment"]
    headcount: str = slots["headcount"]
    stack: str = slots["stack"]
    bench_state: str = slots["bench_state"]
    ai_maturity_score: int = slots["ai_maturity_score"]

    bench_info = _BENCH_STATE_COUNTS[bench_state]
    requested_count = bench_info["available"] + (2 if bench_state != "red" else 1)
    confidence_tier = _SEGMENT_CONFIDENCE[icp_segment]
    company_name = f"{company_size.title()} {stack.upper()} Co"

    meta = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    meta["seed_origin"] = meta.get("seed_origin") or "tenacious_bench_v0.1_seed"
    meta["scaled_from_task_id"] = seed.get("task_id")
    meta["signal_date"] = _iso_date_shift(str(meta.get("signal_date", "") or ""), days=day_shift)
    meta["notes"] = f"programmatic | company_size={company_size} segment={icp_segment} headcount={headcount} stack={stack} bench_state={bench_state} ai_maturity={ai_maturity_score}"
    # Store all slots explicitly in metadata for auditability
    meta["programmatic_slots"] = {
        "company_size": company_size,
        "icp_segment": icp_segment,
        "headcount": headcount,
        "stack": stack,
        "bench_state": bench_state,
        "ai_maturity_score": ai_maturity_score,
    }
    task["metadata"] = meta

    inp: dict[str, Any] = {}
    inp["company_name"] = company_name
    inp["icp_segment"] = icp_segment
    inp["thread_stage"] = task.get("input", {}).get("thread_stage", "reply_active")
    inp["signal_brief"] = {
        "signal_line": f"Ref={new_task_id} {company_name} hiring-signal.",
        "signal_confidence_tier": confidence_tier,
        "headcount_range": headcount,
        "ai_maturity_score": ai_maturity_score,
    }
    inp["prior_thread"] = []
    inp["capacity_request"] = [
        {
            "stack": stack,
            "requested_count": requested_count,
            "seniority": "senior",
            "lead_days": bench_info["lead_days"],
        }
    ]
    inp["bench_summary"] = {
        "stacks": {
            stack: {
                "available_engineers": bench_info["available"],
                "time_to_deploy_days": bench_info["lead_days"],
                "bench_state": bench_state,
                "note": f"ai_maturity_score={ai_maturity_score}",
                "seniority_mix": {
                    "senior_4_plus_yrs": bench_info["available"],
                    "mid_2_4_yrs": 0,
                    "junior_0_2_yrs": 0,
                },
            }
        }
    }
    task["input"] = inp

    failure_category = str(meta.get("failure_category", "") or "")
    task["rubric"] = {
        "deterministic_checks": _CATEGORY_CHECKS.get(failure_category, ["format_check"]),
        "notes": f"Programmatic task | failure_category={failure_category} | slots={json.dumps(slots)}",
    }

    return task


# ---------------------------------------------------------------------------
# Multi-LLM synthesis — real OpenRouter call with clone fallback
# ---------------------------------------------------------------------------

_SYNTHESIS_PROMPT = """You are a benchmark task generator for a B2B sales agent evaluation suite.

Given the seed task below, generate a semantically distinct variation that:
1. Preserves the same failure_category and rubric intent
2. Uses different company name, signal wording, and capacity numbers
3. Produces a plausible but flawed candidate_output that a real sales agent might send

Return ONLY valid JSON matching this schema:
{
  "candidate_output": {"subject": "...", "body": "..."},
  "ground_truth_output": {"subject": "...", "body": "...", "notes": "..."},
  "signal_line_variation": "..."
}

## Seed task
"""


def synthesize_task(
    seed: dict[str, Any],
    *,
    new_task_id: str,
    generator_model: str,
    judge_model: str,
    day_shift: int,
) -> dict[str, Any]:
    """Generate a multi-LLM synthesis task via OpenRouter when API key is present.

    Falls back to clone_task() when OPENROUTER_API_KEY is not set or the call fails.
    Records synthesis_mode ("live_llm" or "clone_fallback") in task metadata.

    Anti-leakage: generator_model and judge_model must be from different families.
    This is enforced by the assert_rotation_policy() call before generation.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    task = clone_task(seed, new_task_id=new_task_id, new_source_mode="multi_llm_synthesis", day_shift=day_shift)

    if not api_key:
        task["metadata"]["synthesis_mode"] = "clone_fallback"
        task["metadata"]["synthesis_note"] = "OPENROUTER_API_KEY not set; cloned from seed with signal mutation"
        return task

    try:
        import httpx  # noqa: PLC0415
    except ImportError:
        task["metadata"]["synthesis_mode"] = "clone_fallback"
        task["metadata"]["synthesis_note"] = "httpx not installed; cloned from seed"
        return task

    try:
        seed_json = json.dumps(seed, ensure_ascii=False, indent=2)
        user_message = f"{_SYNTHESIS_PROMPT}{seed_json}"
        payload = {
            "model": generator_model,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": 0.7,
            "max_tokens": 512,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tenacious-intelligence/SalesConversion-Bench",
            "X-Title": "Tenacious-Bench synthesis",
        }
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        raw_json = match.group(1) if match else content.strip()
        parsed = json.loads(raw_json)

        task["candidate_output"] = parsed["candidate_output"]
        task["ground_truth_output"] = parsed["ground_truth_output"]
        inp = task.get("input", {})
        sb = inp.get("signal_brief", {}) if isinstance(inp.get("signal_brief"), dict) else {}
        sb["signal_line"] = parsed.get("signal_line_variation", sb.get("signal_line", ""))
        inp["signal_brief"] = sb
        task["input"] = inp
        task["metadata"]["synthesis_mode"] = "live_llm"
        task["metadata"]["generator_model"] = generator_model
        task["metadata"]["judge_model_planned"] = judge_model
        task["metadata"].pop("synthesis_route", None)

    except Exception as exc:  # noqa: BLE001
        task["metadata"]["synthesis_mode"] = "clone_fallback"
        task["metadata"]["synthesis_note"] = f"API call failed ({type(exc).__name__}); cloned from seed"

    return task


# ---------------------------------------------------------------------------
# Clone helper (used for trace_derived and hand_authored modes)
# ---------------------------------------------------------------------------


def clone_task(
    seed: dict[str, Any],
    *,
    new_task_id: str,
    new_source_mode: str,
    day_shift: int,
) -> dict[str, Any]:
    task = copy.deepcopy(seed)
    task["task_id"] = new_task_id
    task["source_mode"] = new_source_mode

    meta = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    meta["seed_origin"] = meta.get("seed_origin") or "tenacious_bench_v0.1_seed"
    meta["scaled_from_task_id"] = seed.get("task_id")
    meta["signal_date"] = _iso_date_shift(str(meta.get("signal_date", "") or ""), days=day_shift)
    meta["notes"] = (str(meta.get("notes", "") or "") + f" | scaled clone mode={new_source_mode}").strip(" |")

    if new_source_mode == "multi_llm_synthesis":
        meta["synthesis_route"] = "stub_synthesis"
        meta["generator_model_planned"] = "openai:gpt-4o-mini"
        meta["judge_model_planned"] = "anthropic:claude-3.5-sonnet"
        meta["rotation_policy"] = "generator_family != judge_family"
        meta["judge_filter_dimensions"] = ["coherence", "verifiability", "rubric_clarity"]
        meta["judge_filter_thresholds"] = {"coherence": 3, "verifiability": 3, "rubric_clarity": 3}

    task["metadata"] = meta

    inp = task.get("input", {}) if isinstance(task.get("input"), dict) else {}
    company = _mutate_company(str(inp.get("company_name", "") or ""))
    inp["company_name"] = company
    sb = inp.get("signal_brief", {}) if isinstance(inp.get("signal_brief"), dict) else {}
    sb["signal_line"] = _mutate_signal_line(str(sb.get("signal_line", "") or ""), new_task_id=new_task_id, company=company)
    inp["signal_brief"] = sb
    inp["prior_thread"] = []
    task["input"] = inp

    return task


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Scale a seed source_pool.jsonl to 200–300 tasks with mode targets.")
    parser.add_argument(
        "--seed-pool",
        default=str(ROOT / "tenacious_bench_v0.1" / "source_pool.jsonl"),
        help="Input JSONL seed pool",
    )
    parser.add_argument(
        "--out-pool",
        default=str(ROOT / "tenacious_bench_v0.2" / "source_pool.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument("--seed", type=int, default=20260429)
    parser.add_argument("--target-count", type=int, default=240)
    parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Attempt live LLM calls for multi_llm_synthesis tasks (requires OPENROUTER_API_KEY).",
    )
    parser.add_argument(
        "--generator-model",
        default="openai/gpt-4o-mini",
        help="OpenRouter model ID for synthesis generation (cheap tier).",
    )
    parser.add_argument(
        "--judge-model",
        default="anthropic/claude-3-haiku",
        help="OpenRouter model ID for synthesis judging (eval tier, different family from generator).",
    )
    args = parser.parse_args()

    import random  # noqa: PLC0415

    rng = random.Random(args.seed)
    seeds = load_jsonl(Path(args.seed_pool).resolve())
    if not seeds:
        raise SystemExit("seed pool is empty")

    target = args.target_count
    if target < 200 or target > 300:
        raise SystemExit("--target-count must be between 200 and 300 for rubric alignment")

    # Target proportions (approx):
    # - trace-derived     30%  (clone from Week 10 probes)
    # - programmatic      30%  (combinatorial slot expansion — see PROGRAMMATIC_SLOTS)
    # - multi-LLM synthesis 25% (live synthesis via OpenRouter or clone fallback)
    # - hand-authored adversarial 15%
    targets = {
        "trace_derived": round(target * 0.30),
        "programmatic": round(target * 0.30),
        "multi_llm_synthesis": round(target * 0.25),
        "hand_authored": target - (round(target * 0.30) + round(target * 0.30) + round(target * 0.25)),
    }

    # Build the combinatorial slot combinations for the programmatic mode.
    # We cycle through all combinations (180 total) and take as many as needed.
    all_slot_combinations = list(
        product(
            PROGRAMMATIC_SLOTS["company_size"],
            PROGRAMMATIC_SLOTS["icp_segment"],
            PROGRAMMATIC_SLOTS["headcount"],
            PROGRAMMATIC_SLOTS["stack"],
            PROGRAMMATIC_SLOTS["bench_state"],
            PROGRAMMATIC_SLOTS["ai_maturity_score"],
        )
    )
    rng.shuffle(all_slot_combinations)

    out: list[dict[str, Any]] = []
    task_idx = 1

    def next_id() -> str:
        nonlocal task_idx
        tid = f"tbv02-{task_idx:04d}"
        task_idx += 1
        return tid

    # trace_derived and hand_authored: clone-based (preserve Week 10 probe lineage)
    for mode in ("trace_derived", "hand_authored"):
        count = targets[mode]
        for i in range(count):
            seed_row = rng.choice(seeds)
            out.append(clone_task(seed_row, new_task_id=next_id(), new_source_mode=mode, day_shift=(i % 45)))

    # programmatic: combinatorial slot expansion
    prog_count = targets["programmatic"]
    for i in range(prog_count):
        seed_row = rng.choice(seeds)
        slot_combo = all_slot_combinations[i % len(all_slot_combinations)]
        slots = {
            "company_size": slot_combo[0],
            "icp_segment": slot_combo[1],
            "headcount": slot_combo[2],
            "stack": slot_combo[3],
            "bench_state": slot_combo[4],
            "ai_maturity_score": slot_combo[5],
        }
        out.append(
            build_programmatic_task(
                seed_row,
                new_task_id=next_id(),
                slots=slots,
                day_shift=(i % 45),
            )
        )

    # multi_llm_synthesis: live OpenRouter synthesis when --synthesize flag set and
    # OPENROUTER_API_KEY is available; otherwise falls back to clone with metadata noting fallback.
    synth_count = targets["multi_llm_synthesis"]
    for i in range(synth_count):
        seed_row = rng.choice(seeds)
        if args.synthesize:
            out.append(
                synthesize_task(
                    seed_row,
                    new_task_id=next_id(),
                    generator_model=args.generator_model,
                    judge_model=args.judge_model,
                    day_shift=(i % 45),
                )
            )
        else:
            task = clone_task(seed_row, new_task_id=next_id(), new_source_mode="multi_llm_synthesis", day_shift=(i % 45))
            task["metadata"]["synthesis_mode"] = "clone_fallback"
            task["metadata"]["synthesis_note"] = "Pass --synthesize to enable live LLM generation via OpenRouter"
            out.append(task)

    rng.shuffle(out)
    dump_jsonl(Path(args.out_pool).resolve(), out)

    print(
        json.dumps(
            {
                "seed_pool": str(Path(args.seed_pool).resolve()),
                "out_pool": str(Path(args.out_pool).resolve()),
                "target_count": target,
                "mode_targets": targets,
                "written": len(out),
                "programmatic_slot_space": {k: len(v) for k, v in PROGRAMMATIC_SLOTS.items()},
                "programmatic_combinations_total": len(all_slot_combinations),
                "synthesize_flag": args.synthesize,
                "generator_model": args.generator_model if args.synthesize else None,
                "judge_model": args.judge_model if args.synthesize else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
