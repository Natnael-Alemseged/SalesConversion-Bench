# Pairwise Tie-Break Prompt

You are choosing between two near-duplicate Tenacious-Bench task candidates that target the same failure mode.

Prefer the candidate that:

1. preserves the Week 10 failure more faithfully
2. is easier to verify from the provided context alone
3. has the clearer rubric and less redundant wording

Return JSON:

```json
{
  "winner": "A",
  "reason": "short explanation"
}
```
