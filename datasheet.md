# Datasheet for Tenacious-Bench v0.2

## 1. Motivation

Tenacious-Bench exists because generic support or assistant benchmarks do not grade the commercial safety constraints that matter in Tenacious-style B2B sales work. Week 10 evidence showed repeated failures in areas that public benchmarks do not cover well: bench overcommitment, wrong ICP routing, weakly grounded signal claims, condescending competitor-gap framing, and premature booking CTAs. This benchmark slice is the first authored dataset intended to measure those failures explicitly and reproducibly.

The dataset is also designed to support Path B work. It does not only evaluate the Week 10 generator; it also creates the task substrate from which chosen/rejected preference pairs can later be constructed for a Tenacious-specific critic.

## 2. Composition

Current dataset composition (v0.2):

- total authored pool: 240 tasks
- `train`: 120
- `dev`: 73
- `held_out`: 47

Current source-mode counts:

- `trace_derived`: 72 / 240 (`30.0%`)
- `programmatic`: 72 / 240 (`30.0%`)
- `multi_llm_synthesis`: 60 / 240 (`25.0%`)
- `hand_authored`: 36 / 240 (`15.0%`)

Current failure-category counts:

- `bench_overcommitment`: 48
- `dual_control_coordination`: 35
- `gap_overclaiming`: 44
- `icp_misclassification`: 39
- `signal_overclaiming`: 35
- `tone_drift`: 39

Task fields include:

- task metadata
- brief/input context
- candidate output
- optional ground-truth output
- deterministic rubric checks

Each record is structured so the benchmark can support both direct evaluation and later preference-pair construction. The metadata block carries probe lineage, trace references, signal date, signal source, and source-mode provenance so a reader can trace the task back to its authoring path. The input block captures the fields that matter for Tenacious policy decisions, including `company_name`, `icp_segment`, `thread_stage`, `signal_brief`, `prior_thread`, `capacity_request`, and `bench_summary`. The output side stores the candidate draft under evaluation and, when available, a corrected `ground_truth_output` that later becomes the preferred side of a preference pair. The split sizes were chosen to keep enough training mass for Path B fine-tuning while still preserving separate `dev` and `held_out` partitions for rubric iteration and headline reporting. Family-preserving stratification with a fixed seed was used so closely related task variants do not leak freely across splits. The source-mode mix is intentionally balanced between trace-derived and programmatic rows, with smaller but still material hand-authored and multi-LLM synthesis slices, because the benchmark is meant to reflect both faithful trace formalization and controlled expansion rather than one authoring style only. This version intentionally hits the Week 11 target range (200 to 300 tasks) so the composition breakdown is meaningful and auditable.

## 3. Collection Process

This benchmark slice was built from Week 10 evidence already present in the repo:

- `week_10_data/probe_library.md`
- `week_10_data/failure_taxonomy.md`
- `week_10_data/trace_log.jsonl`

Collection strategy:

1. identify the highest-value Week 10 failure categories
2. create probe-derived seed tasks
3. expand those tasks programmatically through controlled parameter variation
4. add hand-authored edge cases where framing is the failure
5. add multi-LLM synthesis rows (with rotation + judge-filter scaffolding recorded in metadata / audit logs)
6. validate against `schema.json`
7. deduplicate
8. split with a fixed seed (approximately 50/30/20 after family-preserving stratification)
9. run contamination checks

Multi-LLM synthesis is included in v0.2 as an explicit source mode. The repo’s long-term authoring policy (rotation, judge filter, calibration-sample escalation, and audit logging) is documented in `generation_scripts/routing_policy.md` and enforced/scaffolded by `generation_scripts/build_dataset.py`.

Typical task by source mode:

- `trace_derived`: a direct formalization of a Week 10 failure trace, such as a cold outbound draft that repeats the exact confidence-handling mistake shown in `probe-b3388b3c3582`, but rewritten into the benchmark schema with explicit input fields and a corrected reference output.
- `programmatic`: a controlled variant generated from a high-signal seed, such as repeating the same booking-stage rule across several dates, company names, and thread states while keeping the underlying failure category fixed.
- `multi_llm_synthesis`: a synthesized task candidate produced by a routed generator model and filtered by a routed judge model on (coherence, verifiability, rubric clarity), with the route, model families, and decisions recorded in an audit log.
- `hand_authored`: a smaller edge-case task written manually when the failure depends on nuanced framing or context packing, such as a competitor-gap note that can be factually true, commercially rude, or both depending on phrasing.

## 4. Preprocessing / Cleaning / Labeling

The main preprocessing steps were:

- mapping Week 10 probes into a normalized task schema
- adding time-shift metadata fields (`signal_date`, `signal_source`)
- writing a source pool JSONL file
- validating JSON Schema conformance
- running exact-duplicate detection
- splitting tasks into `train`, `dev`, and `held_out` partitions

Contamination checks currently include:

- 8-gram overlap checks
- embedding-similarity checks
- time-shift verification

The intended embedding backend is `sentence-transformers/all-MiniLM-L6-v2`. If unavailable, the repo’s contamination script records a lexical cosine fallback explicitly in the output artifact.

Labeling for the committed benchmark artifacts was performed by a single human annotator: the project author. The label schema is deliberately narrow and operational rather than open-ended. Each task carries up to five binary rubric dimensions: `banned_phrase_check`, `signal_grounding_check`, `booking_stage_check`, `bench_capacity_check`, and `format_check`. A task either passes or fails each dimension that is present on its rubric, and absent checks are left out rather than imputed. This structure lets the deterministic evaluator and later preference construction pipeline map directly onto the same pass/fail targets. Calibration was not treated as a one-shot self-review. Instead, the author completed a 30-task inter-rater agreement pass documented in `inter_rater_agreement.md`, waited more than 24 hours between the first and second labeling passes, and then compared disagreements by dimension to identify where the machine rubric was too weak or too lenient. That calibration loop is the source of the stricter `format_check` and `signal_grounding_check` interpretations described elsewhere in the repo. For the judge-filter stage, the committed run used the deterministic scoring stub that is already checked into source and auditable from the repo. The codebase also contains configuration for routing live LLM judge calls through OpenRouter, but that live path was not executed for the committed artifacts reflected in this release.

## 5. Uses

Intended uses:

- evaluate Tenacious-style prospect-facing outputs
- support Path B preference-pair construction
- document what generic benchmarks miss in this sales workflow
- provide reproducible examples for the reporting PDF

Not intended uses:

- direct prospect outreach without additional review
- claims about general assistant performance outside the Tenacious domain
- production deployment of a trained critic without additional held-out evaluation

## 6. Distribution

The dataset is publicly available at [Natnaela/tenacious-bench](https://huggingface.co/datasets/Natnaela/tenacious-bench). The Hugging Face release is open with no access gating, so readers can inspect the dataset card, browse the task files, and download the JSONL artifacts directly without requesting permission. The repo copy remains useful because it keeps the benchmark generation scripts, evaluator, contamination reports, and training notebook in one place, but the dataset itself is already published as a standalone artifact rather than waiting on a later release step.

License for the written artifacts, dataset card text, and public dataset release: `CC-BY-4.0`. That licensing choice is intentionally attribution-preserving rather than closed because the benchmark is meant to be auditable, reusable for research comparison, and citeable in later domain-evaluation work.

## 7. Maintenance

The dataset is maintained by Natnael Alemseged, the project author and benchmark maintainer for this repo and the corresponding Hugging Face release. Errors should be reported through the repository issue tracker or by opening a discussion tied to the affected task IDs so provenance, split membership, and evaluator consequences can be reviewed together. Versioning is additive and explicit: changes that alter task text, deterministic checks, or split membership should be reflected in the repo artifacts and the published dataset card rather than silently overwritten in place. The current benchmark pool is intended to stay stable enough for comparison, so routine maintenance is expected to focus on corrections, clearer documentation, and evaluator improvements rather than churn in headline counts. Additions are planned when new Tenacious failure families appear or when under-covered categories need more examples, but those expansions should preserve the existing benchmark lineage instead of replacing it. When a revision ships, the maintainer should update the dataset card, split artifacts, contamination outputs, and supporting rationale documents together so downstream readers can tell exactly what changed and why.

### Known Biases and Limitations

This benchmark has several known biases that should shape how results are interpreted. First, there is a single-author bias: all tasks were authored by one person, and the initial task pool was derived from one company’s observed failure patterns rather than from a multi-annotator authoring program. No external annotators were used for task authoring, so the benchmark reflects one maintainer’s decomposition of the Week 10 evidence even though later calibration passes improved internal consistency. Second, there is a geographic and industry bias. The signals, prospecting assumptions, and ICP segment rules all reflect US-based B2B software sales; benchmark behavior on non-US markets, non-SaaS industries, or very different buying cycles is untested. Third, there is a synthesis-mode bias. The committed `multi_llm_synthesis` tasks were generated in clone-fallback mode rather than by a fully live LLM synthesis run, so those 60 tasks share distributional properties with the trace-derived slice and should not be interpreted as an independently sampled synthetic population. Fourth, there is class imbalance in the preference-pair setup: the deterministic evaluator used as the weak baseline yields near-zero scores for some task types, which structurally over-represents those tasks in the rejected position of chosen/rejected pairs. That makes the benchmark useful for targeted commercial-safety auditing, but it also means the resulting preference data is not class-balanced in the way a general-purpose instruction preference corpus would be.

## Data Card Layering

### Telescopic

This is a published benchmark slice for Tenacious sales reliability with committed repo artifacts and a public Hugging Face release.

### Periscopic

It is organized around six failure categories grounded in Week 10 evidence and split into train/dev/held_out for later evaluation and training work.

### Microscopic

Each task contains enough structure for deterministic scoring and later preference-pair construction, including grounded signal metadata and optional corrected outputs.
