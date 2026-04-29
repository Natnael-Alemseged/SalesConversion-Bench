# Rubric Alignment Design (Long-Term)

> Goal: Close remaining rubric gaps by making the multi-LLM authoring pipeline *real and auditable*, scaling the dataset to the required size/proportions, and tightening documentation so graders can verify claims from committed artifacts (without executing code).

## Current state (what already aligns)

- `audit_memo.md` meets the memo evidence thresholds (≤600 words, ≥8 probe IDs, ≥5 trace IDs, distinct gaps).
- `scoring_evaluator.py` is a structurally sound deterministic scorer with decomposed checks, input validation, and calibration notes.
- `generation_scripts/` contains runnable deterministic authoring tooling (schema validation, exact dedup, seeded split, contamination report) and committed judge prompt files, but multi-LLM routing/judge filtering is explicitly stubbed.

## Rubric gaps to close

1. **Generation pipeline**: rotation across model families must be enforced in code (not just described), judge-filter thresholds must be explicit and applied per-dimension, and audit logs must show reproducible decisions. Pairwise dedup selection should be visible.
2. **Datasheet**: must report composition for a 200–300 task dataset, including counts by source-mode, partition (50/30/20), and failure dimension.
3. **Synthesis memos**: must disagree with a *specific paper design choice* with a section/page reference and justify using the trainee’s own evidence (Week 10/11 probe/trace refs).
4. **Methodology**: must describe stratification protocol in prose (not only implied by code).
5. **README**: must state explicit environment requirements (Python version).

## Design choice: “Clean” pipeline refactor (best long-term)

### High-level architecture

Create a small, cohesive authoring package under `generation_scripts/authoring/` that orchestrates:

- deterministic validations (schema, deterministic scorer checks, exact dedup)
- multi-LLM routing policy (cheap vs eval-tier)
- **rotation enforcement** (generator family != judge family per pool)
- **judge filter** (pointwise scoring on 3 dimensions with explicit thresholds)
- **pairwise near-duplicate resolution** (tie-break prompt)
- full **audit logging** (JSONL log per candidate + manifest per run)

This keeps the “read-as-source” rubric legible: graders can open one orchestrator file and see policy + enforcement + thresholds in code.

### New/updated files

Create:

- `generation_scripts/authoring/config.py`
  - declarative model-family inventory (generator/judge families) and tier mapping
  - explicit thresholds for pointwise judge dimensions
  - reproducibility defaults (seed, sample sizes)
- `generation_scripts/authoring/io.py`
  - JSONL load/dump helpers; audit log writer
- `generation_scripts/authoring/rotation.py`
  - enforce “generator family cannot judge same pool”; helper to choose judge family
- `generation_scripts/authoring/judging.py`
  - prompt loading from `generation_scripts/judge_prompts/*.md`
  - strict JSON parse + default-on-failure behavior (malformed outputs reject)
  - pointwise + pairwise interfaces (even if live calls are toggled off)
- `generation_scripts/authoring/dedup.py`
  - near-duplicate detection + keep/drop recording (pairwise winner)
- `generation_scripts/build_dataset.py` (new main entrypoint)
  - orchestrates authoring end-to-end and writes:
    - `tenacious_bench_v0.1/source_pool.jsonl` (or `tenacious_bench_v0.2/` if version bump)
    - `generation_scripts/run_manifest.json` (seed, models used, thresholds)
    - `generation_scripts/audit_logs/authoring_run_<timestamp>.jsonl`

Update (minimally):

- `generation_scripts/judge_filter.py` and `generation_scripts/multi_llm_routing.py`
  - either become thin wrappers around the new package or remain as “interim” legacy; README points to the new entrypoint.

### “Live LLM calls” vs “readable enforcement”

Rubric grading is source-code-only, but it still expects:

- explicit rotation policy in code
- visible judge-filter decomposition with thresholds
- prompts committed as standalone files (already true)
- differentiating cheap vs eval-tier usage (in routing policy + enforced by code paths)

This design supports both:

- a `--dry-run` mode that emits routed decisions and expected judge calls without executing
- a `--run-live` mode (future) that actually calls models and records responses in audit logs

### Judge filter (pointwise + thresholds)

Pointwise judge dimensions:

- **coherence**
- **verifiability**
- **rubric_clarity**

All on {1,3,5}. Threshold policy (documented in code):

- reject if any dimension < 3
- accept if all dimensions >= 3

Pairwise tie-break invoked when:

- near-duplicate overlap > threshold (e.g., Jaccard >= 0.8)

### Rotation & tier policy

- For each authoring batch/pool:
  - generator model family is selected by tier (cheap vs eval)
  - judge model family must be different from the generator’s family
  - pairwise judge uses eval-tier family (still distinct from the generator)
- Eval-tier usage is limited to a documented calibration subset for expensive operations when appropriate (configurable).

## Dataset scaling design (200–300 tasks)

Target composition:

- trace-derived: ~30%
- programmatic: ~30%
- multi-LLM synthesis: ~25%
- hand-authored adversarial: ~15%

Partitioning:

- 50/30/20 split with a fixed seed
- stratify by `metadata.week10_probe_ids` “family” to avoid leakage of near-identical variants across partitions (already implemented in `split_dataset.py`; must be documented in `methodology.md`).

Artifacts to regenerate after scaling:

- `generation_scripts/counts.json`
- `generation_scripts/run_manifest.json`
- `contamination_check.json`
- `datasheet.md` composition tables

## Documentation alignment

### Methodology

Add a short “Stratification protocol” subsection explaining:

- family key definition (`week10_probe_ids` tuple else `source_mode`)
- why it reduces train/held-out leakage and preserves failure-mode diversity

### Synthesis memos

For each memo:

- name a concrete paper decision (with section/page/figure reference)
- disagree with justification grounded in Week 10/11 evidence (probe IDs + trace refs)
- explain the repo-level design implication (pipeline/evaluator choice)

### README

Add explicit Python version requirement and keep commands as the canonical entrypoints.

## Non-goals (for this alignment pass)

- Changing Week 10 agent behavior.
- Training the Path B critic (kept as future work, but pipeline must support it).

