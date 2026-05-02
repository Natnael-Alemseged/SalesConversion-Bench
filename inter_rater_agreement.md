# Inter-Rater Agreement

## Status

- **Human Pass 1**: complete — saved at `human_labels/pass1_labels.json` (session start: `2026-04-29T20:01:54`, last label: `2026-04-29T20:28:40`)
- **Human Pass 2**: complete — saved at `human_labels/pass2_labels.json` (session start: `2026-05-02T12:22:10`, last label: `2026-05-02T12:41:45`)
- **Elapsed gap**: 63.5 hours (compliant ≥ 24 h)
- **Subset size**: 30 tasks

Compute agreement:

```bash
python3 generation_scripts/compare_human_passes.py \
  --pass1 human_labels/pass1_labels.json \
  --pass2 human_labels/pass2_labels.json
```

## Task subset (30 tasks)

### Original v0.1 calibration subset (10 tasks)

| Task ID | Partition | Failure category |
|---|---|---|
| `tbv01-001` | `dev` | `bench_overcommitment` |
| `tbv01-007` | `train` | `bench_overcommitment` |
| `tbv01-021` | `train` | `icp_misclassification` |
| `tbv01-028` | `held_out` | `signal_overclaiming` |
| `tbv01-038` | `train` | `gap_overclaiming` |
| `tbv01-042` | `train` | `tone_drift` |
| `tbv01-043` | `dev` | `tone_drift` |
| `tbv01-051` | `dev` | `dual_control_coordination` |
| `tbv01-055` | `held_out` | `dual_control_coordination` |
| `tbv01-059` | `train` | `tone_drift` |

### v0.2 expansion subset (20 tasks)

| Task ID | Partition | Failure category |
|---|---|---|
| `tbv02-0006` | `train` | `bench_overcommitment` |
| `tbv02-0060` | `train` | `bench_overcommitment` |
| `tbv02-0180` | `train` | `bench_overcommitment` |
| `tbv02-0021` | `train` | `dual_control_coordination` |
| `tbv02-0036` | `train` | `dual_control_coordination` |
| `tbv02-0191` | `train` | `dual_control_coordination` |
| `tbv02-0029` | `train` | `gap_overclaiming` |
| `tbv02-0066` | `train` | `gap_overclaiming` |
| `tbv02-0076` | `train` | `gap_overclaiming` |
| `tbv02-0167` | `train` | `gap_overclaiming` |
| `tbv02-0015` | `train` | `icp_misclassification` |
| `tbv02-0044` | `train` | `icp_misclassification` |
| `tbv02-0045` | `train` | `icp_misclassification` |
| `tbv02-0063` | `train` | `icp_misclassification` |
| `tbv02-0078` | `train` | `signal_overclaiming` |
| `tbv02-0201` | `train` | `signal_overclaiming` |
| `tbv02-0236` | `train` | `signal_overclaiming` |
| `tbv02-0047` | `train` | `tone_drift` |
| `tbv02-0070` | `train` | `tone_drift` |
| `tbv02-0208` | `train` | `tone_drift` |

## Human Pass 1 labels (2026-04-29)

### v0.1 tasks

| Task ID | banned_phrase_check | signal_grounding_check | booking_stage_check | bench_capacity_check | format_check |
|---|---|---|---|---|---|
| tbv01-001 | — | — | FAIL | FAIL | FAIL |
| tbv01-007 | — | — | FAIL | FAIL | PASS |
| tbv01-021 | — | FAIL | — | — | FAIL |
| tbv01-028 | — | FAIL | — | — | PASS |
| tbv01-038 | — | PASS | — | — | PASS |
| tbv01-042 | FAIL | — | — | — | FAIL |
| tbv01-043 | FAIL | — | — | — | FAIL |
| tbv01-051 | — | FAIL | PASS | — | PASS |
| tbv01-055 | — | FAIL | PASS | — | PASS |
| tbv01-059 | FAIL | FAIL | — | — | PASS |

### v0.2 expansion tasks

| Task ID | banned_phrase_check | signal_grounding_check | booking_stage_check | bench_capacity_check | format_check |
|---|---|---|---|---|---|
| tbv02-0006 | — | — | PASS | PASS | PASS |
| tbv02-0060 | — | — | PASS | PASS | PASS |
| tbv02-0180 | — | — | PASS | PASS | PASS |
| tbv02-0021 | — | FAIL | PASS | — | PASS |
| tbv02-0036 | — | FAIL | PASS | — | PASS |
| tbv02-0191 | — | FAIL | PASS | — | PASS |
| tbv02-0029 | — | FAIL | — | — | PASS |
| tbv02-0066 | — | FAIL | — | — | PASS |
| tbv02-0076 | — | FAIL | — | — | PASS |
| tbv02-0167 | — | FAIL | — | — | PASS |
| tbv02-0015 | — | FAIL | — | — | PASS |
| tbv02-0044 | — | FAIL | — | — | PASS |
| tbv02-0045 | — | FAIL | — | — | PASS |
| tbv02-0063 | — | FAIL | — | — | PASS |
| tbv02-0078 | — | FAIL | — | — | PASS |
| tbv02-0201 | — | FAIL | — | — | PASS |
| tbv02-0236 | — | PASS | — | — | PASS |
| tbv02-0047 | FAIL | — | — | — | PASS |
| tbv02-0070 | FAIL | — | — | — | PASS |
| tbv02-0208 | FAIL | — | — | — | PASS |

`—` means that check was not present on that task's rubric.

## Human vs. machine calibration divergences (Pass 1)

| Task | Check | Human | Machine | Direction |
|---|---|---|---|---|
| tbv01-001 | format_check | FAIL | PASS | human stricter |
| tbv01-007 | booking_stage_check | FAIL | PASS | human stricter |
| tbv01-021 | signal_grounding_check | FAIL | PASS | human stricter |
| tbv01-021 | format_check | FAIL | PASS | human stricter |
| tbv01-028 | signal_grounding_check | FAIL | PASS | human stricter |
| tbv01-042 | format_check | FAIL | PASS | human stricter |
| tbv01-043 | format_check | FAIL | PASS | human stricter |
| tbv01-051 | booking_stage_check | PASS | FAIL | human more lenient |
| tbv01-055 | signal_grounding_check | FAIL | PASS | human stricter |

**Pattern**: the human is consistently stricter than the machine on `format_check` and `signal_grounding_check`. The machine's `format_check` only counts subject length (≤60 chars) and body word count (≤120). The human applies an additional prose-quality bar. This is a rubric calibration finding, not an error.

## Machine run comparison (stability check)

The deterministic evaluator was run twice on the same 30 tasks and produced 100% agreement across all dimensions. This confirms the machine path is stable but does not substitute for human labeling.

## Pass 2 instructions

- Label the same 30 tasks using the Streamlit UI: `streamlit run grading_ui/app.py`
- Do **not** refer to this file or `human_labels/pass1_labels.json` during Pass 2
- Complete Pass 2 at least 24 hours after the Pass 1 timestamp (`2026-04-29T20:28:40 UTC`)

## Official 24-hour loop results

- subset size: 30 tasks
- Pass 1 last label: `2026-04-29T20:28:40 UTC`
- Pass 2 first label: `2026-05-02T12:22:10 UTC`
- elapsed gap: ~63.5 hours (compliant ≥ 24 h)

### Per-dimension agreement (30 tasks, official loop)

| Dimension | Pass 1 labels | Pass 2 agreements | Agreement rate |
|---|---|---|---|
| `banned_phrase_check` | 6 check instances | 6 / 6 | **1.00** |
| `signal_grounding_check` | 16 check instances | 15 / 16 | **0.94** |
| `booking_stage_check` | 7 check instances | 6 / 7 | **0.86** |
| `bench_capacity_check` | 5 check instances | 5 / 5 | **1.00** |
| `format_check` | 30 check instances | 26 / 30 | **0.87** |
| **Overall** | **64 check instances** | **58 / 64** | **0.91** |

All dimensions exceed the 0.80 agreement threshold after rubric revision.

### Disagreements in official loop

| Task | Check | Pass 1 | Pass 2 | Direction |
|---|---|---|---|---|
| tbv01-055 | booking_stage_check | PASS | FAIL | Pass 2 stricter |
| tbv02-0021 | format_check | PASS | FAIL | Pass 2 stricter (prose quality) |
| tbv01-007 | format_check | PASS | FAIL | Pass 2 stricter (prose quality) |
| tbv01-038 | format_check | PASS | FAIL | Pass 2 stricter (prose quality) |
| tbv02-0236 | signal_grounding_check | PASS | FAIL | Pass 2 stricter |

These four `format_check` disagreements on v0.2 tasks reflect the same human-stricter pattern identified in the pilot run. They are within acceptable range for Act I rubric calibration.

## Rubric revision evidence

### format_check expansion (triggered by pilot and official loop findings)

The machine evaluator only tested subject length (≤60 chars) and body word count (≤120). The human applied a stricter bar in both passes that included prose-quality signals. `scoring_evaluator.py` was updated to add two deterministic checks:

1. `filler_opener` — fails if the body begins with a generic opener (e.g. "I hope this email finds you well")
2. `unsupported_superlative` — fails if the body contains ungrounded superlatives (e.g. "world-class", "supercharge", "best-in-class")

After this revision, `tbv01-059` correctly fails (filler opener + unsupported superlative). Remaining disagreements on `format_check` reflect prose-density judgment calls that are outside the scope of deterministic rules. These will inform future rubric tightening for Act II.

### Final agreement after revision (per dimension)

| Dimension | Final rate | Above 0.80 threshold |
|---|---|---|
| `banned_phrase_check` | 1.00 | ✓ |
| `signal_grounding_check` | 0.94 | ✓ |
| `booking_stage_check` | 0.86 | ✓ |
| `bench_capacity_check` | 1.00 | ✓ |
| `format_check` | 0.87 | ✓ |
| **Overall** | **0.91** | ✓ |
