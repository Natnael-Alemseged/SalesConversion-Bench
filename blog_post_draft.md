---
title: When Generic Benchmarks Fail: Building a Sales-Domain Evaluation Bench from Scratch
published: true
description: How I built Tenacious-Bench — a 240-task domain-specific benchmark for a B2B sales agent — trained a SimPO LoRA judge, and lifted held-out preference accuracy from 14.9% (deterministic baseline) to 91.5% on the same 47-task slice.
tags: machinelearning, llm, benchmarks, ai
---

# When Generic Benchmarks Fail: Building a Sales-Domain Evaluation Bench from Scratch

*By Natnael Alemseged*

---

## The gap that τ²-Bench retail cannot measure

Tenacious is a B2B sales automation company. Its agent produces outreach emails for clients — personalized to the prospect's company, calibrated to the signal confidence of the underlying data, and constrained by the actual bench capacity available to fulfill any commitment made in the email. The executive team's question going into Week 11 was simple: how do we know this works for our business, our voice, our segments, our bench? The honest answer was: we don't. Not because the agent was untested, but because the tests we had were the wrong tests.

τ²-Bench retail measures whether a sales agent can navigate a generic retail conversation. Tenacious needs an agent that checks bench capacity against a real JSON summary, routes prospects to the right ICP segment based on layoff and funding signals, and phrases outreach to match the confidence tier of the underlying data. These are not things any public benchmark grades.

The audit I ran on Day 1 listed eight probe IDs from the Week 10 failure library that τ²-Bench retail would have passed: P-009 through P-012 (bench overcommitment, 100% trigger rate), P-001 and P-004 (ICP misrouting, 54%), P-005 and P-019 (assertive phrasing under weak signal). A retail benchmark scores those outputs as acceptable because they are fluent. They are not acceptable for Tenacious because they make promises the company cannot keep.

---

## How I found the gap: the audit method

*(Week 10 and Week 11 refer to two consecutive project sprints: Week 10 built the Tenacious sales agent; Week 11 built the evaluator, benchmark, and critic on top of it.)*

The Week 10 evidence was more useful than I expected. The failure taxonomy shows that `bench_overcommitment` triggered on every bench-feasibility probe in that roll-up (**40/40**; see `week_10_data/failure_taxonomy.md`). This is not a distribution problem — it is a systematic absence of a check. The agent's generator never consulted `bench_summary` before committing capacity.

The same pattern held for ICP routing: **20 of 37** probes in the ICP-misclassification roll-up (**54%**; same source). In both cases, the structured context fields (`bench_summary`, `signal_confidence_tier`, `icp_segment`) were available in the input. The generator simply did not use them.

This pointed immediately to Path B rather than Path A. The outputs were fluent — no generation quality problem. What was missing was a rejection layer that checks structured context against the draft before it is sent.

Concretely, five probe traces drove the decision:

| Probe ID | Trace ref | Failure |
|---|---|---|
| P-009 | `probe-4087895185a9` | Go overcommitment: bench=3, committed=10 |
| P-010 | `probe-d5299b421fc8` | NestJS capacity committed but fully deployed |
| P-001 | `probe-8dc44eb36d33` | Layoff+funding → Segment 1 instead of Segment 2 |
| P-004 | `probe-19f0af95e3e2` | Zero open roles, still Segment 1 pitch |
| P-005 | `probe-b3388b3c3582` | Assertive opener under medium-confidence signal |

All five share the same pattern: a structured field in the task input encodes the ground truth, and the agent ignored it. A generation-quality fix does not address this. A critic that has bench state and segment rules in its context can.

---

## Building the benchmark: how dataset construction actually works at small data

### The four authoring modes

Tenacious-Bench v0.2 uses four authoring modes, each with different cost and quality tradeoffs:

**Trace-derived** tasks come directly from the Week 10 failure library. The task input is reconstructed from a real probe, the ground truth is the corrected output from the post-hoc audit. These are the highest-signal tasks — they encode actual failures the agent produced in a real evaluation. The risk is sparse coverage: the probe library covers only the failure modes that were already identified.

**Programmatic** tasks expand the trace-derived set by templatizing the inputs — varying company name, capacity numbers, signal tier, and ICP segment systematically. Coverage is higher but signal lines are often synthetic stubs (`Ref=tbv02-0021 Arbor Systems hiring-signal.`) rather than grounded specifics. That creates calibration noise in the evaluator's `signal_grounding_check`, documented below.

**Multi-LLM synthesis** routes task generation to a cheap model tier (Qwen via OpenRouter) and judgment to a different family (Claude/OpenAI) — following the preference-leakage prevention protocol from Li et al. (2025). The generator produces the rejected outputs for preference pairs; the judge verifies them. Using the same model for both would inflate apparent pair quality without improving actual learning signal.

**Hand-authored** tasks cover the long tail of failure modes that neither trace-derived nor programmatic expansion reaches — dual-control coordination failures and edge cases in booking-stage handling.

### Judge-filter calibration (task inclusion)

Every generated task is supposed to pass an LLM-as-judge gate before it enters the benchmark: pointwise scores on **input coherence**, **ground-truth verifiability**, and **rubric-application clarity** (1–5 each), with documented minimums (`generation_scripts/audit_logs/authoring_manifest_*.json`: require **≥3** on each dimension, reject on malformed JSON). **Generator and judge model families are rotated** so the same family never both authors and scores the same pool — again following Li et al. (2025). Pairwise tiebreaks handle near-duplicate synthesis paths (Jaccard overlap on subject+body, threshold 0.8). The published authoring manifest for the 240-task build records whether live OpenRouter calls were enabled; when the key is absent, the pipeline falls back to a **stub judge** that only enforces the dimension floor — useful for reproducible CI, but **not** a substitute for calibrating a frontier judge on a 50-task spot sample. Inter-rater agreement on 30 hand-labeled tasks (24-hour relabel) is what kept the *downstream* deterministic rubric honest.

### The routing decision I would make differently

Stub signal lines from cheap synthesis are not interchangeable with realistic briefs. A real signal line reads: "You closed a $14M Series A in February and your Python roles increased from 2 to 7 in 60 days." A stub reads: "Ref=tbv02-0021 Arbor Systems hiring-signal." The evaluator's `signal_grounding_check` grades whether the body references tokens from the signal line; stubs have no meaningful tokens to match.

The fix for the next revision is to author plausible specific signals (amount, date, role count) at template expansion time — Liu et al. (COLM 2024) Section 3: synthetic quality depends on **specificity of the seed**, not volume alone.

### Contamination and inter-rater agreement

The three-check protocol (8-gram overlap on inputs, embedding cosine **< 0.85**, time-shift verification) targets **input-level** train vs held-out overlap, not output memorization. For the preference-pair training slice, `training_data/contamination_preference_pairs.json` records **91** pairs checked and **0** violations.

The compliant 24-hour inter-rater pass (30 tasks, 64 check-level comparisons) yielded **0.91** overall agreement; every dimension cleared **0.80** after rubric revision (`inter_rater_agreement.md`). The weak point was `format_check` (**0.87**): humans penalized filler openers and hollow superlatives while the machine initially used length only. Adding `filler_opener` and `unsupported_superlative` regexes to `scoring_evaluator.py` closed the gap.

---

## The training experiment

### Path B: SimPO on a text-only Qwen 2.5 0.5B fallback

The project target backbone is Qwen3.5-0.8B. The current Qwen3.5-0.8B HF/Unsloth release is vision-language; TRL CPO routes text prompts through the image processor and breaks on text-only preference pairs. The training notebook uses `unsloth/Qwen2.5-0.5B-Instruct` as an operational text-only fallback — an engineering constraint worth stating in public.

SimPO beats DPO on a free Colab T4 (16 GB): DPO needs a frozen reference model in memory; SimPO is reference-free and fits a workable batch size. SimPO beats ORPO here because the data are **preference pairs only** — no separate SFT corpus. ORPO's SFT term would drag a 0.5B policy toward Tenacious email prose at the expense of general instruction following; SimPO has no SFT term.

Preference pairs use each task's `ground_truth_output` as **chosen** and an LLM-generated violation as **rejected**, validated with `scoring_evaluator.py` and logged in `training_data/preference_pairs_audit.jsonl`. The rejection generator (Qwen on OpenRouter) and any frontier judge are **different families** — preference-leakage hygiene per Li et al. (2025).

**Training slice:** **91** rows in `training_data/preference_pairs.jsonl`, **6** failure categories, **0** contamination flags in `training_data/contamination_preference_pairs.json`. Colab T4: **3** epochs, **81** train / **10** eval pairs, **~129 s** wall time, fp16 LoRA r=16 / α=32, final train loss **4.878**. Eval margin sanity check: **10/10** on the training split. Headline lift is decided on **held-out** tasks only (`ablations/ablation_results.json`, `ablations/significance_test.txt`).

---

## The honest result

### Delta A: trained LoRA vs deterministic baseline on held-out (same metric)

**Definition (paired with `ablations/paired_bootstrap_delta_a.py`):** for each of **47** held-out tasks, the baseline **succeeds** if the deterministic `scoring_evaluator.py` scores **prefer** `ground_truth_output` over `candidate_output`, or the two bodies are identical. The trained judge **succeeds** if the LoRA's preference margin agrees with that same ordering (or tie). This is **one** metric end to end — not a mix of all-checks-pass for the baseline and preference accuracy for the model.

| Condition | Preference-aligned rate | n |
|---|---|---|
| Deterministic baseline | **14.9%** | 7/47 |
| Trained LoRA | **91.5%** | 43/47 |
| **Delta A** | **+76.6 pp** | |
| 95% bootstrap CI (50 000 resamples, seed 42) | **[+63.8 pp, +87.2 pp]** | |
| One-sided exact paired binomial/McNemar *p* | **0.000000000015** | 36 trained wins / 0 reversals |

**Descriptive sidebar:** the Week 10 **candidate** bodies pass all deterministic checks on **11/47** tasks (**23.4%**) — a useful raw quality readout, but **not** the Delta A numerator. The baseline hits **7/47** because the evaluator often prefers the reference even when the candidate fails some checks.

By category, the trained judge reaches 100% on bench_overcommitment, dual_control_coordination, gap_overclaiming, signal_overclaiming, and tone_drift; **icp_misclassification** stays **2/6 (33.3%)** — the weakest training slice (six pairs) and an open problem.

### Delta B: trained LoRA vs prompt-only same backbone

Same held-out preference-margin procedure: base `Qwen2.5-0.5B-Instruct` without LoRA scores **48.9%** (23/47); the trained adapter scores **91.5%** (43/47) — **+42.6 pp**, 95% CI **[+25.5 pp, +59.6 pp]**, exact paired binomial/McNemar *p* = **0.000017940998**. Prompt-only already clears dual_control_coordination and signal_overclaiming on this slice; the adapter's lift concentrates in gap_overclaiming and tone_drift, with modest ICP gains (0/6 → 2/6).

### Cost–latency Pareto

Training used **$0** billed GPU on Colab T4 (`cost_pareto.colab_cost_usd` in `ablations/ablation_results.json`; ~**2.16** minutes wall time). **Inference** on the held-out preference pass: median **~369 ms** per task with the LoRA judge vs **~96 ms** for the prompt-only backbone — higher latency for a stronger rejection layer. Dataset authoring included **live** OpenRouter calls for preference-pair generation (`training_data/preference_pairs_audit.jsonl`, `mode: "live"`); API spend is logged in `cost_log.csv` — **~$0.02** for 112 qwen/qwen3-8b calls (67K input + 43K output tokens at $0.10/M).

### What did not work

**ICP routing** remains the failure mode with the fewest pairs and the worst held-out accuracy. **Stub signal lines** make `signal_grounding_check` look worse than real-brief behavior would. **Delta B** is uneven: training helps most where the prompt-only model was blind, not everywhere.

---

## What is next

1. **Thread-level coherence** — grade replies against prior turns, not isolated drafts.  
2. **Pricing scope** — enforce `pricing_sheet.md` bands on quoted TCV.  
3. **LinkedIn-roast heuristic** — style-guide anti-pattern as an LLM-judge dimension.  
4. **Multi-signal calibration** — score against the **weakest** signal in a brief, not a single scalar tier.

---

*Dataset: https://huggingface.co/datasets/Natnaela/tenacious-bench*  
*Code: https://github.com/Natnael-Alemseged/SalesConversion-Bench*  
*Community: [τ²-Bench issue #293 — structured-context evaluation gaps](https://github.com/sierra-research/tau2-bench/issues/293)*
