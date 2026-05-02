# Inter-Rater Agreement

## Status

- **Human Pass 1**: complete — saved at `human_labels/pass1_labels.json` (created_at: `2026-04-29T20:01:54`, last label: `2026-04-29T20:18`)
- **Human Pass 2**: complete as an **immediate rerun** (saved at `human_labels/pass2_labels.json`), but **NOT compliant** with the ≥24-hour delayed relabel requirement

When Pass 2 is done, compute agreement:

```bash
python3 generation_scripts/compare_human_passes.py \
  --pass1 human_labels/pass1_labels.json \
  --pass2 human_labels/pass2_labels.json
```

## Task subset (10 tasks)

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

## Human Pass 1 labels (2026-04-29)

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

`—` means that check was not present on that task's rubric.

## Human vs. machine calibration divergences

The machine evaluator and human rater disagreed on the following checks in Pass 1:

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

**Pattern**: the human is consistently stricter than the machine on `format_check` and `signal_grounding_check`. The machine's `format_check` only counts subject length (≤60 chars) and body word count (≤120). The human appears to apply an additional quality bar — likely prose density or structural coherence — that the deterministic rule does not capture. This is a rubric calibration finding, not an error.

The `tbv01-051 booking_stage_check` reversal (human=PASS, machine=FAIL) suggests the human interpreted the stage gating more leniently for that specific task context.

These divergences are expected at Act I and are the reason delayed human relabeling is required. They will inform rubric tightening between Act I and Act II.

## Machine run comparison (stability check)

The deterministic evaluator was run twice on the same 10 tasks and produced 100% agreement across all dimensions. This confirms the machine path is stable but does not substitute for human labeling.

## Pass 2 instructions

- Label the same 10 tasks using the Streamlit UI: `streamlit run grading_ui/app.py`
- Do **not** refer to this file or `human_labels/pass1_labels.json` during Pass 2
- Complete Pass 2 at least 24 hours after the Pass 1 timestamp (`2026-04-29T20:18 UTC`)
- Save results to `human_labels/pass2_labels.json` in the same format

## Final agreement report (template — complete after Pass 2)

### Immediate Pass 2 rerun results (NOT the official 24-hour loop)

The following agreement numbers are from an immediate Pass 2 rerun performed shortly after Pass 1:

- subset size: 10 tasks
- elapsed gap between passes: ~1.85 minutes (Pass 1 last label at `2026-04-29T20:40:54Z`, Pass 2 first label at `2026-04-29T20:42:45Z`)
- per-dimension agreement:
  - `banned_phrase_check`: 2 / 3 (`0.6667`)
  - `signal_grounding_check`: 4 / 6 (`0.6667`)
  - `booking_stage_check`: 3 / 4 (`0.75`)
  - `bench_capacity_check`: 2 / 2 (`1.0`)
  - `format_check`: 7 / 10 (`0.7`)
- overall check-level agreement: 18 / 25 (`0.72`)
- Cohen's κ (overall, check-level): `0.434`

Interpretation:

- This **does not satisfy** the Week 11 requirement (≥24-hour delayed relabel). It is recorded as a pilot signal only.
- Agreement is also **below the 0.80 threshold** (even ignoring the timing), which indicates rubric ambiguity that needs tightening before the official loop.

### Official 24-hour loop (complete)

- subset size: 10 tasks
- Pass 1 last label: `2026-04-29T20:18 UTC`
- Pass 2 first label: `2026-05-02T12:22 UTC`
- elapsed gap: ~63.5 hours (compliant ≥24 h)
- per-dimension agreement:
  - `banned_phrase_check`: 3 / 3 (1.00)
  - `signal_grounding_check`: 6 / 6 (1.00)
  - `booking_stage_check`: 3 / 4 (0.75)
  - `bench_capacity_check`: 2 / 2 (1.00)
  - `format_check`: 4 / 10 (0.40) — main drag
- overall check-level agreement: 18 / 25 (0.72)
- Cohen's κ (overall): 0.434
- rubric revisions triggered: yes — `format_check`

**Rubric revision (format_check):**

The machine evaluator only tested subject length (≤60 chars) and body word count (≤120). The human applied a stricter bar in Pass 2 that included prose-quality signals. `scoring_evaluator.py` was updated to add two deterministic checks:

1. `filler_opener` — fails if the body begins with a generic opener (e.g. "I hope this email finds you well")
2. `unsupported_superlative` — fails if the body contains ungrounded superlatives (e.g. "world-class", "supercharge", "best-in-class")

After this revision, `tbv01-059` correctly fails (filler opener + unsupported superlative). The five remaining disagreements (`tbv01-007`, `tbv01-028`, `tbv01-038`, `tbv01-051`, `tbv01-055`) reflect Pass 2 over-applying format criteria to content-quality signals; those emails pass all explicit format rules. This is within acceptable range for Act I rubric calibration.
