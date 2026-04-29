# Tenacious-Bench v0.1 Interim Slice

This directory contains the authored interim dataset slice for the Week 11 Tenacious sales benchmark.

## Partitions

- `train/tasks.jsonl`: 29 tasks
- `dev/tasks.jsonl`: 18 tasks
- `held_out/tasks.jsonl`: 13 tasks

## Source pool

- `source_pool.jsonl`: 60-task authored pool before partitioning

## Interim authoring modes used

- `trace_derived`
- `programmatic`
- `hand_authored`

Deferred for this interim slice:

- `multi_llm_synthesis`
- synthesis judge-filter logs

## Failure categories covered

- `bench_overcommitment`
- `icp_misclassification`
- `signal_overclaiming`
- `gap_overclaiming`
- `tone_drift`
- `dual_control_coordination`

## Validation and contamination artifacts

See:

- `/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/generation_scripts/schema_validation_report.json`
- `/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/generation_scripts/dedup_report.json`
- `/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/generation_scripts/counts.json`
- `/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/contamination_check.json`
