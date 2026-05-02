"""Build Path B preference pairs for Tenacious-Bench.

For each training task:
  - chosen  = task.ground_truth_output  (already authored, verified good)
  - rejected = LLM-generated bad draft that commits the task's failure_category
  - Both are verified with scoring_evaluator before saving.

Output: training_data/preference_pairs.jsonl
Audit:  training_data/preference_pairs_audit.jsonl

Usage
-----
  # Dry run (heuristic rejected outputs, no API calls):
  python3 generation_scripts/build_preference_pairs.py --dry-run

  # Live run (requires OPENROUTER_API_KEY):
  python3 generation_scripts/build_preference_pairs.py \
      --generator-model qwen/qwen3-8b \
      --max-tasks 120

Preference-leakage prevention
------------------------------
Generator model family must differ from the judge model family used in
judge_filter.py (default: claude / openai).  Qwen is the default generator
here; do not switch it to claude or openai without updating routing_policy.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_evaluator import score_task  # noqa: E402

TRAIN_PATH = ROOT / "tenacious_bench_v0.2" / "train" / "tasks.jsonl"
OUT_PATH = ROOT / "training_data" / "preference_pairs.jsonl"
AUDIT_PATH = ROOT / "training_data" / "preference_pairs_audit.jsonl"

# Generator model — must be a different family from the judge used in judge_filter.py
DEFAULT_GENERATOR = "qwen/qwen3-8b"

SYSTEM_PROMPT = """\
You are a Tenacious Intelligence Corporation sales agent writing B2B outreach emails.

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

FAILURE_INSTRUCTIONS: dict[str, str] = {
    "bench_overcommitment": (
        "Write an email that COMMITS to more engineers or a faster timeline than the "
        "bench_summary supports. Confidently promise the full requested headcount even "
        "though the bench cannot deliver it. Do NOT mention any limitations."
    ),
    "signal_overclaiming": (
        "Write an email that ASSERTS strong, confident claims ('you are scaling "
        "aggressively', 'you must be feeling the pressure') even though the signal "
        "confidence is medium or low. Present weak evidence as certain fact."
    ),
    "gap_overclaiming": (
        "Write an email that FABRICATES or EXAGGERATES competitor gap data — invent "
        "specific peer company names and role counts that are not in the signal brief, "
        "present them as verified fact, and tell the prospect they are falling behind."
    ),
    "icp_misclassification": (
        "Write an email that pitches the WRONG ICP segment. If the company is early-stage "
        "(Series A, AI maturity 0-1), pitch an advanced agentic-systems capability-gap "
        "engagement. If the company is mid-market cost-restructuring, pitch a growth "
        "expansion pitch instead."
    ),
    "tone_drift": (
        "Write an email that uses AT LEAST THREE of the following banned phrases naturally: "
        "world-class, top talent, skyrocket, supercharge, game-changer, synergize, "
        "I hope this email finds you well. Make the email sound like a generic vendor pitch."
    ),
    "dual_control_coordination": (
        "Write an email that IMMEDIATELY sends a booking calendar link and pushes for a "
        "meeting even though the thread stage is not ready_to_schedule. Push hard for "
        "a 30-minute call and include gettenacious.com/arun in the body."
    ),
}


@dataclass
class PairResult:
    task_id: str
    failure_category: str
    status: str  # accepted | skipped_chosen_fails | skipped_rejected_passes | skipped_api_error
    chosen_score: float
    rejected_score: float
    chosen_checks_failed: list[str]
    rejected_checks_failed: list[str]
    generator_model: str
    mode: str  # live | heuristic


def _build_user_message(task: dict[str, Any]) -> str:
    inp = task.get("input", {})
    parts = [f"Company: {inp.get('company_name', 'Unknown')}"]
    parts.append(f"ICP segment: {inp.get('icp_segment', '?')}")
    parts.append(f"Thread stage: {inp.get('thread_stage', 'cold_first_touch')}")
    sig = inp.get("signal_brief", {})
    parts.append(f"Signal: {sig.get('signal_line', 'No signal provided')}")
    parts.append(f"Signal confidence: {sig.get('signal_confidence_tier', 'unknown')}")
    bench = inp.get("bench_summary")
    if bench:
        parts.append(f"Bench summary: {json.dumps(bench)}")
    cap = inp.get("capacity_request")
    if cap:
        parts.append(f"Capacity request: {json.dumps(cap)}")
    thread = inp.get("prior_thread")
    if thread:
        parts.append(f"Prior thread: {json.dumps(thread)}")
    return "\n".join(parts)


def _call_openrouter(
    system: str,
    user: str,
    model: str,
    api_key: str,
    temperature: float = 0.7,
    max_tokens: int = 400,
) -> str | None:
    try:
        import httpx
    except ImportError:
        print("httpx not installed. Run: pip install httpx", file=sys.stderr)
        return None

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tenacious-intelligence/SalesConversion-Bench",
        "X-Title": "Tenacious-Bench preference-pair builder",
    }
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"  API error: {exc}", file=sys.stderr)
        return None


def _parse_email_json(raw: str) -> dict[str, str] | None:
    if not raw:
        return None
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = match.group(1) if match else raw.strip()
    # strip any leading/trailing markdown
    candidate = re.sub(r"^```[a-z]*\n?", "", candidate).rstrip("`").strip()
    try:
        parsed = json.loads(candidate)
        if "subject" in parsed and "body" in parsed:
            return {"subject": str(parsed["subject"]), "body": str(parsed["body"])}
    except json.JSONDecodeError:
        pass
    # fallback: try to extract subject/body lines
    subj = re.search(r'"subject"\s*:\s*"([^"]+)"', raw)
    body_m = re.search(r'"body"\s*:\s*"(.*?)"(?:\s*[,}])', raw, re.DOTALL)
    if subj and body_m:
        return {
            "subject": subj.group(1),
            "body": body_m.group(1).replace("\\n", "\n"),
        }
    return None


def _heuristic_rejected(task: dict[str, Any]) -> dict[str, str]:
    """Generate a deterministic bad draft when no API key is available.

    Each variant is designed to fail the specific checks in the task's rubric,
    not just commit a conceptual violation the evaluator cannot measure.
    """
    cat = task.get("metadata", {}).get("failure_category", "tone_drift")
    inp = task.get("input", {})
    company = inp.get("company_name", "your company")
    cap = inp.get("capacity_request") or []

    if cat == "bench_overcommitment" and cap:
        req = cap[0]
        count = req.get("requested_count", 10)
        stack = req.get("stack", "engineers")
        days = req.get("lead_days", 14)
        return {
            "subject": f"Re: {count} {stack} engineers",
            "body": (f"Absolutely — we can place all {count} senior {stack} engineers within {days} days. Our bench is deep and we move fast. I'll have contracts ready by Wednesday."),
        }

    # signal_overclaiming and icp_misclassification both have signal_grounding_check
    # and format_check in their rubrics. Fail BOTH by using a filler opener (format)
    # and no signal-specific tokens (signal_grounding).
    if cat == "signal_overclaiming":
        return {
            "subject": "Quick chat about your team",
            "body": (
                "I hope this email finds you well. I can see your company is scaling "
                "aggressively and you must be feeling the pressure of recruiting right now. "
                "Companies at your stage always hit a wall around month four. "
                "We have world-class engineers who will supercharge your roadmap. "
                "Quick question — do you have 15 minutes this week?"
            ),
        }

    if cat == "icp_misclassification":
        return {
            "subject": "Quick chat about your AI roadmap",
            "body": (
                "I hope this email finds you well. Most companies in your space are "
                "now deploying world-class agentic systems and dedicated MLOps squads. "
                "Your team should be scoping LLM-orchestrated workflows immediately "
                "to avoid falling behind your competitors in this game-changing space. "
                "Let's supercharge your AI roadmap — quick call this week?"
            ),
        }

    if cat == "gap_overclaiming":
        return {
            "subject": "Your AI maturity is behind the curve",
            "body": (
                f"Hi, I'll be direct: {company}'s AI maturity is falling behind your "
                "top competitors who are all at score 3. You are missing the strategic "
                "moves the sector demands in 2026. Our world-class agentic engineers "
                "can close the gap before your next board meeting. Let's synergize."
            ),
        }

    if cat == "dual_control_coordination":
        return {
            "subject": "Re: next step",
            "body": (
                "Let's get a call on the calendar right away. "
                "Here is Arun's direct booking link: gettenacious.com/arun. "
                "I've blocked time for you this Thursday at 2pm. "
                "Please confirm and we can move forward immediately."
            ),
        }

    # tone_drift — fail banned_phrase_check and format_check
    return {
        "subject": "Tenacious — World-Class Engineering Talent",
        "body": (
            f"I hope this email finds you well. Tenacious has world-class engineers "
            f"who will supercharge {company}'s roadmap. Our top talent will "
            "skyrocket your delivery throughput. Let's synergize and leverage "
            "our ecosystem for maximum game-changing impact. Quick chat this week?"
        ),
    }


def _failed_checks(result: dict[str, Any]) -> list[str]:
    return [c["name"] for c in result.get("checks", []) if not c["passed"]]


def _stub_signal(task: dict[str, Any]) -> bool:
    return str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "")).startswith("Ref=")


def _blocking_chosen_failures(task: dict[str, Any], failed: list[str]) -> list[str]:
    stub = _stub_signal(task)
    return [f for f in failed if not (f == "signal_grounding_check" and stub)]


def _personalize_ground_truth(gt: dict[str, str], task: dict[str, Any]) -> dict[str, str]:
    """Inject company name into templated ground-truth copy for per-task diversity.

    Train tasks reuse ~13 canonical bodies across many companies; without this,
    preference pairs collapse to a handful of identical `chosen` strings.
    """
    company = str(task.get("input", {}).get("company_name") or "").strip()
    subject = str(gt.get("subject") or "").strip()
    body = str(gt.get("body") or "").strip()
    if not company or company.lower() in body.lower():
        return {"subject": subject, "body": body}

    cn = company
    candidates: list[tuple[str, str]] = []

    # Order matters: first match wins (most specific prefixes first).
    if "I saw your recent hiring signal" in body:
        candidates.append(
            (
                body.replace("I saw your recent hiring signal", f"I saw {cn}'s recent hiring signal", 1),
                subject,
            )
        )
    if "I saw your public hiring signal" in body:
        candidates.append(
            (
                body.replace("I saw your public hiring signal", f"I saw {cn}'s public hiring signal", 1),
                subject,
            )
        )
    if "I saw a recent funding signal," in body:
        candidates.append(
            (
                body.replace(
                    "I saw a recent funding signal,",
                    f"I saw a recent funding signal at {cn},",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("Three adjacent companies posted"):
        rest = body[0].lower() + body[1:]
        candidates.append((f"Regarding {cn}: {rest}", subject))
    if "I saw the funding event, but with no public engineering roles" in body:
        candidates.append(
            (
                body.replace(
                    "I saw the funding event, but with no public engineering roles",
                    f"I saw the funding event at {cn}, but with no public engineering roles",
                    1,
                ),
                subject,
            )
        )
    if "If a 30-minute scoping call is the right next step for your side" in body:
        candidates.append(
            (
                body.replace(
                    "If a 30-minute scoping call is the right next step for your side",
                    f"If a 30-minute scoping call is the right next step for {cn}",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("Honest answer: we can responsibly confirm"):
        candidates.append(
            (
                body.replace(
                    "Honest answer: we can responsibly confirm",
                    f"Honest answer for {cn}: we can responsibly confirm",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("Those 2 NestJS engineers are already committed"):
        candidates.append(
            (
                body.replace(
                    "Those 2 NestJS engineers are already committed",
                    f"At {cn}, those 2 NestJS engineers are already committed",
                    1,
                ),
                subject,
            )
        )
    if "I saw both the funding event and the recent restructure." in body:
        candidates.append(
            (
                body.replace(
                    "I saw both the funding event and the recent restructure.",
                    f"I saw both the funding event and the recent restructure at {cn}.",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("We can responsibly confirm 1 senior ML engineer right now"):
        candidates.append(
            (
                body.replace(
                    "We can responsibly confirm 1 senior ML engineer right now",
                    f"At {cn}, we can responsibly confirm 1 senior ML engineer right now",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("Three peer signals suggest this function may be worth reviewing"):
        candidates.append(
            (
                body.replace(
                    "Three peer signals suggest this function may be worth reviewing",
                    f"Three peer signals suggest {cn}'s org may be worth reviewing",
                    1,
                ),
                subject,
            )
        )
    if "The right next step may be a call, but I should confirm that before sending" in body:
        candidates.append(
            (
                body.replace(
                    "The right next step may be a call, but I should confirm that before sending",
                    f"The right next step for {cn} may be a call, but I should confirm that before sending",
                    1,
                ),
                subject,
            )
        )
    if body.startswith("The infra bench requires a 14-day deployment window"):
        candidates.append(
            (
                body.replace(
                    "The infra bench requires a 14-day deployment window",
                    f"The infra bench for {cn} requires a 14-day deployment window",
                    1,
                ),
                subject,
            )
        )

    for new_body, new_subject in candidates:
        sub = new_subject
        if cn.lower() not in new_subject.lower() and len(new_subject) + len(cn) + 3 <= 58:
            sub = f"{new_subject.rstrip()} — {cn}"[:60]
        out = {"subject": sub.strip(), "body": new_body.strip()}
        test_task = {**task, "candidate_output": out}
        result = score_task(test_task)
        failed = _failed_checks(result)
        if not _blocking_chosen_failures(task, failed):
            return out

    return {"subject": subject, "body": body}


def _diversify_chosen(
    gt: dict[str, str],
    task: dict[str, Any],
    seen_chosen: set[str],
    generator_model: str,
    api_key: str | None,
    dry_run: bool,
) -> dict[str, str]:
    """Return a paraphrased variant of gt that still passes the evaluator.

    Falls back to the original gt if we cannot produce a passing variant.
    Only called when the gt text has already been used >= 3 times.
    """
    chosen_text = f"Subject: {gt.get('subject', '')}\n\n{gt.get('body', '')}"
    if chosen_text not in seen_chosen:
        return gt  # still unique, use as-is

    if dry_run or not api_key:
        return gt  # can't paraphrase without API in dry-run

    user_ctx = _build_user_message(task)
    rewrite_system = (
        "Rewrite the following Tenacious outreach email so it conveys the same meaning "
        "with different wording. Keep the same tone markers: direct, grounded, honest, "
        "professional, non-condescending. Preserve the same subject intent and body length. "
        "Do NOT add banned phrases. Do NOT change the factual claims.\n\n"
        f"Original:\n{chosen_text}\n\n"
        'Respond with ONLY a JSON object: {"subject": "...", "body": "..."}'
    )
    raw = _call_openrouter(rewrite_system, user_ctx, generator_model, api_key, temperature=0.8)
    variant = _parse_email_json(raw) if raw else None
    if not variant:
        return gt

    # Verify variant still passes the task's checks
    test_task = {**task, "candidate_output": variant}
    result = score_task(test_task)
    stub_signal = str(task.get("input", {}).get("signal_brief", {}).get("signal_line", "")).startswith("Ref=")
    failed = [c["name"] for c in result["checks"] if not c["passed"] if not (c["name"] == "signal_grounding_check" and stub_signal)]
    return variant if not failed else gt


def build_pairs(
    tasks: list[dict[str, Any]],
    generator_model: str,
    api_key: str | None,
    dry_run: bool,
    max_tasks: int,
    retry_delay: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pairs: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    seen_chosen: set[str] = set()

    for i, task in enumerate(tasks[:max_tasks]):
        task_id = task.get("task_id", f"task-{i}")
        cat = task.get("metadata", {}).get("failure_category", "tone_drift")
        gt = task.get("ground_truth_output", {})

        print(f"[{i + 1}/{min(max_tasks, len(tasks))}] {task_id} ({cat})", end=" ... ", flush=True)

        gt_raw = {
            "subject": str(gt.get("subject", "")).strip(),
            "body": str(gt.get("body", "")).strip(),
        }
        chosen_email = _personalize_ground_truth(gt_raw, task)
        chosen_email = _diversify_chosen(chosen_email, task, seen_chosen, generator_model, api_key, dry_run)

        chosen_result = score_task({**task, "candidate_output": chosen_email})
        chosen_failed = _failed_checks(chosen_result)
        blocking_failures = _blocking_chosen_failures(task, chosen_failed)
        if blocking_failures:
            print(f"SKIP (chosen fails: {blocking_failures})")
            audit.append(
                asdict(
                    PairResult(
                        task_id=task_id,
                        failure_category=cat,
                        status="skipped_chosen_fails",
                        chosen_score=chosen_result["score"],
                        rejected_score=0.0,
                        chosen_checks_failed=chosen_failed,
                        rejected_checks_failed=[],
                        generator_model=generator_model,
                        mode="n/a",
                    )
                )
            )
            continue

        # --- Generate rejected draft ---
        failure_instruction = FAILURE_INSTRUCTIONS.get(cat, FAILURE_INSTRUCTIONS["tone_drift"])
        user_msg = _build_user_message(task)
        rejected_email: dict[str, str] | None = None
        mode = "heuristic"

        if not dry_run and api_key:
            system_bad = (
                f"You are generating a BAD example outreach email for training purposes.\n\n"
                f"INSTRUCTION: {failure_instruction}\n\n"
                "The email must look plausible but commit the specific violation described above.\n"
                'Respond with ONLY a JSON object: {"subject": "...", "body": "..."}'
            )
            raw = _call_openrouter(system_bad, user_msg, generator_model, api_key)
            rejected_email = _parse_email_json(raw) if raw else None
            if rejected_email:
                mode = "live"
            else:
                print("(API parse failed, falling back to heuristic)", end=" ", flush=True)

        if rejected_email is None:
            rejected_email = _heuristic_rejected(task)

        # --- Verify rejected draft fails at least one check ---
        rejected_task = {**task, "candidate_output": rejected_email}
        rejected_result = score_task(rejected_task)
        rejected_failed = _failed_checks(rejected_result)

        if not rejected_failed:
            print("SKIP (rejected unexpectedly passes all checks)")
            audit.append(
                asdict(
                    PairResult(
                        task_id=task_id,
                        failure_category=cat,
                        status="skipped_rejected_passes",
                        chosen_score=chosen_result["score"],
                        rejected_score=rejected_result["score"],
                        chosen_checks_failed=[],
                        rejected_checks_failed=[],
                        generator_model=generator_model,
                        mode=mode,
                    )
                )
            )
            if not dry_run and api_key:
                time.sleep(retry_delay)
            continue

        # --- Save pair ---
        prompt_text = f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n[CONTEXT]\n{user_msg}"
        chosen_text = f"Subject: {chosen_email.get('subject', '')}\n\n{chosen_email.get('body', '')}"
        rejected_text = f"Subject: {rejected_email['subject']}\n\n{rejected_email['body']}"
        seen_chosen.add(chosen_text)

        pair = {
            "task_id": task_id,
            "failure_category": cat,
            "prompt": prompt_text,
            "chosen": chosen_text,
            "rejected": rejected_text,
            "chosen_score": chosen_result["score"],
            "rejected_score": rejected_result["score"],
            "rejected_checks_failed": rejected_failed,
            "generator_model": generator_model,
            "mode": mode,
        }
        pairs.append(pair)

        result_obj = PairResult(
            task_id=task_id,
            failure_category=cat,
            status="accepted",
            chosen_score=chosen_result["score"],
            rejected_score=rejected_result["score"],
            chosen_checks_failed=[],
            rejected_checks_failed=rejected_failed,
            generator_model=generator_model,
            mode=mode,
        )
        audit.append(asdict(result_obj))
        print(f"OK (rejected fails: {rejected_failed}, mode={mode})")

        if not dry_run and api_key:
            time.sleep(retry_delay)

    return pairs, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Path B preference pairs")
    parser.add_argument("--train-file", default=str(TRAIN_PATH))
    parser.add_argument("--out", default=str(OUT_PATH))
    parser.add_argument("--audit", default=str(AUDIT_PATH))
    parser.add_argument("--generator-model", default=DEFAULT_GENERATOR)
    parser.add_argument("--max-tasks", type=int, default=120)
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Seconds to sleep between API calls")
    parser.add_argument("--dry-run", action="store_true", help="Use heuristic rejected outputs only — no API calls")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip() or None
    if not api_key and not args.dry_run:
        print("WARNING: OPENROUTER_API_KEY not set. Falling back to heuristic mode.")
        print("  Set the key or pass --dry-run to suppress this warning.\n")

    tasks = [json.loads(line) for line in Path(args.train_file).read_text().splitlines() if line.strip()]
    print(f"Loaded {len(tasks)} training tasks from {args.train_file}")
    print(f"Generator model : {args.generator_model}")
    print(f"Mode            : {'dry-run (heuristic)' if args.dry_run or not api_key else 'live (API)'}")
    print(f"Max tasks       : {args.max_tasks}")
    print()

    pairs, audit = build_pairs(
        tasks,
        generator_model=args.generator_model,
        api_key=api_key,
        dry_run=args.dry_run,
        max_tasks=args.max_tasks,
        retry_delay=args.retry_delay,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pairs) + "\n")

    audit_path = Path(args.audit)
    audit_path.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in audit) + "\n")

    accepted = sum(1 for a in audit if a["status"] == "accepted")
    skipped_chosen = sum(1 for a in audit if a["status"] == "skipped_chosen_fails")
    skipped_rejected = sum(1 for a in audit if a["status"] == "skipped_rejected_passes")
    live = sum(1 for p in pairs if p["mode"] == "live")
    heuristic = sum(1 for p in pairs if p["mode"] == "heuristic")

    chosen_cnt = Counter(p.get("chosen", "") for p in pairs)
    uniq_chosen = len(chosen_cnt)
    max_rep = max(chosen_cnt.values(), default=0)

    print("\n--- Summary ---")
    print(f"Accepted pairs  : {accepted}")
    print(f"  live API      : {live}")
    print(f"  heuristic     : {heuristic}")
    print(f"Unique chosen   : {uniq_chosen} / {accepted} (max repeat {max_rep})")
    print(f"Skipped (chosen fails)    : {skipped_chosen}")
    print(f"Skipped (rejected passes) : {skipped_rejected}")
    print(f"\nOutput : {out_path}")
    print(f"Audit  : {audit_path}")


if __name__ == "__main__":
    main()
