## Structured-context evaluation gaps in retail domain: capacity constraints, ICP routing, and confidence calibration

### What we built

Working on a domain-specific benchmark for a B2B sales agent, I identified three failure modes that τ²-Bench retail consistently misses — not because the agent produces incoherent output, but because the failures are in **structured-context usage** rather than conversation flow.

### The gap

τ²-Bench retail grades whether an agent follows the correct policy steps. What it cannot grade is whether the agent correctly uses structured input fields (JSON summaries, confidence tiers, routing rules) when those fields encode hard business constraints. Fluent, step-complete output can still be wrong.

Three concrete examples:

**1. Capacity overcommitment**
The agent has access to a `bench_summary` JSON with available headcount per stack. It commits capacity the bench cannot fulfill. Output is fluent, policy-step-compliant, passes retail scoring. Triggered on **100% of capacity-feasibility probes** (40/40) in our evaluation.

**2. ICP segment misrouting**
The agent receives funding, layoff, and role-velocity signals and must route the prospect to the correct segment. The wrong segment produces a fluent, step-complete email. τ²-Bench retail has no analog for classification from noisy structured signals. Triggered on **54% of routing probes** (20/37).

**3. Confidence-calibrated phrasing**
A `signal_confidence_tier` field encodes whether the underlying data is high, medium, or low confidence. Assertive language under a low-confidence signal is a failure — τ²-Bench retail does not grade phrasing against a confidence metadata field.

To measure these gaps we built Tenacious-Bench: 240 tasks across 6 failure categories, 4 authoring modes, family-separated multi-LLM synthesis with preference-leakage prevention (Li et al., 2025). We trained a SimPO LoRA judge (Qwen 2.5 0.5B) on 91 preference pairs derived from these failures.

**Results on held-out set (47 tasks):**
- Baseline (raw agent outputs, deterministic evaluator): **23.4%** pass rate
- Trained judge preference accuracy: **91.5%** (43/47)
- Descriptive gap vs raw pass-rate baseline: **+68.1pp** (23.4% -> 91.5%)
- Official paired Delta A metric from the repo's ablation harness: **+76.6pp** (14.9% -> 91.5%, 95% CI [+63.8pp, +87.2pp], p < 0.0001)

Artifacts:
- Dataset: https://huggingface.co/datasets/Natnaela/tenacious-bench
- Judge adapter: https://huggingface.co/Natnaela/tenacious-judge-lora

### The ask

Is there a mechanism for contributing custom domains to τ²-Bench? The sales/staffing domain covers exactly these patterns — structured capacity checks, signal-based routing, confidence-calibrated output — and the schema and evaluator are ready. Happy to share what a domain contribution would need to include, or discuss whether this fits the project roadmap.
