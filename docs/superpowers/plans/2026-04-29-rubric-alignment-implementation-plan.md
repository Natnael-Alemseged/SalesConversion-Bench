# Rubric Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close remaining rubric gaps by making the authoring pipeline enforce rotation + judge-filter + audit logs in code, scaling the dataset to 200–300 tasks with required mode proportions, and tightening docs (datasheet/methodology/memos/README) to be verifiable from committed artifacts.

**Architecture:** Introduce a small `generation_scripts/authoring/` package that centralizes routing, rotation enforcement, judge filtering, near-dup tie-break selection, and audit logging. Keep deterministic build/validate/split/contam scripts, but add a new orchestrator entrypoint `generation_scripts/build_dataset.py` that produces a manifest + audit logs and calls the existing partitioning/summary scripts.

**Tech Stack:** Python 3.x, existing repo scripts, JSONL artifacts, `jsonschema` validator already in use.

---

### Task 1: Add authoring package + orchestrator entrypoint

**Files:**
- Create: `generation_scripts/authoring/config.py`
- Create: `generation_scripts/authoring/io.py`
- Create: `generation_scripts/authoring/rotation.py`
- Create: `generation_scripts/authoring/judging.py`
- Create: `generation_scripts/authoring/dedup.py`
- Create: `generation_scripts/build_dataset.py`
- Modify: `generation_scripts/README.md` (point to new entrypoint)

- [ ] **Step 1: Write a failing “contract” test (lightweight)**

Create `tests/test_authoring_rotation.py` asserting that when generator family == judge family, the rotation enforcer rejects the plan (raises ValueError).

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q`
Expected: FAIL (tests directory missing / functions not implemented yet).

- [ ] **Step 3: Implement minimal authoring modules**

Implement:
- model family definitions + thresholds in `config.py`
- `select_judge_family(generator_family)` in `rotation.py` with enforcement
- `load_jsonl/dump_jsonl/append_jsonl` in `io.py`
- `parse_judge_json(...)` in `judging.py` with default-on-failure rejection
- near-dup Jaccard detection + “keep/drop” audit in `dedup.py`
- `build_dataset.py` orchestrator that runs:
  - route decisions
  - rotation enforcement
  - (dry-run) judge filter producing structured outputs with explicit thresholds
  - pairwise resolution for near-dups
  - writes manifest + audit log JSONL

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q`
Expected: PASS.

---

### Task 2: Scale dataset to 200–300 with required mode proportions

**Files:**
- Modify: `generation_scripts/build_probe_tasks.py` (or create `generation_scripts/expand_tasks.py`)
- Modify: `datasheet.md`
- Regenerate: `tenacious_bench_v0.1/*/tasks.jsonl` (or bump to `tenacious_bench_v0.2/`)
- Regenerate: `generation_scripts/counts.json`, `generation_scripts/run_manifest.json`, `contamination_check.json`

- [ ] **Step 1: Decide dataset version bump**

If changing task counts materially, prefer creating `tenacious_bench_v0.2/` to preserve the interim slice.

- [ ] **Step 2: Implement scaling logic**

Add a script that:
- starts from existing 60 seeds
- generates additional tasks by controlled programmatic expansion per failure category
- adds a “synthesis placeholder” row format for `multi_llm_synthesis` with audit metadata (if live calls still disabled)
- enforces mode proportions in counts

- [ ] **Step 3: Run build + validation + split + summarize + contamination**

Run:
- `python3 generation_scripts/build_dataset.py --target-count 240 --seed 20260429`
- `python3 generation_scripts/validate_schema.py <new_source_pool>`
- `python3 generation_scripts/dedup.py <new_source_pool>`
- `python3 generation_scripts/split_dataset.py <new_source_pool> --seed 20260429`
- `python3 generation_scripts/summarize_dataset.py`
- `python3 generation_scripts/contamination_check.py`

- [ ] **Step 4: Update `datasheet.md` composition tables**

Update totals and per-mode/per-partition/per-failure counts to match regenerated `counts.json`.

---

### Task 3: Upgrade synthesis memos to “Robust”

**Files:**
- Modify: `synthesis_memos/synthetic_data_best_practices.md`
- Modify: `synthesis_memos/llm_as_a_judge_survey.md`

- [ ] **Step 1: Add “specific design choice” section**

For each memo:
- name a paper decision (with section/page reference)
- disagree
- cite your own Week 10 evidence (probe IDs + trace refs)
- state the repo-level implication (what pipeline/evaluator choice follows)

---

### Task 4: Tighten methodology + README

**Files:**
- Modify: `methodology.md`
- Modify: `README.md`

- [ ] **Step 1: Add stratification protocol prose**

Describe family grouping by `metadata.week10_probe_ids` and why it reduces leakage / improves coverage.

- [ ] **Step 2: Add explicit Python version requirement**

Add a line like “Python 3.11+ recommended” in README setup.

---

### Task 5: Verification checklist (before claiming alignment)

- [ ] Run: `python3 generation_scripts/validate_schema.py <source_pool>`
- [ ] Run: `python3 generation_scripts/dedup.py <source_pool>`
- [ ] Run: `python3 generation_scripts/split_dataset.py <source_pool> --seed 20260429`
- [ ] Confirm: `datasheet.md` reports totals and breakdowns consistent with `generation_scripts/counts.json`
- [ ] Confirm: pipeline code visibly enforces rotation + judge thresholds + audit logs (readable without execution)

