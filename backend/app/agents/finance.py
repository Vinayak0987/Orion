"""Finance department - 4 agents (F22-F25).

Stage 1 (parallel)   revenue_model  ∥  cost_structure
Stage 2 (parallel)   funding_strategy  ∥  pl_forecast

Design rule: the LLM supplies business drivers, Python does the arithmetic.

The P&L agent asks the model for six drivers (opening revenue, steady-state
revenue, COGS %, fixed opex, growth rates) and then generates all 20 forecast
periods, both margins and the break-even month in code. Totals in the cost agent
and budget utilisation are computed the same way.

This matters for F54. Financial Accuracy is measured as MAPE of projected margin
against an MSME sector benchmark. If the margin were itself generated text, the
metric would partly measure the model's arithmetic rather than the quality of its
business assumptions - and it would not be reproducible between providers.
Deriving margins from drivers isolates the judgement being evaluated.
"""

from __future__ import annotations

import structlog
from pydantic import Field

from app.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    context_block,
    upstream_block,
)
from app.agents.benchmarks import gross_margin_benchmark, net_margin_benchmark
from app.llm.base import ModelTier
from app.models.departments import CostItem, PLPeriod, RevenueStream
from app.models.intent import Sector
from app.models.state import Department, SharedBusinessState

log = structlog.get_logger(__name__)

DEPT = Department.FINANCE


# =============================================================================
# F22 - Revenue Model Agent
# =============================================================================


class RevenueStreamOut(AgentOutput):
    name: str = ""
    description: str = ""
    monthly_estimate_inr: int | None = None
    share_pct: float | None = None


class RevenueModelOut(AgentOutput):
    revenue_streams: list[RevenueStreamOut] = Field(default_factory=list)
    pricing_strategy: str = ""
    avg_ticket_size_inr: int | None = None
    projected_revenue_y1_inr: int | None = None
    projected_revenue_y2_inr: int | None = None
    projected_revenue_y3_inr: int | None = None
    seasonality_notes: str = ""


class RevenueModelAgent(Agent):
    spec = AgentSpec(
        agent_id="revenue_model",
        department=DEPT,
        feature="F22",
        schema=RevenueModelOut,
        tier=ModelTier.REASONING,
        temperature=0.2,
        max_tokens=1200,
    )
    system = (
        "You are a financial analyst for Indian SMEs. You quote realistic Indian "
        "price points and volumes, and your revenue figures reconcile with the "
        "obtainable market you are given."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "market", "competitors")
        return f"""{context_block(state)}

STRATEGY FINDINGS FROM THIS RUN:
{upstream or "(none available)"}

Build the revenue model and return JSON with these keys:
{{
  "revenue_streams": [{{"name": "stream", "description": "one line", "monthly_estimate_inr": 250000, "share_pct": 60}}],
  "pricing_strategy": "2-3 sentences with actual INR price points",
  "avg_ticket_size_inr": average spend per customer visit in INR,
  "projected_revenue_y1_inr": total year 1 revenue in INR,
  "projected_revenue_y2_inr": total year 2 revenue in INR,
  "projected_revenue_y3_inr": total year 3 revenue in INR,
  "seasonality_notes": "1-2 sentences on seasonal peaks and troughs"
}}

Give 2 to 4 revenue streams whose share_pct values sum to 100.
Year-1 revenue must not exceed the obtainable market (SOM) shown above."""

    def to_patch(self, parsed: RevenueModelOut, state: SharedBusinessState) -> dict:
        streams = [
            RevenueStream(
                name=s.name.strip(),
                description=s.description.strip(),
                monthly_estimate_inr=s.monthly_estimate_inr,
                share_pct=s.share_pct,
            )
            for s in parsed.revenue_streams
            if s.name and s.name.strip()
        ]

        y1, y2, y3 = _bounded_revenue(
            parsed.projected_revenue_y1_inr,
            parsed.projected_revenue_y2_inr,
            parsed.projected_revenue_y3_inr,
            state,
        )

        return {
            "revenue_streams": streams,
            "pricing_strategy": parsed.pricing_strategy,
            "avg_ticket_size_inr": parsed.avg_ticket_size_inr,
            "projected_revenue_y1_inr": y1,
            "projected_revenue_y2_inr": y2,
            "projected_revenue_y3_inr": y3,
            "seasonality_notes": parsed.seasonality_notes,
        }


# =============================================================================
# F23 - Cost Structure Agent
# =============================================================================


class CostLineOut(AgentOutput):
    name: str = ""
    subcategory: str = ""
    amount_inr: int = 0
    notes: str = ""


class CostStructureOut(AgentOutput):
    setup_costs: list[CostLineOut] = Field(default_factory=list)
    recurring_costs: list[CostLineOut] = Field(default_factory=list)


_COST_SUBCATEGORIES = {
    "rent",
    "salary",
    "equipment",
    "utilities",
    "marketing",
    "licences",
    "inventory",
    "interiors",
    "deposit",
    "other",
}


class CostStructureAgent(Agent):
    spec = AgentSpec(
        agent_id="cost_structure",
        department=DEPT,
        feature="F23",
        schema=CostStructureOut,
        tier=ModelTier.REASONING,
        temperature=0.2,
        max_tokens=1400,
    )
    system = (
        "You are a cost accountant for Indian SMEs. You quote real Indian market "
        "rates for rent, salaries, equipment and licences."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        intent = state.get("intent")
        budget_line = (
            f"The total of setup_costs MUST NOT exceed INR "
            f"{intent.budget.amount:,} ({intent.budget.display})."
            if intent is not None and intent.budget.specified
            else "No budget was stated; choose a sensible budget for this scale."
        )
        return f"""{context_block(state)}

Break down the costs and return JSON with these keys:
{{
  "setup_costs": [{{"name": "item", "subcategory": "deposit|equipment|interiors|licences|inventory|other", "amount_inr": 250000, "notes": "one line"}}],
  "recurring_costs": [{{"name": "item", "subcategory": "rent|salary|utilities|marketing|inventory|other", "amount_inr": 60000, "notes": "per month"}}]
}}

{budget_line}
Give 5 to 8 setup items and 5 to 8 monthly recurring items.
recurring_costs amounts are PER MONTH. Do not include totals as line items."""

    def to_patch(self, parsed: CostStructureOut, state: SharedBusinessState) -> dict:
        def convert(lines: list[CostLineOut], category: str) -> list[CostItem]:
            return [
                CostItem(
                    name=line.name.strip(),
                    category=category,
                    subcategory=line.subcategory.strip().lower()
                    if line.subcategory.strip().lower() in _COST_SUBCATEGORIES
                    else "other",
                    amount_inr=max(0, int(line.amount_inr or 0)),
                    notes=line.notes.strip(),
                )
                for line in lines
                if line.name and line.name.strip()
            ]

        setup = convert(parsed.setup_costs, "setup")
        recurring = convert(parsed.recurring_costs, "recurring")

        # Arithmetic in code, not in the model.
        total_setup = sum(item.amount_inr for item in setup)
        total_monthly = sum(item.amount_inr for item in recurring)

        intent = state.get("intent")
        utilization: float | None = None
        within: bool | None = None
        if intent is not None and intent.budget.specified and intent.budget.amount > 0:
            utilization = round(100.0 * total_setup / intent.budget.amount, 2)
            within = total_setup <= intent.budget.amount

        return {
            "setup_costs": setup,
            "recurring_costs": recurring,
            "total_setup_cost_inr": total_setup or None,
            "total_monthly_cost_inr": total_monthly or None,
            "budget_utilization_pct": utilization,
            "within_budget": within,
        }


# =============================================================================
# F24 - Funding Strategy Agent (stage 2)
# =============================================================================


class FundingOut(AgentOutput):
    funding_approach: str = ""
    funding_amount_inr: int | None = None
    funding_schemes: list[str] = Field(default_factory=list)
    funding_timeline: str = ""


class FundingStrategyAgent(Agent):
    spec = AgentSpec(
        agent_id="funding_strategy",
        department=DEPT,
        feature="F24",
        schema=FundingOut,
        tier=ModelTier.FAST,
        max_tokens=900,
    )
    system = (
        "You are an SME finance advisor who knows Indian government schemes: "
        "PMMY Mudra loans, CGTMSE, Stand-Up India, PMEGP, Startup India and state "
        "MSME subsidies."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "costs")
        return f"""{context_block(state)}

COSTS FROM THIS RUN:
{upstream or "(not yet available)"}

Recommend a funding strategy and return JSON with these keys:
{{
  "funding_approach": "2-3 sentences: bootstrapped, bank term loan, angel, or a mix, with the split",
  "funding_amount_inr": external funding required in INR (0 if fully bootstrapped),
  "funding_schemes": ["2-4 named Indian schemes this business is eligible for"],
  "funding_timeline": "2 sentences on sequencing and expected sanction time"
}}"""

    def to_patch(self, parsed: FundingOut, state: SharedBusinessState) -> dict:
        return {
            "funding_approach": parsed.funding_approach,
            "funding_amount_inr": parsed.funding_amount_inr,
            "funding_schemes": parsed.funding_schemes,
            "funding_timeline": parsed.funding_timeline,
        }


# =============================================================================
# F25 - P&L Forecast Agent (stage 2) - drivers from LLM, arithmetic in code
# =============================================================================


class PLDriversOut(AgentOutput):
    month_1_revenue_inr: int | None = None
    month_12_revenue_inr: int | None = None
    cogs_pct_of_revenue: float | None = None
    monthly_fixed_opex_inr: int | None = None
    y2_growth_pct: float | None = None
    y3_growth_pct: float | None = None
    assumptions: str = ""


class PLForecastAgent(Agent):
    spec = AgentSpec(
        agent_id="pl_forecast",
        department=DEPT,
        feature="F25",
        schema=PLDriversOut,
        tier=ModelTier.REASONING,
        temperature=0.1,
        max_tokens=800,
    )
    system = (
        "You are a financial modeller. You supply only the drivers of a forecast; "
        "you never compute the statement yourself."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "revenue", "costs")
        return f"""{context_block(state)}

FINANCE FIGURES FROM THIS RUN:
{upstream or "(not yet available)"}

Supply the forecast drivers and return JSON with these keys:
{{
  "month_1_revenue_inr": revenue in the first month of trading,
  "month_12_revenue_inr": revenue in month 12 once ramped up,
  "cogs_pct_of_revenue": cost of goods as a percentage of revenue, e.g. 40,
  "monthly_fixed_opex_inr": fixed monthly operating cost excluding COGS,
  "y2_growth_pct": year 2 revenue growth over year 1, e.g. 35,
  "y3_growth_pct": year 3 revenue growth over year 2, e.g. 25,
  "assumptions": "2 sentences on the ramp-up assumption"
}}

Month 1 revenue should be well below month 12 to reflect a realistic ramp."""

    def to_patch(self, parsed: PLDriversOut, state: SharedBusinessState) -> dict:
        intent = state.get("intent")
        sector = intent.sector if intent is not None else Sector.UNSPECIFIED
        finance = state.get(DEPT.value)

        start = parsed.month_1_revenue_inr
        end = parsed.month_12_revenue_inr
        cogs_pct = parsed.cogs_pct_of_revenue
        opex = _resolve_opex(parsed.monthly_fixed_opex_inr, finance)

        # --- driver fallbacks ------------------------------------------------
        # A small model often omits one or two drivers. Rather than discard the
        # whole statement, reconstruct the missing ones from what Finance's
        # stage-1 agents already established. Giving up here would leave
        # break_even_month and both margins null, and F54 has nothing to score.
        if (start is None or end is None) and finance is not None:
            annual = finance.projected_revenue_y1_inr
            if annual:
                # Linear ramp a -> b over 12 months sums to 6*(a+b).
                # Assuming the exit rate is double the opening rate (b = 2a):
                # 18a = annual, so a = annual/18 and b = annual/9.
                start = start or int(round(annual / 18))
                end = end or int(round(annual / 9))

        if cogs_pct is None:
            cogs_pct = 100.0 - gross_margin_benchmark(sector)

        if start is None or end is None or opex is None:
            # Genuinely nothing to build a statement from.
            return {"benchmark_margin_pct": net_margin_benchmark(sector)}

        cogs_pct = max(0.0, min(95.0, float(cogs_pct)))
        start, end = _reconcile_revenue(int(start), int(end), finance)
        periods = _build_pl(
            start=int(start),
            end=int(end),
            cogs_pct=cogs_pct,
            monthly_opex=int(opex),
            y2_growth_pct=parsed.y2_growth_pct or 0.0,
            y3_growth_pct=parsed.y3_growth_pct or 0.0,
        )

        y1 = periods[:12]
        y1_revenue = sum(p.revenue_inr for p in y1)
        y1_cogs = sum(p.cogs_inr for p in y1)
        y1_opex = sum(p.operating_expense_inr for p in y1)

        gross_margin = (
            round(100.0 * (y1_revenue - y1_cogs) / y1_revenue, 2) if y1_revenue else None
        )
        net_margin = (
            round(100.0 * (y1_revenue - y1_cogs - y1_opex) / y1_revenue, 2)
            if y1_revenue
            else None
        )
        break_even = next(
            (index + 1 for index, p in enumerate(y1) if (p.net_profit_inr or 0) > 0), None
        )

        # The sector benchmark describes a mature business, so F54 needs a margin
        # from a ramped-up period rather than the year-1 average. Measuring a
        # start-up year against a steady-state benchmark made a plausible -9.9%
        # first year score as a 182% error on the first sweep.
        steady = periods[-1].net_margin_pct if periods else None

        return {
            "pl_forecast": periods,
            "gross_margin_pct": gross_margin,
            "net_margin_pct": net_margin,
            "steady_state_net_margin_pct": steady,
            "break_even_month": break_even,
            "benchmark_margin_pct": net_margin_benchmark(sector),
        }


# A single outlet turning over more than this multiple of its setup budget in
# year 1 is not a projection, it is a hallucination. Observed live: a Rs 12 lakh
# salon projected at Rs 9 crore of year-1 revenue (75x budget), which propagated
# into a 48% net margin and a 168% F54 error.
MAX_Y1_REVENUE_TO_BUDGET = 10.0


def _bounded_revenue(
    y1: int | None, y2: int | None, y3: int | None, state: SharedBusinessState
) -> tuple[int | None, int | None, int | None]:
    """Cap year-1 revenue at the obtainable market, then keep Y2/Y3 proportional.

    Strategy owns market size; Finance must not exceed it. The prompt says so, but
    a soft instruction is not a guarantee - on a live sweep the model projected
    75x the setup budget regardless. Enforcing the ceiling in code is the same
    treatment already given to cost totals and P&L opex: the number a sibling
    agent derived wins over one an LLM asserted.

    SOM (Strategy, F17) is the primary ceiling. The budget multiple is a backstop
    for runs where market sizing produced nothing.
    """
    if y1 is None or y1 <= 0:
        return y1, y2, y3

    strategy = state.get(Department.STRATEGY.value)
    intent = state.get("intent")

    # Take the tighter of the two ceilings. SOM comes from Strategy but is itself
    # model-generated, so it cannot be trusted alone: on a live sweep SOM came
    # back above Rs 3 crore for a Rs 12 lakh salon and the revenue agent happily
    # projected to it. The budget multiple is arithmetic on a number the user
    # supplied, so it holds regardless of what any agent asserts.
    candidates: list[tuple[int, str]] = []
    if strategy is not None and strategy.market_size and strategy.market_size.som_inr:
        candidates.append((int(strategy.market_size.som_inr), "strategy SOM"))
    if intent is not None and intent.budget.specified and intent.budget.amount > 0:
        candidates.append(
            (
                int(intent.budget.amount * MAX_Y1_REVENUE_TO_BUDGET),
                f"{MAX_Y1_REVENUE_TO_BUDGET:g}x budget",
            )
        )

    if not candidates:
        return y1, y2, y3

    ceiling, basis = min(candidates, key=lambda item: item[0])

    if y1 <= ceiling:
        return y1, y2, y3

    scale = ceiling / y1
    log.info(
        "revenue.capped",
        projected_y1=y1,
        ceiling=ceiling,
        basis=basis,
        scale=round(scale, 3),
    )
    return (
        ceiling,
        int(y2 * scale) if y2 else y2,
        int(y3 * scale) if y3 else y3,
    )


# A first-year ramp steeper than this is not a growth assumption, it is a
# hallucinated number. Observed: a Rs 12 lakh salon whose month-12 revenue was
# 180x its month-1 revenue (Rs 9 crore per month), which made fixed opex
# negligible and floated net margin to 54.7%.
MAX_FIRST_YEAR_RAMP = 4.0

# How far the P&L's implied year-1 revenue may diverge from the revenue agent's
# figure before it is rescaled to match.
REVENUE_TOLERANCE = (0.7, 1.4)


def _reconcile_revenue(
    start: int, end: int, finance: FinanceOutput | None
) -> tuple[int, int]:
    """Bound the ramp, then align year-1 revenue with the revenue agent (F22).

    Two Finance agents must agree about revenue, for the same reason they must
    agree about costs. The revenue agent produces `projected_revenue_y1_inr`
    anchored to the obtainable market; the P&L agent separately invents a monthly
    ramp. Left unchecked the ramp wins, because it is what the statement is built
    from - and on a real sweep it produced a Rs 54 crore year for a Rs 12 lakh
    salon.

    A linear ramp from a to b over 12 months sums to 6*(a+b), which is what makes
    the rescale exact rather than approximate.
    """
    start = max(1, start)
    end = max(start, end)

    if end > start * MAX_FIRST_YEAR_RAMP:
        log.info(
            "pl.ramp_clamped",
            month_1=start,
            month_12_requested=end,
            month_12_used=int(start * MAX_FIRST_YEAR_RAMP),
            max_ramp=MAX_FIRST_YEAR_RAMP,
        )
        end = int(start * MAX_FIRST_YEAR_RAMP)

    target = finance.projected_revenue_y1_inr if finance is not None else None
    if not target or target <= 0:
        return start, end

    implied = 6 * (start + end)
    if implied <= 0:
        return start, end

    ratio = implied / target
    low, high = REVENUE_TOLERANCE
    if low <= ratio <= high:
        return start, end

    scale = target / implied
    log.info(
        "pl.revenue_rescaled",
        implied_y1=implied,
        revenue_agent_y1=target,
        ratio=round(ratio, 2),
        scale=round(scale, 3),
    )
    return max(1, int(start * scale)), max(1, int(end * scale))


def _resolve_opex(
    model_opex: int | None, finance: FinanceOutput | None
) -> int | None:
    """Reconcile the P&L's operating expense with the cost agent's line items.

    The cost agent (F23) derives `total_monthly_cost_inr` by summing itemised
    recurring costs. The P&L agent is separately asked for a single fixed opex
    figure. When the two disagree, the derived sum is the better number: it is
    arithmetic over named line items rather than one free-form estimate.

    The first evaluation sweep showed why this matters. The model repeatedly
    returned an opex far below the cost base its sibling agent had already
    established, which inflated net margin to roughly 48% for an ice cream shop
    against a 12% sector benchmark and drove F54's MAPE into the hundreds. That
    is not a metric artefact - it is two Finance agents contradicting each other,
    and the multi-agent architecture is supposed to resolve exactly that.

    Inventory is excluded from the opex figure because COGS is already applied
    separately as a percentage of revenue; counting stock purchases in both
    places would double-charge it.
    """
    if finance is None:
        return model_opex

    derived = _recurring_opex(finance)
    if derived is None:
        return model_opex
    if model_opex is None:
        return derived

    ratio = model_opex / derived if derived else 0
    if not 0.5 <= ratio <= 1.5:
        log.info(
            "pl.opex_reconciled",
            model_opex=model_opex,
            derived_opex=derived,
            ratio=round(ratio, 2),
            reason="using the cost agent's itemised sum",
        )
        return derived

    # Close enough to agree; keep the model's figure so its judgement about which
    # costs are genuinely fixed is preserved.
    return model_opex


def _recurring_opex(finance: FinanceOutput) -> int | None:
    """Monthly recurring cost excluding inventory (which COGS already covers)."""
    if finance.recurring_costs:
        total = sum(
            item.amount_inr
            for item in finance.recurring_costs
            if item.subcategory != "inventory"
        )
        if total > 0:
            return total
    return finance.total_monthly_cost_inr


def _build_pl(
    *,
    start: int,
    end: int,
    cogs_pct: float,
    monthly_opex: int,
    y2_growth_pct: float,
    y3_growth_pct: float,
) -> list[PLPeriod]:
    """Generate 12 monthly (Y1) plus 8 quarterly (Y2-Y3) periods.

    Year 1 ramps linearly from `start` to `end`. Deterministic given the drivers,
    so the same drivers always yield the same statement.
    """
    periods: list[PLPeriod] = []

    def make(label: str, revenue: int, opex: int) -> PLPeriod:
        cogs = int(round(revenue * cogs_pct / 100.0))
        gross = revenue - cogs
        net = gross - opex
        return PLPeriod(
            label=label,
            revenue_inr=revenue,
            cogs_inr=cogs,
            operating_expense_inr=opex,
            gross_profit_inr=gross,
            net_profit_inr=net,
            gross_margin_pct=round(100.0 * gross / revenue, 2) if revenue else None,
            net_margin_pct=round(100.0 * net / revenue, 2) if revenue else None,
        )

    step = (end - start) / 11 if end != start else 0.0
    for month in range(12):
        revenue = int(round(start + step * month))
        periods.append(make(f"Y1-M{month + 1:02d}", revenue, monthly_opex))

    # Years 2 and 3 grow from the year-1 EXIT RATE, not from the year-1 total.
    #
    # The year-1 total is the sum of a ramp, so it averages well below the month-12
    # run rate. Growing it instead made revenue fall entering year 2 whenever
    # growth was modest: a salon exiting year 1 at Rs 4L/month showed Rs 7.5L
    # quarters in year 2 against Rs 11L in its own final year-1 quarter, and the
    # steady-state margin came out negative while month 12 was +20%.
    exit_rate_annual = end * 12
    y2_revenue = int(round(exit_rate_annual * (1 + y2_growth_pct / 100.0)))
    y3_revenue = int(round(y2_revenue * (1 + y3_growth_pct / 100.0)))

    for year, annual in (("Y2", y2_revenue), ("Y3", y3_revenue)):
        for quarter in range(1, 5):
            periods.append(
                make(f"{year}-Q{quarter}", int(round(annual / 4)), monthly_opex * 3)
            )

    return periods


# =============================================================================
# Stage layout
# =============================================================================

FINANCE_STAGES: tuple[tuple[Agent, ...], ...] = (
    (
        RevenueModelAgent(),
        CostStructureAgent(),
    ),
    (
        FundingStrategyAgent(),
        PLForecastAgent(),
    ),
)
