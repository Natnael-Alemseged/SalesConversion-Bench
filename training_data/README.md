# Path B training data (`preference_pairs.jsonl`)

This folder holds **verified preference pairs** for LoRA / SimPO-style training: each row has a `prompt`, a `chosen` email that passes `scoring_evaluator.py`, and a `rejected` email that fails at least one rubric check for that task.

## Regenerate

From the repo root:

```bash
# Heuristic rejected drafts only (no API calls; reproducible)
python3 generation_scripts/build_preference_pairs.py --dry-run --max-tasks 120

# Live rejected drafts (requires OPENROUTER_API_KEY and httpx)
python3 generation_scripts/build_preference_pairs.py --max-tasks 120
```

**Chosen side:** pairs start from each train task’s `ground_truth_output`, then apply **deterministic personalization** (company name injected into templated bodies) so `chosen` strings are not dominated by a handful of duplicates. Optional **API paraphrase** runs only when the same chosen text would repeat many times *and* a key is set.

**Rejected side:** without an API key, heuristics are tuned per `failure_category` so `score_task` reliably produces at least one failure.

## Current artifact (verify after each run)

After `build_preference_pairs.py`, the script prints **accepted pair count**, **live vs heuristic** rejected counts, and **unique chosen / max repeat**. Typical dry-run shape:

- **~100+** accepted pairs from 120 train tasks (remainder skipped when chosen fails scoring or rejected accidentally passes).
- **`mode`: `heuristic`** for every row if `OPENROUTER_API_KEY` is unset.
- **Unique chosen** count should be **well above** the old ~10 baseline thanks to personalization.

Submission targets in `FINAL_SUBMISSION_TASKS.md` (**200–500** pairs) still imply scaling up (more tasks, API rejects, or additional rewrite passes)—this directory is the **working** slice unless you expand the pipeline.

## Contamination

Dataset-wide held-out checks live in `../contamination_check.v0.2.json` (train/dev vs held-out tasks).

For **preference pairs** specifically, run:

```bash
python3 generation_scripts/contamination_preference_pairs.py
```

Output: `training_data/contamination_preference_pairs.json` — flags train tasks used in pairs whose **input_text** shares an 8-gram with any **held_out** task (same rule family as `generation_scripts/contamination_check.py`).

## Files

| File | Purpose |
|------|---------|
| `preference_pairs.jsonl` | One JSON object per line for trainers |
| `preference_pairs_audit.jsonl` | Per-task accept/skip reasons |
| `contamination_preference_pairs.json` | Pair-vs-held overlap report (generated) |
