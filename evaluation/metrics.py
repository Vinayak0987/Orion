"""F54-F58 - the quantitative metrics.

Every metric takes a finished `SharedBusinessState` and returns a `MetricResult`
with a score, a details dict, and an `applicable` flag. Nothing is silently
imputed: a metric that cannot be computed says so rather than returning zero,
because scoring an absent value as 0 would understate an arm that simply did not
emit that field and would be indistinguishable from one that emitted a wrong one.

    F54  Financial Accuracy      MAPE of projected margin vs sector benchmark
    F55  Competitor Coverage     verified competitors found / ground truth
    F56  Plan Completeness       substantive expected fields / expected fields
    F57  Consistency             cross-department checks passed / checks applicable
    F58  Routing Efficiency      token and time delta, dynamic vs all-departments
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.benchmarks import all_sourced, benchmark_for
from app.models.state import Department, SharedBusinessState
from app.orchestrator.completeness import score_completeness

# Metric names, used as the `metric` column in SQLite (F60).
FINANCIAL_ACCURACY = "financial_accuracy_mape"
COMPETITOR_COVERAGE = "competitor_coverage_rate"
PLAN_COMPLETENESS = "plan_completeness"
CONSISTENCY = "consistency_score"
ROUTING_EFFICIENCY = "routing_efficiency"

ALL_METRICS = (
    FINANCIAL_ACCURACY,
    COMPETITOR_COVERAGE,
    PLAN_COMPLETENESS,
    CONSISTENCY,
)

# Lower is better for MAPE; higher is better for the rest. The report needs this
# to avoid drawing the wrong conclusion from a smaller number.
LOWER_IS_BETTER = frozenset({FINANCIAL_ACCURACY})


@dataclass(slots=True)
class MetricResult:
    metric: str
    score: float | None
    applicable: bool = True
    reason: str = ""
    details: dict = field(default_factory=dict)

    @property
    def recorded(self) -> bool:
        return self.applicable and self.score is not None


# =============================================================================
# F54 - Financial Accuracy Score (MAPE)
# =============================================================================


def financial_accuracy(state: SharedBusinessState) -> MetricResult:
    """MAPE of the projected net margin against the sector benchmark.

    MAPE = |projected - benchmark| / |benchmark| * 100

    Net margin is used rather than revenue because revenue depends on the scale
    the entrepreneur chose, while margin is a structural property of the sector
    and therefore comparable against a published benchmark.

    WHICH MARGIN
    ------------
    The steady-state margin is scored, not the year-1 average. Sector benchmarks
    describe mature businesses, whereas a year-1 figure includes start-up ramp-up.
    The first sweep measured a year-1 margin of -9.88% against a +12% benchmark
    and reported a 182% error - but a small first-year loss is a plausible outcome
    for a new business, so that was an apples-to-oranges comparison rather than an
    inaccurate plan.

    `net_margin_pct` is the fallback for arms that report only one margin, notably
    the single-LLM baseline, which is asked for year-1 percentages and does not
    distinguish. `details.margin_basis` records which was used, so the paper can
    state the comparison honestly rather than implying both arms were measured
    identically.

    A plan with no margin is NOT scored as 100% error. That would conflate "said
    nothing" with "said something wrong", and the former is already penalised by
    F56 Completeness. Double-counting it would inflate the apparent gap between
    arms.
    """
    finance = state.get("finance")
    intent = state.get("intent")

    if finance is None:
        return MetricResult(
            FINANCIAL_ACCURACY,
            None,
            applicable=False,
            reason="no finance section; absence is scored by F56, not here",
        )

    steady = getattr(finance, "steady_state_net_margin_pct", None)
    if steady is not None:
        projected, basis = float(steady), "steady_state"
    elif finance.net_margin_pct is not None:
        projected, basis = float(finance.net_margin_pct), "year_1_average"
    else:
        return MetricResult(
            FINANCIAL_ACCURACY,
            None,
            applicable=False,
            reason="no net margin projected; absence is scored by F56, not here",
        )

    if intent is None:
        return MetricResult(
            FINANCIAL_ACCURACY, None, applicable=False, reason="no intent on state"
        )

    benchmark = benchmark_for(intent.sector)
    if benchmark.net_margin_pct == 0:
        return MetricResult(
            FINANCIAL_ACCURACY, None, applicable=False, reason="benchmark is zero"
        )

    expected = benchmark.net_margin_pct
    mape = abs(projected - expected) / abs(expected) * 100.0

    return MetricResult(
        FINANCIAL_ACCURACY,
        round(mape, 2),
        details={
            "projected_net_margin_pct": projected,
            "margin_basis": basis,
            "year_1_net_margin_pct": finance.net_margin_pct,
            "benchmark_net_margin_pct": expected,
            "sector": intent.sector.value,
            "benchmark_source": benchmark.source,
            "benchmark_sourced": benchmark.sourced,
            "absolute_error_pp": round(abs(projected - expected), 2),
        },
    )


# =============================================================================
# F55 - Competitor Coverage Rate
# =============================================================================


def _normalise(name: str) -> str:
    """Loose match so "Naturals Ice Cream" counts as "Naturals"."""
    cleaned = "".join(char for char in name.lower() if char.isalnum() or char.isspace())
    stop = {"the", "ice", "cream", "cafe", "restaurant", "shop", "store", "salon", "and", "co"}
    tokens = [token for token in cleaned.split() if token not in stop]
    return " ".join(tokens) or cleaned.strip()


def _matches(found: str, actual: str) -> bool:
    left, right = _normalise(found), _normalise(actual)
    if not left or not right:
        return False
    return left == right or left in right or right in left


def competitor_coverage(
    state: SharedBusinessState,
    ground_truth: list[str] | None,
) -> MetricResult:
    """Fraction of manually verified nearby businesses the system found.

    RQ3's headline metric. `Competitor.source` separates the arms: a plan whose
    competitors are all `llm_inferred` is the text-only condition, one with
    `google_places` or `openstreetmap` entries is grounded.

    Requires hand-collected ground truth. Without it the metric is not scored -
    comparing against the model's own output would be circular.
    """
    strategy = state.get("strategy")
    found = list(strategy.competitors) if strategy is not None else []
    sources = sorted({competitor.source for competitor in found})

    if not ground_truth:
        return MetricResult(
            COMPETITOR_COVERAGE,
            None,
            applicable=False,
            reason="no hand-verified ground truth for this prompt",
            details={"found_count": len(found), "sources": sources},
        )

    matched = [
        actual
        for actual in ground_truth
        if any(_matches(competitor.name, actual) for competitor in found)
    ]
    coverage = 100.0 * len(matched) / len(ground_truth)

    return MetricResult(
        COMPETITOR_COVERAGE,
        round(coverage, 2),
        details={
            "ground_truth_count": len(ground_truth),
            "found_count": len(found),
            "matched_count": len(matched),
            "matched": matched,
            "found_names": [competitor.name for competitor in found],
            "sources": sources,
            "grounded": any(s != "llm_inferred" for s in sources),
        },
    )


# =============================================================================
# F56 - Plan Completeness Score
# =============================================================================


def plan_completeness(state: SharedBusinessState) -> MetricResult:
    """Percentage of expected fields present and substantive.

    Reuses `score_completeness` (F16) so the API and the paper report the same
    number. Denominated over the run's active departments, so dynamic routing is
    not penalised for correctly skipping Operations.
    """
    metadata = state.get("metadata")
    active = (
        list(metadata.active_departments)
        if metadata is not None and metadata.active_departments
        else list(Department)
    )
    report = score_completeness(state, active)

    if report.expected_count == 0:
        return MetricResult(
            PLAN_COMPLETENESS, None, applicable=False, reason="no expected fields"
        )

    return MetricResult(
        PLAN_COMPLETENESS,
        report.score,
        details={
            "present_count": report.present_count,
            "expected_count": report.expected_count,
            "missing": report.missing,
            "scored_departments": [d.value for d in active],
        },
    )


# =============================================================================
# F57 - Consistency Score
# =============================================================================


@dataclass(slots=True)
class ConsistencyCheck:
    name: str
    passed: bool
    detail: str


def _consistency_checks(state: SharedBusinessState) -> list[ConsistencyCheck]:
    """Cross-department agreement checks.

    Only checks whose inputs both exist are returned, so an arm is not penalised
    for a check it had no data for - that gap is F56's job.
    """
    checks: list[ConsistencyCheck] = []
    strategy = state.get("strategy")
    finance = state.get("finance")
    marketing = state.get("marketing")
    operations = state.get("operations")
    intent = state.get("intent")

    # 1. Strategy's obtainable market must accommodate Finance's revenue.
    som = strategy.market_size.som_inr if strategy and strategy.market_size else None
    revenue = finance.projected_revenue_y1_inr if finance else None
    if som and revenue:
        checks.append(
            ConsistencyCheck(
                "revenue_within_som",
                revenue <= som,
                f"year-1 revenue {revenue:,} vs SOM {som:,}",
            )
        )

    # 2. Setup cost must fit the budget the user stated.
    setup = finance.total_setup_cost_inr if finance else None
    if setup and intent is not None and intent.budget.specified and intent.budget.amount:
        checks.append(
            ConsistencyCheck(
                "setup_within_budget",
                setup <= intent.budget.amount,
                f"setup {setup:,} vs budget {intent.budget.amount:,}",
            )
        )

    # 3. Marketing spend must fit inside the monthly cost base.
    spend = marketing.total_marketing_budget_inr if marketing else None
    monthly = finance.total_monthly_cost_inr if finance else None
    if spend and monthly:
        checks.append(
            ConsistencyCheck(
                "marketing_within_monthly_cost",
                spend <= monthly,
                f"marketing {spend:,} vs monthly cost {monthly:,}",
            )
        )

    # 4. Payroll must fit inside the monthly cost base.
    payroll = operations.total_monthly_payroll_inr if operations else None
    if payroll and monthly:
        checks.append(
            ConsistencyCheck(
                "payroll_within_monthly_cost",
                payroll <= monthly,
                f"payroll {payroll:,} vs monthly cost {monthly:,}",
            )
        )

    # 5. Margins must be internally coherent.
    if finance and finance.gross_margin_pct is not None and finance.net_margin_pct is not None:
        checks.append(
            ConsistencyCheck(
                "net_margin_below_gross",
                finance.net_margin_pct <= finance.gross_margin_pct,
                f"net {finance.net_margin_pct}% vs gross {finance.gross_margin_pct}%",
            )
        )

    # 6. Revenue must at least cover the annual cost base.
    if revenue and monthly:
        checks.append(
            ConsistencyCheck(
                "revenue_covers_annual_cost",
                revenue >= monthly * 12,
                f"revenue {revenue:,} vs annual cost {monthly * 12:,}",
            )
        )

    # 7. Every workflow owner must be a role the staffing plan created.
    if operations and operations.daily_workflow and operations.roles:
        titles = {role.title.strip().lower() for role in operations.roles}
        owners = [
            step.owner_role.strip().lower()
            for step in operations.daily_workflow
            if step.owner_role.strip()
        ]
        if owners:
            unknown = [
                owner for owner in owners
                if not any(owner in title or title in owner for title in titles)
            ]
            checks.append(
                ConsistencyCheck(
                    "workflow_owners_are_real_roles",
                    not unknown,
                    f"{len(unknown)} of {len(owners)} owners not in staffing plan",
                )
            )

    # 8. Channel budget shares must sum to about 100%.
    if marketing and marketing.channels:
        shares = [c.budget_share_pct for c in marketing.channels if c.budget_share_pct is not None]
        if len(shares) >= 2:
            total = sum(shares)
            checks.append(
                ConsistencyCheck(
                    "channel_shares_sum_to_100",
                    95.0 <= total <= 105.0,
                    f"shares sum to {total:.1f}%",
                )
            )

    # 9. The P&L's operating expense must match the cost agent's monthly total.
    #
    # Surfaced by the first evaluation sweep: multi-agent MAPE ran into the
    # hundreds because the P&L agent supplied a fixed opex far below the monthly
    # cost the cost-structure agent had already derived, inflating net margin.
    # Two Finance agents disagreeing about the same number is exactly the
    # cross-department inconsistency F57 exists to measure.
    if finance and finance.pl_forecast and monthly:
        first_period_opex = finance.pl_forecast[0].operating_expense_inr
        if first_period_opex:
            ratio = first_period_opex / monthly
            checks.append(
                ConsistencyCheck(
                    "pl_opex_matches_cost_structure",
                    0.5 <= ratio <= 1.5,
                    f"P&L opex {first_period_opex:,} vs monthly cost {monthly:,} "
                    f"(ratio {ratio:.2f})",
                )
            )

    return checks


def consistency(state: SharedBusinessState) -> MetricResult:
    """Percentage of applicable cross-department checks that pass.

    This is the metric the append-only state contract (F15) exists to make
    meaningful: because no agent can overwrite another department's section, a
    disagreement is a real disagreement between specialists rather than a
    last-writer-wins artefact.
    """
    checks = _consistency_checks(state)
    if not checks:
        return MetricResult(
            CONSISTENCY,
            None,
            applicable=False,
            reason="no cross-department checks had both inputs available",
        )

    passed = [check for check in checks if check.passed]
    return MetricResult(
        CONSISTENCY,
        round(100.0 * len(passed) / len(checks), 2),
        details={
            "checks_applicable": len(checks),
            "checks_passed": len(passed),
            "failures": [
                {"check": check.name, "detail": check.detail}
                for check in checks
                if not check.passed
            ],
        },
    )


# =============================================================================
# F58 - Routing Efficiency
# =============================================================================


def routing_efficiency(
    dynamic_state: SharedBusinessState,
    control_state: SharedBusinessState,
) -> MetricResult:
    """Token and time saving of dynamic routing, plus the quality delta.

    RQ2 asks whether routing improves efficiency *without degrading quality*, so a
    saving is only meaningful alongside the quality change. The score returned is
    the token saving percentage; the quality delta travels in details and the
    report presents both together.
    """
    def tokens(state: SharedBusinessState) -> int:
        return sum(trace.total_tokens for trace in state.get("agent_traces") or [])

    dynamic_tokens, control_tokens = tokens(dynamic_state), tokens(control_state)
    dynamic_meta, control_meta = dynamic_state["metadata"], control_state["metadata"]
    dynamic_ms = dynamic_meta.total_duration_ms or 0
    control_ms = control_meta.total_duration_ms or 0

    if control_tokens == 0:
        return MetricResult(
            ROUTING_EFFICIENCY,
            None,
            applicable=False,
            reason="control arm consumed no tokens",
        )

    token_saving = 100.0 * (control_tokens - dynamic_tokens) / control_tokens
    time_saving = (
        100.0 * (control_ms - dynamic_ms) / control_ms if control_ms else None
    )

    dynamic_quality = plan_completeness(dynamic_state).score
    control_quality = plan_completeness(control_state).score
    quality_delta = (
        round(dynamic_quality - control_quality, 2)
        if dynamic_quality is not None and control_quality is not None
        else None
    )

    return MetricResult(
        ROUTING_EFFICIENCY,
        round(token_saving, 2),
        details={
            "dynamic_tokens": dynamic_tokens,
            "control_tokens": control_tokens,
            "token_saving_pct": round(token_saving, 2),
            "dynamic_duration_ms": dynamic_ms,
            "control_duration_ms": control_ms,
            "time_saving_pct": round(time_saving, 2) if time_saving is not None else None,
            "dynamic_completeness": dynamic_quality,
            "control_completeness": control_quality,
            "quality_delta_pp": quality_delta,
            "skipped_departments": [d.value for d in dynamic_meta.skipped_departments],
            "routing_actually_skipped": bool(dynamic_meta.skipped_departments),
        },
    )


# =============================================================================
# Batch scoring
# =============================================================================


def score_state(
    state: SharedBusinessState,
    ground_truth: list[str] | None = None,
) -> list[MetricResult]:
    """The four per-plan metrics. F58 needs two runs and is computed separately."""
    return [
        financial_accuracy(state),
        competitor_coverage(state, ground_truth),
        plan_completeness(state),
        consistency(state),
    ]


def benchmark_caveat() -> str | None:
    """Warning to attach to any F54 figure while benchmarks are unsourced."""
    if all_sourced():
        return None
    from app.agents.benchmarks import unsourced_sectors

    return (
        "PROVISIONAL: financial accuracy is scored against unsourced benchmark "
        f"estimates for {', '.join(unsourced_sectors())}. Fill "
        "evaluation/benchmarks.csv with cited figures before publishing this metric."
    )
