# Methodology

## Path Declaration

This project selects **Path B: preference-tuned judge or critic**.

The Week 10 evidence points to a system that often produces outputs that are fluent enough to send but not reliable enough to trust. The dominant measured failures are not generic prose-quality failures; they are violations the system should be able to detect and reject. In `week_10_data/failure_taxonomy.md`, `bench_overcommitment` triggers **40/40 (100%)**, `icp_misclassification` triggers **20/37 (54%)**, and `gap_overclaiming` remains high-risk. The corresponding Week 10 probe bundle in `week_10_data/probe_library.md` shows the same pattern at the trace level: `probe-4087895185a9`, `probe-c1a89e56414b`, and `probe-d5299b421fc8` document bench-feasibility failures; `probe-8dc44eb36d33` and `probe-19f0af95e3e2` document ICP misrouting; `probe-b3388b3c3582` documents assertive wording under weak confidence. These are critic-friendly failures: the agent often has enough context to know better, but the current system lacks a reliable Tenacious-specific checker that can block bad drafts before they are sent.

Two required-reading papers support this choice. Gu et al., *A Survey on LLM-as-a-Judge*, argue that reliable judge systems need explicit validation, calibration, and standardization beyond a basic judging pipeline, especially when prompt wording and ordering can change scores (Section 4 and Section 6.1) [https://arxiv.org/html/2411.15594](https://arxiv.org/html/2411.15594). Liu et al., *Best Practices and Lessons Learned on Synthetic Data for Language Models*, argue that synthetic-data pipelines need disciplined verification and stronger contamination controls because rephrased synthetic examples can defeat token-level decontamination (Section 3 and Section 4, "Training with synthetic data makes evaluation decontamination harder") [https://arxiv.org/html/2404.07503](https://arxiv.org/html/2404.07503). Those recommendations fit this repo's situation: Tenacious needs a calibrated critic on top of hard business rules, and the benchmark build needs explicit contamination accounting.

Path B is therefore the best fit for Act III and Act IV. The training target will be a Tenacious-specific critic that scores candidate outputs against hard business rules and style constraints, then supports rejection sampling or rollback in front of the Week 10 generator. Path C would be a better fit if the main issue were intermediate action selection over long multistep trajectories. The current evidence instead concentrates on final-output violations that can be judged from the brief, bench state, thread stage, and draft itself.

## Week 10 Evidence Inventory

The current repo contains the following Week 10 evidence artifacts:

- `week_10_data/failure_taxonomy.md`
- `week_10_data/probe_library.md`
- `week_10_data/trace_log.jsonl`
- `week_10_data/agent/` source

The `trace_log.jsonl` file points to a saved `tau2-bench` retail simulation run at:

- `../tau2-bench/data/simulations/ce-run-retail-test-qwen3-next-80b-a3b-instruct-t0-20260425_161918/results.json`

That run contains 20 real simulation records, but it is included here only as benchmark-mismatch evidence. The Tenacious-specific trace evidence used for Path B selection comes from the Week 10 probe bundle rather than `trace_log.jsonl`. Representative probe traces are `probe-4087895185a9` (`P-009`, Go staffing overcommitment), `probe-d5299b421fc8` (`P-010`, committed NestJS capacity misread as available), `probe-8dc44eb36d33` (`P-001`, layoff-plus-funding misrouting), `probe-19f0af95e3e2` (`P-004`, zero-open-roles still passing Segment 1), and `probe-b3388b3c3582` (`P-005`, overconfident signal phrasing). These traces are the main reason the methodology chooses a critic path over a longer-horizon planner path.

## Evidence Limits

The available saved benchmark run is a retail benchmark, not a Tenacious sales benchmark. It is therefore informative for benchmark-mismatch analysis but not sufficient as direct supervision for Tenacious-specific quality. The Tenacious-specific evidence for Act I comes primarily from the Week 10 probe and taxonomy bundle, which names the failure modes, trigger rates, and concrete trace references generated during Week 10.

This limitation is explicit in the interim submission so that later dataset and training claims are not backfilled into Act I.

## Act I Scoring Design

The first-pass evaluator is intentionally deterministic wherever the Week 10 evidence already supports hard checks. It currently scores five dimensions:

1. `banned_phrase_check`
2. `signal_grounding_check`
3. `booking_stage_check`
4. `bench_capacity_check`
5. `format_check`

The bench-capacity check reuses the Week 10 capacity checker in `week_10_data/agent/enrichment/bench_capacity.py`. This keeps the evaluator anchored to the actual rule logic already implemented for P-009 through P-012 instead of duplicating a hand-written approximation.

The evaluator is scoped to Act I, not final benchmark completeness. It is designed to support:

- three hand-built example tasks in `schema.json`
- immediate extension into trace-derived and programmatic tasks in Act II
- later preference-pair construction for Path B in Act III

The current 60-task interim slice is also intentionally stratified across source modes and failure categories so the train/dev/held-out split does not collapse into a single authoring pattern or a single business-risk type.

## Partitioning Plan

The dataset is partitioned with a fixed seed (`20260429`) using `generation_scripts/split_dataset.py`.

### Stratification protocol (leakage control + failure coverage)

Splitting is **family-stratified and failure-category-aware** to reduce leakage from near-identical variants and to preserve failure-mode coverage across partitions.

Implementation (see `generation_scripts/split_dataset.py`):

- define a family key from `metadata.scaled_from_task_id` when present, because that field captures which benchmark row a later expansion descended from
- if no seed task ID is present, fall back to the tuple of `metadata.week10_probe_ids` (joined into a stable string)
- if neither exists, fall back to `failure_category::source_mode` as the family key
- bucket families by `metadata.failure_category`
- assign whole families to `train`, `dev`, or `held_out` while targeting the 50/30/20 ratio inside each failure-category bucket

Rationale:

- programmatic and synthesis expansions can create near-duplicates that are hard to detect via token-level dedup alone
- keeping a probe-family intact prevents accidental “training on the answer” when held-out variants share the same Week 10 probe lineage
- category-aware assignment keeps one failure family from dominating a split and serves the Week 11 goal of testing generalization across failure dimensions rather than memorization of one probe’s wording

Current partition counts:

- `tenacious_bench_v0.1`: 29 / 18 / 13 (train/dev/held_out)
- `tenacious_bench_v0.2`: 120 / 73 / 47 (train/dev/held_out)

The 50/30/20 split was chosen so that the training partition is large enough for preference-pair construction (Path B), the dev partition supports iterative evaluator tuning without leaking held-out signal, and the held-out partition remains sealed for final ablation scoring. Stratification is applied by failure category and constrained by probe-family integrity: `split_dataset.py` keeps each Week 10 probe family intact while targeting proportional allocation inside each `failure_category` bucket. This matters for coverage because the six failure categories vary in how well they probe different rubric dimensions — a random split without stratification risks a held-out partition that over-represents easy dimensions and under-represents the hardest ones (bench overcommitment and ICP misclassification).

Artifacts:

- dataset partitions under `tenacious_bench_v0.1/`
- split manifest at `generation_scripts/run_manifest.json`
- composition counts at `generation_scripts/counts.json`

Contamination artifacts:

- `contamination_check.json` (v0.1)
- `contamination_check.v0.2.json` (v0.2)

The current contamination run records:

- separate 8-gram overlap checks for held-out vs `train` and held-out vs `dev`
- separate embedding-similarity checks against a target threshold of `0.85` for held-out vs `train` and held-out vs `dev`
- lineage-aware time-shift verification using `signal_date`, `signal_source`, and shared source-family provenance

In prose:

- v0.2: flagged **0 held-out-vs-train 8-gram violations** and **0 held-out-vs-dev 8-gram violations**.
- v0.2: flagged dense-similarity warnings above the `0.85` threshold across both held-out-vs-train and held-out-vs-dev comparisons. The current 240-task slice contains many same-family scaled variants, so the report now records these as real warnings instead of collapsing them into a single "pass" claim.
- v0.2: verifies signal provenance fields for public-signal tasks and enforces a minimum 7-day gap when held-out and train/dev tasks share the same source family.

This is enough to document contamination hygiene in an auditable way, and it also makes the current limitation explicit: the present v0.2 slice is clean on exact surface overlap but not yet clean on dense semantic similarity.

Current implementation note:

- the contamination script pins `sentence-transformers/all-MiniLM-L6-v2` as the embedding backend
- the committed v0.2 artifact now records partition-aware pair reports (`held_out_vs_train` and `held_out_vs_dev`) instead of only a merged comparison
- the current committed v0.2 report was generated with the script's explicit `lexical_fallback` backend in this local runtime, and that backend choice is recorded in the JSON artifact itself
- because the current source pool contains many same-family scaled variants, the embedding threshold produces warnings that should be treated as a dataset-composition issue rather than hidden in prose

## Judge Training Plan for Path B

The Path B training data will be constructed as preference pairs:

- `rejected`: outputs that exhibit known Week 10 failures
- `chosen`: corrected versions that satisfy the evaluator

The initial pair sources will be:

- probe-triggered bad drafts from Week 10
- corrected hand rewrites grounded in the Tenacious style guide
- later dev-tier model rewrites that pass the evaluator

Preference leakage prevention will follow the Week 11 brief: the same model family will not both generate and judge the same example pool.
