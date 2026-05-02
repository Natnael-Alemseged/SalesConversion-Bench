---
license: cc-by-4.0
task_categories:
  - text-classification
  - text-generation
language:
  - en
tags:
  - sales
  - evaluation
  - benchmark
  - preference
  - b2b
pretty_name: Tenacious-Bench
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: train
        path: train/tasks.jsonl
      - split: dev
        path: dev/tasks.jsonl
      - split: held_out
        path: held_out/tasks.jsonl
---

# Tenacious-Bench v0.2

A domain-specific evaluation benchmark for B2B sales outreach agents. Measures compliance with structured business rules that generic benchmarks (τ²-Bench retail, etc.) cannot grade: bench capacity constraints, ICP segment routing, signal confidence calibration, and tone compliance.

## Why this benchmark exists

The Week 10 Tenacious agent failed every bench-capacity probe (40/40, 100%) and misrouted 54% of ICP classification tasks — while producing fluent, τ²-Bench-passing output. Tenacious-Bench was built to make these failures visible and measurable.

## Splits

| Split | Tasks | Purpose |
|---|---|---|
| `train` | 120 | Preference pair construction, few-shot development |
| `dev` | 73 | Rubric development, inter-rater calibration |
| `held_out` | 47 | Held-out evaluation only — do not use for training |

**Total: 240 tasks** across 6 failure categories.

## Failure categories

| Category | Description |
|---|---|
| `bench_overcommitment` | Agent commits capacity beyond what `bench_summary` supports |
| `icp_misclassification` | Agent routes prospect to wrong ICP segment given signals |
| `signal_overclaiming` | Agent asserts certainty beyond `signal_confidence_tier` |
| `gap_overclaiming` | Agent claims capability gaps the company cannot fill |
| `tone_drift` | Agent uses banned phrases or style-guide violations |
| `dual_control_coordination` | Agent bypasses required dual-approval for booking |

## Task format

Each task is a JSON object with:

```json
{
  "task_id": "tbv02-0007",
  "input": {
    "system_prompt": "...",
    "signal_line": "...",
    "bench_summary": {},
    "capacity_request": []
  },
  "candidate_output": {"subject": "...", "body": "..."},
  "ground_truth_output": {"subject": "...", "body": "..."},
  "rubric": {"checks": ["bench_capacity_check", "format_check"]},
  "metadata": {"failure_category": "bench_overcommitment", "difficulty": "medium"}
}
```

## Evaluator

Score tasks with the deterministic evaluator:

```bash
python3 scoring_evaluator.py --task-file tenacious_bench_v0.2/held_out/tasks.jsonl
```

Five checks: `bench_capacity_check`, `signal_grounding_check`, `booking_stage_check`, `banned_phrase_check`, `format_check`. See `schema.json` for full check descriptions.

## Trained judge

A SimPO LoRA adapter trained on preference pairs derived from this benchmark's train split:

- Adapter: [Natnaela/tenacious-judge-lora](https://huggingface.co/Natnaela/tenacious-judge-lora)
- Backbone: `unsloth/Qwen2.5-0.5B-Instruct`
- Held-out preference accuracy: **91.5% (43/47)**
- Delta A vs Week 10 baseline: **+76.6pp** (95% CI [+63.8pp, +87.2pp], p < 0.0001)
- Known gap: `icp_misclassification` 2/6 = 33.3%

## Contamination

Three-check protocol (8-gram overlap, embedding similarity cosine < 0.85, time-shift) is implemented in `generation_scripts/contamination_check.py` and emitted as `contamination_check.v0.2.json`. The current v0.2 dataset shows zero 8-gram violations but dense-similarity warnings across held-out vs train/dev because the source pool includes many same-family scaled variants; those warnings are reported explicitly rather than suppressed.

## Citation

```
@misc{tenacious-bench-2026,
  author = {Alemseged, Natnael},
  title = {Tenacious-Bench: A Domain-Specific Evaluation Benchmark for B2B Sales Agents},
  year = {2026},
  publisher = {HuggingFace},
  url = {https://huggingface.co/datasets/Natnaela/tenacious-bench}
}
```

## License

CC-BY-4.0
