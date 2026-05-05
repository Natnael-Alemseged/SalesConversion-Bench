# Tenacious-Bench Week 11 Executive Memo
**Date:** 2026-05-02
**Re:** Path B SimPO Judge

## Page 1 — The Decision
### Summary
The Week 10 agent failed every bench-capacity probe and misrouted 54% of ICP probes because it often ignored structured context even when the prose looked fluent. I trained a Path B SimPO LoRA critic on 91 verified preference pairs and evaluated it on a 47-task Tenacious-Bench held-out split built around those failure modes. On the held-out preference metric, the trained critic reached **91.5%** (43/47) versus a **14.9%** deterministic Week 10 baseline (7/47), a **+76.6pp** lift with **95% paired bootstrap CI [+63.8pp, +87.2pp]** and **one-sided paired bootstrap p < 0.0001**.

### Delta A
The deterministic baseline is measured on the **same preference-accuracy target** as the trained judge: candidate output versus ground-truth output under the same rubric. By category, the trained judge is **100%** on bench_overcommitment (11/11), dual_control_coordination (7/7), gap_overclaiming (11/11), signal_overclaiming (6/6), and tone_drift (6/6), with one clear weakness: **icp_misclassification 33.3% (2/6)**.

### Delta B
The prompt-engineered baseline uses the **same `Qwen2.5-0.5B-Instruct` backbone and same intervention shape** as the trained condition: same scoring prompt, same two-pass candidate-vs-reference comparison, same 47 held-out tasks, but **no LoRA adapter**. It reaches **48.9%** (23/47). The trained LoRA reaches **91.5%** (43/47), a **+42.6pp** lift with **95% bootstrap CI [+29.8pp, +57.4pp]** and **p < 0.0001**. This result should be read honestly: training is **not necessary** for dual_control_coordination or signal_overclaiming on this backbone, but it is the difference-maker for gap_overclaiming and tone_drift, where prompt-only failed.

### Cost, Latency, and Production Recommendation
Measured on the local Unsloth setup used for evaluation, inference cost is **$0/task with the LoRA judge** and **$0/task for prompt-only** because both run locally with no external API spend. **Production agent inference (OpenRouter path):** The current inference stack routes classification calls through OpenRouter to `qwen/qwen3-235b-a22b`. Provider-side prompt caching has not been verified for this route, so caching should not be counted as a confirmed cost-saving mechanism. Current cost-control options include reducing prompt length, using a smaller model, replacing simple classifications with deterministic rules, or switching to a provider/model combination with documented prompt caching support. The tradeoff is latency, not marginal API cost: **368.76 ms p50** for the trained judge versus **96.06 ms p50** for prompt-only, or about **+272 ms**. **Recommendation: deploy with caveat.** Use the trained critic as a pre-send rejection filter for bench_overcommitment, dual_control_coordination, gap_overclaiming, signal_overclaiming, and tone_drift, where held-out performance is 100%. **Do not deploy it for ICP segment routing** until targeted retraining lifts that slice from **33.3%** to at least **80%** held-out preference accuracy. Production sign-off should require **p50 latency under 500 ms per evaluation pass** on the intended inference SKU and **marginal hosting cost below $0.00001/task**; the held-out T4 run cleared both gates at **368.76 ms** and roughly **$0.0000014/task**.

## Page 2 — Skeptic's Appendix
### Four Tenacious-Bench v0.1 Coverage Gaps
**1. Thread-level coherence:** v0.1 has no multi-turn thread tasks, so it cannot grade contradictions across a reply sequence. **v0.2 addition:** a thread-coherence partition with prior email, reply, and follow-up context.

**2. Pricing scope violations:** v0.1 has no tasks whose pass/fail depends on quoting the right TCV or price band. **v0.2 addition:** pricing-band tasks with allowed-range metadata and numeric extraction checks.

**3. Reputational tone failure:** v0.1 has no task family for “would this get screenshotted as bad outreach” from the Tenacious style guide. **v0.2 addition:** a reputational-tone partition seeded with style-guide-violating drafts and judged against the guide.

**4. Private champion context:** v0.1 has no tasks where the correct move depends on non-public relationship facts such as a dormant champion or warm intro path. **v0.2 addition:** a synthetic private-context field in the brief plus tasks that fail when that context is mishandled.

### Public-Signal Lossiness
Ground truth for included tasks is necessarily lossy because it relies on **public hiring signals, layoffs data, funding headlines, and redacted case-study-style briefs** rather than the full private account context a live Tenacious rep would have. The specific failure path is that these signals can be **stale or stripped of named-account nuance**, so an output that parrots the public brief can score as correct even when it would underperform in a real sales motion. That means the reported numbers likely **overstate absolute production quality**, even though **Delta A and Delta B remain valid relative comparisons** because candidate and reference outputs are judged under the same brief.

### Honest Unresolved Training Failure
The one unresolved training failure is **ICP misclassification**. After SimPO tuning, the LoRA adapter still assigns the **wrong log-probability ordering** on many dual-segment ICP preference pairs, so the trained judge prefers the weaker candidate when it must weigh two segment rules at once. This appears in held-out performance as **2/6 correct (33.3%)** with **mean margin -0.26**. The next step is not “more data” in general; it is **targeted contrast pairs** that isolate segment-rule tradeoffs, followed by a re-check that this slice reaches **at least 80%** without regressing the categories already at 100%.

### Kill-Switch Trigger
In production, run a **weekly random audit of at least 25 critic decisions** and **disable the trained critic, reverting to the prompt-only judge on the same backbone**, if **blind human reviewers mark 35% or more of sampled rejections as clear false positives for two consecutive weeks**. That threshold is anchored to the current worst held-out slice, **33.3% on ICP**: if live false rejects rise above that level for two weeks, the deployment is collapsing toward the known failure floor. Also disable and revert if the **human override rate on critic rejections exceeds 30% for two consecutive weeks**, because at that point the critic is adding send-time friction without enough filtering value to justify the measured **+272 ms** latency cost.
