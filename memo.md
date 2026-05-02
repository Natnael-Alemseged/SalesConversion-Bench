# Tenacious-Bench Week 11 — Executive Memo

**To:** Tenacious Leadership  
**From:** Natnael Alemseged  
**Date:** 2026-05-02  
**Re:** Path B SimPO Judge — Evaluation Results and Deployment Recommendation

---

## Page 1 — Results and Recommendation

### Summary

The Week 10 agent failed every bench-capacity probe (40/40) and misrouted 54% of ICP classification probes because it produced fluent outputs that ignored structured context fields. A preference-tuned critic (Path B) was built to detect these violations: a SimPO LoRA adapter trained on 91 verified preference pairs, evaluated against a 47-task held-out benchmark purpose-built for Tenacious's failure modes. On an apples-to-apples preference metric, the trained critic correctly identifies the better output on 91.5% of held-out tasks versus a 14.9% deterministic baseline — a lift of **+76.6 percentage points** (95% paired bootstrap CI **[+63.8pp, +87.2pp]**, 50 000 resamples, seed 42; one-sided paired bootstrap **p < 0.0001**).

### Delta A — Trained Judge vs Week 10 Baseline

| Condition | Pass rate |
|---|---|
| Week 10 baseline (deterministic preference accuracy, held-out split) | 14.9% (7/47) |
| Trained LoRA judge (preference accuracy, held-out split) | **91.5% (43/47)** |
| **Lift** | **+76.6pp** |
| 95% bootstrap CI (50 000 resamples, seed 42) | [+63.8pp, +87.2pp] |
| p-value (one-sided paired bootstrap) | **< 0.0001** |

The deterministic baseline here now uses the **same target** as the trained judge: for each held-out task, score `candidate_output` and `ground_truth_output` under the same rubric and count success only when the baseline prefers the reference (or the two texts are identical). For descriptive context, the old raw candidate-output pass rate was 23.4% (11/47), but that figure is no longer used in Delta A because it is not the same metric as preference accuracy.

By failure category, the trained judge reaches bench_overcommitment (11/11 = 100%), dual_control_coordination (7/7 = 100%), gap_overclaiming (11/11 = 100%), signal_overclaiming (6/6 = 100%), tone_drift (6/6 = 100%). **Exception: icp_misclassification 2/6 = 33.3%.** This category remains unresolved and must be treated as a known gap at deployment.

### Delta B — Trained Judge vs Prompt-Engineered Same Backbone

The prompt-only baseline loads the same `Qwen2.5-0.5B-Instruct` backbone without the LoRA adapter and scores the same 47 held-out preference comparisons. It reaches 48.9% (23/47). The trained LoRA reaches 91.5% (43/47), a **+42.6pp** lift with 95% bootstrap CI **[+29.8pp, +57.4pp]** and p < 0.0001. The largest gains are gap_overclaiming (0/11 → 11/11) and tone_drift (0/6 → 6/6); prompt-only already solved dual_control_coordination and signal_overclaiming on this slice.

### Delta C — Public Benchmark Context (Informational Only)

For rubric completeness, `ablations/ablation_results.json` now includes an informational Delta C imported from the external `conversion-engine` repo rather than re-running `tau2-bench` here. That external sealed retail method (`dual_control_v2`) scored **0.45 pass@1** against a published **0.42** `tau2-bench` retail reference ceiling, for a **+3.0pp** gap. This is useful benchmark context, but it is **not directly comparable** to Tenacious-Bench Delta A/B because the domain, task family, and metric differ: `tau2-bench` measures retail task completion, while this repo's main ablations measure Tenacious-specific preference accuracy over judged outreach outputs.

### Cost and Latency

| Metric | Value |
|---|---|
| Training wall time (Tesla T4, free Colab) | **2.16 minutes** (`training/training_run.log`, `ablations/ablation_results.json`) |
| Training billed cost | **$0** (`cost_pareto.colab_cost_usd`) |
| **Marginal inference $ / held-out task** (47 tasks × 2 conditions, local Unsloth) | **$0 vs $0** (`cost_log.csv` evaluation row: LoRA judge and prompt-only baseline both local; no API spend) |
| One-time dataset authoring (logged) | **~$0.02** estimated for live OpenRouter preference-pair calls (`cost_log.csv`; audit: `training_data/preference_pairs_audit.jsonl`) — amortizes over all pairs, not per future send |
| Inference latency p50, trained LoRA judge | **368.76 ms** (`delta_a.trained_judge` in `ablations/ablation_results.json`) |
| Inference latency p50, prompt-only same backbone | **96.06 ms** (`delta_b.prompt_engineered_baseline`) |
| Latency ratio (trained / prompt-only, same machine) | **~3.8×** — deployment trades **~272 ms extra p50 per preference decision** for the **+42.6pp** gain vs prompt-only on the same backbone (see Delta B) |
| Dataset authoring (full reconciliation) | Use provider billing export; audit trail: `training_data/preference_pairs_audit.jsonl` |
| LoRA adapter | [Natnaela/tenacious-judge-lora](https://huggingface.co/Natnaela/tenacious-judge-lora) |

**Production implication:** Marginal **API $/task** in this stack is **~$0** when the judge runs **on owned GPU/CPU**; the decision is whether **~3.8×** judge latency and **hosting capacity** are acceptable for the measured **preference-accuracy** lift. Cloud **$/hour** for a chosen SKU still needs a separate quote — not logged here.

### Recommendation

**Deploy with caveat.** Held-out **Delta A** shows **+76.6pp** preference accuracy (**91.5%** vs **14.9%**, 95% CI **[+63.8pp, +87.2pp]**); **Delta B** confirms **+42.6pp** vs prompt-only on the **same backbone** (**91.5%** vs **48.9%**, CI **[+29.8pp, +57.4pp]**). The trained critic is ready for use as a pre-send rejection filter on bench_overcommitment, dual_control_coordination, gap_overclaiming, signal_overclaiming, and tone_drift — where the judge is **100%** on held-out slices. **Do not deploy for ICP segment routing:** icp_misclassification is **2/6 (33.3%)** on held-out, so routing decisions must stay human or rule-based until retrained with targeted pairs. Accept deployment only if **~3.8×** judge **p50 latency** vs prompt-only (see Cost and Latency) fits send-time SLOs on the chosen hardware. Kill-switch and audit triggers are on Page 2.

---

## Page 2 — Skeptic's Appendix

### Four Failure Modes With No Task Coverage in Tenacious-Bench v0.1

*v0.1 had no task family that exercises these behaviors end-to-end; v0.2 additions below are the coverage fix (some remain roadmap if not yet in `held_out`).*

**1. Thread-level coherence.** v0.1 tasks grade **single-shot** outreach; **no** multi-turn thread is in the task inventory. **v0.2 addition:** a **thread-coherence** partition (prior email + reply + follow-up) with rubric checks for contradictions across turns.

**2. Pricing scope violations.** v0.1 does **not** include tasks whose pass/fail hinges on **TCV or quote band** vs `pricing_sheet.md`. **v0.2 addition:** tasks with explicit **allowed band** metadata plus **regex / structured extract** on quoted numbers in the body.

**3. LinkedIn-roast / reputational tone.** v0.1 has **no** probe for “would this get screenshotted as bad outreach” from the style guide. **v0.2 addition:** **`llm_judge_hook`** in `scoring_evaluator.py` with style-guide context (non-deterministic but targeted).

**4. Private referral / champion context.** Briefs are built from **public** signals and **redacted** case-study patterns; v0.1 includes **no** tasks where the correct motion depends on **non-public relationship facts** (e.g. dormant champion, internal blocker, warm intro via a named ally). **v0.2 addition:** a **synthetic private-context** field in the brief JSON and tasks that fail if the draft mishandles that metadata.

### Public-Signal Lossiness

**Ground-truth faithfulness (existing tasks):** Rubric fields and scorer inputs are **proxies** for a live Tenacious motion — **public hiring and layoffs text**, **funding headlines**, and **redacted case-study-style** briefs. **Mechanism:** those signals can **lag** org reality or **omit named-account nuance** that a rep would use in production. The bench still scores “correct” relative to the **provided** brief, so an output that **parrots stale public facts** can **match reference** while **underperforming** in a live account. **Headline impact:** **Delta A/B compare candidate vs reference under the same brief**, so the **relative lift** is internally valid; **absolute** “would this win the deal” quality can still be **optimistic** vs production because the **grounding truth is public-signal–limited**.

**Authoring lossiness (separate issue):** The evaluator's `signal_grounding_check` scored 0/30 = 0% on held-out tasks with **synthetic stub** signal lines (`Ref=tbv02-0021 Arbor Systems hiring-signal.`). Stub lines carry **no scorable tokens**; that is a **dataset construction** issue. The old **23.4%** raw candidate-output pass rate **understates** deterministic performance on tasks with **realistic** signal lines. **v0.2 fix:** author **specific plausible** signals (amount, date, role count) instead of stubs.

### Honest Unresolved Failure: ICP Misclassification

The trained judge correctly prefers the reference output on only 2 of 6 icp_misclassification held-out tasks (33.3%, mean margin −0.26). The likely cause: ICP routing requires reasoning about two segment rules simultaneously, the training set had only 6 pairs in this category, and the rejected outputs in that category were harder to distinguish from the chosen outputs by log-probability alone. More targeted pairs with explicit segment-rule contrast are needed — not simply more total preference pairs.

### Kill-Switch Condition

**Benchmark-regression gate (post-change verification):** Remove the trained critic from the deployment pipeline if **icp_misclassification** preference accuracy on a freshly drawn sample of **20+** tasks falls **below 60%** — **60%** is a deliberate floor **above** the observed held-out **33.3% (2/6)** for that slice, so further collapse means the critic is **not fit for ICP-adjacent filtering**. Also roll back if any category that is **100%** on the current held-out split drops **below 80%** after a **model, adapter, or judge-prompt** change (**80%** = material break from **perfect** slice scores on gap_overclaiming, tone_drift, etc.). Recheck with:

```
python3 scoring_evaluator.py --task-file tenacious_bench_v0.2/held_out/tasks.jsonl
```

Compare against `ablations/ablation_results.json` as the reference baseline.

**Production-observable gate (no full held-out re-run required):** On a **weekly** random sample of **n ≥ 25** critic decisions (stratify approve/reject), if **blind human reviewers** mark **≥35%** of **rejections** as **clear false positives** (wrong block), **disable the critic** and revert to the **prompt-only judge on the same backbone** until the benchmark gate passes again — **35%** is ordered near the **worst held-out slice** failure rate (**~33%** on ICP) so sustained noise at that level is **incompatible** with a pre-send filter. Optionally track **human override rate** (sends approved despite critic reject): **two consecutive weeks** above **30%** triggers the same **disable + revert** pending investigation.
