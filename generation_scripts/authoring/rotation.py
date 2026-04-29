from __future__ import annotations

from dataclasses import dataclass

ModelName = str
ModelFamily = str


def model_family(model_name: ModelName) -> ModelFamily:
    """Return the model family for rotation enforcement.

    Convention:
    - model names are stored as "<family>:<model>", e.g. "openai:gpt-4.1"
    """

    if ":" not in model_name:
        return "unknown"
    return model_name.split(":", 1)[0].strip().lower() or "unknown"


@dataclass(frozen=True)
class RotationDecision:
    generator_model: ModelName
    judge_model: ModelName
    generator_family: ModelFamily
    judge_family: ModelFamily
    enforced: bool
    reason: str


def enforce_rotation(*, generator_model: ModelName, judge_model: ModelName) -> RotationDecision:
    """Enforce preference-leakage prevention: generator family cannot judge same pool.

    Policy:
    - reject any configuration where generator_family == judge_family
    """

    gen_family = model_family(generator_model)
    judge_family = model_family(judge_model)
    if gen_family != "unknown" and gen_family == judge_family:
        raise ValueError(f"Rotation violation: generator_family == judge_family == {gen_family!r} (generator_model={generator_model!r}, judge_model={judge_model!r})")
    return RotationDecision(
        generator_model=generator_model,
        judge_model=judge_model,
        generator_family=gen_family,
        judge_family=judge_family,
        enforced=True,
        reason="generator family differs from judge family",
    )
