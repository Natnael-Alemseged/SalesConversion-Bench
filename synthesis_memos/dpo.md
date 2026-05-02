# Synthesis Memo: Direct Preference Optimization

Rafailov et al., *Direct Preference Optimization: Your Language Model is Secretly a Reward Model* (NeurIPS 2023).

## Design choice I disagree with (Section 3 — reference model as a stability anchor)

DPO's central design decision is to keep a frozen reference model in memory throughout training and use the KL-divergence from that reference as a regularizer. The paper argues this is necessary to prevent the policy from diverging too far from the pre-trained distribution and collapsing to degenerate outputs. Section 3 treats the reference model as a non-negotiable structural requirement: without it, the implicit reward signal is undefined.

The implicit assumption is that the reference model cost is acceptable — that practitioners can afford to hold a second copy of the base model frozen in GPU memory while the policy trains. For large-scale research setups with 80 GB A100s this is true. The paper does not address what happens when this assumption breaks.

## Why this fails for the Tenacious-Bench training setup

The training target is Qwen 2.5 0.5B on a free Colab T4 (16 GB VRAM). A 16-bit LoRA run of a 0.5B model requires approximately 3–4 GB for the policy. A frozen reference model of the same size adds the same cost again, plus optimizer states and activations. At full batch size DPO on this slot runs at `per_device_train_batch_size=1` with aggressive gradient accumulation — or does not run at all on the larger Qwen 2.5 3B variant that would otherwise improve judge quality.

The Week 10 failure evidence does not require a strong KL regularizer to be useful. The failures in probe IDs `P-009` through `P-012` (bench overcommitment) and `P-001`, `P-004` (ICP misrouting) are binary: the output either asserts a capacity number that exceeds the bench, or it does not. The reward landscape is step-function, not smooth. A KL penalty calibrated for smooth reward optimization on a general-purpose assistant is mismatched to this structure — it will dampen useful gradient signal at the hard decision boundaries.

## What I use instead

SimPO (Meng, Xia, and Chen, NeurIPS 2024) eliminates the reference model entirely by using length-normalized log-probabilities under the policy as the reward signal. The margin penalty (γ) replaces the KL regularizer. At `simpo_gamma=0.5`, the training objective penalizes pairs where the policy does not cleanly prefer the chosen output — which is exactly the right signal for Tenacious-Bench's step-function reward structure where the chosen/rejected boundary is deterministically verified.

Concretely: every `chosen` in `training_data/preference_pairs.jsonl` passed all 5 checks in `scoring_evaluator.py` before being accepted. Every `rejected` failed at least one. The margin is not ambiguous. DPO's KL anchor is overkill for this boundary and costs VRAM that could instead go to a larger LoRA rank or larger base model.

## Where I agree

DPO's core insight — that the reward model is implicit in the policy ratio and does not need to be trained separately — is correct and underlies SimPO as well. The explicit reward model step is unnecessary; both algorithms learn from preference pairs without it. The contribution of Rafailov et al. is real; SimPO is an extension of it, not a rejection.

The paper is also correct that preference pair quality matters more than quantity. The contamination filtering and dual-verification protocol in `generation_scripts/build_preference_pairs.py` follows directly from this: 91 high-quality verified pairs are more useful than 500 unverified pairs where the rejected output actually passes the rubric.
