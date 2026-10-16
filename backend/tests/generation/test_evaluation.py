"""Tests for F53-F58 - baseline and metrics.

Offline. The metrics are pure functions over state, and the baseline is exercised
against a scripted client.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

# Research / evaluation harness — not the deployed app. Skipped by default;
# run with:  pytest -m research
pytestmark = pytest.mark.research

from app.generation.config import settings
from app.generation.agents.benchmarks import (
    BENCHMARKS,
    UNSOURCED,
    MarginBenchmark,
    all_sourced,
    load_benchmarks_csv,
    net_margin_benchmark,
    unsourced_sectors,
)
from app.generation.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.generation.llm.chain import LLMClient
from app.generation.models.departments import (
    FinanceOutput,
    MarketingOutput,
    OperationsOutput,
    StrategyOutput,
)
from app.generation.models.intent import Budget, BusinessIntent, Location, Sector
from app.generation.models.state import Department, RunStatus, new_state
from evaluation.baseline import BaselineOutput, generate_baseline
from evaluation.harness import ALL_ARMS, load_prompts
from evaluation.metrics import (
    COMPETITOR_COVERAGE,
    CONSISTENCY,
    FINANCIAL_ACCURACY,
    LOWER_IS_BETTER,
    PLAN_COMPLETENESS,
    benchmark_caveat,
    competitor_coverage,
    consistency,
    financial_accuracy,
    plan_completeness,
    routing_efficiency,
    score_state,
)


def intent_for(sector: Sector = Sector.FOOD_AND_BEVERAGE, budget: int = 1_500_000):
    return BusinessIntent(
        business_type="ice_cream_shop",
        business_type_label="Ice Cream Shop",
        sector=sector,
        location=Location(area="Andheri West"),
        budget=Budget(amount=budget, specified=True),
    )


def state_with(**sections):
    state = new_state("s1", "Ice cream shop in Andheri West, Rs 15L budget")
    state["intent"] = sections.pop("intent", intent_for())
    for key, value in sections.items():
        state[key] = value
    state["metadata"].active_departments = list(Department)
    return state


# =============================================================================
# Benchmark provenance
# =============================================================================


def test_shipped_benchmarks_are_marked_unsourced() -> None:
    """F54 divides by these; a reader must be able to tell they are estimates."""
    assert all_sourced() is False
    assert len(unsourced_sectors()) == len(BENCHMARKS)


def test_benchmark_caveat_is_emitted_while_unsourced() -> None:
    caveat = benchmark_caveat()
    assert caveat is not None
    assert "PROVISIONAL" in caveat


def test_sourced_benchmark_clears_the_caveat(monkeypatch) -> None:
    cited = {
        sector: MarginBenchmark(sector, b.gross_margin_pct, b.net_margin_pct, "MSME AR 2024 T4.2")
        for sector, b in BENCHMARKS.items()
    }
    monkeypatch.setattr("app.generation.agents.benchmarks.BENCHMARKS", cited)
    assert all_sourced() is True
    assert benchmark_caveat() is None


def test_load_benchmarks_csv_applies_cited_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.generation.agents.benchmarks.BENCHMARKS", dict(BENCHMARKS))
    path = tmp_path / "benchmarks.csv"
    path.write_text(
        "sector,gross_margin_pct,net_margin_pct,source\n"
        "food_and_beverage,62.0,9.5,\"MSME Annual Report 2023-24 Table 4.2\"\n"
        "not_a_sector,10,10,x\n"
        "retail,bad,8.0,y\n",
        encoding="utf-8",
    )

    applied = load_benchmarks_csv(path)
    assert applied == 1  # bad sector and bad number skipped, run continues


def test_load_benchmarks_csv_missing_file_is_not_an_error(tmp_path) -> None:
    assert load_benchmarks_csv(tmp_path / "absent.csv") == 0


def test_empty_source_column_stays_unsourced(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.generation.agents.benchmarks.BENCHMARKS", dict(BENCHMARKS))
    path = tmp_path / "b.csv"
    path.write_text(
        "sector,gross_margin_pct,net_margin_pct,source\nretail,30,8,\n", encoding="utf-8"
    )
    load_benchmarks_csv(path)
    from app.generation.agents.benchmarks import BENCHMARKS as live

    assert live[Sector.RETAIL].source == UNSOURCED
    assert live[Sector.RETAIL].sourced is False


# =============================================================================
# F54 - financial accuracy
# =============================================================================


def test_mape_is_zero_when_margin_matches_benchmark() -> None:
    expected = net_margin_benchmark(Sector.FOOD_AND_BEVERAGE)
    state = state_with(finance=FinanceOutput(net_margin_pct=expected))

    result = financial_accuracy(state)
    assert result.score == 0.0
    assert result.details["benchmark_sourced"] is False


def test_mape_computed_by_hand() -> None:
    """Benchmark 12%, projected 18% -> |18-12|/12*100 = 50%."""
    state = state_with(finance=FinanceOutput(net_margin_pct=18.0))
    assert financial_accuracy(state).score == 50.0


def test_mape_is_symmetric_in_direction() -> None:
    """Under- and over-shooting by the same amount score the same error."""
    over = financial_accuracy(state_with(finance=FinanceOutput(net_margin_pct=18.0))).score
    under = financial_accuracy(state_with(finance=FinanceOutput(net_margin_pct=6.0))).score
    assert over == under == 50.0


def test_missing_margin_is_not_scored_as_maximum_error() -> None:
    """Absence is F56's business. Scoring it here would double-count it."""
    result = financial_accuracy(state_with(finance=FinanceOutput()))
    assert result.applicable is False
    assert result.score is None
    assert "F56" in result.reason


def test_mape_uses_the_prompt_sector() -> None:
    state = state_with(
        intent=intent_for(Sector.MANUFACTURING), finance=FinanceOutput(net_margin_pct=9.0)
    )
    result = financial_accuracy(state)
    assert result.details["sector"] == "manufacturing"
    assert result.score == 0.0  # manufacturing benchmark is 9%


def test_mape_is_lower_is_better() -> None:
    assert FINANCIAL_ACCURACY in LOWER_IS_BETTER
    assert PLAN_COMPLETENESS not in LOWER_IS_BETTER


def test_mape_prefers_the_steady_state_margin() -> None:
    """Sector benchmarks describe mature businesses. The first sweep scored a
    year-1 margin of -9.88% against a +12% benchmark as a 182% error, when a small
    first-year loss is a plausible outcome - an apples-to-oranges comparison."""
    state = state_with(
        finance=FinanceOutput(net_margin_pct=-9.88, steady_state_net_margin_pct=7.87)
    )
    result = financial_accuracy(state)

    assert result.details["margin_basis"] == "steady_state"
    assert result.details["projected_net_margin_pct"] == 7.87
    assert result.details["year_1_net_margin_pct"] == -9.88
    # |7.87 - 12| / 12 * 100
    assert result.score == pytest.approx(34.42, abs=0.01)


def test_mape_falls_back_to_year_one_when_no_steady_state() -> None:
    """The single-LLM baseline reports one margin without distinguishing, so the
    basis must be recorded rather than assumed identical across arms."""
    state = state_with(finance=FinanceOutput(net_margin_pct=18.0))
    result = financial_accuracy(state)

    assert result.details["margin_basis"] == "year_1_average"
    assert result.score == 50.0


def test_mape_not_applicable_without_a_finance_section() -> None:
    result = financial_accuracy(state_with())
    assert result.applicable is False


# =============================================================================
# F55 - competitor coverage
# =============================================================================


def test_coverage_requires_ground_truth() -> None:
    """Scoring against the model's own output would be circular."""
    state = state_with(strategy=StrategyOutput(competitors=[{"name": "Naturals"}]))
    result = competitor_coverage(state, None)
    assert result.applicable is False
    assert "ground truth" in result.reason


def test_full_coverage() -> None:
    state = state_with(
        strategy=StrategyOutput(
            competitors=[
                {"name": "Naturals Ice Cream", "source": "google_places"},
                {"name": "Baskin Robbins", "source": "google_places"},
            ]
        )
    )
    result = competitor_coverage(state, ["Naturals", "Baskin Robbins"])
    assert result.score == 100.0
    assert result.details["grounded"] is True


def test_partial_coverage_computed_by_hand() -> None:
    """Found 1 of 4 real businesses -> 25%."""
    state = state_with(strategy=StrategyOutput(competitors=[{"name": "Naturals"}]))
    result = competitor_coverage(state, ["Naturals", "Apsara", "Snowbite", "Gokul"])
    assert result.score == 25.0
    assert result.details["matched"] == ["Naturals"]


def test_coverage_tolerates_name_variants() -> None:
    state = state_with(strategy=StrategyOutput(competitors=[{"name": "Naturals Ice Cream"}]))
    assert competitor_coverage(state, ["Naturals"]).score == 100.0


def test_coverage_does_not_match_unrelated_names() -> None:
    state = state_with(strategy=StrategyOutput(competitors=[{"name": "Cold Stone Creamery"}]))
    assert competitor_coverage(state, ["Apsara Ice Creams"]).score == 0.0


def test_coverage_records_the_rq3_arm() -> None:
    grounded = state_with(
        strategy=StrategyOutput(competitors=[{"name": "Naturals", "source": "openstreetmap"}])
    )
    text_only = state_with(
        strategy=StrategyOutput(competitors=[{"name": "Naturals", "source": "llm_inferred"}])
    )
    assert competitor_coverage(grounded, ["Naturals"]).details["grounded"] is True
    assert competitor_coverage(text_only, ["Naturals"]).details["grounded"] is False


def test_zero_coverage_when_nothing_found() -> None:
    result = competitor_coverage(state_with(strategy=StrategyOutput()), ["Naturals"])
    assert result.score == 0.0
    assert result.applicable is True


# =============================================================================
# F56 - plan completeness
# =============================================================================


def test_completeness_scores_only_active_departments() -> None:
    """A skipped department must not count against the run."""
    state = state_with(strategy=StrategyOutput(executive_summary="A" * 40))
    state["metadata"].active_departments = [Department.STRATEGY]

    result = plan_completeness(state)
    assert result.details["expected_count"] == 6
    assert result.details["scored_departments"] == ["strategy"]


def test_completeness_defaults_to_all_departments() -> None:
    state = state_with(strategy=StrategyOutput())
    state["metadata"].active_departments = []
    assert plan_completeness(state).details["expected_count"] == 26


# =============================================================================
# F57 - consistency
# =============================================================================


def test_consistency_all_checks_pass() -> None:
    state = state_with(
        strategy=StrategyOutput(market_size={"som_inr": 10_000_000}),
        finance=FinanceOutput(
            projected_revenue_y1_inr=6_000_000,
            total_setup_cost_inr=1_200_000,
            total_monthly_cost_inr=300_000,
            gross_margin_pct=60.0,
            net_margin_pct=18.0,
        ),
        marketing=MarketingOutput(total_marketing_budget_inr=60_000),
        operations=OperationsOutput(total_monthly_payroll_inr=150_000),
    )
    result = consistency(state)
    assert result.score == 100.0
    assert result.details["failures"] == []


def test_consistency_catches_revenue_above_som() -> None:
    state = state_with(
        strategy=StrategyOutput(market_size={"som_inr": 1_000_000}),
        finance=FinanceOutput(projected_revenue_y1_inr=9_000_000),
    )
    result = consistency(state)
    assert result.score == 0.0
    assert result.details["failures"][0]["check"] == "revenue_within_som"


def test_consistency_catches_budget_overshoot() -> None:
    state = state_with(finance=FinanceOutput(total_setup_cost_inr=2_000_000))
    failures = [f["check"] for f in consistency(state).details["failures"]]
    assert "setup_within_budget" in failures


def test_consistency_catches_workflow_owner_not_in_staffing() -> None:
    """The staged sub-graph exists to prevent exactly this."""
    state = state_with(
        operations=OperationsOutput(
            roles=[{"title": "Store manager", "headcount": 1}],
            daily_workflow=[
                {"order": 1, "name": "Open", "owner_role": "Chief Robot Officer"}
            ],
        )
    )
    failures = [f["check"] for f in consistency(state).details["failures"]]
    assert "workflow_owners_are_real_roles" in failures


def test_consistency_accepts_matching_workflow_owner() -> None:
    state = state_with(
        operations=OperationsOutput(
            roles=[{"title": "Store manager", "headcount": 1}],
            daily_workflow=[{"order": 1, "name": "Open", "owner_role": "Store manager"}],
        )
    )
    assert consistency(state).score == 100.0


def test_consistency_catches_channel_shares_not_summing() -> None:
    state = state_with(
        marketing=MarketingOutput(
            channels=[
                {"name": "Instagram", "budget_share_pct": 40},
                {"name": "Google", "budget_share_pct": 20},
            ]
        )
    )
    failures = [f["check"] for f in consistency(state).details["failures"]]
    assert "channel_shares_sum_to_100" in failures


def test_consistency_partial_score_computed_by_hand() -> None:
    """2 of 3 applicable checks pass -> 66.67%."""
    state = state_with(
        finance=FinanceOutput(
            total_setup_cost_inr=1_200_000,   # within budget: pass
            total_monthly_cost_inr=200_000,
            gross_margin_pct=60.0,
            net_margin_pct=80.0,             # net above gross: fail
        ),
        marketing=MarketingOutput(total_marketing_budget_inr=50_000),  # within cost: pass
    )
    result = consistency(state)
    assert result.details["checks_applicable"] == 3
    assert result.score == pytest.approx(66.67, abs=0.01)


def test_consistency_catches_pl_opex_disagreeing_with_cost_structure() -> None:
    """Surfaced by the first sweep: the P&L agent used an opex far below the cost
    agent's monthly total, inflating net margin and wrecking F54."""
    state = state_with(
        finance=FinanceOutput(
            total_monthly_cost_inr=330_000,
            pl_forecast=[
                {"label": "Y1-M01", "revenue_inr": 400_000, "operating_expense_inr": 50_000}
            ],
        )
    )
    failures = [f["check"] for f in consistency(state).details["failures"]]
    assert "pl_opex_matches_cost_structure" in failures


def test_consistency_accepts_matching_pl_opex() -> None:
    state = state_with(
        finance=FinanceOutput(
            total_monthly_cost_inr=330_000,
            pl_forecast=[
                {"label": "Y1-M01", "revenue_inr": 400_000, "operating_expense_inr": 320_000}
            ],
        )
    )
    failures = [f["check"] for f in consistency(state).details["failures"]]
    assert "pl_opex_matches_cost_structure" not in failures


def test_consistency_not_applicable_on_empty_state() -> None:
    result = consistency(new_state("s", "prompt"))
    assert result.applicable is False


# =============================================================================
# F58 - routing efficiency
# =============================================================================


def build_run(tokens: int, duration_ms: int, skipped: list[Department]):
    from app.generation.models.state import AgentTrace

    state = state_with(strategy=StrategyOutput(executive_summary="A" * 40))
    state["agent_traces"] = [
        AgentTrace(
            agent_id="a",
            department=Department.STRATEGY,
            prompt_tokens=tokens,
            completion_tokens=0,
        )
    ]
    metadata = state["metadata"]
    metadata.total_duration_ms = duration_ms
    metadata.skipped_departments = skipped
    metadata.active_departments = [d for d in Department if d not in skipped]
    metadata.status = RunStatus.COMPLETED
    metadata.completed_at = datetime.now(UTC).isoformat()
    return state


def test_routing_saving_computed_by_hand() -> None:
    """8000 vs 10000 tokens -> 20% saving; 9s vs 12s -> 25% time saving."""
    dynamic = build_run(8000, 9000, [Department.OPERATIONS])
    control = build_run(10000, 12000, [])

    result = routing_efficiency(dynamic, control)
    assert result.score == 20.0
    assert result.details["time_saving_pct"] == 25.0
    assert result.details["routing_actually_skipped"] is True


def test_routing_zero_saving_when_nothing_skipped() -> None:
    """A physical business routes identically in both arms; zero is correct."""
    dynamic = build_run(10000, 10000, [])
    control = build_run(10000, 10000, [])

    result = routing_efficiency(dynamic, control)
    assert result.score == 0.0
    assert result.details["routing_actually_skipped"] is False


def test_routing_reports_quality_delta_alongside_saving() -> None:
    """RQ2 needs both: a saving is only meaningful if quality holds."""
    dynamic = build_run(8000, 9000, [Department.OPERATIONS])
    control = build_run(10000, 12000, [])

    details = routing_efficiency(dynamic, control).details
    assert "quality_delta_pp" in details
    assert details["dynamic_completeness"] is not None


def test_routing_not_applicable_without_control_tokens() -> None:
    dynamic = build_run(8000, 9000, [Department.OPERATIONS])
    control = build_run(0, 0, [])
    assert routing_efficiency(dynamic, control).applicable is False


# =============================================================================
# Batch scoring
# =============================================================================


def test_score_state_returns_all_four_metrics() -> None:
    results = score_state(state_with(finance=FinanceOutput(net_margin_pct=12.0)))
    assert [r.metric for r in results] == [
        FINANCIAL_ACCURACY,
        COMPETITOR_COVERAGE,
        PLAN_COMPLETENESS,
        CONSISTENCY,
    ]


def test_score_state_never_raises_on_empty_state() -> None:
    """Completeness of an empty plan is genuinely 0%, so it IS scored. The other
    three are not applicable, because "said nothing" is not the same as "said
    something wrong" and only F56 should penalise absence."""
    results = {r.metric: r for r in score_state(new_state("s", "prompt"))}

    assert len(results) == 4
    assert results[PLAN_COMPLETENESS].score == 0.0
    assert results[PLAN_COMPLETENESS].recorded is True
    assert results[FINANCIAL_ACCURACY].applicable is False
    assert results[COMPETITOR_COVERAGE].applicable is False
    assert results[CONSISTENCY].applicable is False


# =============================================================================
# F53 - baseline
# =============================================================================


BASELINE_PAYLOAD = {
    "executive_summary": "A premium gelato outlet in Andheri West for young families.",
    "vision": "Mumbai's favourite gelato.",
    "mission": "Fresh desserts daily.",
    "business_model_type": "B2C retail",
    "value_proposition": "Small-batch gelato with a sugar-free line.",
    "tam_inr": 24000000000,
    "sam_inr": 480000000,
    "som_inr": 4500000,
    "market_overview": "Mumbai frozen dessert demand is growing among young families.",
    "market_statistics": ["14% CAGR"],
    "industry_growth_rate_pct": 14.0,
    "competitors": [{"name": "Naturals", "rating": 4.4, "price_level": 2}],
    "market_gaps": ["no sugar-free range"],
    "positioning": "Premium artisanal.",
    "location_score": 14.0,
    "location_rationale": "High footfall near the metro station.",
    "risks": [{"category": "regulatory", "description": "FSSAI delay", "severity": "high", "likelihood": "medium", "mitigation": "apply early"}],
    "revenue_streams": [{"name": "Dine-in", "monthly_estimate_inr": 400000, "share_pct": 65}],
    "pricing_strategy": "Scoops at INR 120.",
    "projected_revenue_y1_inr": 7000000,
    "projected_revenue_y2_inr": 9500000,
    "projected_revenue_y3_inr": 12000000,
    "setup_costs": [{"name": "Deposit", "subcategory": "deposit", "amount_inr": 450000}],
    "recurring_costs": [{"name": "Rent", "subcategory": "made_up", "amount_inr": 75000}],
    "total_setup_cost_inr": 1400000,
    "total_monthly_cost_inr": 190000,
    "funding_approach": "Bootstrap plus a Mudra loan.",
    "funding_schemes": ["PMMY Mudra Tarun"],
    "gross_margin_pct": 60.0,
    "net_margin_pct": 18.0,
    "break_even_month": 4,
    "recommended_name": "Barfi & Co",
    "personality_traits": ["playful", "premium"],
    "primary_hex": "#F2C4D0",
    "taglines": ["Small batch, big joy"],
    "logo_style": "Combination mark",
    "channels": [{"name": "Instagram", "budget_share_pct": 100, "primary_kpi": "reach"}],
    "personas": [{"name": "Ananya", "age_range": "30-38", "occupation": "manager"}],
    "campaign_phases": [{"phase": "launch", "day_range": "Day 1-30", "objective": "trial", "activities": ["offer"]}],
    "target_keywords": ["gelato andheri"],
    "content_topics": ["gelato vs ice cream"],
    "vendors": [{"category": "Dairy", "supplies": "milk", "sourcing_type": "local"}],
    "roles": [{"title": "Store manager", "headcount": 1, "monthly_salary_inr": 35000}],
    "tools": [{"name": "Petpooja", "purpose": "POS", "cost": "paid"}],
    "daily_workflow": [{"order": 2, "name": "Serve"}, {"order": 1, "name": "Open"}],
}

INTENT_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri West",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}


class SequencedProvider(LLMProvider):
    """Answers the intent call first, then the baseline call."""

    def __init__(self, fail: bool = False) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self._fail = fail
        self.calls = 0
        self.last_request: LLMRequest | None = None

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-3.6-flash"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.last_request = request
        if self.calls == 1:
            payload = INTENT_PAYLOAD
        elif self._fail:
            raise ProviderUnavailable("baseline model unavailable")
        else:
            payload = BASELINE_PAYLOAD
        return LLMResponse(
            text=json.dumps(payload),
            provider=self.name,
            model="gemini-3.6-flash",
            prompt_tokens=200,
            completion_tokens=1800,
        )


def scripted_client(fail: bool = False) -> LLMClient:
    class Dead(LLMProvider):
        def __init__(self, name):
            self.name = name
            self.tracker = FreeTierTracker(name=name.value)

        def model_for(self, tier):
            return "dead"

        async def is_available(self):
            return False

        async def complete(self, request):
            raise ProviderUnavailable("dead")

    return LLMClient(
        groq=Dead(ProviderName.GROQ),
        gemini=SequencedProvider(fail),
        ollama=Dead(ProviderName.OLLAMA),
    )


@pytest.mark.asyncio
async def test_baseline_populates_all_five_departments() -> None:
    state = await generate_baseline(
        "Ice cream shop in Andheri West, Rs 15L budget", client=scripted_client()
    )

    for department in Department:
        assert state.get(department.value) is not None, department.value
    assert state["metadata"].status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_baseline_is_scored_over_all_departments() -> None:
    """Otherwise it would get a smaller denominator than the multi-agent arm."""
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client())
    assert state["metadata"].active_departments == list(Department)
    assert plan_completeness(state).details["expected_count"] == 26


@pytest.mark.asyncio
async def test_baseline_marks_competitors_as_llm_inferred() -> None:
    """The baseline has no grounding, so F55 must see it as the text-only arm."""
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client())
    assert all(c.source == "llm_inferred" for c in state["strategy"].competitors)


@pytest.mark.asyncio
async def test_baseline_applies_the_same_coercions_as_agents() -> None:
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client())

    assert state["strategy"].location_score == 10.0  # 14.0 clamped
    assert state["finance"].recurring_costs[0].subcategory == "other"  # invalid coerced
    assert [s.name for s in state["operations"].daily_workflow] == ["Open", "Serve"]  # sorted


@pytest.mark.asyncio
async def test_baseline_is_scorable_by_every_metric() -> None:
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client())
    results = {r.metric: r for r in score_state(state, ["Naturals"])}

    assert results[FINANCIAL_ACCURACY].recorded
    assert results[COMPETITOR_COVERAGE].score == 100.0
    assert results[PLAN_COMPLETENESS].recorded
    assert results[CONSISTENCY].recorded


@pytest.mark.asyncio
async def test_baseline_failure_is_a_data_point_not_a_crash() -> None:
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client(fail=True))

    assert state["metadata"].status is RunStatus.FAILED
    assert state["metadata"].completeness_score == 0.0
    assert state["agent_traces"][0].status == "failed"


def test_baseline_schema_covers_the_completeness_checklist() -> None:
    """Every field F56 looks for must be requestable from the baseline, or the
    comparison would penalise it for something it was never asked to produce."""
    from app.generation.orchestrator.completeness import EXPECTED_FIELDS

    baseline_fields = set(BaselineOutput.model_fields)
    aliases = {
        "market_size": "tam_inr",
        "color_palette": "primary_hex",
        "pl_forecast": "projected_revenue_y1_inr",
        "content_frequency": "content_topics",
        "inventory_requirements": "vendors",
        "total_headcount_y1": "roles",
    }
    for fields in EXPECTED_FIELDS.values():
        for field in fields:
            assert field in baseline_fields or aliases.get(field) in baseline_fields, field


# =============================================================================
# Baseline bugs found on a live sweep
# =============================================================================


def test_baseline_flattens_department_wrapped_output() -> None:
    """Observed: the model mirrored the prompt's section headers and returned
    {"STRATEGY": {...}, "FINANCE": {...}}. Every field was then missing, and
    because all fields are optional the empty result validated and was reported
    as a completed baseline scoring 0% - a false landslide for RQ1."""
    nested = {
        "STRATEGY": {
            "executive_summary": "A premium gelato outlet in Andheri West.",
            "vision": "Be the go-to dessert stop.",
        },
        "FINANCE": {"total_setup_cost_inr": 1_400_000, "net_margin_pct": 18.0},
        "OPERATIONS": {"daily_workflow": [{"order": 1, "name": "Open store"}]},
    }
    parsed = BaselineOutput.model_validate(nested)

    assert parsed.executive_summary.startswith("A premium")
    assert parsed.total_setup_cost_inr == 1_400_000
    assert parsed.net_margin_pct == 18.0
    assert len(parsed.daily_workflow) == 1


def test_baseline_still_accepts_flat_output() -> None:
    parsed = BaselineOutput.model_validate({"executive_summary": "A" * 40, "net_margin_pct": 12.0})
    assert parsed.executive_summary.startswith("AAAA")
    assert parsed.net_margin_pct == 12.0


@pytest.mark.asyncio
async def test_baseline_pins_its_own_model() -> None:
    """Observed: the baseline ran on Ollama's 3B model while the paper would have
    reported gemini-3.6-flash, because the request walked the normal chain."""
    provider = SequencedProvider()

    class Dead(LLMProvider):
        def __init__(self, name):
            self.name = name
            self.tracker = FreeTierTracker(name=name.value)

        def model_for(self, tier):
            return "dead"

        async def is_available(self):
            return False

        async def complete(self, request):
            raise ProviderUnavailable("dead")

    client = LLMClient(
        groq=Dead(ProviderName.GROQ), gemini=provider, ollama=Dead(ProviderName.OLLAMA)
    )
    await generate_baseline("Ice cream shop in Andheri", client=client)

    assert provider.last_request is not None
    assert provider.last_request.model == settings.gemini_baseline_model


@pytest.mark.asyncio
async def test_near_empty_baseline_is_recorded_as_a_failure() -> None:
    """An all-defaults response must not be reported as a completed 0% plan."""

    class EmptyProvider(SequencedProvider):
        async def complete(self, request: LLMRequest) -> LLMResponse:
            self.calls += 1
            payload = INTENT_PAYLOAD if self.calls == 1 else {"vision": "be great"}
            return LLMResponse(
                text=json.dumps(payload),
                provider=self.name,
                model="gemini-3.6-flash",
                prompt_tokens=200,
                completion_tokens=10,
            )

    class Dead(LLMProvider):
        def __init__(self, name):
            self.name = name
            self.tracker = FreeTierTracker(name=name.value)

        def model_for(self, tier):
            return "dead"

        async def is_available(self):
            return False

        async def complete(self, request):
            raise ProviderUnavailable("dead")

    client = LLMClient(
        groq=Dead(ProviderName.GROQ),
        gemini=EmptyProvider(),
        ollama=Dead(ProviderName.OLLAMA),
    )
    state = await generate_baseline("Ice cream shop in Andheri", client=client)

    assert state["metadata"].status is RunStatus.FAILED
    assert "populated fields" in (state["agent_traces"][0].error or "")


@pytest.mark.asyncio
async def test_a_full_baseline_is_not_flagged_empty() -> None:
    state = await generate_baseline("Ice cream shop in Andheri", client=scripted_client())
    assert state["metadata"].status is RunStatus.COMPLETED


def test_llm_request_model_override_is_honoured_by_providers() -> None:
    """The mechanism behind the pinned baseline model."""
    from app.generation.llm.groq_provider import GroqProvider

    provider = GroqProvider()
    request = LLMRequest(prompt="x", tier=ModelTier.FAST, model="pinned-model")
    assert (request.model or provider.model_for(request.tier)) == "pinned-model"

    unpinned = LLMRequest(prompt="x", tier=ModelTier.FAST)
    assert (unpinned.model or provider.model_for(unpinned.tier)) == settings.groq_model_fast


# =============================================================================
# Prompt set
# =============================================================================


def test_prompt_set_has_at_least_thirty_prompts() -> None:
    prompts, _ = load_prompts()
    assert len(prompts) >= 30


def test_prompt_ids_are_unique() -> None:
    prompts, _ = load_prompts()
    ids = [p.id for p in prompts]
    assert len(ids) == len(set(ids))


def test_prompt_set_covers_every_sector() -> None:
    prompts, _ = load_prompts()
    covered = {p.sector for p in prompts}
    expected = {s.value for s in Sector if s is not Sector.UNSPECIFIED}
    assert expected <= covered


def test_prompt_set_includes_digital_businesses_for_rq2() -> None:
    """RQ2 needs prompts where routing can actually skip a department."""
    prompts, _ = load_prompts()
    digital = [p for p in prompts if p.expect_operations is False]
    assert len(digital) >= 5


def test_prompt_set_includes_unspecified_budgets() -> None:
    prompts, _ = load_prompts()
    assert any(p.scale == "unspecified" for p in prompts)


def test_all_arms_declared() -> None:
    assert set(ALL_ARMS) == {"multi_agent", "baseline", "all_departments", "no_grounding"}
