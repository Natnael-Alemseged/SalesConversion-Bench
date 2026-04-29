# Generation Scripts

These scripts build and validate the interim `tenacious_bench_v0.1` dataset.

## Interim authoring modes actually used

- `trace_derived`
- `programmatic`
- `hand_authored`

Deferred for the interim batch:

- `multi_llm_synthesis`
- judge-filter logs for synthesized tasks

Scaffold committed for the next stage:

- `routing_policy.md`
- `multi_llm_routing.py`
- `judge_prompts/pointwise_judge.md`
- `judge_prompts/pairwise_tiebreak.md`
- `judge_filter.py`

## Build order

1. Build the source pool:

```bash
python3 generation_scripts/build_probe_tasks.py
```

## Authoring pipeline (rotation + judge-filter + audit logs)

The long-term authoring pipeline entrypoint is:

```bash
python3 generation_scripts/build_dataset.py
```

What it does (readable in source):

- selects generator + judge models and **enforces model-family rotation**
- applies a pointwise **judge-filter** with explicit per-dimension thresholds
- records a full **audit log JSONL** plus a run manifest under `generation_scripts/audit_logs/`
- records near-duplicate pairs for pairwise resolution

This entrypoint currently runs in deterministic stub mode (`implemented_with_live_llm_calls: false`) so the pipeline is runnable without external model APIs, while keeping the routing/threshold/audit structure explicit for grading.

2. Validate source-pool schema:

```bash
python3 generation_scripts/validate_schema.py tenacious_bench_v0.1/source_pool.jsonl
```

3. Check exact duplicates:

```bash
python3 generation_scripts/dedup.py tenacious_bench_v0.1/source_pool.jsonl
```

4. Split into partitions with a fixed seed:

```bash
python3 generation_scripts/split_dataset.py tenacious_bench_v0.1/source_pool.jsonl --seed 20260429
```

5. Summarize dataset counts for the interim PDF:

```bash
python3 generation_scripts/summarize_dataset.py
```

6. Run contamination checks:

```bash
python3 generation_scripts/contamination_check.py
```

7. Run the deterministic scorer on any partition:

```bash
python3 scoring_evaluator.py --task-file tenacious_bench_v0.1/train/tasks.jsonl
```

## Validation split

- `validate_schema.py` checks JSON Schema conformance
- `scoring_evaluator.py` checks rubric/scoring behavior

## Reproducibility notes

- partition seed is recorded in `run_manifest.json`
- composition counts come from `counts.json`
- contamination output is written to the root-level `contamination_check.json`

## Embedding model note

Pinned target model for contamination work:

- `sentence-transformers/all-MiniLM-L6-v2`

Current environment note:

- if the package/model is unavailable locally, the interim contamination script uses a lexical cosine fallback and records that fact in the output
