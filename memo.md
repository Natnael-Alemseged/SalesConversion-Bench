# Tenacious-Bench Week 11 — Executive Memo

**To:** Tenacious Leadership  
**From:** Natnael Alemseged  
**Date:** 2026-05-02  
**Re:** Path B SimPO Judge — Evaluation Results and Deployment Recommendation

---

## Page 1 — Results and Recommendation

### Summary

The Week 10 agent failed every bench-capacity probe (40/40) and misrouted 54% of ICP classification probes because it produced fluent outputs that ignored structured context fields. A preference-tuned critic (Path B) was built to detect these violations: a SimPO LoRA adapter trained on 91 verified preference pairs, evaluated against a 47-task held-out benchmark purpose-built for Tenacious's failure modes. The trained critic correctly identifies the better output on 91.5% of held-out tasks versus a 23.4% baseline — a lift of **+68.1 percentage points** that is statistically significant and reproducible.

### Delta A — Trained Judge vs Week 10 Baseline

| Condition | Pass rate |
|---|---|
| Week 10 baseline (deterministic scoring, raw agent outputs) | 23.4% (11/47) |
| Trained LoRA judge (preference accuracy, held-out split) | **91.5% (43/47)** |
| **Lift** | **+68.1pp** |
| 95% bootstrap CI (50 000 resamples, seed 42) | [+55.3pp, +80.9pp] |
| p-value (one-sided paired bootstrap) | **< 0.0001** |

By failure category: bench_overcommitment (11/11 = 100%), dual_control_coordination (7/7 = 100%), gap_overclaiming (11/11 = 100%), signal_overclaiming (6/6 = 100%), tone_drift (6/6 = 100%). **Exception: icp_misclassification 2/6 = 33.3%.** This category remains unresolved and must be treated as a known gap at deployment.

### Delta B — Trained Judge vs Prompt-Engineered Same Backbone

The prompt-only baseline loads the same `Qwen2.5-0.5B-Instruct` backbone without the LoRA adapter and scores the same 47 held-out preference comparisons. It reaches 48.9% (23/47). The trained LoRA reaches 91.5% (43/47), a **+42.6pp** lift with 95% bootstrap CI **[+29.8pp, +57.4pp]** and p < 0.0001. The largest gains are gap_overclaiming (0/11 → 11/11) and tone_drift (0/6 → 6/6); prompt-only already solved dual_control_coordination and signal_overclaiming on this slice.

### Delta C — Public Benchmark Context (Informational Only)

For rubric completeness, `ablations/ablation_results.json` now includes an informational Delta C imported from the external `conversion-engine` repo rather than re-running `tau2-bench` here. That external sealed retail method (`dual_control_v2`) scored **0.45 pass@1** against a published **0.42** `tau2-bench` retail reference ceiling, for a **+3.0pp** gap. This is useful benchmark context, but it is **not directly comparable** to Tenacious-Bench Delta A/B because the domain, task family, and metric differ: `tau2-bench` measures retail task completion, while this repo's main ablations measure Tenacious-specific preference accuracy over judged outreach outputs.

### Cost and Latency

| Metric | Value |
|---|---|
| Training wall time (Tesla T4, free Colab) | **2.16 minutes** |
| Training cost | **$0** |
| Inference latency p50 | **368.76 ms** |
| LoRA adapter | [Natnaela/tenacious-judge-lora](https://huggingface.co/Natnaela/tenacious-judge-lora) |

### Recommendation

**Deploy with caveat.** The trained critic is ready for use as a pre-send rejection filter on bench_overcommitment, dual_control_coordination, gap_overclaiming, signal_overclaiming, and tone_drift. Do not rely on it for ICP segment routing decisions until the icp_misclassification category is retrained with more targeted pairs. The kill-switch condition and deployment constraints are on Page 2.

---

## Page 2 — Skeptic's Appendix

### Four Failure Modes Not Captured by This Benchmark

**1. Thread-level coherence.** Every task in Tenacious-Bench v0.2 is evaluated in isolation. A real deployment must grade whether the reply is consistent with the prior thread — not just whether it passes standalone rubric checks. An agent that passes all five checks in isolation can still contradict a prior commitment made two emails earlier.

**2. Pricing scope violations.** `pricing_sheet.md` defines public-quotable price bands. The evaluator does not check whether quoted TCV figures fall within those bands. A regex or structured-extract check on the body would catch fabricated quotes of the kind documented in BAD example #11 in the style guide.

**3. LinkedIn-roast test.** The Tenacious style guide names an anti-pattern test: "would this email get screenshotted and posted on LinkedIn as an example of bad outreach?" This is not deterministically gradable. It requires an LLM judge with access to the full style guide — the `llm_judge_hook` stub in `scoring_evaluator.py` is where this belongs in v0.2.

**4. Multi-signal confidence integration.** The current `signal_confidence_tier` is a single scalar. Real Tenacious briefs combine funding signals, role-velocity signals, and layoff signals at different confidence levels. The v0.2 rubric should grade whether the draft's confidence is calibrated to the *weakest* signal in the brief, not the strongest. An agent that accurately reports a high-confidence funding signal while overstating a low-confidence role-velocity signal currently passes.

### Public-Signal Lossiness

The evaluator's `signal_grounding_check` scored 0/30 = 0% on held-out tasks with synthetic stub signal lines (`Ref=tbv02-0021 Arbor Systems hiring-signal.`). This is a dataset construction limitation, not a model limitation: the evaluator checks whether the email body references tokens from the signal line, and stub lines contain no meaningful tokens. The 23.4% baseline therefore understates how the deterministic evaluator would perform on tasks with real grounded signal lines. The v0.2 fix is to write specific plausible signals at authoring time (amount, date, role count) rather than stubs.

### Honest Unresolved Failure: ICP Misclassification

The trained judge correctly prefers the reference output on only 2 of 6 icp_misclassification held-out tasks (33.3%, mean margin −0.26). The likely cause: ICP routing requires reasoning about two segment rules simultaneously, the training set had only 6 pairs in this category, and the rejected outputs in that category were harder to distinguish from the chosen outputs by log-probability alone. More targeted pairs with explicit segment-rule contrast are needed — not simply more total preference pairs.

### Kill-Switch Condition

Remove the trained critic from the deployment pipeline if the icp_misclassification preference accuracy on a freshly drawn sample of 20+ tasks falls below 60%, or if any failure category that currently scores 100% drops below 80% after a model update or prompt change. The evaluator command to recheck is:

```
python3 scoring_evaluator.py --task-file tenacious_bench_v0.2/held_out/tasks.jsonl
```

Compare against `ablations/ablation_results.json` as the reference baseline.
