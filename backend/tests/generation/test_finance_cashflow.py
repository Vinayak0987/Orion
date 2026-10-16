"""Tests for the deterministic cash-flow / unit-economics scorer (Phase 3). Offline.

All numbers are hand-checked so the arithmetic is pinned and reproducible.
"""

from __future__ import annotations

from app.generation.agents.finance_cashflow import (
    build_cash_flow,
    compute_cash_position,
    contribution_margin_pct,
    fallback_summary,
    lowest_cash,
    runway_months,
)
from app.generation.models.departments import FinanceOutput, PLPeriod
from app.generation.models.intent import BusinessIntent, Budget


def _pl(net_by_month: list[int]) -> list[PLPeriod]:
    """Build Y1 monthly P&L periods with the given net-profit path."""
    return [
        PLPeriod(label=f"Y1-M{i + 1:02d}", revenue_inr=100_000, net_profit_inr=net)
        for i, net in enumerate(net_by_month)
    ]


def _finance(net_by_month: list[int], *, setup: int = 400_000, funding: int = 0,
             gross_margin: float | None = 60.0) -> FinanceOutput:
    return FinanceOutput(
        pl_forecast=_pl(net_by_month),
        total_setup_cost_inr=setup,
        funding_amount_inr=funding,
        gross_margin_pct=gross_margin,
    )


def _intent(budget: int = 1_500_000) -> BusinessIntent:
    return BusinessIntent(business_type="ice_cream_shop", budget=Budget(amount=budget, specified=True))


# =============================================================================
# cash-flow construction (hand-checked)
# =============================================================================


def test_cash_flow_first_month_pays_setup() -> None:
    # opening = budget 1,500,000 + funding 0 = 1,500,000
    # month 1 net = -100,000, minus setup 400,000 -> net_cash -500,000
    #   closing = 1,500,000 - 500,000 = 1,000,000
    fin = _finance([-100_000, -50_000, 0], setup=400_000)
    periods = build_cash_flow(fin, _intent(1_500_000))
    assert len(periods) == 3
    assert periods[0].net_cash_flow_inr == -500_000
    assert periods[0].closing_cash_inr == 1_000_000
    # month 2: +(-50,000) -> 950,000 ; month 3: +0 -> 950,000
    assert periods[1].closing_cash_inr == 950_000
    assert periods[2].closing_cash_inr == 950_000


def test_funding_adds_to_opening_capital() -> None:
    # opening = 1,000,000 budget + 500,000 funding = 1,500,000
    fin = _finance([0], setup=0, funding=500_000)
    periods = build_cash_flow(fin, _intent(1_000_000))
    assert periods[0].closing_cash_inr == 1_500_000


def test_no_pl_yields_no_cash_flow() -> None:
    assert build_cash_flow(FinanceOutput(), _intent()) == []


# =============================================================================
# lowest cash + runway
# =============================================================================


def test_lowest_cash_finds_the_trough() -> None:
    fin = _finance([-100_000, -200_000, 50_000, 100_000], setup=300_000)
    periods = build_cash_flow(fin, _intent(1_500_000))
    # closings: m1 1,500,000-100,000-300,000=1,100,000 ; m2 900,000 ; m3 950,000 ; m4 1,050,000
    month, cash = lowest_cash(periods)
    assert month == 2
    assert cash == 900_000


def test_runway_none_when_cash_never_negative() -> None:
    fin = _finance([50_000, 50_000, 50_000], setup=100_000)
    periods = build_cash_flow(fin, _intent(1_500_000))
    assert runway_months(periods) is None  # survives the horizon


def test_runway_counts_months_before_going_negative() -> None:
    # tiny capital, heavy monthly losses -> goes negative
    fin = _finance([-200_000, -200_000, -200_000], setup=200_000)
    periods = build_cash_flow(fin, _intent(300_000))
    # opening 300,000 ; m1: -200,000-200,000 -> -100,000 (already negative at index 0)
    assert runway_months(periods) == 0


def test_runway_positive_then_negative() -> None:
    fin = _finance([100_000, -300_000, -300_000], setup=0)
    periods = build_cash_flow(fin, _intent(200_000))
    # opening 200,000 ; m1 300,000 ; m2 0 ; m3 -300,000  -> first negative at index 2
    assert runway_months(periods) == 2


# =============================================================================
# unit economics + full compute + fallback summary
# =============================================================================


def test_contribution_margin_from_gross_margin() -> None:
    assert contribution_margin_pct(_finance([0], gross_margin=55.0)) == 55.0
    assert contribution_margin_pct(FinanceOutput()) is None


def test_compute_cash_position_bundles_everything() -> None:
    fin = _finance([-100_000, -50_000, 20_000], setup=400_000, gross_margin=60.0)
    pos = compute_cash_position(fin, _intent(1_500_000))
    assert len(pos["cash_flow"]) == 3
    assert pos["lowest_cash_month"] is not None
    assert pos["contribution_margin_pct"] == 60.0
    # deterministic
    assert compute_cash_position(fin, _intent(1_500_000)) == pos


def test_fallback_summary_variants() -> None:
    assert "could not be projected" in fallback_summary({"cash_flow": []})
    survive = compute_cash_position(_finance([50_000, 50_000], setup=0), _intent(1_000_000))
    assert "stays positive" in fallback_summary(survive)
    shortfall = compute_cash_position(_finance([-300_000, -300_000], setup=0), _intent(200_000))
    assert "negative" in fallback_summary(shortfall)
