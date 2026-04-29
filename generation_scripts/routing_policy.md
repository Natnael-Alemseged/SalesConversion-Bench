# Generation Routing Policy

This document records the intended multi-route authoring policy for the final benchmark build, even though the current interim batch only used `trace_derived`, `programmatic`, and `hand_authored` sources.

## Route tiers

### Cheap synthesis tier

Use a lower-cost model for breadth generation when the task is primarily a paraphrase, surface-form variation, or controlled slot substitution of an already validated seed.

Typical use:

- produce 3 to 5 candidate phrasings from one validated seed
- vary company names, dates, thread stages, and signal wording
- keep the failure category fixed

Cheap-tier generations are never promoted directly into the benchmark. They must pass schema validation, deduplication, and the pointwise judge filter before they can be considered.

### Eval-tier synthesis tier

Use a stronger model for tasks where the difficulty depends on nuanced business framing, confidence calibration, or competitor-gap sourcing rather than simple paraphrase.

Typical use:

- generate corrected rewrites for preference pairs
- write edge cases where the failure is subtle but commercially important
- adjudicate borderline cases after cheap-tier filtering

## Rotation policy

- One model family generates the candidate pool for a batch.
- A different model family performs pointwise judging for that same batch.
- Pairwise tie-breaks use the eval-tier judge model, not the original generator.
- Preference-pair creation must not use the same model family as both the rejected-output generator and the final judge for that example pool.

This policy exists to reduce self-preference leakage and keep Act III / Act IV evaluation legible.

## Judge filter stages

1. Run schema validation and deterministic checks first.
2. Run pointwise scoring on:
   - coherence
   - verifiability
   - rubric clarity
3. Reject candidates with any dimension below the minimum threshold.
4. If two candidates survive and are near-duplicates, run pairwise comparison to keep only the stronger version.
5. Keep the winning candidate plus an audit log of route, model, and judge outcomes.

## Interim status on 2026-04-29

- Implemented in production for this repo: deterministic validation and dataset splitting.
- Scaffolded but not yet executed with live model calls: pointwise judging, pairwise near-duplicate comparison, and explicit cheap-tier versus eval-tier routing.
