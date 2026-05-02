# Optional ICP Misclassification Refinement Playbook

Status: optional fallback, not required for the current submission.

The current Path B result should be kept as the primary result:

- Held-out preference success: 43/47 = 91.5%
- Delta A lift over Week 10 baseline: +68.1 percentage points
- 95% paired bootstrap CI: approximately [+55.3, +80.9]
- Known weak category: `icp_misclassification`, 2/6 held-out preference wins

Do not retrain only to hide this caveat. The challenge rewards honest ablation reporting. Use this playbook only if there is enough time to improve the trained adapter without risking contamination or weakening the submission story.

## Goal

Improve the adapter's ability to prefer the correct ICP-specific outreach strategy over a plausible but wrong-segment pitch.

This means teaching distinctions such as:

- Early-stage / AI-maturity 0-1 prospects should not receive advanced agentic-systems transformation pitches.
- Cost-restructuring or constrained mid-market prospects should not receive generic growth-expansion pitches.
- Weak public signals should produce careful questions, not confident segment assumptions.
- The chosen output should explicitly fit the supplied `icp_segment`, `thread_stage`, and signal confidence.

## Do Not Touch Held-Out

Never edit, train on, paraphrase from, or generate near-duplicates of these failed held-out tasks:

- `tbv02-0026`
- `tbv02-0002`
- `tbv02-0217`
- `tbv02-0034`

These task IDs can be inspected only to understand the failure type. They must remain sealed evaluation examples.

## Recommended Route

1. Inspect the failed ICP tasks and write a two-sentence diagnosis for each.
2. Add 20-40 new ICP preference pairs using only the training partition or newly authored training-only examples.
3. Keep the original 91-pair dataset unchanged as `preference_pairs.v1.jsonl`.
4. Save the augmented set as `training_data/preference_pairs_icp_refine.jsonl`.
5. Re-run the same Colab notebook with the augmented file.
6. Re-run the clean held-out preference-margin cell.
7. Accept the refinement only if overall Delta A stays positive and ICP improves without regressions elsewhere.

## Pair Construction Pattern

Each new pair should have:

- `prompt`: same Tenacious system prompt and structured context format as the existing preference pairs.
- `chosen`: a grounded outreach draft that matches the correct ICP segment and signal confidence.
- `rejected`: a plausible, fluent draft that pitches the wrong ICP segment.
- `failure_category`: `icp_misclassification`.
- `task_id`: a new training-only ID, not a held-out ID.

Good rejected examples are not low-quality spam. They should be persuasive but strategically wrong.

Example rejected behavior:

- For an early-stage company with low AI maturity, pitch advanced agentic workflow transformation.
- For a cost-constrained mid-market company, pitch aggressive growth hiring.
- For medium/low confidence signal, assert certainty about their operating model.

Example chosen behavior:

- Name only the supplied signal.
- Ask rather than assert when confidence is medium/low.
- Match the offer to the company stage and ICP segment.
- Keep one ask.
- Avoid banned phrases and unsupported capability claims.

## Acceptance Criteria

Only use the refined adapter if all of these hold:

- Overall held-out preference success stays at or above the current 43/47 result, or any drop is clearly justified.
- `icp_misclassification` improves above 2/6.
- No previously perfect categories collapse below 80%.
- Delta A remains positive with a 95% CI above zero.
- The memo/blog clearly state that this was a targeted refinement run.

If those conditions fail, keep the original adapter:

`https://huggingface.co/Natnaela/tenacious-judge-lora`

## How To Report If Refined

If the refinement succeeds, report both runs:

- Run 1: original 91-pair SimPO adapter, strong overall result with ICP caveat.
- Run 2: ICP-targeted refinement, same notebook and hyperparameters, augmented training file.

Do not silently replace the original result. The comparison is useful evidence because it shows the weak category was diagnosed and addressed with targeted data rather than extra generic compute.

## Time-Box

Maximum recommended time: 60-90 minutes.

If this starts taking longer, stop. The current result already satisfies the main challenge criterion; final memo, dataset publication, evidence graph, blog, and demo video are higher priority.
