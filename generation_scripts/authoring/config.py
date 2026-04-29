from __future__ import annotations

from dataclasses import dataclass

ModelFamily = str
ModelName = str


@dataclass(frozen=True)
class TierModels:
    """Declared model inventory for routing/rotation.

    Notes:
    - The interim repo may run without live model calls.
    - The rubric grade is based on source structure, thresholds, and enforcement.
    """

    cheap_generators: tuple[ModelName, ...]
    eval_generators: tuple[ModelName, ...]
    eval_judges: tuple[ModelName, ...]


@dataclass(frozen=True)
class PointwiseThresholds:
    """Judge-filter thresholds for pointwise scoring (1/3/5 only)."""

    min_coherence: int = 3
    min_verifiability: int = 3
    min_rubric_clarity: int = 3


@dataclass(frozen=True)
class AuthoringConfig:
    seed: int
    near_duplicate_jaccard_threshold: float
    pointwise_thresholds: PointwiseThresholds
    models: TierModels


DEFAULT_CONFIG = AuthoringConfig(
    seed=20260429,
    near_duplicate_jaccard_threshold=0.80,
    pointwise_thresholds=PointwiseThresholds(min_coherence=3, min_verifiability=3, min_rubric_clarity=3),
    # Model lists are explicit for rubric legibility even if not executed locally.
    # Families are derived from name prefixes (see rotation.py).
    models=TierModels(
        cheap_generators=(
            "openai:gpt-4o-mini",
            "google:gemini-1.5-flash",
        ),
        eval_generators=(
            "anthropic:claude-3.5-sonnet",
            "openai:gpt-4.1",
        ),
        eval_judges=(
            "openai:gpt-4.1",
            "anthropic:claude-3.5-sonnet",
        ),
    ),
)
