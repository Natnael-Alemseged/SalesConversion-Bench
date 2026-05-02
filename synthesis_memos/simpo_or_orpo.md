# Synthesis Memo: SimPO vs ORPO — Choosing a Reference-Free Algorithm

Meng, Xia, and Chen, *SimPO: Simple Preference Optimization with a Reference-Free Reward* (NeurIPS 2024).
Hong, Lee, and Thorne, *ORPO: Monolithic Preference Optimization without Reference Model* (EMNLP 2024).

Both papers eliminate the reference model. This memo explains why SimPO is selected over ORPO for this project.

## Design choice I disagree with in ORPO (Section 2 — monolithic SFT+preference loss)

ORPO's core design is to merge the SFT objective and the preference objective into a single loss term — a log-likelihood term on the chosen output combined with an odds-ratio penalty on the rejected output. Hong et al. argue this is elegant: a single training pass aligns the model both toward the distribution of good outputs and away from bad outputs simultaneously, without needing a separate SFT stage.

The implicit requirement is that the chosen outputs collectively form a coherent SFT corpus. ORPO's monolithic loss treats the chosen outputs as supervised training data and the rejected outputs as contrast data. If the chosen outputs are a representative sample of the target behavior distribution, this works well. Section 3 validates on Phi-2 and Llama-2 fine-tuning tasks where the chosen outputs are long-form instruction responses — sufficient in quantity and stylistic range to anchor the SFT term.

## Why ORPO does not fit the Tenacious-Bench training data

The `training_data/preference_pairs.jsonl` file contains 91 preference pairs. The chosen outputs are the verified `ground_truth_output` fields from the training partition of Tenacious-Bench — short outreach emails, 3–6 sentences each, drawn from 6 failure categories. This is not an SFT corpus. It is a preference-verification set.

Using ORPO on this data would apply an SFT gradient to 91 emails spanning 6 narrow failure modes. The expected result is that the model's general instruction-following capability degrades toward the narrow Tenacious email format — exactly the outcome ORPO's monolithic loss is designed to avoid when the SFT corpus is large and diverse. At this scale and domain, the SFT component of ORPO is a liability, not a benefit.

The same concern does not apply to SimPO. SimPO's loss function does not contain an SFT term. It minimizes the margin between chosen and rejected log-probability ratios, normalized by sequence length, without pulling the model toward the chosen outputs as a distribution. The policy is updated to prefer chosen over rejected; it is not trained to imitate chosen. This is the correct formulation when the training set is narrow.

## Why SimPO is selected

SimPO has three properties that match the Tenacious-Bench setup:

**1. No reference model, no SFT objective.** VRAM is free for a larger LoRA rank or increased batch size. On T4 (16 GB), this is the difference between `r=16` LoRA at `batch_size=2` and `r=8` LoRA at `batch_size=1`.

**2. Length-normalized reward.** SimPO normalizes log-probabilities by sequence length before computing the margin. Tenacious-Bench chosen outputs are typically longer than rejected outputs (the rejected heuristics use filler openers and superlatives; the chosen outputs are substantive and grounded). Without length normalization the model would be penalized for choosing longer outputs regardless of content. The normalization removes this bias.

**3. Margin penalty matched to a hard-boundary reward.** `simpo_gamma=0.5` enforces a minimum margin between chosen and rejected reward before the pair contributes positive gradient. For a preference dataset where the boundary is deterministic (chosen passes all 5 evaluator checks; rejected fails at least one), this margin acts as a minimum confidence threshold — pairs where the model already clearly prefers chosen contribute less gradient than ambiguous pairs. This is the correct behavior for a dataset with verified, non-fuzzy labels.

## Where I agree with ORPO

The paper is correct that eliminating the reference model is the right direction for resource-constrained training. The two papers agree on this point; the disagreement is only about whether to add the SFT objective. For a practitioner with a large, high-quality instruction-following dataset, ORPO's monolithic loss would be the stronger choice.

The paper is also correct that the odds-ratio penalty is well-defined without a reference model. The mathematical contribution is sound. The selection of SimPO over ORPO is a data-size and domain-specificity judgment, not a quality judgment on the ORPO algorithm.
