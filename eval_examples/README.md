# Eval Examples

This folder identifies three example tasks that can be used in the interim PDF report.

- programmatic example: `tbv01-021`
- trace-derived example: `tbv01-007`
- adversarial / hand-authored example: `tbv01-059`

Raw evaluator outputs are committed here:

- [tbv01-021.json](/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/eval_examples/tbv01-021.json)
- [tbv01-007.json](/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/eval_examples/tbv01-007.json)
- [tbv01-059.json](/Users/natnaelalemseged/code-projects/backend/SalesConversion-Bench/eval_examples/tbv01-059.json)

These task IDs exist in the partitioned dataset and can be scored end to end using:

```bash
python3 scoring_evaluator.py --task-file tenacious_bench_v0.1/train/tasks.jsonl
```
