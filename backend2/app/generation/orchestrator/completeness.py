"""F16 - State validation and completeness check.

Two independent checks run after the graph finishes:

    score_completeness()      what fraction of expected sections is substantive
    detect_contradictions()   cross-department logic errors

`EXPECTED_FIELDS` is the 26-field checklist that the Plan Completeness Score
(F56) is computed from. It is defined here, once, and reused by both the runtime
validator and the evaluation harness - so the number the paper reports is the
same number the API returns.

Scoring is denominated over ACTIVE departments only. Scoring a skipped
Operations section as "missing" would penalise dynamic routing for working
correctly, and RQ2 would show a false quality regression.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from app.generation.models.intent import BusinessIntent
from app.generation.models.state import Department, SharedBusinessState

# The F56 checklist. Field names must exist on the department models in
# app/models/departments.py - `test_orchestrator.py` asserts that they do.
EXPECTED_FIELDS: dict[Department, tuple[str, ...]] = {
    Department.STRATEGY: (
        "executive_summary",
        "market_size",
        "risks",
        "competitors",
        "market_overview",
        "location_score",
    ),
    Department.FINANCE: (
        "revenue_streams",
        "setup_costs",
        "recurring_costs",
        "funding_approach",
        "pl_forecast",
        "break_even_month",
    ),
    Department.BRANDING: (
        "recommended_name",
        "personality_traits",
        "color_palette",
        "taglines",
        "logo_style",
    ),
    Department.MARKETING: (
        "channels",
        "personas",
        "campaign_phases",
        "target_keywords",
        "content_topics",
    ),
    Department.OPERATIONS: (
        "vendors",
        "roles",
        "tools",
        "daily_workflow",
    ),
}

TOTAL_EXPECTED_FIELDS = sum(len(v) for v in EXPECTED_FIELDS.values())

# A string shorter than this is a label, not content.
MIN_SUBSTANTIVE_TEXT_LENGTH = 20

# Fields that are legitimately short. A brand name is the whole point of F26 and
# "Shitalaya" is a complete answer at 9 characters; scoring it as insubstantial
# understated Plan Completeness (F56) on a real run and would have done so for
# both the multi-agent and baseline arms, hiding a genuine capability.
SHORT_TEXT_FIELDS: dict[str, int] = {
    "branding.recommended_name": 2,
    "branding.logo_style": 6,
    "strategy.business_model_type": 3,
    "finance.funding_approach": 6,
    "marketing.content_frequency": 6,
}


def minimum_length_for(field_key: str) -> int:
    """Substantive-text threshold for a `department.field` key."""
    return SHORT_TEXT_FIELDS.get(field_key, MIN_SUBSTANTIVE_TEXT_LENGTH)


def is_substantive(value: object, min_text_length: int = MIN_SUBSTANTIVE_TEXT_LENGTH) -> bool:
    """F56 - "present AND substantive", not merely non-null.

    A section that contains an empty list, an empty string, or a three-word
    placeholder does not count. This is what stops a single-LLM baseline from
    scoring well by emitting section headers with no content.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return len(value.strip()) >= min_text_length
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, BaseModel):
        return any(
            is_substantive(getattr(value, name, None)) for name in type(value).model_fields
        )
    return bool(value)


@dataclass(slots=True)
class CompletenessReport:
    score: float
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    expected_count: int = 0

    @property
    def present_count(self) -> int:
        return len(self.present)


def score_completeness(
    state: SharedBusinessState,
    active_departments: tuple[Department, ...] | list[Department],
) -> CompletenessReport:
    """Percentage of expected fields that are present and substantive."""
    active = set(active_departments)
    present: list[str] = []
    missing: list[str] = []

    for department, fields in EXPECTED_FIELDS.items():
        if department not in active:
            continue
        section = state.get(department.value)
        for field_name in fields:
            key = f"{department.value}.{field_name}"
            value = getattr(section, field_name, None) if section is not None else None
            substantive = is_substantive(value, minimum_length_for(key))
            (present if substantive else missing).append(key)

    expected = len(present) + len(missing)
    score = round(100.0 * len(present) / expected, 2) if expected else 0.0
    return CompletenessReport(
        score=score, present=present, missing=missing, expected_count=expected
    )


def detect_contradictions(
    state: SharedBusinessState,
    intent: BusinessIntent | None = None,
) -> list[str]:
    """Cross-department sanity checks (F16).

    These are hard logic errors, not quality judgements. The Consistency Score
    (F57) builds on the same idea but scores proportionally instead of listing.
    """
    warnings: list[str] = []
    finance = state.get(Department.FINANCE.value)
    strategy = state.get(Department.STRATEGY.value)
    marketing = state.get(Department.MARKETING.value)
    operations = state.get(Department.OPERATIONS.value)
    resolved_intent = intent or state.get("intent")

    # --- budget envelope -----------------------------------------------------
    if finance is not None and resolved_intent is not None:
        budget = resolved_intent.budget
        setup = finance.total_setup_cost_inr
        if budget.specified and setup is not None and setup > budget.amount:
            overshoot = 100.0 * (setup - budget.amount) / budget.amount
            warnings.append(
                f"Setup cost Rs {setup:,} exceeds stated budget "
                f"Rs {budget.amount:,} by {overshoot:.1f}%"
            )

    # --- margin sanity -------------------------------------------------------
    if finance is not None:
        gross = finance.gross_margin_pct
        net = finance.net_margin_pct
        if gross is not None and not 0.0 <= gross <= 95.0:
            warnings.append(f"Gross margin {gross}% is outside a plausible 0-95% range")
        if net is not None and gross is not None and net > gross:
            warnings.append(f"Net margin {net}% exceeds gross margin {gross}%")
        if net is not None and net < -50.0:
            # Observed on a real run: gross 70% but net -263%, because the model
            # sized revenue far below the cost base it had already produced.
            # Arithmetically correct, commercially incoherent - exactly the kind
            # of cross-agent disagreement F57 is meant to surface.
            warnings.append(
                f"Net margin {net}% implies the business loses more than it earns; "
                f"revenue projection is inconsistent with the cost structure"
            )
        if finance.break_even_month is not None and finance.break_even_month <= 0:
            warnings.append(
                f"Break-even month {finance.break_even_month} must be a positive month index"
            )
        if (
            finance.break_even_month is None
            and finance.pl_forecast
            and net is not None
            and net > 0
        ):
            warnings.append(
                "Net margin is positive but no break-even month was reached in the forecast"
            )

    # --- revenue must cover the cost base ------------------------------------
    if finance is not None:
        annual_revenue = finance.projected_revenue_y1_inr
        monthly_cost = finance.total_monthly_cost_inr
        if annual_revenue is not None and monthly_cost is not None and monthly_cost > 0:
            annual_cost = monthly_cost * 12
            if annual_revenue < annual_cost:
                shortfall = 100.0 * (annual_cost - annual_revenue) / annual_cost
                warnings.append(
                    f"Year-1 revenue Rs {annual_revenue:,} is {shortfall:.0f}% below the "
                    f"annual operating cost Rs {annual_cost:,}"
                )

    # --- strategy TAM vs finance revenue (precursor to F57) ------------------
    if strategy is not None and finance is not None:
        market = strategy.market_size
        revenue = finance.projected_revenue_y1_inr
        if market is not None and market.som_inr is not None and revenue is not None:
            if revenue > market.som_inr:
                warnings.append(
                    f"Year-1 revenue Rs {revenue:,} exceeds obtainable market "
                    f"(SOM) Rs {market.som_inr:,}"
                )

    # --- marketing spend vs finance envelope ---------------------------------
    if marketing is not None and finance is not None:
        spend = marketing.total_marketing_budget_inr
        monthly = finance.total_monthly_cost_inr
        if spend is not None and monthly is not None and spend > monthly:
            warnings.append(
                f"Marketing budget Rs {spend:,} exceeds total monthly operating "
                f"cost Rs {monthly:,}"
            )

    # --- payroll vs finance envelope -----------------------------------------
    if operations is not None and finance is not None:
        payroll = operations.total_monthly_payroll_inr
        monthly = finance.total_monthly_cost_inr
        if payroll is not None and monthly is not None and payroll > monthly:
            warnings.append(
                f"Operations payroll Rs {payroll:,} exceeds total monthly cost "
                f"Rs {monthly:,}"
            )

    return warnings
