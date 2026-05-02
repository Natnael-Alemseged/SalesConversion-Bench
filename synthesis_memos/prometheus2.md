# Synthesis Memo: Prometheus 2

Kim et al., *Prometheus 2: An Open-Source Language Model Specialized in Evaluating Other Language Models* (2024).

## Design choice I disagree with (Section 3 — 100K preference pairs as the minimum viable scale)

Prometheus 2 is trained on approximately 100,000 preference pairs drawn from Feedback Collection and Preference Collection — both sourced from GPT-4 annotations over a large instruction-following dataset. The paper's implicit argument is that reliable open judge behavior requires this scale: the training section does not offer a scaling ablation below ~50K pairs and presents 100K as the baseline that produces useful transfer.

The selection of 100K as the working scale is partially a consequence of the evaluation target: Prometheus 2 is designed to generalize across arbitrary rubrics on arbitrary tasks, essentially replicating GPT-4 judge behavior on unseen dimensions. Generalizing to arbitrary rubrics requires enough training examples to cover the rubric distribution. At 100K, the data covers enough variation that the judge can interpolate to unseen rubrics at evaluation time.

## Why this scale cannot be replicated for Tenacious-Bench

The preference pair budget for this project is fixed at the scale of the training partition: 240 tasks, of which ~120 were used as the generation pool. After verification (chosen must pass all 5 checks; rejected must fail at least one) and contamination filtering (12 pairs removed), the final dataset is 91 pairs. This is approximately 1/1000th of Prometheus 2's training data.

The reason is not laziness or resource shortage — it is that generalizing to arbitrary rubrics is not the goal. The Tenacious judge only needs to learn five deterministic checks on one domain: bench capacity, ICP routing, signal confidence calibration, tone compliance, and booking stage. These five checks are stable and narrow. A judge that reliably applies them on Tenacious-Bench tasks does not need to generalize to poetry evaluation or code review.

This is the key design divergence: Prometheus 2 targets breadth (arbitrary rubric generalization); Tenacious-Bench targets depth (reliable narrow-domain business-rule verification). Depth at small scale is achievable in a way that breadth at small scale is not. If the Tenacious-Bench judge were designed to evaluate arbitrary sales emails from any company, 91 pairs would be clearly insufficient. For the specific five-check rubric on this domain, 91 verified pairs may produce a judge with usable agreement rates.

## What Prometheus 2 gets right that Tenacious-Bench replicates

**Preference pair construction from rubric-anchored ground truth.** Prometheus 2 generates preference pairs by: (1) defining a rubric dimension, (2) generating a chosen output that scores high on that dimension, (3) generating a rejected output that scores low. This is exactly the construction in `generation_scripts/build_preference_pairs.py`: `FAILURE_INSTRUCTIONS` defines the rubric dimension, `ground_truth_output` is the chosen (pre-verified), the LLM-generated violation is the rejected (post-verified to fail at least one check).

**Separation between generator model family and judge model family.** Prometheus 2 uses GPT-4 for feedback generation and trains an open judge on that feedback — two different model families. `generation_scripts/routing_policy.md` documents the same rotation for Tenacious-Bench: Qwen (via OpenRouter) generates the rejected outputs; Claude/GPT-4 (judge model family) runs `generation_scripts/judge_filter.py`. This is the preference-leakage prevention protocol from Li et al. (2025), implemented in the same spirit as Prometheus 2's construction approach.

**Evaluation against human agreement as the primary metric.** The paper reports Pearson/Kendall correlation with human judgments as the core benchmark. Inter-rater agreement against a second human pass (documented in `inter_rater_agreement.md`) follows the same logic: the right question is not whether the automated judge gives a specific score, but whether it agrees with a calibrated human rater at the rubric dimension level.

## What cannot be replicated at this scale

The Prometheus 2 training produces a judge that generalizes. Tenacious-Bench's trained judge will not generalize — it will specialize. If a new failure category emerges in Week 12 (e.g., pricing scope violations from `pricing_sheet.md`), the trained judge will need new preference pairs for that dimension. Prometheus 2's generalization to unseen rubrics is a genuine capability advantage that requires data scale and rubric diversity that this project does not have.

This is a known limitation documented in `blog_post_draft.md` under "What is next" — the judge is narrow by design, and the v0.2 roadmap explicitly names the steps needed to expand it (thread-level coherence, pricing scope, multi-signal confidence integration).
