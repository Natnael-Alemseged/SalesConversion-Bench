# Synthesis Memo: A Survey on LLM-as-a-Judge

Gu et al., *A Survey on LLM-as-a-Judge* (2024–2025, latest revision).

## Design choice I disagree with (Section 6.1 — prompt sensitivity and consistency)

The survey treats prompt sensitivity primarily as a calibration and consistency problem to be solved through better prompting techniques — chain-of-thought, swap augmentation, few-shot examples. The implicit recommendation is that prompt engineering is the main lever for making LLM judges reliable. Section 6.1 documents that score distributions shift significantly with surface-level prompt changes, but the proposed mitigations are all still prompt-level interventions.

## Why this fails for Tenacious-Bench given current evidence

The Week 10 failures are not ambiguous quality judgments. The highest-cost cluster is **bench overcommitment**, which the Week 10 taxonomy reports at **40/40 (100%)** and which is captured in probe IDs `P-009` through `P-012` in `week_10_data/probe_library.md`.

Concrete trace evidence:

- `P-009` (10 Go engineers promised; bench has 3): `probe-4087895185a9`, `probe-c1a89e56414b`, `probe-bebe5469b030`
- `P-010` (NestJS engineers “available” but actually committed): `probe-d5299b421fc8`
- `P-011` (2 senior ML promised; bench has 1): `probe-258f1573489a`
- `P-012` (7-day infra start promised; 14-day lead time): `probe-21a138e1feac`

These are factual mismatches against structured task fields (`bench_summary`, `capacity_request`). No amount of prompt engineering makes an LLM judge more reliable on this check — the ground truth is in a structured data field, not in natural language quality. An LLM that is "well-calibrated" on tone dimensions will still hallucinate bench capacity facts unless the structured bench state is injected into its context explicitly.

The same applies to ICP routing and confidence calibration failures:

- `P-001` ICP misrouting: `probe-8dc44eb36d33` (layoff+funding should route to Segment 2)
- `P-005` confidence-insensitive opener: `probe-b3388b3c3582` (assertive phrasing under weak confidence)

These failures also have deterministic anchors in the task context (segment rules, confidence tier). Framing them as calibration problems to be solved with better prompting underestimates how much the structured business context matters.

## What I do instead in this repo

The evaluator in `scoring_evaluator.py` runs deterministic hard-rule checks first and reserves LLM judging for the dimensions that genuinely require natural-language reasoning (the `llm_judge_hook` stub for tone coherence and rubric clarity). The pointwise judge in `generation_scripts/judge_prompts/pointwise_judge.md` is scoped to three dimensions where deterministic checking is insufficient. The architectural principle is: deterministic rules as first gate, LLM judge as second gate only where the first gate cannot reach. This is more reliable than relying on prompt calibration for checks that have structural ground truth.

## Where I agree

The survey is correct that judge rubrics must be narrow and explicit to produce consistent scores. The five-check decomposition in `scoring_evaluator.py` (banned phrases, signal grounding, booking stage, bench capacity, format) follows this directly. A single "is this a good email?" prompt would reproduce exactly the consistency failures Section 4 documents.
