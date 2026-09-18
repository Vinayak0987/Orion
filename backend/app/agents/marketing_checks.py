"""Deterministic marketing consistency & unit-economics checks (F33a support).

Pure Python, no LLM, no I/O. Marketing is a numeric department whose figures must
reconcile - internally (channel shares sum to 100) and with Finance (marketing
spend fits the operating budget; the plan's implied customer count and allowable
CAC are economically coherent). This module computes those checks:

  * budget-share sum   - channel budget_share_pct should sum to ~100.
  * budget vs op-cost  - total_marketing_budget_inr should fit the Finance
                         monthly operating cost.
  * CAC / customers    - customers-needed/month = (Y1 revenue / 12) / avg ticket;
                         allowable CAC = marketing budget / customers-needed.
  * campaign coherence - the 3 phase budgets vs ~3 months of marketing budget.

Same discipline as the other departments' scorers: computed here, never asserted
by the model, so it is deterministic and unit-testable. It does NOT score channel
choice quality - only numeric coherence.
"""

from __future__ import annotations

from app.models.departments import MarketingOutput
from app.models.state import Department, SharedBusinessState

# Channel shares should sum to ~100%. Outside this band is a real defect.
_SHARE_LOW, _SHARE_HIGH = 95.0, 105.0
# An allowable CAC below this (in INR) means the plan needs far more customers
# than the budget could plausibly acquire - an incoherent plan. Heuristic floor.
_MIN_PLAUSIBLE_CAC_INR = 10
# Campaign phase budgets should be within this factor of ~3 months of spend.
_CAMPAIGN_TOLERANCE = (0.5, 2.0)


def budget_share_total(marketing: MarketingOutput) -> float | None:
    """Sum of channel budget_share_pct, or None if no channels carry a share."""
    shares = [c.budget_share_pct for c in marketing.channels if c.budget_share_pct is not None]
    if not shares:
        return None
    return round(sum(shares), 2)


def _finance(state: SharedBusinessState):
    return state.get(Department.FINANCE.value)


def customers_needed_monthly(state: SharedBusinessState) -> int | None:
    """(Year-1 revenue / 12) / average ticket -> customers required per month."""
    finance = _finance(state)
    if finance is None:
        return None
    revenue = finance.projected_revenue_y1_inr
    ticket = finance.avg_ticket_size_inr
    if not revenue or not ticket or ticket <= 0:
        return None
    return int(round((revenue / 12) / ticket))


def allowable_cac(marketing: MarketingOutput, customers: int | None) -> int | None:
    """Marketing budget / customers-needed -> implied max cost per acquisition."""
    budget = marketing.total_marketing_budget_inr
    if not budget or not customers or customers <= 0:
        return None
    return int(round(budget / customers))


def check_marketing(marketing: MarketingOutput, state: SharedBusinessState) -> dict:
    """Everything F33a writes, computed deterministically. Returns a dict of the
    frozen field names so the agent's to_patch is a thin pass-through."""
    warnings: list[str] = []

    # 1. Channel shares sum to ~100.
    share_total = budget_share_total(marketing)
    if share_total is not None and not (_SHARE_LOW <= share_total <= _SHARE_HIGH):
        warnings.append(
            f"channel budget shares sum to {share_total}%, not 100% - the mix is "
            f"under- or over-allocated"
        )

    # 2. Marketing spend fits the monthly operating cost.
    finance = _finance(state)
    budget = marketing.total_marketing_budget_inr
    if finance is not None and budget and finance.total_monthly_cost_inr:
        if budget > finance.total_monthly_cost_inr:
            warnings.append(
                f"monthly marketing budget (Rs {budget:,}) exceeds the total monthly "
                f"operating cost (Rs {finance.total_monthly_cost_inr:,})"
            )

    # 3. CAC / customers-needed reconciliation with Finance.
    customers = customers_needed_monthly(state)
    cac = allowable_cac(marketing, customers)
    if cac is not None and cac < _MIN_PLAUSIBLE_CAC_INR:
        warnings.append(
            f"plan needs ~{customers} customers/month but the marketing budget "
            f"allows only Rs {cac} per acquisition - the numbers are incoherent"
        )

    # 4. Campaign phase budgets vs ~3 months of marketing spend.
    phase_total = sum(p.budget_inr or 0 for p in marketing.campaign_phases)
    if budget and phase_total > 0:
        three_months = budget * 3
        low, high = _CAMPAIGN_TOLERANCE
        if not (three_months * low <= phase_total <= three_months * high):
            warnings.append(
                f"campaign phase budgets total Rs {phase_total:,} but ~3 months of "
                f"marketing spend is Rs {three_months:,} - they do not reconcile"
            )

    return {
        "budget_share_total_pct": share_total,
        "customers_needed_monthly": customers,
        "allowable_cac_inr": cac,
        "marketing_warnings": warnings,
    }


def fallback_summary(result: dict) -> str:
    """Deterministic summary used when the LLM synthesis pass is unavailable."""
    customers = result.get("customers_needed_monthly")
    cac = result.get("allowable_cac_inr")
    warnings = result.get("marketing_warnings") or []
    if customers and cac:
        econ = f"plan needs ~{customers} customers/month at Rs {cac} allowable CAC"
    else:
        econ = "unit economics could not be computed (missing revenue or ticket size)"
    if not warnings:
        return f"Marketing plan is internally consistent; {econ}."
    return f"{econ.capitalize()}. Issues: " + "; ".join(warnings[:3]) + "."
