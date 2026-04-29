# Methodology

## Path Declaration

This project selects **Path B: preference-tuned judge or critic**.

The Week 10 evidence points to a system that often produces outputs that are fluent enough to send but not reliable enough to trust. The dominant measured failures are not generic prose-quality failures; they are violations the system should be able to detect and reject. In `week_10_data/failure_taxonomy.md`, `bench_overcommitment` triggers **40/40 (100%)**, `icp_misclassification` triggers **20/37 (54%)**, and `gap_overclaiming` remains high-risk. The corresponding Week 10 probe bundle in `week_10_data/probe_library.md` shows the same pattern at the trace level: `probe-4087895185a9`, `probe-c1a89e56414b`, and `probe-bebe5469b030` document overcommitment failures for Go staffing; `probe-8dc44eb36d33` and `probe-bde8ece3a8ff` document layoff-plus-funding misrouting; `probe-b3388b3c3582` documents assertive wording under weak confidence. These are critic-friendly failures: the agent often has enough context to know better, but the current system lacks a reliable Tenacious-specific checker that can block bad drafts before they are sent.

Path B is therefore the best fit for Act III and Act IV. The training target will be a Tenacious-specific critic that scores candidate outputs against hard business rules and style constraints, then supports rejection sampling or rollback in front of the Week 10 generator. Path C would be a better fit if the main issue were intermediate action selection over long multistep trajectories. The current evidence instead concentrates on final-output violations that can be judged from the brief, bench state, thread stage, and draft itself.

## Week 10 Evidence Inventory

The current repo contains the following Week 10 evidence artifacts:

- `week_10_data/failure_taxonomy.md`
- `week_10_data/probe_library.md`
- `week_10_data/trace_log.jsonl`
- `week_10_data/agent/` source

The `trace_log.jsonl` file points to a saved `tau2-bench` retail simulation run at:

- `/Users/natnaelalemseged/code-projects/backend/tau2-bench/data/simulations/ce-run-retail-test-qwen3-next-80b-a3b-instruct-t0-20260425_161918/results.json`

That run contains 20 real simulation records. Example simulation IDs used in the audit are:

- `f66839d0-fd13-4b1b-9eac-ad11836811df`
- `ec9f91d2-3bc2-46c9-842c-59349f204db1`
- `92662dc5-0856-4048-a24e-a1692c9f65fb`
- `16592a4c-6b65-40fe-9a0b-01e40a965172`
- `c8a367b4-dee9-4a4a-ad5c-8dccd6b06125`

These traces are useful as evidence that the existing public benchmark measures retail customer-support task success, not Tenacious-specific sales-policy adherence.

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

## Partitioning Plan

The intended dataset layout for Act II is:

- `train`: 50%
- `dev_public`: 30%
- `held_out_sealed`: 20%

Held-out tasks will be screened using the Week 11 contamination requirements:

- n-gram overlap threshold
- embedding-similarity threshold
- time-shift verification for public-signal tasks

No contamination-check result is claimed yet in this file because the dataset has not been authored.

## Judge Training Plan for Path B

The Path B training data will be constructed as preference pairs:

- `rejected`: outputs that exhibit known Week 10 failures
- `chosen`: corrected versions that satisfy the evaluator

The initial pair sources will be:

- probe-triggered bad drafts from Week 10
- corrected hand rewrites grounded in the Tenacious style guide
- later dev-tier model rewrites that pass the evaluator

Preference leakage prevention will follow the Week 11 brief: the same model family will not both generate and judge the same example pool.
