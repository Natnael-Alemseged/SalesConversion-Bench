# Methodology Rationale

## Path Selection: Path B (Preference-Tuned Judge / Critic)

### Training algorithm: SimPO (Simple Preference Optimization without Reference Model)

SimPO is selected over DPO and ORPO for three reasons grounded in the specific constraints of this project:

**1. Reference-free training fits the resource envelope.**
DPO requires a frozen reference model in memory during training. On a free Colab T4, that doubles the effective memory requirement. SimPO (Meng, Xia, and Chen, NeurIPS 2024) eliminates the reference model by using a length-normalized reward derived directly from the policy log-probabilities. The same training slot runs SimPO at full batch size or DPO at half batch size — SimPO wins on the cost-Pareto.

**2. The margin penalty matches the task structure.**
SimPO's objective penalizes pairs where the chosen-rejected margin is below a threshold γ. For Tenacious-Bench, the margin signal is clearer than for general preference tasks: chosen outputs are verified to pass all deterministic checks, rejected outputs are verified to fail at least one. The boundary is hard, not fuzzy. SimPO's margin-based objective is better suited to this step-function reward landscape than DPO's KL-regularized formulation.

**3. ORPO was considered and rejected on one ground.**
ORPO (Hong, Lee, and Thorne, EMNLP 2024) merges the SFT and preference objectives into a single monolithic loss. This is elegant when the training data is a unified instruction-following set, but Tenacious-Bench's training partition is preference pairs only — there is no separate SFT corpus. Using ORPO without a high-quality SFT component risks over-fitting the monolithic loss to the preference signal and losing the base model's formatting and instruction-following capabilities. SimPO's cleaner separation is the safer choice at this data scale.

### Backbone: Qwen 2.5 0.5B Instruct operational fallback

Selected for three reasons:

1. The intended backbone was Qwen3.5-0.8B, matching the Week 11 brief, but the current HF/Unsloth release is multimodal and routes TRL CPO text prompts through a vision processor on Colab.
2. `unsloth/Qwen2.5-0.5B-Instruct` is text-only, fits T4 in 16-bit LoRA without quantization, and avoids the image-processor failure.
3. The judge use case does not require generation quality — it requires reliable classification of pass/fail on structured business-rule violations. A 0.5B text-only model with task-specific LoRA is sufficient for the first ablation.

### Week 10 trace evidence for Path B

The following probe IDs from `week_10_data/probe_library.md` are the primary evidence base for this path selection:

| Probe ID | Trace ref | Failure | Why it supports Path B |
|---|---|---|---|
| P-009 | `probe-4087895185a9`, `probe-c1a89e56414b` | Go overcommitment (bench=3, committed=10) | Agent had bench state available; failed to check it. A critic with bench state in context would catch this. |
| P-010 | `probe-d5299b421fc8` | NestJS capacity committed as available, actually deployed | Same pattern: structured data ignored at generation time. |
| P-001 | `probe-8dc44eb36d33` | Layoff + funding signal → Segment 1 pitch instead of Segment 2 | ICP routing rule violation. Segment rules are deterministic; a critic can learn them. |
| P-004 | `probe-19f0af95e3e2` | Zero open roles, still passed Segment 1 | Another routing failure with a hard-threshold ground truth. |
| P-005 | `probe-b3388b3c3582` | Assertive phrasing under medium-confidence signal | Confidence-tier phrasing rule. Deterministic anchor exists in signal_brief. |

All five failures share a pattern: the agent's generator ignored structured context fields (bench_summary, capacity_request, signal_confidence_tier, icp_segment) that were available in the input. A generation-quality fix (Path A) does not address this — the generator already produces fluent output. What is missing is a rejection layer that checks structured context against the draft before the draft is sent. That is Path B.

### Why not Path C

Path C (process reward model) fits trajectory failures — cases where individually reasonable steps compound into a bad outcome. The Week 10 evidence does not show this pattern. The failures above are single-turn: the agent produces one bad email on one input. There is no multi-step trajectory to reward. Path C is the right choice when the failure is in intermediate decisions; Path B is the right choice when the failure is in the final output.

### Paper citations

- Rafailov et al., *Direct Preference Optimization* (NeurIPS 2023) — foundational algorithm; SimPO is selected over this for reference-model cost reasons stated above.
- Meng, Xia, and Chen, *SimPO: Simple Preference Optimization with a Reference-Free Reward* (NeurIPS 2024) — selected training algorithm.
- Hong, Lee, and Thorne, *ORPO: Monolithic Preference Optimization without Reference Model* (EMNLP 2024) — considered and rejected; rationale above.
- Kim et al., *Prometheus 2: An Open-Source Language Model Specialized in Evaluating Other Language Models* (2024) — reference architecture for a small open judge trained from preferences; Tenacious-Bench follows the same data construction pattern (chosen/rejected pairs from structured rubrics) at smaller scale.
- Li et al., *Preference Leakage: A Contamination Problem in LLM-as-a-Judge* (2025) — generator model family (Qwen) is intentionally different from the judge model family (Claude / OpenAI) used in `generation_scripts/judge_filter.py`. This rotation is documented in `generation_scripts/routing_policy.md`.
