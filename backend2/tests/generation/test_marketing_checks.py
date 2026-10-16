"""Tests for the deterministic marketing checker (Phase 2). Offline, hand-checked."""

from __future__ import annotations

from app.generation.agents.marketing_checks import (
    allowable_cac,
    budget_share_total,
    check_marketing,
    customers_needed_monthly,
    fallback_summary,
)
from app.generation.models.departments import Channel, CampaignPhase, FinanceOutput, MarketingOutput
from app.generation.models.state import Department, new_state


def _state(*, revenue: int | None = 8_400_000, ticket: int | None = 500,
           op_cost: int | None = 200_000):
    st = new_state("s", "prompt")
    st[Department.FINANCE.value] = FinanceOutput(
        projected_revenue_y1_inr=revenue,
        avg_ticket_size_inr=ticket,
        total_monthly_cost_inr=op_cost,
    )
    return st


def _mkt(*, shares: list[float], budget: int | None = 100_000,
         phases: list[int] | None = None) -> MarketingOutput:
    channels = [Channel(name=f"c{i}", budget_share_pct=s) for i, s in enumerate(shares)]
    campaign = [
        CampaignPhase(phase="launch", day_range="D", budget_inr=b)
        for b in (phases or [])
    ]
    return MarketingOutput(
        channels=channels, total_marketing_budget_inr=budget, campaign_phases=campaign
    )


# =============================================================================
# building blocks (hand-checked)
# =============================================================================


def test_budget_share_total() -> None:
    assert budget_share_total(_mkt(shares=[60.0, 40.0])) == 100.0
    assert budget_share_total(_mkt(shares=[50.0, 30.0])) == 80.0
    assert budget_share_total(_mkt(shares=[])) is None


def test_customers_needed_monthly_hand_checked() -> None:
    # 8,400,000 / 12 = 700,000 per month ; / 500 ticket = 1400 customers
    assert customers_needed_monthly(_state(revenue=8_400_000, ticket=500)) == 1400


def test_customers_needed_none_without_finance() -> None:
    assert customers_needed_monthly(new_state("s", "p")) is None
    assert customers_needed_monthly(_state(revenue=None)) is None
    assert customers_needed_monthly(_state(ticket=0)) is None


def test_allowable_cac_hand_checked() -> None:
    # budget 100,000 / 1400 customers = 71 (rounded)
    assert allowable_cac(_mkt(shares=[100.0], budget=100_000), 1400) == 71
    assert allowable_cac(_mkt(shares=[100.0], budget=None), 1400) is None
    assert allowable_cac(_mkt(shares=[100.0], budget=100_000), 0) is None


# =============================================================================
# check_marketing warnings
# =============================================================================


def test_clean_plan_no_warnings() -> None:
    mkt = _mkt(shares=[60.0, 40.0], budget=100_000, phases=[100_000, 100_000, 100_000])
    result = check_marketing(mkt, _state())
    assert result["budget_share_total_pct"] == 100.0
    assert result["customers_needed_monthly"] == 1400
    assert result["allowable_cac_inr"] == 71
    assert result["marketing_warnings"] == []


def test_shares_not_summing_to_100_warns() -> None:
    result = check_marketing(_mkt(shares=[50.0, 30.0]), _state())
    assert any("sum to 80" in w for w in result["marketing_warnings"])


def test_budget_over_operating_cost_warns() -> None:
    # marketing budget 500,000 > op cost 200,000
    mkt = _mkt(shares=[100.0], budget=500_000)
    result = check_marketing(mkt, _state(op_cost=200_000))
    assert any("exceeds the total monthly operating cost" in w for w in result["marketing_warnings"])


def test_incoherent_cac_warns() -> None:
    # huge revenue, tiny ticket -> millions of customers needed, CAC < Rs 10
    mkt = _mkt(shares=[100.0], budget=50_000)
    result = check_marketing(mkt, _state(revenue=500_000_000, ticket=100))
    assert result["allowable_cac_inr"] < 10
    assert any("incoherent" in w for w in result["marketing_warnings"])


def test_campaign_budget_mismatch_warns() -> None:
    # 3 months of 100,000 = 300,000 ; phases total 3,000,000 -> 10x, out of tolerance
    mkt = _mkt(shares=[100.0], budget=100_000, phases=[1_000_000, 1_000_000, 1_000_000])
    result = check_marketing(mkt, _state())
    assert any("do not reconcile" in w for w in result["marketing_warnings"])


def test_check_is_deterministic() -> None:
    mkt = _mkt(shares=[60.0, 40.0], budget=100_000)
    assert check_marketing(mkt, _state()) == check_marketing(mkt, _state())


def test_fallback_summary_variants() -> None:
    clean = {"customers_needed_monthly": 1400, "allowable_cac_inr": 71, "marketing_warnings": []}
    assert "consistent" in fallback_summary(clean)
    issues = {"customers_needed_monthly": 1400, "allowable_cac_inr": 71,
              "marketing_warnings": ["shares sum to 80%"]}
    assert "Issues" in fallback_summary(issues)
    nomath = {"customers_needed_monthly": None, "allowable_cac_inr": None, "marketing_warnings": []}
    assert "could not be computed" in fallback_summary(nomath)
