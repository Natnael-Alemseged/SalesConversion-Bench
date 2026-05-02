# Final Submission — Remaining Tasks

Deadline: Saturday 21:00 UTC

---

## BLOCK 1 — Unblocked (do today in parallel)

### 1.1 Publish HuggingFace Dataset
- [ ] Create a new HF dataset repo: `Natnaela/tenacious-bench`
- [ ] Upload `tenacious_bench_v0.2/train/tasks.jsonl`, `dev/tasks.jsonl`, `held_out/tasks.jsonl`
- [ ] Upload `datasheet.md`, `schema.json`, `contamination_check.v0.2.json`
- [ ] Add `README.md` (dataset card) covering: motivation, splits, quickstart example, license CC-BY-4.0
- [ ] Set license to CC-BY-4.0
- [ ] Note: the existing HF repo (`Natnaela/my-qwen-0.5b-lora`) is a **model**, not a dataset — publish separately under `datasets/`

### 1.2 Build `training_data/` (preference pairs for Path B)
- [ ] For each failed task in `tenacious_bench_v0.2/train/`, pair: `rejected` = bad draft, `chosen` = corrected draft that passes evaluator
- [ ] Source rejected outputs from probe-triggered failures (probe-4087895185a9, probe-d5299b421fc8, probe-8dc44eb36d33, probe-19f0af95e3e2, probe-b3388b3c3582)
- [ ] Source chosen outputs: use Week 10 hand-fixes OR dev-tier model rewrites that pass `scoring_evaluator.py`
- [ ] Prevent preference leakage: use a **different model family** for chosen rewrites vs the judge model
- [ ] Format as chat-template pairs: `{"prompt": ..., "chosen": ..., "rejected": ...}`
- [ ] Aim for 200–500 high-quality pairs (quality over quantity)
- [ ] Save to `training_data/preference_pairs.jsonl`
- [ ] Run contamination check against held-out partition

### 1.3 Write Remaining Synthesis Memos (5 memos, independent)

**Common (2 missing):**
- [ ] `synthesis_memos/datasheets_and_data_cards.md` — Gebru et al. 2021 + Pushkarna et al. FAccT 2022. Key point to argue: where your datasheet diverges from the template and why.
- [ ] `synthesis_memos/contamination_survey.md` — Chen et al. EMNLP 2025. Key point: which of the three dynamic-eval strategies you adopted and why the others didn't fit.

**Path B specific (pick 3):**
- [ ] `synthesis_memos/dpo.md` — Rafailov et al. NeurIPS 2023. Key point: why you chose SimPO/ORPO over vanilla DPO for this setup.
- [ ] `synthesis_memos/simpo_or_orpo.md` — Meng et al. NeurIPS 2024 OR Hong et al. EMNLP 2024. Key point: which one and the concrete justification.
- [ ] `synthesis_memos/prometheus2.md` — Kim et al. 2024. Key point: what Prometheus 2 got right that you replicate and what you can't replicate at this scale.
- [ ] `synthesis_memos/preference_leakage.md` — Li et al. 2025. Key point: what rotation policy you applied to avoid this in your training data.

### 1.4 Write `methodology_rationale.md`
- [ ] One page max
- [ ] Cite at least 3 path-specific papers from Path B reading list
- [ ] Reference at least 3 Week 10 trace IDs (probe-4087895185a9, probe-c1a89e56414b, probe-d5299b421fc8 minimum)
- [ ] State the training algorithm chosen (SimPO or ORPO) and justify vs DPO
- [ ] State backbone chosen (Qwen 3.5 0.8B or 2B) and justify

---

## BLOCK 2 — After training_data/ is ready

### 2.1 Training Run in Colab
- [ ] Open `Welcome_To_Colab.ipynb` and configure for Path B (SimPO or ORPO)
- [ ] Load `training_data/preference_pairs.jsonl`
- [ ] Set backbone: Qwen 3.5 0.8B (or 2B if VRAM allows)
- [ ] Run LoRA fine-tune — target 30–90 min wall time on T4
- [ ] Log: seed, learning rate, batch size, epochs, LoRA rank/alpha
- [ ] Save training loss curve as `training/loss_curve.png` or logged to file
- [ ] Save full run log to `training/training_run.log`
- [ ] Push LoRA adapter to `Natnaela/tenacious-judge-lora` on HuggingFace

---

## BLOCK 3 — After training run

### 3.1 Ablations
- [ ] **Delta A**: trained judge vs Week 10 baseline on `held_out/tasks.jsonl` — must be positive, 95% CI, p < 0.05 paired bootstrap
- [ ] **Delta B**: trained judge vs prompt-engineered version on same backbone, no training — report honestly even if negative
- [ ] **Cost-Pareto**: per-task cost + latency with judge vs without
- [ ] Use eval-tier model (Claude Sonnet 4.6) — max 3–4 passes total on held-out
- [ ] Save raw scores to `ablations/held_out_traces.jsonl`
- [ ] Save summary table to `ablations/ablation_results.json`
- [ ] Run paired bootstrap significance test, save output to `ablations/significance_test.txt`

### 3.2 `evidence_graph.json`
- [ ] Every numeric claim in the memo maps to one of: task ID, ablation table row, training log line, or public source
- [ ] Format: `[{"claim": "...", "value": ..., "source": "ablations/ablation_results.json#row3"}]`

---

## BLOCK 4 — Final artifacts

### 4.1 `memo.pdf` (exactly 2 pages)
- [ ] **Page 1 — The Decision**
  - 3-sentence executive summary
  - Delta A headline: lift on Tenacious-Bench held-out with 95% CI
  - Delta B result (honest — report even if negative)
  - Cost per task with vs without trained component
  - Recommendation: deploy / deploy with caveat / do not deploy + what would need to change
- [ ] **Page 2 — Skeptic's Appendix**
  - 4 failure modes Tenacious-Bench v0.1 still doesn't capture + what v0.2 would add
  - Public-signal lossiness in ground truth
  - One honest unresolved training failure
  - Kill-switch trigger condition for the trained component in production

### 4.2 Blog Post (1,200–2,000 words)
- [ ] Draft structure now; fill in ablation numbers after Block 3
- [ ] Sections: the gap → audit method → dataset build → training experiment → honest result → what's next
- [ ] Publish to HuggingFace community blog, Substack, or personal site
- [ ] Must include: lift with confidence intervals, Delta B result honestly stated
- [ ] Save URL

### 4.3 Community Engagement
- [ ] File a GitHub issue on the τ²-Bench repo presenting your Tenacious-specific gap finding and linking the HF dataset
- [ ] Save issue URL

### 4.4 Demo Video (max 6 min, publicly accessible, no login)
- [ ] Walk through HuggingFace dataset (datasheet visible, all 3 partitions visible)
- [ ] Show one task being scored end-to-end by `scoring_evaluator.py`
- [ ] Show one ablation result — open `held_out_traces.jsonl`, trace a numeric claim to its source
- [ ] Show the blog post page
- [ ] Show the community engagement artifact (GitHub issue link)
- [ ] Upload to YouTube (unlisted ok) or Loom

---

## Publication Checklist (before anything goes public)

- [ ] Datasheet present — all 7 Gebru sections non-stub
- [ ] License CC-BY-4.0 on dataset
- [ ] README runnable — stranger can reproduce headline number in < 1 hour
- [ ] Reproducibility seed — all scripts use fixed seed, seed in log filename
- [ ] Held-out sealed — separate file, not exposed in training scripts
- [ ] Contamination report committed
- [ ] Attribution clean — every cited paper credited, no private Tenacious detail
- [ ] Program staff sign-off before publishing under your identity

---

## Summary Timeline

```
TODAY (Fri)
├── 1.1  Publish HF dataset (tenacious-bench)
├── 1.2  Build training_data/ preference pairs   ← HARDEST BLOCKER
├── 1.3  Write synthesis memos (5)               ← parallel writing
└── 1.4  Write methodology_rationale.md

SAT MORNING
├── 2.1  Training run in Colab (30–90 min)
└── 3.1  Ablations + significance tests

SAT MIDDAY
├── 3.2  evidence_graph.json
└── 4.1  memo.pdf

SAT AFTERNOON (before 21:00 UTC)
├── 4.2  Blog post (finalize + publish)
├── 4.3  Community engagement (GitHub issue)
└── 4.4  Demo video
```
