# Synthesis Memo: Best Practices and Lessons Learned on Synthetic Data for Language Models

Liu et al., *Best Practices and Lessons Learned on Synthetic Data for Language Models* (COLM 2024).

## Design choice I disagree with (Section 4 — "Training with synthetic data makes evaluation decontamination harder")

The paper recommends treating synthesis breadth as the primary lever for closing capability gaps once a curation pipeline exists, with decontamination controls as a secondary concern. The implicit sequencing is: build your synthesis pipeline first, then worry about contamination. Section 4 frames decontamination as a known cost of scaling synthetic data, not as a reason to delay synthesis.

## Why this fails for Tenacious-Bench given current evidence

The Week 10 failure taxonomy shows that `bench_overcommitment` triggered at **100% (40/40 probes)** and `icp_misclassification` at **54% (20/37 probes)**. These are not capability gaps that benefit from synthesis breadth — they are systematic policy violations that any synthesis model will replicate unless the seed authoring explicitly encodes the policy.

Concrete Week 10 probe + trace evidence:

- `P-009` (bench overcommitment): `probe-4087895185a9`, `probe-c1a89e56414b`
- `P-010` (capacity misread as available): `probe-d5299b421fc8`
- `P-001` (ICP misrouting): `probe-8dc44eb36d33`

Scaling a synthesis pipeline on top of these unresolved patterns does not close the gap; it mass-produces the same violations in slightly different surface forms.

The contamination concern from Section 4 is also more acute here than in general-purpose benchmarks. Because this benchmark is derived from a small, domain-specific seed corpus (the Week 10 probe library), rephrased synthetic variants have high lexical similarity to their seeds. The repo therefore makes contamination checks a first-class artifact:

- 8-gram overlap check
- embedding-similarity check (threshold 0.85)
- time-shift verification for `signal_date` / `signal_source`

These are implemented in `generation_scripts/contamination_check.py` and recorded as committed JSON artifacts (for example, `contamination_check.v0.2.json`). Starting with synthesis breadth before those checks exist would contaminate the held-out partition in exactly the way the paper warns about.

## What I do instead in this repo

The authoring order is:

1. evidence-grounded seeds first (trace-derived and programmatic)
2. hand-authored edge cases second
3. multi-LLM synthesis only after validation + contamination artifacts are in place

In practice, this repo now includes a 240-task `tenacious_bench_v0.2` pool that explicitly includes `multi_llm_synthesis` rows **plus** contamination reporting. This sequencing is the opposite of the paper's implicit “synthesis first, decontam later” framing in Section 4: here, decontamination checks are treated as a gating condition for scaling.

## Where I agree

The paper's emphasis on curation and verification over raw volume is correct. In this repo, that shows up as:

- schema validation (`generation_scripts/validate_schema.py`)
- deterministic scoring gates (`scoring_evaluator.py`)
- pointwise judge-filter scaffolding and audit logs (`generation_scripts/build_dataset.py`, `generation_scripts/judge_prompts/`)

Quality filtering before inclusion is non-negotiable for a domain-specific benchmark.
