"""Finance schema additions (Phase 2) - frozen-safe field checks.

Proves the new cash-flow/unit-economics fields are additive: every existing
FinanceOutput field is untouched and defaults as before, and the new fields
default empty/None so a baseline run (synthesis off) produces an identical
section. Fully offline - pure Pydantic.
"""

from __future__ import annotations

from app.generation.models.departments import (
    CashFlowPeriod,
    CostItem,
    EvidenceItem,
    FinanceOutput,
    PLPeriod,
    RevenueStream,
)


def test_existing_finance_fields_unchanged() -> None:
    f = FinanceOutput()
    assert f.revenue_streams == []
    assert f.pricing_strategy is None
    assert f.avg_ticket_size_inr is None
    assert f.projected_revenue_y1_inr is None
    assert f.setup_costs == []
    assert f.recurring_costs == []
    assert f.total_setup_cost_inr is None
    assert f.total_monthly_cost_inr is None
    assert f.within_budget is None
    assert f.funding_approach is None
    assert f.funding_schemes == []
    assert f.pl_forecast == []
    assert f.gross_margin_pct is None
    assert f.net_margin_pct is None
    assert f.steady_state_net_margin_pct is None
    assert f.break_even_month is None
    assert f.benchmark_margin_pct is None


def test_new_synthesis_fields_default_empty() -> None:
    f = FinanceOutput()
    assert f.cash_flow == []
    assert f.lowest_cash_month is None
    assert f.lowest_cash_inr is None
    assert f.runway_months is None
    assert f.contribution_margin_pct is None
    assert f.finance_summary is None
    assert f.finance_evidence == []


def test_cash_flow_period_model() -> None:
    p = CashFlowPeriod(label="M04", net_cash_flow_inr=-30_000, closing_cash_inr=120_000)
    assert p.label == "M04"
    assert p.net_cash_flow_inr == -30_000
    assert p.closing_cash_inr == 120_000


def test_finance_output_roundtrips_with_new_fields() -> None:
    f = FinanceOutput(
        revenue_streams=[RevenueStream(name="Dine-in")],
        setup_costs=[CostItem(name="Equipment", category="setup", amount_inr=400_000)],
        pl_forecast=[PLPeriod(label="Y1-M01", revenue_inr=100_000)],
        cash_flow=[
            CashFlowPeriod(label="M01", net_cash_flow_inr=-50_000, closing_cash_inr=450_000),
            CashFlowPeriod(label="M04", net_cash_flow_inr=-30_000, closing_cash_inr=120_000),
        ],
        lowest_cash_month=4,
        lowest_cash_inr=120_000,
        runway_months=8,
        contribution_margin_pct=55.0,
        finance_summary="Cash dips to Rs 1.2L in month 4; arrange the loan before then.",
        finance_evidence=[EvidenceItem(claim="runway is 8 months", kind="inference", confidence=0.6)],
    )
    restored = FinanceOutput.model_validate_json(f.model_dump_json())
    assert restored == f
    assert restored.lowest_cash_month == 4
    assert restored.cash_flow[1].closing_cash_inr == 120_000
    assert restored.finance_evidence[0].kind == "inference"
