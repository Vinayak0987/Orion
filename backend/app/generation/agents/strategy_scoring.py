"""Deterministic strategic-option scorer (F17a support).

The LLM proposes options and rates each on five 1-5 dimensions; this module
turns those ratings into a single 0-100 score with a transparent per-dimension
breakdown. The score is COMPUTED here, never asserted by the model - the same
discipline as the finance agents computing totals in code, and the reason the
"don't let the LLM just say Option A is best" requirement is actually satisfied.

Pure Python, no LLM, no I/O: fully deterministic and unit-testable. Given the
same ratings it always yields the same score, so a run is reproducible and the
ranking can be asserted in tests.
"""

from __future__ import annotations

from app.generation.models.departments import StrategicOption

# Weights sum to 1.0. Strategic fit and competitive advantage matter most for an
# early-stage business plan; reversibility least. Tunable, but fixed per run so
# scores are comparable across options and across runs.
WEIGHTS: dict[str, float] = {
    "strategic_fit": 0.30,
    "competitive_advantage": 0.25,
    "cost_efficiency": 0.20,
    "risk_level": 0.15,  # already oriented so 5 = low risk
    "reversibility": 0.10,  # 5 = easily reversed
}

# A missing sub-rating is treated as the neutral midpoint (3/5) rather than
# zero, so an option is not silently punished for an omission the model made.
_NEUTRAL = 3


def _rating(option: StrategicOption, dimension: str) -> int:
    value = getattr(option, dimension, None)
    if value is None:
        return _NEUTRAL
    return int(value)


def score_option(option: StrategicOption) -> tuple[float, dict[str, float]]:
    """Return (score_0_100, per_dimension_contribution).

    Each 1-5 rating is normalised to 0-1 as (r-1)/4, weighted, summed, and
    scaled to 0-100. The breakdown records each dimension's weighted points so
    the recommendation can explain exactly why one option outscored another.
    """
    breakdown: dict[str, float] = {}
    total = 0.0
    for dimension, weight in WEIGHTS.items():
        normalised = (_rating(option, dimension) - 1) / 4  # 1->0.0, 5->1.0
        points = round(normalised * weight * 100, 2)
        breakdown[dimension] = points
        total += points
    return round(total, 2), breakdown


def score_options(options: list[StrategicOption]) -> list[StrategicOption]:
    """Score every option in place and return them ranked best-first.

    Ties break by name for determinism. Returns the same objects (mutated) so
    the caller can store them directly on the section.
    """
    for option in options:
        score, breakdown = score_option(option)
        option.score = score
        option.score_breakdown = breakdown
    return sorted(options, key=lambda o: (-(o.score or 0.0), o.name))


def recommended_option_name(options: list[StrategicOption]) -> str | None:
    """The name of the highest-scoring option, or None if there are none."""
    if not options:
        return None
    return score_options(options)[0].name
