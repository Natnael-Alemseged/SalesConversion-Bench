# Interim Submission Plan

This document lays out the implementation plan for the remaining interim-submission work in this repo.

It is intentionally practical rather than idealized. The goal is to ship a truthful, defensible interim package built on the evidence already present in `week_10_data/`, while keeping the work aligned with the Week 11 brief and the Path B decision.

## Current Status

Already completed in root:

- `README.md`
- `methodology.md`
- `audit_memo.md`
- `schema.json`
- `scoring_evaluator.py`
- `ACT_I_IMPLEMENTATION_NOTES.md`
- `cost_log.csv`

Still missing for a stronger interim submission:

- `tenacious_bench_v0.1/`
- `datasheet.md`
- `generation_scripts/`
- `contamination_check.json`
- `inter_rater_agreement.md`
- reading synthesis memos
- interim PDF report

## Objective

Build the smallest legitimate interim package that:

1. contains a real Tenacious-Bench dataset structure
2. includes enough authored tasks to demonstrate the benchmark direction
3. documents dataset construction choices
4. shows at least a first contamination-check pass
5. starts the quality-control loop for labeling consistency
6. leaves a clean path into Path B preference-data preparation

## Delivery Strategy

The critical path for interim is:

1. complete the required common-reading memos
2. update the schema and early dataset framing
3. author the dataset
4. run contamination checks
5. complete the guaranteed two-pass inter-rater subset for the PDF

Implementation order:

1. draft the first reading synthesis memos
2. draft the datasheet motivation / uses framing
3. scaffold `tenacious_bench_v0.1/`
4. author the first batch of tasks
5. add generation scripts
6. start inter-rater pass 1 as soon as the first usable task batch exists
7. run contamination checks
8. complete documentation and memo refinement

## Scope For Interim

The Week 11 final target is 200–300 tasks. For interim, the practical target is a smaller but real dataset slice.

Recommended interim target:

- `train`: 30–40 tasks
- `dev`: 15–25 tasks
- `held_out`: 10–15 tasks

Total:

- **60–80 tasks**

This is enough to prove the benchmark is real without pretending the final corpus is done.

## Folder And File Plan

### 1. Dataset directory

Create:

```text
tenacious_bench_v0.1/
  train/
    tasks.jsonl
  dev/
    tasks.jsonl
  held_out/
    tasks.jsonl
  README.md
```

Purpose:

- store the interim dataset partitions
- keep the held-out partition separated clearly
- make the dataset browsable without opening the brief

Naming note:

- use `train/`, `dev/`, and `held_out/` exactly in the repo plan, because the interim checklist names those partitions explicitly
- interim-specific note:
  - for the Wednesday interim repo, `held_out/` must be present because the brief explicitly requires three partitions in the repo
  - for the later public artifact stage, revisit held-out handling so the sealed slice is not exposed in conflict with the public-artifact quality bar

### 2. Generation scripts

Create:

```text
generation_scripts/
  build_probe_tasks.py
  validate_schema.py
  dedup.py
  split_dataset.py
  summarize_dataset.py
  contamination_check.py
  run_manifest.json
  schema_validation_report.json
  dedup_report.json
  counts.json
  README.md
```

Purpose of each:

- `build_probe_tasks.py`
  - convert Week 10 probes into first-pass task objects matching `schema.json`
- `validate_schema.py`
  - validates each JSONL record against `schema.json` (explicit runnable path)
  - emits `schema_validation_report.json` (valid/invalid counts + first N errors)
- `dedup.py`
  - runs exact-duplicate detection across the authored pool
  - runs near-duplicate detection using the same embedding model as the contamination check
  - emits `dedup_report.json` and writes a deduplicated working set for splitting
- `split_dataset.py`
  - partition authored tasks into train / dev / held-out
  - must accept a fixed `--seed` argument
  - must record the seed used in output logs or companion metadata
- `summarize_dataset.py`
  - emits `counts.json` used by `interim_report.md` (no hand-entered composition counts)
  - reports:
    - tasks per partition
    - tasks per source mode (trace-derived / programmatic / hand-authored / synthesis)
    - tasks per failure dimension / category
- `contamination_check.py`
  - generates the root-level `contamination_check.json` by running the three required checks:
    - n-gram overlap
    - embedding similarity
    - time-shift verification (for tasks referencing public signals)
- `run_manifest.json`
  - records what authoring modes were used in the interim batch
  - records task counts per mode
  - records model usage status
  - records dedup policy + links to `dedup_report.json`
- `README.md`
  - explain how the tasks were produced in the interim

Validation is intentionally split:

- `generation_scripts/validate_schema.py` enforces `schema.json` conformance
- `scoring_evaluator.py` grades rubric / scoring behavior

These are complementary, not redundant.

Interim documentation note:

- for a trace-derived / programmatic / hand-authored interim batch, document explicitly that:
  - multi-LLM synthesis routes were not yet used, if that remains true
  - no synthesis-model calls were made for the interim batch, if that remains true
  - judge-filter logs are deferred until the multi-LLM synthesis stage runs
  - exact-duplicate detection and dedup policy still apply

### 3. Documentation

Create:

- `datasheet.md`
- `inter_rater_agreement.md`
- `synthesis_memos/`
- `eval_examples/`

Suggested memo files:

```text
synthesis_memos/
  synthetic_data_best_practices.md
  llm_as_a_judge_survey.md
```

These two are a good first pair because they directly support:

- benchmark construction
- Path B judge design

## Task Authoring Plan

### Source priority

Author tasks using the following order:

1. **Probe-derived**
   - fastest and best grounded for interim
   - use `week_10_data/probe_library.md`
   - use `week_10_data/failure_taxonomy.md`

2. **Programmatic variants**
   - expand probe patterns by varying:
     - segment
     - confidence
     - stack
     - requested staffing count
     - lead time
     - CTA stage

3. **Hand-authored edge cases**
   - use for the hardest early examples:
     - booking too early
     - condescending competitor-gap framing
     - weak-signal overclaiming
     - cross-thread leakage placeholders

4. **Multi-LLM synthesis**
   - required by the final Week 11 benchmark design
   - intentionally deferred for interim unless enough time remains after the evidence-grounded batch is complete
   - if deferred, the interim docs must say so explicitly rather than silently omitting the mode

### Categories to cover first

Prioritize these categories because they are best supported by current evidence and fit Path B:

1. `bench_overcommitment`
2. `icp_misclassification`
3. `signal_overclaiming`
4. `gap_overclaiming`
5. `tone_drift`
6. `dual_control_coordination`

### Target distribution for interim

Recommended rough split:

- `bench_overcommitment`: 15 tasks
- `icp_misclassification`: 10 tasks
- `signal_overclaiming`: 10 tasks
- `gap_overclaiming`: 9 tasks
- `tone_drift`: 9 tasks
- `dual_control_coordination`: 7 tasks

That gives a first batch of **60 tasks**.

Raise the first authored batch slightly to **60 tasks minimum** so the partition targets align cleanly with the intended 50/30/20 split.

### Probe expansion logic

The generation script should not convert one probe into one task mechanically. Interim authoring should expand each eligible probe into a small controlled family of tasks.

Recommended expansion rules:

- one base probe -> **2 to 4 task variants**
- vary `signal_confidence_tier` where the probe supports confidence-sensitive phrasing
- vary `thread_stage` where CTA timing or booking behavior is relevant
- vary `requested_count`, `seniority`, and `lead_days` for capacity probes
- vary whether the candidate output is:
  - an obviously bad draft
  - a subtle near-miss draft
  - a corrected or compliant draft

Examples:

- `P-009` can expand into:
  - unsupported large Go staffing promise
  - unsupported senior Go promise with smaller count
  - corrected partial-capacity reply
- `P-001` can expand into:
  - wrong Segment 1 growth pitch
  - corrected Segment 2 cost-pressure framing
- `P-022` can expand into:
  - booking link too early
  - exploratory question instead of booking
  - valid booking CTA after explicit readiness

## Contamination-Check Plan

Create:

- `contamination_check.json`

Interim version should include:

1. partition counts
2. n-gram overlap check summary
3. exact-duplicate detection
4. embedding-similarity check output
5. time-shift verification output

The brief explicitly names three contamination checks, so the interim artifact should record all three:

- n-gram overlap with the held-out threshold enforced at **less than 8-gram overlap** on input fields
- embedding similarity with cosine similarity required to be **below 0.85**
- time-shift verification

Minimum honest interim behavior:

- run exact duplicate detection
- run simple n-gram overlap checks across partitions
- run an embedding-similarity pass across partitions, even if the interim dataset is still small
- run time-shift verification on all tasks that reference public signals

Embedding-model choice for reproducibility:

- use one pinned embedding model for the interim contamination run
- recommended default: `sentence-transformers/all-MiniLM-L6-v2`
- record the chosen model name in:
  - `pyproject.toml` (canonical dependency pin for this repo)
  - `contamination_check.json`
  - `generation_scripts/README.md`

Time-shift verification should be made checkable by task metadata. Add and populate fields such as:

- `signal_date`
- `signal_source`

for tasks that reference public events like funding, layoffs, or leadership changes.

For trace-derived and programmatic-only interim tasks, explain in the contamination artifact why the contamination risk is structurally lower than the later synthesis-heavy batch, but still run and log the three required checks.

## Inter-Rater Agreement Plan

Create:

- `inter_rater_agreement.md`

Interim objective:

1. select 30 tasks from the authored batch
2. perform label pass 1 immediately after the first usable batch exists
3. record rubric dimensions
4. schedule label pass 2 for 24 hours later

Important:

- the **10–15 task interim PDF subset** must complete the full two-pass loop before the interim cutoff
- pass 1 for that 10–15 task subset must begin **at least 24 hours before the submission deadline**, otherwise pass 2 is structurally impossible
- only the remaining tasks beyond that guaranteed subset may be recorded as pass-1 complete / pass-2 pending
- do not present unfinished re-label work as completed agreement

Sequencing note:

- pass 1 begins during task-authoring, not after all documentation is complete
- pass 2 and the agreement summary land later, after the 24-hour gap

Interim deliverable note:

- because the Wednesday PDF report requires inter-rater agreement results, the plan should target at least one completed two-pass subset for interim
- practical target:
  - complete a **10–15 task two-pass sample** in time for the PDF
  - continue toward the larger 30-task target for the fuller dataset-quality loop

## Datasheet Plan

Create:

- `datasheet.md`

Minimum sections:

1. Motivation
2. Composition
3. Collection process
4. Preprocessing / transformation
5. Uses
6. Distribution
7. Maintenance

Also include the layered detail framing from Data Cards:

- telescopic
- periscopic
- microscopic

For interim, the datasheet should describe the dataset as:

- **v0.1 interim benchmark slice**
- derived from Week 10 evidence and authored extensions

Sequencing note:

- draft Motivation, Uses, and Collection framing early
- finalize Composition and partition counts after the first dataset batch exists

This reduces the risk that authoring drifts away from what the datasheet later claims.

## Reading Memo Plan

Create:

```text
synthesis_memos/
  synthetic_data_best_practices.md
  llm_as_a_judge_survey.md
```

Each memo should contain:

1. paper claim summary
2. which Week 11 design choice it influences
3. where we agree
4. where we disagree based on Week 10 evidence

These memos should be started before heavy dataset authoring, because the brief expects the common reading to inform the authoring decisions rather than merely document them after the fact.

For interim, the two required common-reading memos should be treated as completed deliverables, not rough drafts. A completed memo should include:

1. one paper claim or design principle
2. the Week 11 design choice it affects
3. an explicit agreement or disagreement
4. justification tied to Week 10 evidence or the benchmark design

Summary-only notes do not satisfy the intent of the brief.

## Methodology Update Plan

`methodology.md` is no longer done once the Act I files exist. After the dataset partitions and contamination checks are on disk, update it with:

1. final interim partition counts
2. contamination artifact paths
3. partitioning protocol as actually implemented
4. deferred work and why it was deferred

This ensures the repo-level methodology matches the real dataset state rather than freezing at the Act I draft stage.

## Interim PDF Plan

The Wednesday interim submission requires:

- GitHub repo
- PDF report

Create a source file for the PDF in the repo, for example:

```text
interim_report.md
```

and export it to PDF for submission.

The PDF must include:

1. Bench composition
   - counts per dimension
   - counts per partition
   - counts per source mode

2. Inter-rater agreement results
   - use the completed two-pass interim subset

3. Three example tasks with rubric application shown end to end
   - one programmatic
   - one trace-derived
   - one adversarial

4. What is working, what is not, plan for Days 4–7

Implementation note:

- the counts shown in the PDF must be derived from the real JSONL files, not hand-entered
- `generation_scripts/summarize_dataset.py` is the canonical counts generator and must emit `generation_scripts/counts.json`
- `interim_report.md` should only use numbers that were generated from `generation_scripts/counts.json`

Suggested supporting command:

- add a “counts” step in the generation workflow that:
  - runs `generation_scripts/summarize_dataset.py`
  - prints a short human-readable summary to stdout
  - writes `generation_scripts/counts.json`

This keeps the PDF composition section tied to reproducible artifact counts.

Evidence requirement for the PDF example tasks:

- the “three example tasks with rubric application shown” must be backed by a reproducible evaluator run
- choose three concrete task IDs:
  - one programmatic
  - one trace-derived
  - one adversarial
- run `scoring_evaluator.py` against those tasks and include in `interim_report.md`:
  - the numeric score
  - the per-dimension rubric breakdown (whatever the evaluator emits)
  - the exact command used
- store raw evaluator output in-repo (for example `eval_examples/`) and quote excerpts in the report

## Implementation Sequence

### Phase 1: Reading + framing

Deliver:

- first two synthesis memos in `synthesis_memos/`
- early draft sections for `datasheet.md`:
  - Motivation
  - Uses
  - Collection framing
- `interim_report.md` scaffold with required section headers

### Phase 2: Dataset scaffold

Deliver:

- `schema.json` updated to include metadata fields needed for time-shift verification, including `signal_date` and `signal_source`
- `tenacious_bench_v0.1/` folder structure
- `generation_scripts/` scaffold

### Phase 3: First authored task batch

Deliver:

- `tasks.jsonl` files with first 60–80 tasks
- schema validation run:
  - `generation_scripts/validate_schema.py` executed
  - `generation_scripts/schema_validation_report.json` committed
- dedup run:
  - `generation_scripts/dedup.py` executed
  - `generation_scripts/dedup_report.json` committed
- label pass 1 on a 30-task subset starts here
- identify the smaller 10–15 task subset that must complete the two-pass loop for the interim PDF

Validation note:

- schema validation needs an explicit runnable command, not just scoring
- add and document one exact validation path in `generation_scripts/README.md`
- recommended implementation:
  - install `jsonschema`
  - run a small script or one-liner that validates each JSONL record against `schema.json`

### Phase 4: Dataset documentation + partition hygiene

Deliver:

- `datasheet.md`
- `generation_scripts/README.md`
- dataset `README.md`
- dataset summary run:
  - `generation_scripts/summarize_dataset.py` executed
  - `generation_scripts/counts.json` committed
- contamination run:
  - `generation_scripts/contamination_check.py` executed
  - root-level `contamination_check.json` committed
- update `methodology.md` with implemented partitioning and contamination information
- update root `README.md` with real partition counts and evaluator run command

### Phase 5: Quality controls

Deliver:

- `inter_rater_agreement.md`
- completed two-pass agreement computation for the 10–15 task interim subset, with at minimum percentage agreement per rubric dimension
- truthful status note for any remaining larger-sample agreement work

### Phase 6: Memo refinement + deferred-mode note

Deliver:

- refined synthesis memos if needed
- explicit note in docs that multi-LLM synthesis is deferred or partial for interim
- completed `interim_report.md` ready for PDF export

## Risks

### Risk 1: dataset too small

Mitigation:

- prioritize probe-derived and programmatic tasks first

### Risk 2: contamination checks delayed

Mitigation:

- run exact duplicate and n-gram checks first for speed
- run the embedding-similarity pass early, even on a small batch
- embedding similarity must complete before sealing `held_out/`

### Risk 3: inter-rater timing slips

Mitigation:

- start pass 1 as soon as task batch exists
- the 10–15 task interim subset is non-optional and must complete pass 2 in time for the PDF
- only the remaining larger 30-task loop may be recorded as partially pending

### Risk 4: docs drift away from actual artifacts

Mitigation:

- write docs only after files and counts exist
- keep all counts tied to real JSONL rows on disk

## Definition of Done For Interim

The interim package is in a strong state when the repo contains:

- root-level Act I files already completed
- `tenacious_bench_v0.1/` with real `train/`, `dev/`, and `held_out/` files
- `generation_scripts/` with reproducible task-building scripts and generated artifacts:
  - `validate_schema.py` and `schema_validation_report.json`
  - `dedup.py` and `dedup_report.json`
  - `split_dataset.py` (seeded)
  - `summarize_dataset.py` and `counts.json`
  - `contamination_check.py`
- `generation_scripts/run_manifest.json`
- `datasheet.md`
- root-level `contamination_check.json`
- `inter_rater_agreement.md` with truthful status
- at least two completed reading memos
- `interim_report.md` ready for PDF export
- `eval_examples/` containing the three PDF example task runs

## Pre-Review Checklist

Before sending the plan for review, sanity-check these points:

1. folder names in the plan match the brief exactly: `train/`, `dev/`, `held_out/`
2. Phase 1 really starts with completed common-reading memos, not placeholder drafts
3. the plan explicitly states what is deferred for interim:
   - multi-LLM synthesis
   - judge-filter logs for synthesized tasks
4. the plan guarantees one completed 10–15 task two-pass inter-rater subset for the interim PDF
5. contamination checks cover:
   - n-gram overlap
   - embedding similarity
   - time-shift verification
6. `methodology.md` is scheduled for update after dataset generation
7. the PDF report source is represented in the repo and tied to real JSONL-derived counts
8. the PDF’s three example tasks include raw evaluator outputs saved in-repo (not described from memory)

Review gate:

- if any checklist item fails, identify:
  - which phase owns the fix
  - whether the failure blocks interim quality
  - what fallback is acceptable without misrepresenting progress

## Recommended Next Action

Begin with:

1. drafting the two synthesis memos
2. drafting the Motivation / Uses / Collection sections of `datasheet.md`
3. updating `schema.json` planning for `signal_date` and `signal_source`
4. then creating `tenacious_bench_v0.1/` and `generation_scripts/`
5. then generating the first probe-derived task batch

That keeps the work aligned with the brief: common reading first, dataset framing second, dataset authoring immediately after.
