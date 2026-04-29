# Datasheet for Tenacious-Bench v0.2

## 1. Motivation

Tenacious-Bench exists because generic support or assistant benchmarks do not grade the commercial safety constraints that matter in Tenacious-style B2B sales work. Week 10 evidence showed repeated failures in areas that public benchmarks do not cover well: bench overcommitment, wrong ICP routing, weakly grounded signal claims, condescending competitor-gap framing, and premature booking CTAs. This interim slice is the first authored dataset intended to measure those failures explicitly and reproducibly.

The dataset is also designed to support Path B work. It does not only evaluate the Week 10 generator; it also creates the task substrate from which chosen/rejected preference pairs can later be constructed for a Tenacious-specific critic.

## 2. Composition

Current dataset composition (v0.2):

- total authored pool: 240 tasks
- `train`: 120
- `dev`: 70
- `held_out`: 50

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

This version intentionally hits the Week 11 target range (200 to 300 tasks) so the composition breakdown is meaningful and auditable.

## 3. Collection Process

This interim slice was built from Week 10 evidence already present in the repo:

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
8. split with a fixed seed (50/30/20 target)
9. run contamination checks

Multi-LLM synthesis is included in v0.2 as an explicit source mode. The repo’s long-term authoring policy (rotation, judge filter, and audit logging) is documented in `generation_scripts/routing_policy.md` and enforced/scaffolded by `generation_scripts/build_dataset.py`.

Typical task by source mode:

- `trace_derived`: a direct formalization of a Week 10 failure trace, such as a cold outbound draft that repeats the exact confidence-handling mistake shown in `probe-b3388b3c3582`, but rewritten into the benchmark schema with explicit input fields and a corrected reference output.
- `programmatic`: a controlled variant generated from a high-signal seed, such as repeating the same booking-stage rule across several dates, company names, and thread states while keeping the underlying failure category fixed.
- `multi_llm_synthesis`: a synthesized task candidate produced by a routed generator model and filtered by a routed judge model on (coherence, verifiability, rubric clarity), with the route, model families, and decisions recorded in an audit log.
- `hand_authored`: a smaller edge-case task written manually when the failure depends on nuanced framing or context packing, such as a competitor-gap note that can be factually true, commercially rude, or both depending on phrasing.

## 4. Preprocessing / Transformation

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

## 5. Uses

Intended uses:

- evaluate Tenacious-style prospect-facing outputs
- support Path B preference-pair construction
- document what generic benchmarks miss in this sales workflow
- provide reproducible examples for the interim PDF report

Not intended uses:

- direct prospect outreach without additional review
- claims about general assistant performance outside the Tenacious domain
- production deployment of a trained critic without additional held-out evaluation

## 6. Distribution

The interim slice currently lives only in this repo. It is not yet a public HuggingFace dataset and is not yet packaged as a final public artifact. Interim handling differs from final public handling in one important way: the Wednesday brief requires `held_out/` to exist in the repo, while the later public-artifact quality bar requires revisiting held-out exposure before public release.

License for the interim written artifacts and dataset card text: `CC-BY-4.0`. The benchmark JSONL files are still an interim repo artifact rather than a formally published dataset release, but the planned public-release posture is attribution-preserving rather than closed.

## 7. Maintenance

Near-term maintenance work:

- replace stub synthesis rows with live routed synthesis runs (keeping the same audit log structure)
- replace the interim lexical embedding fallback with the pinned embedding model
- complete inter-rater agreement results
- expand evaluator coverage to competitor-gap sourcing and thread leakage
- build Path B preference pairs from corrected outputs

Concrete maintenance plan:

- grow the pool from 60 tasks to the 200 to 300 task target by adding more trace-derived seeds before broadening synthesis
- replace the lexical similarity fallback with the pinned `sentence-transformers/all-MiniLM-L6-v2` backend and re-run contamination reporting
- add an issue-driven re-review pass whenever a new Week 10 or Week 11 failure category is discovered, so the datasheet and evaluator evolve with the benchmark rather than lagging behind it

## Data Card Layering

### Telescopic

This is an interim benchmark slice for Tenacious sales reliability, not the final public benchmark.

### Periscopic

It is organized around six failure categories grounded in Week 10 evidence and split into train/dev/held_out for later evaluation and training work.

### Microscopic

Each task contains enough structure for deterministic scoring and later preference-pair construction, including grounded signal metadata and optional corrected outputs.
