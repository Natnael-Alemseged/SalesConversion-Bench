# When Generic Benchmarks Fail: Building a Sales-Domain Evaluation Bench from Scratch

*By Natnael Alemseged*

---

## The gap that τ²-Bench retail cannot measure

[INTRO — 2-3 sentences on the Tenacious agent and the problem it solves. Then: the question the executive team asked that a generic benchmark cannot answer.]

When the Tenacious executive team asked "how do we know this works for our business, our voice, our segments, our bench?" — the honest answer was: we don't. Not because the Week 10 agent was untested, but because the tests we had were the wrong tests.

τ²-Bench retail measures whether a sales agent can navigate a generic retail conversation. Tenacious needs an agent that can check bench capacity against a real JSON summary, route prospects to the right ICP segment based on layoff and funding signals, and phrase outreach appropriately for the confidence level of the underlying data. These are not things any public benchmark grades.

The audit memo I wrote on Day 1 listed eight probe IDs from the Week 10 failure library that τ²-Bench retail would have passed: P-009 through P-012 (bench overcommitment at 100% trigger rate), P-001 and P-004 (ICP misrouting at 54%), P-005 and P-019 (assertive phrasing under weak signal). A retail benchmark would score those as acceptable because the outputs are fluent. They are not acceptable for Tenacious because they make promises the company cannot keep.

---

## How I found the gap: the audit method

[AUDIT METHOD — describe the failure taxonomy, probe library, what the Week 10 traces showed, and why that pointed to a critic rather than generation quality improvement.]

The Week 10 evidence was more useful than I expected. The failure taxonomy at `week_10_data/failure_taxonomy.md` showed that bench_overcommitment triggered on every single bench-feasibility probe (40/40). This is not a distribution problem — it is a systematic absence of a check. The agent's generator never consulted `bench_summary.json` before committing capacity.

The same pattern held for ICP routing: 20 of 37 probes routed the wrong segment. In both cases, the structured context fields (bench_summary, signal_confidence_tier, icp_segment) were available in the input. The generator simply did not use them.

This pointed immediately to Path B rather than Path A. The outputs were fluent — no generation quality problem. The problem was that the system had no mechanism to detect when a fluent output violated a hard business rule.

---

## Building the benchmark: how dataset construction actually works at small data

[DATASET BUILD — 4 authoring modes, multi-LLM routing, judge filter, contamination protocol. Name the hard design choices.]

### The four authoring modes

[FILL IN: trace-derived, programmatic, multi-LLM synthesis, hand-authored — describe each briefly and the tradeoffs]

### The routing decision I would make differently

The multi-LLM synthesis pipeline routes to Qwen (generator) and Claude (judge) by design — preference-leakage prevention requires different model families for generation and evaluation (Li et al., 2025). In practice, the synthetic signal lines produced by the cheap generator tier are stubs: `"Ref=tbv02-0021 Arbor Systems hiring-signal."` rather than real grounded signals like `"You closed a $14M Series A in February and your Python roles increased from 2 to 7 in 60 days."` The evaluator's signal_grounding_check cannot grade stub signal lines reliably, which created calibration noise in the inter-rater agreement pass.

The fix for v0.2 is to write real signal lines at authoring time even for programmatic tasks — not ground them in live data (expensive), but generate plausible specific signals (amount, date, role count) as part of the template expansion. This is a lesson from Liu et al. (COLM 2024) Section 3: synthetic data quality depends on the specificity of the seed, not just the volume of expansion.

### Contamination: three checks, one surprise

[FILL IN: 8-gram, embedding, time-shift. Note what the actual contamination check found.]

The contamination results in `contamination_check.v0.2.json` show [FILL IN AFTER ABLATIONS].

### Inter-rater agreement and what it revealed about the rubric

The first inter-rater agreement run (immediate re-label, non-compliant) produced 0.72 overall agreement. The 24-hour compliant run reproduced the same number. The main drag was `format_check` at 0.40.

The pattern was diagnostic: in Pass 1, I applied a length-only standard. In Pass 2, I was unconsciously also checking for filler openers ("I hope this email finds you well") and unsupported superlatives ("world-class"). The machine evaluator was only checking length. The fix was to add two deterministic conditions to `format_check` — filler_opener and unsupported_superlative — which brought the machine check in line with the human bar. This is the right response to below-80% agreement: find the specific divergence, tighten the rubric, re-verify.

---

## The training experiment

### Path B: SimPO on Qwen 3.5 0.8B

[FILL IN AFTER TRAINING RUN — backbone, LoRA rank/alpha, training loss curve summary, wall time]

The preference pair construction used `ground_truth_output` from each training task as the chosen output and an LLM-generated violation as the rejected output. Each pair was verified by `scoring_evaluator.py` before saving: chosen must pass all rubric checks, rejected must fail at least one.

Final training set: [FILL IN] pairs across 6 failure categories after contamination filtering.

The generator model (Qwen, via OpenRouter) differs from the judge model family (Claude) by design — this is the preference-leakage prevention protocol from Li et al. (2025).

---

## The honest result

### Delta A: trained judge vs Week 10 baseline on Tenacious-Bench held-out

[FILL IN AFTER ABLATIONS]

### Delta B: trained judge vs prompt-engineered version, same backbone

[FILL IN AFTER ABLATIONS — report honestly even if negative]

### What did not work

[FILL IN AFTER ABLATIONS]

---

## What is next

Four things Tenacious-Bench v0.1 still does not capture, and what v0.2 would need to add:

1. **Thread-level coherence** — the current benchmark evaluates single emails in isolation. A real deployment needs to grade whether the agent's reply is consistent with the prior thread, not just whether it passes standalone checks.
2. **Pricing scope violations** — `pricing_sheet.md` defines public quotable bands. The evaluator does not currently check whether quoted prices are within those bands. A regex or structured-extract check would catch BAD #11-style fabricated TCV quotes.
3. **LinkedIn-roast test** — the style guide includes a named anti-pattern test ("would this get screenshotted and posted on LinkedIn?"). This is not deterministically gradable but is a strong signal the LLM judge should grade.
4. **Multi-signal confidence integration** — the current `signal_confidence_tier` is a single scalar. Real Tenacious briefs combine funding signals, role-velocity signals, and layoff signals at different confidence levels. A v0.2 rubric should grade whether the draft's confidence is calibrated to the weakest signal in the brief, not the strongest.

---

*Dataset: [HuggingFace URL]*
*Code: [GitHub URL]*
*Community: [GitHub issue / forum link]*
