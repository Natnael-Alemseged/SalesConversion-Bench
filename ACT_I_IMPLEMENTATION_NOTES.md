## Act I Implementation Notes

This repo had the Week 10 evidence bundle, the Week 11 brief, and the environment scaffold, but it did not yet have the actual Act I submission files. The goal of this pass is to convert the current repo from "prepared to start" into a real interim submission with machine-checkable artifacts.

### What I am adding

1. `methodology.md`
   - Declares Path B.
   - Justifies the choice with the evidence already present in `week_10_data/`.
   - Documents the evidence limits honestly: the available `tau2-bench` run is a retail workflow benchmark, while the Tenacious-specific failure evidence comes from the Week 10 probe and taxonomy artifacts.

2. `audit_memo.md`
   - Explains what the retail benchmark does not grade for Tenacious.
   - Grounds the argument in real probe IDs, probe trace references, and real simulation IDs from the saved Week 10 run.

3. `schema.json`
   - Defines a first-pass Tenacious-Bench task format.
   - Includes three example tasks so the evaluator can run immediately.

4. `scoring_evaluator.py`
   - Implements deterministic scoring for the first-pass rubric.
   - Reuses the real Week 10 bench-capacity checker from `week_10_data/agent/enrichment/bench_capacity.py` instead of re-inventing or hardcoding that logic.
   - Runs against the examples in `schema.json`.

5. `cost_log.csv`
   - Initializes the log with headers so cost tracking is no longer a blank placeholder.

### Why this shape

The Week 11 brief is strict about Act I: the schema has to be machine-verifiable, and the evaluator has to run on real tasks. The fastest way to get to a legitimate interim state is to build a deterministic evaluator around the failures already measured in Week 10:

- bench overcommitment
- unsupported or weakly grounded claims
- tone-policy violations
- premature booking CTA

That lines up with the Path B decision. It also gives you a concrete substrate for Act II and Act III instead of a purely narrative submission.

### Evidence policy used for these files

- Only cite artifacts that are present in this repo or explicitly referenced by files in this repo.
- Treat `week_10_data/trace_log.jsonl` and the saved `results.json` run it points to as real benchmark evidence.
- Treat `probe_library.md` and `failure_taxonomy.md` as the authoritative Tenacious-specific failure evidence bundle for Week 10.
- Do not claim any OpenRouter synthesis, held-out evaluation, or inter-rater work has happened yet.

### What this does not claim

- It does not claim the dataset has been authored.
- It does not claim the judge has been trained.
- It does not claim the current evaluator covers the full Week 11 rubric.

It gives you a truthful Act I base that can be extended without rewriting the story later.
