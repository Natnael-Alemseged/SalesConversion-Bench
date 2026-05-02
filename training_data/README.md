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

### Parallel run (multiple OpenRouter keys)

Valid for speeding up **live** runs: put several keys in the environment, then shard tasks across threads (one key per shard by default):

```bash
export OPENROUTER_API_KEYS="sk-or-v1-aaa,...,sk-or-v1-bbb"   # or OPENROUTER_API_KEY + OPENROUTER_API_KEY_2 ...
python3 generation_scripts/build_preference_pairs_parallel.py --workers 5 --max-tasks 120 --retry-delay 0.5
```

The parallel script **loads repo `.env` automatically** (unless `--no-dotenv`). To **skip** a broken duplicate slot (e.g. “key #4”) without editing secrets:

```bash
# in .env
OPENROUTER_OMIT_KEY_SLOTS=OPEN_ROUTER_KEY_4,OPENROUTER_API_KEYS[4]
```

Or pass `--omit-key-slot OPEN_ROUTER_KEY_4 --omit-key-slot 'OPENROUTER_API_KEYS[4]'`.

By default it also **preflights** each distinct key with `GET /api/v1/key` and drops keys whose numeric `limit_remaining` is `<= 0`. Use `--no-preflight-keys` to disable.

See `generation_scripts/build_preference_pairs_parallel.py` docstring for env var formats.

**Check which env keys work** (GET `/api/v1/key`, no model spend; loads repo `.env` if present):

```bash
python3 generation_scripts/verify_openrouter_keys.py
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
