# Synthesis Memo: Datasheets for Datasets + Data Cards

Gebru et al., *Datasheets for Datasets* (2021).
Pushkarna et al., *Data Cards: Purposeful and Transparent Dataset Documentation* (FAccT 2022).

## Design choice I disagree with (Gebru Section 3 — "Composition")

Both papers treat the composition section as a factual inventory: how many instances, what types, what splits. The implicit assumption is that composition questions have clean answers the dataset author simply records. Gebru lists "does the dataset contain all possible instances or is it a sample?" as a composition question, and Pushkarna's periscopic layer extends this with distribution statistics and feature-level breakdowns.

The assumption breaks down for synthetically authored benchmarks where the composition is an output of a policy, not an observation. In Tenacious-Bench, the 240-task composition reflects an authoring decision — 30% trace-derived, 30% programmatic, 25% multi-LLM synthesis, 15% hand-authored — not a sample drawn from a pre-existing corpus. Describing this as a factual inventory misrepresents how the data was produced and obscures the design choices that determine what failure modes are over- or under-represented.

## Why this matters for Tenacious-Bench specifically

The Week 10 failure taxonomy shows `bench_overcommitment` triggered at 100% (40/40 probes) and `icp_misclassification` at 54% (20/37 probes). Those trigger rates directly shaped the failure-category weights in the dataset: `bench_overcommitment` and `gap_overclaiming` each have 48 tasks; `dual_control_coordination` has 35. These counts are not a neutral observation — they encode a judgment about which failures deserve more adversarial coverage. A standard composition inventory would list the counts without explaining that judgment.

A better documentation approach for this kind of benchmark is to treat composition as a **policy document**, not a count table. For each failure category, record:
- why this category was weighted the way it was (trace evidence)
- what the authoring pipeline would have produced under a uniform distribution
- where the current distribution is likely to bias evaluator scores

Tenacious-Bench's `datasheet.md` follows this approach: each failure category section names the Week 10 probe IDs that motivated its weighting, not just the task counts.

## Where I follow the papers without disagreement

Gebru's collection and preprocessing sections are applied directly. The datasheet records:
- source inputs (Week 10 probe library, trace_log.jsonl, style guide v2, public Crunchbase and layoffs.fyi samples)
- what was redacted (company names replaced with synthetic names, pricing placeholders used for non-public bands)
- the fixed seed used for train/dev/held-out splits (`20260429`)

Pushkarna's layered detail (telescopic / periscopic / microscopic) is partially implemented. The telescopic layer (one-paragraph overview) and periscopic layer (per-split counts, failure-category distribution, source-mode breakdown) are complete. The microscopic layer (per-task quality scores, per-check pass rates) is deferred to the ablation phase when held-out evaluation produces those numbers.

## What this produces in the repo

The composition section of `datasheet.md` documents:
- why counts are not uniform across failure categories
- the authoring-policy decisions behind each category weight
- what a v0.3 revision would need to address if the held-out evaluation shows coverage gaps

This is a stronger documentation artifact than a count table because it makes the authoring policy auditable, not just the output.
