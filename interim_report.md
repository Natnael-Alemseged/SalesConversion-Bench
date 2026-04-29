# Interim Report Source

## Repo Checklist (Interim submission)

This report is meant to be a single index into the required interim artifacts (Acts I–II).

- Root overview: `README.md`
- Act I audit: `audit_memo.md` (≤600 words target)
- Schema and examples: `schema.json`
- Deterministic evaluator: `scoring_evaluator.py`
- Dataset partitions: `tenacious_bench_v0.1/train/tasks.jsonl`, `tenacious_bench_v0.1/dev/tasks.jsonl`, `tenacious_bench_v0.1/held_out/tasks.jsonl`
- Datasheet (Gebru + Pushkarna layering): `datasheet.md`
- Methodology (Path declaration + partitioning + contamination notes): `methodology.md`
- Generation + validation scripts (dedup, split, contamination, judge prompts): `generation_scripts/`
- Contamination output: `contamination_check.json`
- Inter-rater agreement protocol + results: `inter_rater_agreement.md`
- Human labels: `human_labels/pass1_labels.json`, `human_labels/pass2_labels.json`
- Synthesis memos (≥2 common-reading): `synthesis_memos/`
- Cost log: `cost_log.csv`

## System Overview (optional, for clarity)

The Week 11 interim deliverable covers Acts I–II: audit → schema → authored dataset + evaluator. This diagram is not explicitly required by the rubric, but it makes the artifact relationships easy to review.

```mermaid
flowchart TD
  A[Week 10 evidence<br/>probe_library + failure_taxonomy + traces] --> B[Act I: Audit memo<br/>audit_memo.md]
  A --> C[Act I: Schema design<br/>schema.json]
  A --> D[Act I: Deterministic evaluator<br/>scoring_evaluator.py]

  C --> E[Act II: Source pool<br/>tenacious_bench_v0.1/source_pool.jsonl]
  E --> F[Validate + Dedup<br/>generation_scripts/validate_schema.py<br/>generation_scripts/dedup.py]
  F --> G[Split (seeded)<br/>generation_scripts/split_dataset.py]
  G --> H[Partitions<br/>train / dev / held_out]
  H --> I[Contamination checks<br/>generation_scripts/contamination_check.py<br/>contamination_check.json]

  D --> J[Score tasks deterministically<br/>on JSONL partitions]
  H --> J

  J --> K[Inter-rater subset + labels<br/>inter_rater_agreement.md<br/>human_labels/pass1_labels.json<br/>human_labels/pass2_labels.json]
  I --> L[Interim report<br/>this file]
  K --> L
```

## Bench Composition

Current counts from `generation_scripts/counts.json`:

- partitions:
  - `train`: 29
  - `dev`: 18
  - `held_out`: 13
- source modes:
  - `programmatic`: 41
  - `hand_authored`: 12
  - `trace_derived`: 7
- failure categories:
  - `bench_overcommitment`: 12
  - `dual_control_coordination`: 8
  - `gap_overclaiming`: 10
  - `icp_misclassification`: 10
  - `signal_overclaiming`: 10
  - `tone_drift`: 10

## Inter-Rater Agreement Results

Status at the current implementation checkpoint:

- task subset selection is committed in `inter_rater_agreement.md`
- machine-assisted pass 1 labels are recorded in `eval_examples/inter_rater_pass1_labels.json`
- machine-assisted comparison run is recorded in `eval_examples/inter_rater_comparison_run1_vs_run2.json`
- a human Pass 2 was performed as an immediate rerun (see `human_labels/pass2_labels.json`), but it is **not compliant** with the ≥24-hour delayed relabel requirement

Immediate rerun agreement (pilot only):

- overall check-level agreement: `18 / 25` (`0.72`)
- per-dimension:
  - `banned_phrase_check`: `2 / 3` (`0.6667`)
  - `signal_grounding_check`: `4 / 6` (`0.6667`)
  - `booking_stage_check`: `3 / 4` (`0.75`)
  - `bench_capacity_check`: `2 / 2` (`1.0`)
  - `format_check`: `7 / 10` (`0.7`)

This section must be updated with the **official ≥24-hour delayed** agreement results before the interim package is final.

## Compliance Notes Against Week 11 Interim Spec (Acts I–II)

This repo contains all required artifact *types*, but the following items remain to fully satisfy the Week 11 interim expectations:

- **Delayed inter-rater loop**: the spec requires a ≥24-hour delayed relabel (Pass 2). Current Pass 2 is an immediate rerun and is recorded as a pilot only.
- **Inter-rater threshold trigger**: the pilot agreement is below 0.80 in multiple dimensions, which implies rubric ambiguity and should trigger rubric tightening before the official delayed loop.
- **Embedding contamination backend**: `sentence-transformers` is declared as the intended embedding backend, but the current contamination artifact should be regenerated using that backend (not a fallback) before finalizing the interim package.
- **Dataset scale**: the authored pool is currently 60 tasks; the Week 11 Act II target is 200–300 tasks. This interim slice is acceptable as a scaffold, but the scale gap should be stated explicitly in the interim narrative.
- **LLM-as-a-judge filtering evidence**: judge prompts and routing policy exist in `generation_scripts/`, but the interim authoring batch did not call any models and does not yet include judge-filter logs. If the interim is meant to claim “judge-filtered,” add a logged judge-filter pass; otherwise, state that judge-filtering is deferred and limit interim claims accordingly.

## Three Example Tasks With Rubric Application

Suggested examples for the PDF:

1. programmatic: `tbv01-021`
   - output file: `eval_examples/tbv01-021.json`
   - current score: `1.0`
2. trace-derived: `tbv01-007`
   - output file: `eval_examples/tbv01-007.json`
   - current score: `0.6667`
3. adversarial / hand-authored: `tbv01-059`
   - output file: `eval_examples/tbv01-059.json`
   - current score: `0.3333`

These JSON files now contain the raw task payload plus evaluator output and can be excerpted directly into the PDF.

## What Is Working

- the repo now contains a real 60-task authored pool
- schema validation passes
- exact-duplicate detection passes
- the partitioned dataset exists on disk
- contamination output is generated and recorded
- the deterministic evaluator runs against JSONL partition files

## What Is Not Yet Working

- the official (≥24-hour delayed) inter-rater agreement loop is not yet complete and is the most time-sensitive remaining blocker
- the contamination artifact should be regenerated using the pinned `sentence-transformers` embedding backend
- the authored pool is still interim-sized (60) relative to the Act II target (200–300)
- judge-filter logs are not yet present for the authored pool (judge prompts exist, but filtering is deferred unless explicitly run and logged)

## Plan For Days 4–7

- rerun Human Pass 2 after ≥24 hours, compute agreement, and tighten rubric if <0.80
- install and rerun contamination with the pinned embedding model and commit the updated `contamination_check.json`
- expand dataset toward 200–300 tasks with more trace-derived and programmatic variants, then rerun dedup/split/contamination
- convert corrected outputs into Path B preference pairs
- prepare Colab training inputs for the critic
