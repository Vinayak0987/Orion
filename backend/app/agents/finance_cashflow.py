"""Deterministic cash-flow and unit-economics computation (F25a support).

Pure Python, no LLM, no I/O: given a completed FinanceOutput and the run's
intent, it derives the month-by-month CASH position for year 1 and the core unit
economics. This answers the question the profit-only P&L does not - "when does
the business run lowest on cash, and does it survive to break-even" - which is
the most common reason small businesses fail.

Same discipline as `strategy_scoring.py` / the finance totals: everything is
COMPUTED here from figures sibling agents already produced, never asserted by a
model, so it is deterministic and unit-testable.

Cash model (deliberately simple and defensible):
    opening cash = owner capital (intent budget) + external funding (F24)
    month 0      = opening cash - total setup cost           (up-front spend)
    month n      = previous closing + that month's net profit (from the P&L)
The year-1 monthly net-profit path comes from the P&L periods labelled 'Y1-M..'.
"""

from __future__ import annotations

from app.models.departments import CashFlowPeriod, FinanceOutput
from app.models.intent import BusinessIntent


def _opening_capital(finance: FinanceOutput, intent: BusinessIntent | None) -> int:
    """Cash available before trading: owner's budget + external funding.

    The owner's budget (what they told us they have) plus any external funding
    the funding agent (F24) said they would raise. If no budget was stated, fall
    back to funding alone, then to the setup cost (assume they fund exactly the
    setup)."""
    budget = intent.budget.amount if (intent and intent.budget.specified) else 0
    funding = finance.funding_amount_inr or 0
    capital = budget + funding
    if capital > 0:
        return capital
    return finance.total_setup_cost_inr or 0


def _y1_monthly_net(finance: FinanceOutput) -> list[tuple[str, int]]:
    """The year-1 monthly (label, net_profit) path from the P&L periods."""
    out: list[tuple[str, int]] = []
    for period in finance.pl_forecast:
        if period.label.startswith("Y1-M"):
            month = period.label.split("-M")[-1]  # "01".."12"
            out.append((f"M{month}", int(period.net_profit_inr or 0)))
    return out


def build_cash_flow(
    finance: FinanceOutput, intent: BusinessIntent | None
) -> list[CashFlowPeriod]:
    """Year-1 monthly closing cash balance. Empty if there is no P&L to build on."""
    monthly = _y1_monthly_net(finance)
    if not monthly:
        return []

    opening = _opening_capital(finance, intent)
    setup = finance.total_setup_cost_inr or 0

    periods: list[CashFlowPeriod] = []
    balance = opening  # cash on hand before trading
    for index, (label, net) in enumerate(monthly):
        # Month 1 pays the up-front setup cost in addition to its operating result.
        net_cash = net - (setup if index == 0 else 0)
        balance += net_cash
        periods.append(
            CashFlowPeriod(
                label=label,
                net_cash_flow_inr=int(net_cash),
                closing_cash_inr=int(balance),
            )
        )
    return periods


def lowest_cash(periods: list[CashFlowPeriod]) -> tuple[int | None, int | None]:
    """(month_number, closing_cash) at the lowest point, or (None, None)."""
    if not periods:
        return None, None
    low = min(periods, key=lambda p: p.closing_cash_inr)
    month = int(low.label.lstrip("M"))
    return month, low.closing_cash_inr


def runway_months(periods: list[CashFlowPeriod]) -> int | None:
    """Months until cash first goes negative; None if it never does (survives).

    A business that never dips below zero in year 1 has 'covered' runway (return
    None -> interpreted as 'no shortfall in the forecast horizon'). Otherwise the
    runway is the month index at which cash first turns negative, minus one
    (the last fully-funded month).
    """
    if not periods:
        return None
    for index, period in enumerate(periods):
        if period.closing_cash_inr < 0:
            return index  # months survived before going negative
    return None  # never negative in the 12-month horizon


def contribution_margin_pct(finance: FinanceOutput) -> float | None:
    """Contribution margin % = 100 - COGS%.

    Derived from the P&L's gross margin (gross margin % == contribution margin at
    the unit level when COGS is the only variable cost, which is the model this
    project uses). Falls back to None if no gross margin is available.
    """
    if finance.gross_margin_pct is not None:
        return round(float(finance.gross_margin_pct), 2)
    return None


def compute_cash_position(
    finance: FinanceOutput, intent: BusinessIntent | None
) -> dict:
    """Everything F25a writes, computed deterministically. Returns a dict of the
    frozen field names so the agent's to_patch is a thin pass-through."""
    periods = build_cash_flow(finance, intent)
    low_month, low_inr = lowest_cash(periods)
    return {
        "cash_flow": periods,
        "lowest_cash_month": low_month,
        "lowest_cash_inr": low_inr,
        "runway_months": runway_months(periods),
        "contribution_margin_pct": contribution_margin_pct(finance),
    }


def fallback_summary(position: dict) -> str:
    """Deterministic summary used when the LLM synthesis pass is unavailable."""
    if not position.get("cash_flow"):
        return "Cash-flow could not be projected (no P&L available)."
    low_month = position.get("lowest_cash_month")
    low_inr = position.get("lowest_cash_inr")
    runway = position.get("runway_months")
    if runway is not None:
        return (
            f"Cash turns negative around month {runway + 1}; arrange additional "
            f"funding before then (lowest point Rs {low_inr:,} in month {low_month})."
        )
    return (
        f"Cash stays positive through year 1; the lowest point is Rs {low_inr:,} "
        f"in month {low_month}."
    )
