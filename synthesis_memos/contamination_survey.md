# Synthesis Memo: Recent Advances in LLM Benchmarks Against Data Contamination

Chen et al., *Recent Advances in Large Language Model Benchmarks against Data Contamination: From Static to Dynamic Evaluation* (EMNLP 2025).

## Design choice I disagree with (Section 4 — dynamic evaluation as the primary mitigation)

The paper argues that static benchmarks are fundamentally contamination-prone and that dynamic evaluation — regenerating tasks at eval time from templates, held-out seed facts, or live data streams — is the correct long-term mitigation. The survey classifies static benchmarks as high-risk by default and frames dynamic generation as the preferred path for any serious evaluation work going forward.

The implicit claim is that dynamism is achievable at low cost given modern LLM generation capabilities. Section 4.2 describes template-based dynamic generation and Section 4.3 describes live-data-anchored generation as practical options for most benchmark authors.

## Why full dynamic evaluation is not the right call for Tenacious-Bench

The Tenacious-Bench use case has a specific constraint the paper does not address: the evaluation target is a narrow, domain-specific business-rule system, not a general-capability model. The held-out tasks must encode real Tenacious business rules — bench capacity limits, ICP segment boundaries, confidence-tier phrasing requirements — because that is what makes the benchmark diagnostic rather than generic. Dynamically generating tasks at eval time from templates would produce surface variation but would still require the same authoring effort to encode the business-rule ground truth. Dynamic generation does not reduce that effort; it redistributes it from offline authoring to online generation with additional latency and API cost.

The time-shift concern from Section 3.2 is also less acute here. Tenacious-Bench does not rely on public knowledge facts (trivia, code solutions, math proofs) that models are likely to have memorized. It relies on task inputs derived from synthetic company signals (`signal_line`, `bench_summary`, `capacity_request`) that do not exist in any training corpus. The contamination risk is not that models have memorized the answers — it is that models trained on the training partition will over-fit to the held-out input format. That is a different problem from the one the paper primarily addresses.

## What I adopt from the paper instead

The three-check contamination protocol from Section 3.1 (n-gram overlap, embedding similarity, time-shift verification) is implemented directly in `generation_scripts/contamination_check.py` and applied to produce `contamination_check.v0.2.json`. These checks run on the task input fields, not the outputs, because the relevant contamination vector for this benchmark is input-level overlap between train and held-out partitions.

The 8-gram overlap threshold (less than 8-gram overlap on input fields between held-out and training tasks) is taken directly from the survey's recommendations. The embedding similarity threshold (cosine < 0.85 using sentence-transformers) follows the survey's guidance for semantic deduplication.

For the preference-pair training data specifically, an additional contamination check runs against held-out task inputs before any pair is saved to `training_data/preference_pairs.jsonl`. This is a stronger requirement than the paper recommends for static benchmarks, adopted because the training data is derived from the same task pool and the leakage surface is closer.

## What the paper gets right that the field ignores

Section 5 on membership inference attacks is underappreciated. The paper notes that models can sometimes be probed to detect whether a specific example was in their training data. For a benchmark that will be published and used to evaluate future models, this matters: a model fine-tuned on Tenacious-Bench training data could in principle detect held-out tasks through membership inference rather than genuine generalization. The paper does not provide a practical mitigation for small benchmark authors, but naming the risk is useful. The held-out partition is kept in a separate file and not committed in training scripts precisely to reduce this surface.
