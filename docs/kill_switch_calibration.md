# Kill-Switch Threshold Calibration

**Document type:** Threshold derivation note  
**Date:** 2026-05-02  
**Status:** Pilot thresholds — replace after 4 weeks of production audit data

---

## What the kill-switch governs

Two operational gates are defined in `memo.md` and enforced by the deployment
checklist:

| Gate | Trigger | Action |
|------|---------|--------|
| Benchmark regression | Any held-out category drops below its floor | Disable LoRA judge, revert to prompt-only |
| Production false-reject rate | **Two consecutive** weekly audits with ≥35% false positives on sampled rejections | Disable + revert to prompt-only |
| Human override rate | Two consecutive weeks above 30% | Disable + investigate |

This document derives and justifies those numeric thresholds.

---

## Gate 1 — Benchmark regression floors

### 100%-slice floor: 80%

The trained judge scores 100% on five of six held-out slices: bench_overcommitment
(11/11), dual_control_coordination (7/7), gap_overclaiming (11/11),
signal_overclaiming (6/6), tone_drift (6/6).

**Floor derivation.** For a slice with n tasks scoring 100%, a post-change drop
to 80% means at least ⌈0.20 × n⌉ tasks now fail. For the smallest 100%-slice
(signal_overclaiming, n=6), 80% means at least 1 new failure. At n=11
(bench_overcommitment, gap_overclaiming) it means at least 2–3 new failures.
One genuine regression is enough to trigger investigation; two is enough to
disable. 80% therefore catches a real break with low false-alarm probability
while tolerating a single edge-case variance on small slices.

**Alternative considered.** A 90% floor would trigger on 1 failure out of
signal_overclaiming (n=6), which is a plausible one-off edge case rather than
a regression signal. 80% avoids hair-trigger false alarms on small slices.

### ICP floor: 60%

The trained judge currently scores 2/6 (33.3%) on icp_misclassification —
a known weak spot. The floor is set at 60% (≥4/6 correct on a 20-task
re-sample, rounded).

**Floor derivation.**
- Current held-out rate: 33.3% (2/6). n=6 is too small to make a statistical
  claim; this is acknowledged as a qualitative signal.
- 60% is chosen as a floor well above the current observed 33.3% failure rate,
  so that if the critic degrades further (e.g. falls to 0% or 16.7%) the gate
  fires, but a marginal improvement from 33.3% to 40–50% does NOT trigger a
  rollback (that would be an improvement, not a regression).
- Binomial 95% CI on 2/6: [0.04, 0.78] (Wilson interval). The floor of 60%
  sits above the current point estimate, meaning the gate fires only if a
  re-sample confirms performance is definitively worse than the known baseline.

**Pilot note.** With n=6, these estimates have wide uncertainty. The 60%
floor should be recalibrated after collecting ≥20 ICP-category evaluations
from the first production month.

---

## Gate 2 — Production false-reject rate: 35%

### What is measured

A weekly random sample of n ≥ 25 critic decisions (stratified: 50% from approved
sends, 50% from rejected sends) is reviewed by a blind human auditor. The false-
reject rate is the fraction of REJECTED sends that the auditor marks as "should
have been approved."

### Threshold derivation

The 35% threshold is anchored to the worst-performing held-out slice (ICP
misclassification: 33.3% incorrect decisions). The reasoning is:

1. If the production false-reject rate equals the held-out failure rate of the
   worst category, that category's errors are leaking into production at scale.
2. A sustained 35% false-reject rate means the critic is blocking roughly 1 in 3
   legitimate sends — this materially harms pipeline throughput before enough
   evidence accumulates for a held-out rerun.
3. Setting the threshold above the ICP held-out rate (33.3% → 35%) adds a small
   buffer for measurement noise in the weekly sample.

**Statistical check for n=25 sample.** Under the null hypothesis that the true
false-reject rate is 20% (acceptable threshold), a 35% observed rate in n=25
trials gives an exact binomial p-value of ~0.07 (one-sided). This is a moderate
signal, not a definitive one — **`memo.md` therefore requires two consecutive
weekly audits at ≥35%** before disable, rather than a single observation.

### Pilot calibration plan

These thresholds are pilot defaults derived from held-out data and binomial
reasoning on small counts. They should be replaced after collecting:
- ≥ 4 weeks of weekly audit samples (n ≥ 25 per week, total n ≥ 100)
- A fitted false-reject rate distribution per category
- A recalibrated threshold using the 95th percentile of the null distribution
  fitted to actual production data

---

## Gate 3 — Human override rate: 30%

The human override rate is the fraction of critic-rejected sends that a
representative (a sales rep or team lead) approves and sends anyway.

### Threshold derivation

A 30% override rate means representatives disagree with the critic on nearly 1
in 3 decisions. At this level:
- The critic is not being trusted operationally, which signals either calibration
  drift or a mismatch between the training distribution and live production.
- The prompt-only baseline (48.9% preference accuracy) is a safer fallback than
  a distrusted critic — it performs worse on the benchmark but at least does not
  generate friction with the team.

30% is a pilot default. It should be lowered to 20% once the team has 4+ weeks
of data and representative behavior has stabilized.

---

## Files referenced

| File | Role |
|------|------|
| `ablations/ablation_results.json` | Source for held-out category rates |
| `ablations/significance_test.txt` | Bootstrap CI reference |
| `inter_rater_agreement.md` | Human labeling calibration |
| `memo.md` | Operational gates (Gates 1–3 as written policy) |
| `ablations/v01_coverage_audit.txt` | v0.1 gap family verification |
