# Generation Routing Policy

This document records the multi-route authoring policy used by the current source scaffold. Live model calls are still stubbed, but the routing, calibration-sample escalation, rotation, and audit structure are implemented in source.

## Route tiers

### Cheap synthesis tier

Use a lower-cost model for breadth generation when the task is primarily a paraphrase, surface-form variation, or controlled slot substitution of an already validated seed.

Typical use:

- produce 3 to 5 candidate phrasings from one validated seed
- vary company names, dates, thread stages, and signal wording
- keep the failure category fixed

Cheap-tier generations are never promoted directly into the benchmark. They must pass schema validation, deduplication, and the pointwise judge filter before they can be considered.

For `multi_llm_synthesis` tasks, cheap-tier generation is the default path.

### Eval-tier synthesis tier

Use a stronger model for tasks where the difficulty depends on nuanced business framing, confidence calibration, or competitor-gap sourcing rather than simple paraphrase.

Typical use:

- generate corrected rewrites for preference pairs
- write edge cases where the failure is subtle but commercially important
- adjudicate borderline cases after cheap-tier filtering

Eval-tier generation is also used for a seeded calibration sample of `multi_llm_synthesis` tasks and for trace-preserving rewrites where the source failure must be preserved faithfully.

## Rotation policy

- One model family generates the candidate pool for a batch.
- A different model family performs pointwise judging for that same batch.
- Pairwise tie-breaks use the eval-tier judge model, not the original generator.
- Preference-pair creation must not use the same model family as both the rejected-output generator and the final judge for that example pool.

In the current scaffold:

- most `multi_llm_synthesis` tasks route to the cheap generator tier
- a deterministic 10% calibration sample is escalated to eval-tier generation
- all judge calls remain eval-tier, and rotation enforcement prevents generator-family reuse at the judge step

This policy exists to reduce self-preference leakage and keep Act III / Act IV evaluation legible.

## Judge filter stages

1. Run schema validation and deterministic checks first.
2. Run pointwise scoring on:
   - coherence
   - verifiability
   - rubric clarity
3. Reject candidates with any dimension below the minimum threshold (`3` for coherence, verifiability, and rubric clarity).
4. If two candidates survive and are near-duplicates, run pairwise comparison to keep only the stronger version.
5. Keep the winning candidate plus an audit log of route, model, and judge outcomes.

## Current source status on 2026-04-30

- Implemented in source for this repo: deterministic validation, family/category-aware dataset splitting, route selection, cheap-versus-eval generator assignment, rotation enforcement, pointwise thresholding, and near-duplicate pair logging.
- Still stubbed: live external model calls that would replace the current deterministic judge/generator stand-ins.

## References

- Li et al., *Preference Leakage: A Contamination Problem in LLM-as-a-Judge* (2025) — motivates the rotation policy. A model that generates outputs for a task has shown self-preference bias when asked to judge the same task. The family-separation rule (generator family ≠ judge family) is a direct mitigation of this leakage mechanism.
