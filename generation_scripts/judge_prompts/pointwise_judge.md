# Pointwise Judge Prompt

You are grading a candidate Tenacious-Bench task candidate for benchmark inclusion.

Score each dimension on a 1 / 3 / 5 scale only.

## Dimension 1: Coherence

- `1`: The task is internally inconsistent, confusing, or mismatched with its own input context.
- `3`: The task mostly makes sense, but one part of the input/output/rubric alignment is underspecified or awkward.
- `5`: The task is clear, self-consistent, and easy for another evaluator to interpret.

## Dimension 2: Verifiability

- `1`: The task cannot be reliably checked from the provided context, or it depends on hidden facts.
- `3`: Some important parts are checkable, but at least one key judgment still relies on inference or unstated evidence.
- `5`: The task can be judged from the provided context, metadata, and rubric without outside guesswork.

## Dimension 3: Rubric Clarity

- `1`: The rubric is too vague to tell what pass versus fail means.
- `3`: The rubric names the right behavior, but the pass/fail boundary is still somewhat fuzzy.
- `5`: The rubric states concrete checks or decision rules that make pass/fail interpretation straightforward.

Return JSON:

```json
{
  "coherence": 1,
  "verifiability": 1,
  "rubric_clarity": 1,
  "decision": "reject",
  "reason": "short explanation"
}
```
