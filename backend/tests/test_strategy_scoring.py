"""Tests for the deterministic strategic-option scorer (Phase 2). Pure, offline."""

from __future__ import annotations

from app.agents.strategy_scoring import (
    WEIGHTS,
    recommended_option_name,
    score_option,
    score_options,
)
from app.models.departments import StrategicOption


def _opt(name: str, **ratings) -> StrategicOption:
    return StrategicOption(name=name, **ratings)


def test_weights_sum_to_one() -> None:
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_all_fives_scores_100() -> None:
    opt = _opt(
        "perfect",
        strategic_fit=5,
        competitive_advantage=5,
        cost_efficiency=5,
        risk_level=5,
        reversibility=5,
    )
    score, breakdown = score_option(opt)
    assert score == 100.0
    assert abs(sum(breakdown.values()) - 100.0) < 1e-6


def test_all_ones_scores_zero() -> None:
    opt = _opt(
        "worst",
        strategic_fit=1,
        competitive_advantage=1,
        cost_efficiency=1,
        risk_level=1,
        reversibility=1,
    )
    score, _ = score_option(opt)
    assert score == 0.0


def test_missing_ratings_treated_as_neutral_midpoint() -> None:
    """An omitted dimension counts as 3/5, not 0 - the option is not punished."""
    opt = _opt("partial")  # no ratings at all
    score, _ = score_option(opt)
    # 3/5 on every dimension -> normalised 0.5 -> 50.0
    assert score == 50.0


def test_higher_fit_beats_lower_fit_all_else_equal() -> None:
    high = _opt("high", strategic_fit=5, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=3)
    low = _opt("low", strategic_fit=1, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=3)
    assert score_option(high)[0] > score_option(low)[0]


def test_strategic_fit_outweighs_reversibility() -> None:
    """A one-step gain in the heaviest dimension beats a one-step gain in the
    lightest, proving the weighting is applied."""
    fit_gain = _opt("fit", strategic_fit=4, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=3)
    rev_gain = _opt("rev", strategic_fit=3, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=4)
    assert score_option(fit_gain)[0] > score_option(rev_gain)[0]


def test_score_options_ranks_best_first_and_mutates() -> None:
    a = _opt("A", strategic_fit=5, competitive_advantage=5, cost_efficiency=5, risk_level=5, reversibility=5)
    b = _opt("B", strategic_fit=2, competitive_advantage=2, cost_efficiency=2, risk_level=2, reversibility=2)
    ranked = score_options([b, a])
    assert [o.name for o in ranked] == ["A", "B"]
    # scored in place
    assert a.score == 100.0 and a.score_breakdown
    assert b.score is not None and b.score < a.score


def test_ties_break_by_name_deterministically() -> None:
    x = _opt("Zebra", strategic_fit=3, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=3)
    y = _opt("Alpha", strategic_fit=3, competitive_advantage=3, cost_efficiency=3, risk_level=3, reversibility=3)
    ranked = score_options([x, y])
    assert [o.name for o in ranked] == ["Alpha", "Zebra"]  # equal score -> name order


def test_scoring_is_deterministic() -> None:
    opt = _opt("d", strategic_fit=4, competitive_advantage=2, cost_efficiency=5, risk_level=3, reversibility=1)
    assert score_option(opt) == score_option(opt)


def test_recommended_option_name() -> None:
    a = _opt("A", strategic_fit=2, competitive_advantage=2, cost_efficiency=2, risk_level=2, reversibility=2)
    b = _opt("B", strategic_fit=5, competitive_advantage=5, cost_efficiency=5, risk_level=5, reversibility=5)
    assert recommended_option_name([a, b]) == "B"
    assert recommended_option_name([]) is None
