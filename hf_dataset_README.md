---
license: cc-by-4.0
language:
  - en
tags:
  - evaluation
  - b2b-sales
  - llm-as-judge
pretty_name: Tenacious-Bench v0.2
---

# Tenacious-Bench v0.2

Machine-checkable sales-domain evaluation tasks for Tenacious-style B2B outreach (bench capacity, ICP fit, signal grounding, tone, booking stage). Built from Week 10 traces, probes, and multi-LLM authoring.

## Splits

| Split | Tasks |
|-------|------:|
| `train/` | 120 |
| `dev/` | 73 |
| `held_out/` | 47 |

Each split is one JSONL file: `tasks.jsonl` (one JSON object per line).

## Quickstart

```python
from datasets import load_dataset

ds = load_dataset(
    "Natnaela/teaciousBench",
    data_files={
        "train": "train/tasks.jsonl",
        "dev": "dev/tasks.jsonl",
        "held_out": "held_out/tasks.jsonl",
    },
)
print(ds["train"][0].keys())
```

Local scoring uses `schema.json` and your evaluator script against each task record.

## Documentation

- **`datasheet.md`** — full Gebru-style datasheet (motivation, composition, uses, limitations).
- **`schema.json`** — task and rubric schema.
- **`contamination_check.v0.2.json`** — contamination report for the dynamic-eval pipeline.

## License

CC-BY-4.0
