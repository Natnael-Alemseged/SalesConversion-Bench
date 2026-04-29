from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "tenacious_bench_v0.1" / "source_pool.jsonl"


def make_task(
    *,
    task_id: str,
    task_type: str,
    difficulty: str,
    source_mode: str,
    failure_category: str,
    company_name: str,
    icp_segment: int,
    thread_stage: str,
    signal_line: str,
    signal_confidence_tier: str,
    candidate_subject: str,
    candidate_body: str,
    deterministic_checks: list[str],
    week10_probe_ids: list[str],
    week10_trace_refs: list[str],
    signal_date: str = "",
    signal_source: str = "",
    prior_thread: list[dict[str, str]] | None = None,
    capacity_request: list[dict[str, object]] | None = None,
    bench_summary: dict | None = None,
    ground_truth_subject: str = "",
    ground_truth_body: str = "",
    notes: str = "",
) -> dict:
    task = {
        "task_id": task_id,
        "task_type": task_type,
        "difficulty": difficulty,
        "source_mode": source_mode,
        "metadata": {
            "week10_probe_ids": week10_probe_ids,
            "week10_trace_refs": week10_trace_refs,
            "failure_category": failure_category,
            "signal_date": signal_date,
            "signal_source": signal_source,
            "seed_origin": "week_10_probe_library",
            "notes": notes,
        },
        "input": {
            "company_name": company_name,
            "icp_segment": icp_segment,
            "thread_stage": thread_stage,
            "signal_brief": {
                "signal_line": signal_line,
                "signal_confidence_tier": signal_confidence_tier,
            },
            "prior_thread": prior_thread or [],
        },
        "candidate_output": {
            "subject": candidate_subject,
            "body": candidate_body,
        },
        "rubric": {
            "deterministic_checks": deterministic_checks,
            "notes": f"Interim task for {failure_category}.",
        },
    }
    if capacity_request:
        task["input"]["capacity_request"] = capacity_request
    if bench_summary:
        task["input"]["bench_summary"] = bench_summary
    if ground_truth_subject or ground_truth_body:
        task["ground_truth_output"] = {
            "subject": ground_truth_subject,
            "body": ground_truth_body,
            "notes": "Reference correction for Path B preference-pair construction.",
        }
    return task


def bench_summary(stack: str, *, available: int, senior: int, lead_days: int, note: str = "") -> dict:
    return {
        "stacks": {
            stack: {
                "available_engineers": available,
                "time_to_deploy_days": lead_days,
                "note": note,
                "seniority_mix": {
                    "senior_4_plus_yrs": senior,
                    "mid_2_4_yrs": max(available - senior, 0),
                    "junior_0_2_yrs": 0,
                },
            }
        }
    }


def build_tasks() -> list[dict]:
    tasks: list[dict] = []
    idx = 1

    def add(task: dict) -> None:
        nonlocal idx
        tasks.append(task)
        idx += 1

    # bench_overcommitment (15)
    bench_cases = [
        {
            "probe": "P-009",
            "refs": ["probe-4087895185a9", "probe-c1a89e56414b"],
            "stack": "go",
            "available": 3,
            "senior": 3,
            "lead_days": 21,
            "requested": 10,
            "thread_stage": "reply_active",
            "bad": "Yes, we can cover 10 senior Go engineers within three weeks. Happy to send the booking link.",
            "good": "Honest answer: we can responsibly confirm 3 senior Go engineers in that window, not 10. If partial coverage helps, I can outline the ramp.",
        },
        {
            "probe": "P-010",
            "refs": ["probe-d5299b421fc8"],
            "stack": "fullstack_nestjs",
            "available": 2,
            "senior": 2,
            "lead_days": 30,
            "requested": 2,
            "thread_stage": "reply_active",
            "note": "Currently committed on the Modo Compass engagement through Q3 2026.",
            "bad": "We have 2 NestJS engineers free now and can start them this month.",
            "good": "Those 2 NestJS engineers are already committed, so I should not promise them. If a later ramp is still useful, I can outline options.",
        },
        {
            "probe": "P-011",
            "refs": ["probe-258f1573489a"],
            "stack": "ml",
            "available": 2,
            "senior": 1,
            "lead_days": 14,
            "requested": 2,
            "thread_stage": "reply_active",
            "bad": "Yes, we can place 2 senior ML engineers immediately.",
            "good": "We can responsibly confirm 1 senior ML engineer right now; promising 2 senior ML engineers would overstate current capacity.",
        },
        {
            "probe": "P-012",
            "refs": ["probe-21a138e1feac"],
            "stack": "infra",
            "available": 4,
            "senior": 3,
            "lead_days": 14,
            "requested": 2,
            "thread_stage": "reply_active",
            "bad": "We can start the infra team in 7 days.",
            "good": "The infra bench requires a 14-day deployment window, so I should not promise a 7-day start.",
        },
    ]
    for case in bench_cases:
        for variant in range(1, 4):
            requested = case["requested"] if variant == 1 else max(case["requested"] - variant, 1)
            bad_body = case["bad"] if variant != 3 else case["good"]
            stage = case["thread_stage"] if variant != 2 else "ready_to_schedule"
            checks = ["bench_capacity_check", "format_check"]
            if "booking link" in bad_body.lower() or stage != "ready_to_schedule":
                checks.append("booking_stage_check")
            add(
                make_task(
                    task_id=f"tbv01-{idx:03d}",
                    task_type="warm_reply_email",
                    difficulty="medium" if variant < 3 else "easy",
                    source_mode="trace_derived" if variant == 1 else "programmatic",
                    failure_category="bench_overcommitment",
                    company_name="Northstar" if case["probe"] != "P-010" else "Modo",
                    icp_segment=1,
                    thread_stage=stage,
                    signal_line="You closed a Series A recently and asked about immediate team coverage.",
                    signal_confidence_tier="high",
                    candidate_subject="Re: team capacity",
                    candidate_body=bad_body,
                    deterministic_checks=checks,
                    week10_probe_ids=[case["probe"]],
                    week10_trace_refs=case["refs"],
                    signal_date="2026-03-10",
                    signal_source="week_10_probe_library",
                    prior_thread=[{"role": "prospect", "content": "Can you cover this team quickly?"}],
                    capacity_request=[
                        {
                            "stack": case["stack"],
                            "requested_count": requested,
                            "seniority": "senior",
                            "lead_days": 7 if case["probe"] == "P-012" else case["lead_days"],
                        }
                    ],
                    bench_summary=bench_summary(
                        case["stack"],
                        available=case["available"],
                        senior=case["senior"],
                        lead_days=case["lead_days"],
                        note=case.get("note", ""),
                    ),
                    ground_truth_subject="Re: team capacity",
                    ground_truth_body=case["good"],
                    notes=f"{case['probe']} variant {variant}",
                )
            )

    # icp_misclassification (10)
    icp_specs = [
        ("P-001", ["probe-8dc44eb36d33"], "layoff+funding should route to Segment 2", 2),
        ("P-004", ["probe-19f0af95e3e2"], "recent funding with zero engineering roles should not pass Segment 1", 0),
    ]
    for probe, refs, signal_line, target_segment in icp_specs:
        for variant in range(1, 6):
            wrong_segment = 1 if probe == "P-001" else 1
            bad = (
                "Congratulations on the recent funding — you are clearly in growth mode."
                if probe == "P-001"
                else "Congratulations on the raise. This looks like the right moment to add engineering capacity."
            )
            good = (
                "I saw both the funding event and the recent restructure. If cost rebalancing is the live issue, I can share two patterns we see after contractions."
                if probe == "P-001"
                else "I saw the funding event, but with no public engineering roles I do not want to assume there is a current hiring-capacity need."
            )
            add(
                make_task(
                    task_id=f"tbv01-{idx:03d}",
                    task_type="cold_outbound_email",
                    difficulty="medium",
                    source_mode="trace_derived" if variant == 1 else "programmatic",
                    failure_category="icp_misclassification",
                    company_name="Helix" if probe == "P-001" else "Harbor",
                    icp_segment=wrong_segment,
                    thread_stage="cold_first_touch",
                    signal_line=signal_line,
                    signal_confidence_tier="high" if variant < 4 else "medium",
                    candidate_subject="Context: hiring at your team",
                    candidate_body=bad if variant < 4 else good,
                    deterministic_checks=["signal_grounding_check", "format_check"],
                    week10_probe_ids=[probe],
                    week10_trace_refs=refs,
                    signal_date=f"2026-02-{10 + variant:02d}",
                    signal_source="week_10_probe_library",
                    ground_truth_subject="Context: your operating window",
                    ground_truth_body=good,
                    notes=f"Expected segment should be {target_segment}",
                )
            )

    # signal_overclaiming (10)
    for variant in range(10):
        weak = variant < 5
        bad = "Congratulations on the recent funding — you are clearly in growth mode and likely feeling recruiting pressure already."
        good = "I saw a recent funding signal, but I do not want to over-read it. Is scaling engineering capacity actually a current priority?"
        add(
            make_task(
                task_id=f"tbv01-{idx:03d}",
                task_type="cold_outbound_email",
                difficulty="medium",
                source_mode="trace_derived" if variant == 0 else "programmatic",
                failure_category="signal_overclaiming",
                company_name="Aster",
                icp_segment=1,
                thread_stage="cold_first_touch",
                signal_line="A single weak funding signal is present; confidence should remain exploratory.",
                signal_confidence_tier="low" if weak else "medium",
                candidate_subject="Question: scaling after funding",
                candidate_body=bad if weak else good,
                deterministic_checks=["signal_grounding_check", "format_check"],
                week10_probe_ids=["P-005"] if weak else ["P-006"],
                week10_trace_refs=["probe-b3388b3c3582"] if weak else ["probe-da2612b9fa29"],
                signal_date=f"2026-01-{10 + variant:02d}",
                signal_source="crunchbase_signal",
                ground_truth_subject="Question: is hiring capacity the live issue?",
                ground_truth_body=good,
                notes="Confidence-aware phrasing task",
            )
        )

    # gap_overclaiming (9)
    for variant in range(9):
        bad = (
            "Your AI maturity is behind the curve. Your leadership has not yet made the strategic moves the market requires."
            if variant < 5
            else "Three adjacent companies posted senior MLOps roles recently. That may be a useful comparison point if AI delivery capacity is under review."
        )
        good = "Three adjacent companies posted senior MLOps roles recently. That may be a useful comparison point if AI delivery capacity is under review."
        add(
            make_task(
                task_id=f"tbv01-{idx:03d}",
                task_type="cold_outbound_email",
                difficulty="hard",
                source_mode="hand_authored" if variant < 3 else "programmatic",
                failure_category="gap_overclaiming",
                company_name="FelixPay",
                icp_segment=4,
                thread_stage="cold_first_touch",
                signal_line="Three peer companies in the same sector posted senior MLOps roles in the last 90 days.",
                signal_confidence_tier="high",
                candidate_subject="Question: your MLOps function in 2026",
                candidate_body=bad,
                deterministic_checks=["signal_grounding_check", "format_check"],
                week10_probe_ids=["P-029", "P-030"] if variant < 5 else ["P-031"],
                week10_trace_refs=["probe-058ed0079e78"] if variant < 5 else [],
                signal_date=f"2026-02-{5 + variant:02d}",
                signal_source="peer_job_post_signal",
                ground_truth_subject="Question: your MLOps function in 2026",
                ground_truth_body=good,
                notes=f"Gap framing should be research-oriented, not condescending. Variant {variant + 1}.",
            )
        )

    # tone_drift (9)
    tone_bads = [
        (
            "Quick chat about world-class talent",
            "I hope this email finds you well. We provide world-class talent and top talent across stacks.",
        ),
        ("Following up again", "Just following up again to see if you had a chance to review this."),
        ("Context: your team", "We can synergize and add value to your ecosystem."),
    ]
    for variant in range(9):
        subject, body = tone_bads[variant % len(tone_bads)]
        good = "I saw your recent hiring signal and wanted to ask one concrete question: is delivery capacity the actual constraint right now?"
        add(
            make_task(
                task_id=f"tbv01-{idx:03d}",
                task_type="re_engagement_email" if variant % 3 == 1 else "cold_outbound_email",
                difficulty="easy",
                source_mode="hand_authored" if variant < 4 else "programmatic",
                failure_category="tone_drift",
                company_name="Lattice",
                icp_segment=1,
                thread_stage="re_engagement" if variant % 3 == 1 else "cold_first_touch",
                signal_line="You posted three engineering roles in the last 60 days.",
                signal_confidence_tier="medium",
                candidate_subject=subject,
                candidate_body=body,
                deterministic_checks=["banned_phrase_check", "format_check"],
                week10_probe_ids=["P-013"] if variant % 3 == 0 else ["P-014"],
                week10_trace_refs=[],
                signal_date=f"2026-03-{1 + variant:02d}",
                signal_source="job_post_signal",
                ground_truth_subject="Question: engineering capacity",
                ground_truth_body=good,
                notes=f"Tone-preservation task variant {variant + 1}.",
            )
        )

    # dual_control_coordination (7)
    for variant in range(7):
        early = variant < 4
        body = (
            "The cleanest next step is a 30-minute call. Here is Arun's calendar: https://gettenacious.com/arun"
            if early
            else "If a short scoping call would be useful, I can send a calendar link after you confirm that is the best next step."
        )
        stage = "reply_active" if early else "ready_to_schedule"
        signal_line = (
            "I saw the March restructure announcement and the cost-pressure context in your note."
            if early
            else "You explicitly said a 30-minute scoping call next week would be useful, so stage gating now permits a scheduling CTA."
        )
        prior = (
            [{"role": "prospect", "content": "Can you share a little more on process before we schedule?"}]
            if early
            else [{"role": "prospect", "content": "A 30-minute scoping call next week would be useful."}]
        )
        add(
            make_task(
                task_id=f"tbv01-{idx:03d}",
                task_type="warm_reply_email",
                difficulty="medium",
                source_mode="hand_authored" if variant < 2 else "programmatic",
                failure_category="dual_control_coordination",
                company_name="Arbor",
                icp_segment=2,
                thread_stage=stage,
                signal_line=signal_line,
                signal_confidence_tier="high",
                candidate_subject="Re: next step",
                candidate_body=body,
                deterministic_checks=["booking_stage_check", "signal_grounding_check", "format_check"],
                week10_probe_ids=["P-022"] if early else ["P-023"],
                week10_trace_refs=[],
                signal_date="2026-03-14",
                signal_source="layoffs_fyi",
                prior_thread=prior,
                ground_truth_subject="Re: next step",
                ground_truth_body="If a 30-minute scoping call is the right next step for your side, I can send the calendar link. If not, I can answer the process questions first.",
                notes=f"CTA timing / booking-stage task variant {variant + 1}.",
            )
        )

    # extra adversarial coordination / tone tasks to reach 60
    extras = [
        (
            "dual_control_coordination",
            "reply_active",
            "The right next step is a call, so I am dropping my calendar here: https://gettenacious.com/arun",
            "The right next step may be a call, but I should confirm that before sending a booking link.",
            ["P-022"],
        ),
        (
            "tone_drift",
            "cold_first_touch",
            "I hope this email finds you well. Our world-class engineers can supercharge your roadmap.",
            "I saw your public hiring signal and wanted to ask one grounded question about delivery capacity.",
            ["P-013"],
        ),
        (
            "gap_overclaiming",
            "cold_first_touch",
            "You are behind your competitors on AI maturity and need to catch up now.",
            "Three peer signals suggest this function may be worth reviewing, but I do not want to assume that from the outside.",
            ["P-030"],
        ),
    ]
    for category, stage, bad, good, probes in extras:
        add(
            make_task(
                task_id=f"tbv01-{idx:03d}",
                task_type="warm_reply_email" if category == "dual_control_coordination" else "cold_outbound_email",
                difficulty="hard",
                source_mode="hand_authored",
                failure_category=category,
                company_name="Verve",
                icp_segment=4 if category == "gap_overclaiming" else 1,
                thread_stage=stage,
                signal_line="Public signals exist, but the message should stay grounded and stage-aware.",
                signal_confidence_tier="medium",
                candidate_subject="Context: your team",
                candidate_body=bad,
                deterministic_checks=["format_check", "signal_grounding_check"]
                + (["booking_stage_check"] if category == "dual_control_coordination" else [])
                + (["banned_phrase_check"] if category == "tone_drift" else []),
                week10_probe_ids=probes,
                week10_trace_refs=[],
                signal_date="2026-03-20",
                signal_source="week_10_probe_library",
                prior_thread=[{"role": "prospect", "content": "Can you share more detail first?"}] if category == "dual_control_coordination" else [],
                ground_truth_subject="Context: your team",
                ground_truth_body=good,
                notes="Extra interim task to reach the 60-task minimum.",
            )
        )

    assert len(tasks) == 60, len(tasks)
    return tasks


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks()
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for task in tasks:
            handle.write(json.dumps(task) + "\n")
    print(f"Wrote {len(tasks)} tasks to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
