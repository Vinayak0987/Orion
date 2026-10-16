"""Tests for F10-F13 and F16 - Business Orchestrator.

Fully offline. The LLM is faked and department runners are injected, so the DAG
topology, real concurrency, failure isolation and completeness scoring are all
verified without a single network call.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from app.generation.agents.registry import DEPARTMENT_RUNNERS, make_placeholder, register_runner
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
    CostItem,
    FinanceOutput,
    MarketSize,
    StrategyOutput,
)
from app.generation.models.intent import Budget, BusinessIntent, Scale, Sector
from app.generation.models.state import (
    Department,
    RunStatus,
    apply_department_patch,
    new_state,
)
from app.generation.orchestrator.completeness import (
    EXPECTED_FIELDS,
    MIN_SUBSTANTIVE_TEXT_LENGTH,
    TOTAL_EXPECTED_FIELDS,
    detect_contradictions,
    is_substantive,
    minimum_length_for,
    score_completeness,
)
from app.generation.orchestrator.graph import build_graph, describe_graph
from app.generation.orchestrator.progress import ProgressEmitter, ProgressEventType
from app.generation.orchestrator.routing import (
    ALL_DEPARTMENTS,
    STAGE_1,
    STAGE_2,
    resolve_departments,
)
from app.generation.orchestrator.runner import orchestrate, run_summary, total_tokens


# =============================================================================
# Fixtures / fakes
# =============================================================================


@pytest.fixture(autouse=True)
def offline_departments():
    """Swap the 21 real agents for placeholders.

    This file tests orchestration - routing, DAG shape, concurrency, failure
    isolation, scoring. Letting the real agents run would make every test issue
    live LLM calls. Agent behaviour is covered in test_agents.py against a
    scripted client.
    """
    original = dict(DEPARTMENT_RUNNERS)
    for department in Department:
        register_runner(department, make_placeholder(department))
    yield
    for department, runner in original.items():
        register_runner(department, runner)


PHYSICAL_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}

DIGITAL_PAYLOAD = {
    "business_type": "online_tutoring_platform",
    "business_type_label": "Online Tutoring Platform",
    "sector": "education",
    "area": "",
    "city": "",
    "budget_text": "",
    "confidence": 0.85,
}


class ScriptedProvider(LLMProvider):
    def __init__(self, payload: dict) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self._payload = payload

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-1.5-flash"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self._payload),
            provider=self.name,
            model="gemini-1.5-flash",
            prompt_tokens=40,
            completion_tokens=30,
        )


class DeadProvider(LLMProvider):
    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "dead"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable("dead")


def fake_client(payload: dict) -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(payload),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


def physical_intent() -> BusinessIntent:
    return BusinessIntent(
        business_type="ice_cream_shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        budget=Budget(amount=1_500_000, specified=True),
        is_physical=True,
        requires_operations=True,
    )


def digital_intent() -> BusinessIntent:
    return BusinessIntent(
        business_type="online_tutoring_platform",
        sector=Sector.EDUCATION,
        is_physical=False,
        requires_operations=False,
    )


# =============================================================================
# F10 - routing rules
# =============================================================================


def test_physical_business_activates_all_five_departments() -> None:
    decision = resolve_departments(physical_intent())
    assert decision.active == ALL_DEPARTMENTS
    assert decision.skipped == ()
    assert decision.dynamic is True


def test_digital_business_skips_operations() -> None:
    decision = resolve_departments(digital_intent())
    assert Department.OPERATIONS not in decision.active
    assert decision.skipped == (Department.OPERATIONS,)
    assert len(decision.active) == 4
    assert "skipped" in decision.reason


def test_force_all_is_the_rq2_control_arm() -> None:
    decision = resolve_departments(digital_intent(), force_all=True)
    assert decision.active == ALL_DEPARTMENTS
    assert decision.skipped == ()
    assert decision.dynamic is False
    assert "control arm" in decision.reason


def test_disabling_dynamic_routing_via_config(monkeypatch) -> None:
    from app.generation.orchestrator import routing

    monkeypatch.setattr(routing.settings, "enable_dynamic_routing", False)
    decision = resolve_departments(digital_intent())
    assert decision.active == ALL_DEPARTMENTS
    assert decision.dynamic is False


def test_stage_layout_for_physical_business() -> None:
    stages = resolve_departments(physical_intent()).stages
    assert stages == (STAGE_1, STAGE_2, (Department.OPERATIONS,))


def test_stage_layout_drops_empty_third_stage() -> None:
    stages = resolve_departments(digital_intent()).stages
    assert stages == (STAGE_1, STAGE_2)


def test_active_departments_keep_canonical_order() -> None:
    active = resolve_departments(physical_intent()).active
    assert active.index(Department.STRATEGY) == 0
    assert active.index(Department.OPERATIONS) == len(active) - 1


def test_routing_decision_is_immutable() -> None:
    decision = resolve_departments(physical_intent())
    with pytest.raises((AttributeError, TypeError)):
        decision.active = ()  # type: ignore[misc]


# =============================================================================
# F11 - DAG topology
# =============================================================================


def _noop_runner(department: Department):
    async def runner(state):
        return {}

    return runner


def _runners_for(departments) -> dict:
    return {d: _noop_runner(d) for d in departments}


def test_describe_graph_reports_parallel_stage() -> None:
    description = describe_graph(resolve_departments(physical_intent()))
    stages = description["stages"]

    assert stages[0]["departments"] == ["strategy"]
    assert stages[0]["execution"] == "sequential"
    assert set(stages[1]["departments"]) == {"finance", "branding", "marketing"}
    assert stages[1]["execution"] == "parallel"
    assert stages[2]["departments"] == ["operations"]


def test_describe_graph_for_digital_business() -> None:
    description = describe_graph(resolve_departments(digital_intent()))
    assert len(description["stages"]) == 2
    assert description["skipped_departments"] == ["operations"]
    assert description["dynamic_routing"] is True


def test_build_graph_compiles_for_both_topologies() -> None:
    for intent in (physical_intent(), digital_intent()):
        decision = resolve_departments(intent)
        emitter = ProgressEmitter("s", len(decision.active))
        graph = build_graph(decision, emitter, runners=_runners_for(decision.active))
        assert graph is not None


# =============================================================================
# F12 - real parallel execution
# =============================================================================


@pytest.mark.asyncio
async def test_stage_2_departments_run_concurrently() -> None:
    """Evidence for the paper: Finance, Branding and Marketing overlap in time.

    Each runner sleeps 150 ms. Sequential execution would take >=450 ms;
    concurrent execution finishes in roughly 150 ms.
    """
    windows: dict[str, tuple[float, float]] = {}
    sleep_s = 0.15

    def timed_runner(department: Department):
        async def runner(state):
            start = time.perf_counter()
            await asyncio.sleep(sleep_s)
            windows[department.value] = (start, time.perf_counter())
            return {}

        return runner

    decision = resolve_departments(physical_intent())
    emitter = ProgressEmitter("s", len(decision.active))
    graph = build_graph(
        decision, emitter, runners={d: timed_runner(d) for d in decision.active}
    )

    state = new_state("s", "prompt")
    state["intent"] = physical_intent()

    wall_start = time.perf_counter()
    await graph.ainvoke(state)
    wall_ms = (time.perf_counter() - wall_start) * 1000

    stage2 = ["finance", "branding", "marketing"]
    assert all(d in windows for d in stage2)

    # Pairwise overlap proves concurrency.
    for i in range(len(stage2)):
        for j in range(i + 1, len(stage2)):
            a_start, a_end = windows[stage2[i]]
            b_start, b_end = windows[stage2[j]]
            assert a_start < b_end and b_start < a_end, (
                f"{stage2[i]} and {stage2[j]} did not overlap"
            )

    # 5 departments x 150 ms sequential = 750 ms. Three stages = ~450 ms.
    assert wall_ms < 700, f"expected staged concurrency, took {wall_ms:.0f}ms"


@pytest.mark.asyncio
async def test_operations_waits_for_all_of_stage_2() -> None:
    """Operations has three inbound edges, so it is a join barrier (F12)."""
    order: list[str] = []

    def recording_runner(department: Department):
        async def runner(state):
            await asyncio.sleep(0.02)
            order.append(department.value)
            return {}

        return runner

    decision = resolve_departments(physical_intent())
    emitter = ProgressEmitter("s", len(decision.active))
    graph = build_graph(
        decision, emitter, runners={d: recording_runner(d) for d in decision.active}
    )

    state = new_state("s", "prompt")
    state["intent"] = physical_intent()
    await graph.ainvoke(state)

    assert order[0] == "strategy"
    assert order[-1] == "operations"
    assert set(order[1:4]) == {"finance", "branding", "marketing"}


@pytest.mark.asyncio
async def test_parallel_departments_write_disjoint_sections() -> None:
    """Concurrent writes must merge, not collide (F15 + LangGraph reducers)."""

    def writing_runner(department: Department, patch: dict):
        async def runner(state):
            return apply_department_patch(state, department, patch)

        return runner

    decision = resolve_departments(physical_intent())
    emitter = ProgressEmitter("s", len(decision.active))
    runners = {
        Department.STRATEGY: writing_runner(
            Department.STRATEGY, {"executive_summary": "A premium gelato outlet in Andheri."}
        ),
        Department.FINANCE: writing_runner(Department.FINANCE, {"break_even_month": 9}),
        Department.BRANDING: writing_runner(
            Department.BRANDING, {"recommended_name": "Frostbite Gelato"}
        ),
        Department.MARKETING: writing_runner(
            Department.MARKETING, {"content_frequency": "weekly"}
        ),
        Department.OPERATIONS: writing_runner(
            Department.OPERATIONS, {"inventory_approach": "just in time"}
        ),
    }
    graph = build_graph(decision, emitter, runners=runners)

    state = new_state("s", "prompt")
    state["intent"] = physical_intent()
    result = await graph.ainvoke(state)

    assert result["strategy"].executive_summary.startswith("A premium")
    assert result["finance"].break_even_month == 9
    assert result["branding"].recommended_name == "Frostbite Gelato"
    assert result["marketing"].content_frequency == "weekly"
    assert result["operations"].inventory_approach == "just in time"


@pytest.mark.asyncio
async def test_failing_department_does_not_abort_the_run() -> None:
    """F52 - a failed department is isolated; the rest still complete."""

    async def exploding(state):
        raise RuntimeError("Groq exploded")

    decision = resolve_departments(physical_intent())
    emitter = ProgressEmitter("s", len(decision.active))
    runners = _runners_for(decision.active)
    runners[Department.BRANDING] = exploding
    graph = build_graph(decision, emitter, runners=runners)

    state = new_state("s", "prompt")
    state["intent"] = physical_intent()
    result = await graph.ainvoke(state)

    assert any("branding" in e and "Groq exploded" in e for e in result["errors"])
    failed = [t for t in result["agent_traces"] if t.status == "failed"]
    assert len(failed) == 1
    assert failed[0].department is Department.BRANDING
    # The join barrier still fired.
    assert any(
        e.event is ProgressEventType.DEPARTMENT_COMPLETED
        and e.department == "operations"
        for e in emitter.events
    )


@pytest.mark.asyncio
async def test_progress_events_cover_every_department() -> None:
    captured = []

    async def callback(event):
        captured.append(event)

    decision = resolve_departments(physical_intent())
    emitter = ProgressEmitter("s", len(decision.active), callback)
    graph = build_graph(decision, emitter, runners=_runners_for(decision.active))

    state = new_state("s", "prompt")
    state["intent"] = physical_intent()
    await graph.ainvoke(state)

    started = {e.department for e in captured if e.event is ProgressEventType.DEPARTMENT_STARTED}
    completed = {
        e.department for e in captured if e.event is ProgressEventType.DEPARTMENT_COMPLETED
    }
    assert started == {d.value for d in decision.active}
    assert completed == {d.value for d in decision.active}
    assert emitter.completed == 5


@pytest.mark.asyncio
async def test_progress_callback_failure_does_not_abort_run() -> None:
    """A dead WebSocket must not waste free-tier quota already spent."""

    async def bad_callback(event):
        raise ConnectionError("browser closed")

    decision = resolve_departments(digital_intent())
    emitter = ProgressEmitter("s", len(decision.active), bad_callback)
    graph = build_graph(decision, emitter, runners=_runners_for(decision.active))

    state = new_state("s", "prompt")
    state["intent"] = digital_intent()
    result = await graph.ainvoke(state)

    assert result["errors"] == []


def test_progress_event_percent() -> None:
    emitter = ProgressEmitter("s", 4)
    assert emitter.total == 4
    event = ProgressEmitter("s", 4).events
    assert event == []


# =============================================================================
# F16 - completeness and contradictions
# =============================================================================


def test_expected_fields_exist_on_department_models() -> None:
    """Guards the frozen-field-name contract: the F56 checklist must not drift
    away from the actual schemas."""
    from app.generation.models.state import DEPARTMENT_MODELS

    for department, fields in EXPECTED_FIELDS.items():
        model_fields = set(DEPARTMENT_MODELS[department].model_fields)
        unknown = set(fields) - model_fields
        assert not unknown, f"{department.value} checklist references unknown {unknown}"


def test_total_expected_fields_is_at_least_20() -> None:
    """F56 requires a checklist of 20+ expected sections."""
    assert TOTAL_EXPECTED_FIELDS >= 20


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("too short", False),
        ("A premium gelato outlet targeting Andheri families.", True),
        ([], False),
        (["one item"], True),
        ({}, False),
        ({"a": 1}, True),
        (0, True),
        (9, True),
        (12.5, True),
    ],
)
def test_is_substantive(value: object, expected: bool) -> None:
    assert is_substantive(value) is expected


def test_is_substantive_for_nested_model() -> None:
    assert is_substantive(MarketSize()) is False
    assert is_substantive(MarketSize(tam_inr=50_000_000)) is True


def test_completeness_scores_only_active_departments() -> None:
    """Scoring a skipped department as missing would make dynamic routing look
    like a quality regression in RQ2."""
    state = new_state("s", "prompt")
    decision = resolve_departments(digital_intent())

    report = score_completeness(state, decision.active)

    assert report.expected_count == sum(
        len(EXPECTED_FIELDS[d]) for d in decision.active
    )
    assert not any(key.startswith("operations.") for key in report.missing)


def test_completeness_full_marks() -> None:
    state = new_state("s", "prompt")
    state["strategy"] = StrategyOutput(
        executive_summary="A premium gelato outlet targeting Andheri families.",
        market_size=MarketSize(tam_inr=50_000_000),
        risks=[{"category": "market", "description": "x", "severity": "high", "likelihood": "low"}],
        competitors=[{"name": "Naturals"}],
        market_overview="Mumbai frozen dessert demand grew 14% year on year.",
        location_score=8.5,
    )

    report = score_completeness(state, [Department.STRATEGY])
    assert report.score == 100.0
    assert report.missing == []


def test_completeness_partial_score() -> None:
    state = new_state("s", "prompt")
    state["strategy"] = StrategyOutput(
        executive_summary="A premium gelato outlet targeting Andheri families.",
        location_score=8.5,
    )

    report = score_completeness(state, [Department.STRATEGY])
    assert report.score == pytest.approx(33.33, abs=0.01)
    assert "strategy.market_size" in report.missing


def test_detect_contradiction_budget_exceeded() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(
        total_setup_cost_inr=2_000_000,
        setup_costs=[CostItem(name="equipment", category="setup", amount_inr=2_000_000)],
    )

    warnings = detect_contradictions(state, physical_intent())
    assert any("exceeds stated budget" in w for w in warnings)


def test_detect_contradiction_net_margin_above_gross() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(gross_margin_pct=40.0, net_margin_pct=55.0)

    warnings = detect_contradictions(state, physical_intent())
    assert any("exceeds gross margin" in w for w in warnings)


def test_detect_contradiction_revenue_above_som() -> None:
    state = new_state("s", "prompt")
    state["strategy"] = StrategyOutput(market_size=MarketSize(som_inr=1_000_000))
    state["finance"] = FinanceOutput(projected_revenue_y1_inr=5_000_000)

    warnings = detect_contradictions(state, physical_intent())
    assert any("exceeds obtainable market" in w for w in warnings)


def test_detect_contradiction_implausible_gross_margin() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(gross_margin_pct=140.0)

    warnings = detect_contradictions(state, physical_intent())
    assert any("plausible" in w for w in warnings)


def test_no_contradictions_on_consistent_plan() -> None:
    state = new_state("s", "prompt")
    state["strategy"] = StrategyOutput(market_size=MarketSize(som_inr=10_000_000))
    state["finance"] = FinanceOutput(
        total_setup_cost_inr=1_200_000,
        projected_revenue_y1_inr=4_000_000,
        gross_margin_pct=55.0,
        net_margin_pct=18.0,
        break_even_month=9,
        total_monthly_cost_inr=250_000,
    )

    assert detect_contradictions(state, physical_intent()) == []


def test_empty_state_produces_no_contradictions() -> None:
    """Absence of data is a completeness problem, not a contradiction."""
    assert detect_contradictions(new_state("s", "prompt"), physical_intent()) == []


# =============================================================================
# Metric bugs found on a live Groq run
# =============================================================================


def test_short_brand_name_counts_as_substantive() -> None:
    """Observed: the branding agent returned 'Shitalaya' (9 chars) and F56 scored
    it as missing, understating completeness for a correct answer."""
    from app.generation.models.departments import BrandingOutput

    state = new_state("s", "prompt")
    state["branding"] = BrandingOutput(recommended_name="Shitalaya")

    report = score_completeness(state, [Department.BRANDING])
    assert "branding.recommended_name" in report.present


def test_generic_prose_field_still_needs_length() -> None:
    """The short-field exemption must not weaken the metric everywhere."""
    state = new_state("s", "prompt")
    state["strategy"] = StrategyOutput(executive_summary="Too short.")

    report = score_completeness(state, [Department.STRATEGY])
    assert "strategy.executive_summary" in report.missing


def test_minimum_length_lookup() -> None:
    assert minimum_length_for("branding.recommended_name") == 2
    assert minimum_length_for("strategy.executive_summary") == MIN_SUBSTANTIVE_TEXT_LENGTH


def test_is_substantive_accepts_explicit_threshold() -> None:
    assert is_substantive("Shitalaya", 2) is True
    assert is_substantive("Shitalaya") is False


def test_detect_contradiction_deeply_negative_net_margin() -> None:
    """Observed: gross 70% but net -263%, and nothing flagged it."""
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(gross_margin_pct=70.0, net_margin_pct=-263.33)

    warnings = detect_contradictions(state, physical_intent())
    assert any("loses more than it earns" in w for w in warnings)


def test_detect_contradiction_revenue_below_annual_cost() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(
        projected_revenue_y1_inr=1_200_000, total_monthly_cost_inr=285_000
    )

    warnings = detect_contradictions(state, physical_intent())
    assert any("below the annual operating cost" in w for w in warnings)


def test_detect_contradiction_positive_margin_without_break_even() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(
        gross_margin_pct=60.0,
        net_margin_pct=15.0,
        break_even_month=None,
        pl_forecast=[{"label": "Y1-M01", "revenue_inr": 100_000}],
    )

    warnings = detect_contradictions(state, physical_intent())
    assert any("no break-even month" in w for w in warnings)


def test_healthy_finance_section_triggers_no_new_warnings() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput(
        projected_revenue_y1_inr=7_000_000,
        total_monthly_cost_inr=400_000,
        gross_margin_pct=60.0,
        net_margin_pct=18.0,
        break_even_month=4,
        pl_forecast=[{"label": "Y1-M01", "revenue_inr": 300_000}],
    )
    assert detect_contradictions(state, physical_intent()) == []


# =============================================================================
# F13 - end-to-end orchestration
# =============================================================================


@pytest.mark.asyncio
async def test_orchestrate_physical_business_end_to_end() -> None:
    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        persist=False,
    )

    assert state["intent"].sector is Sector.FOOD_AND_BEVERAGE
    assert state["intent"].scale is Scale.SMALL
    metadata = state["metadata"]
    assert metadata.active_departments == list(ALL_DEPARTMENTS)
    assert metadata.skipped_departments == []
    assert metadata.total_duration_ms is not None
    assert metadata.completed_at is not None
    # Placeholder runners write nothing, so completeness is 0 until Phase 5.
    assert metadata.completeness_score == 0.0
    assert metadata.status is RunStatus.PARTIAL


@pytest.mark.asyncio
async def test_orchestrate_digital_business_skips_operations() -> None:
    state = await orchestrate(
        "Start an online tutoring platform for CBSE students",
        client=fake_client(DIGITAL_PAYLOAD),
        persist=False,
    )

    metadata = state["metadata"]
    assert metadata.skipped_departments == [Department.OPERATIONS]
    assert Department.OPERATIONS not in metadata.active_departments
    assert metadata.dynamic_routing_used is True


@pytest.mark.asyncio
async def test_orchestrate_force_all_runs_operations_for_digital_business() -> None:
    """The two RQ2 arms on the same prompt."""
    prompt = "Start an online tutoring platform for CBSE students"

    dynamic = await orchestrate(
        prompt, client=fake_client(DIGITAL_PAYLOAD), persist=False
    )
    control = await orchestrate(
        prompt,
        client=fake_client(DIGITAL_PAYLOAD),
        force_all_departments=True,
        persist=False,
    )

    assert len(dynamic["metadata"].active_departments) == 4
    assert len(control["metadata"].active_departments) == 5
    assert control["metadata"].dynamic_routing_used is False
    # Same intent in both arms - the only difference is the department set.
    assert dynamic["intent"].business_type == control["intent"].business_type


@pytest.mark.asyncio
async def test_orchestrate_records_a_trace_per_department() -> None:
    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        persist=False,
    )
    assert len(state["agent_traces"]) == 5
    assert total_tokens(state) == 0  # placeholders spend nothing


@pytest.mark.asyncio
async def test_orchestrate_rejects_invalid_prompt_before_llm_call() -> None:
    from app.generation.intent import PromptValidationError

    with pytest.raises(PromptValidationError):
        await orchestrate("cafe", client=fake_client(PHYSICAL_PAYLOAD), persist=False)


@pytest.mark.asyncio
async def test_orchestrate_marks_partial_on_department_failure() -> None:
    async def exploding(state):
        raise RuntimeError("provider down")

    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        runners={Department.FINANCE: exploding},
        persist=False,
    )

    assert state["metadata"].status is RunStatus.PARTIAL
    assert any("finance" in e for e in state["errors"])


@pytest.mark.asyncio
async def test_orchestrate_timeout_returns_partial_state(monkeypatch) -> None:
    """F52 - a timeout must still yield whatever completed."""
    from app.generation.orchestrator import runner as runner_module

    monkeypatch.setattr(runner_module.settings, "generation_timeout_seconds", 1)

    async def slow(state):
        await asyncio.sleep(5)
        return {}

    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        runners={d: slow for d in ALL_DEPARTMENTS},
        persist=False,
    )

    assert state["metadata"].status is RunStatus.TIMEOUT
    assert state["intent"] is not None  # intent survived


@pytest.mark.asyncio
async def test_orchestrate_completeness_reflects_real_department_output() -> None:
    async def strategy_runner(state):
        return apply_department_patch(
            state,
            Department.STRATEGY,
            {
                "executive_summary": "A premium gelato outlet targeting Andheri families.",
                "market_size": MarketSize(tam_inr=50_000_000),
                "risks": [
                    {
                        "category": "market",
                        "description": "seasonal demand",
                        "severity": "medium",
                        "likelihood": "high",
                    }
                ],
                "competitors": [{"name": "Naturals Ice Cream"}],
                "market_overview": "Mumbai frozen dessert demand grew 14% year on year.",
                "location_score": 8.5,
            },
        )

    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        runners={Department.STRATEGY: strategy_runner},
        persist=False,
    )

    report = score_completeness(state, [Department.STRATEGY])
    assert report.score == 100.0
    assert state["metadata"].completeness_score > 0.0


@pytest.mark.asyncio
async def test_run_summary_shape() -> None:
    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        persist=False,
    )
    decision = resolve_departments(state["intent"])
    summary = run_summary(state, decision)

    assert set(summary) == {
        "session_id",
        "status",
        "intent",
        "routing",
        "completeness_score",
        "validation_warnings",
        "total_duration_ms",
        "total_tokens",
        "departments_completed",
        "errors",
        "plan",
    }
    assert summary["routing"]["stages"][1]["execution"] == "parallel"


@pytest.mark.asyncio
async def test_orchestrate_persists_session(tmp_path, monkeypatch) -> None:
    from app.generation.db import sqlite

    db_file = tmp_path / "orchestrator.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()

    state = await orchestrate(
        "Ice cream shop in Andheri, Rs 15L budget",
        client=fake_client(PHYSICAL_PAYLOAD),
        persist=True,
    )

    record = sqlite.get_session(state["session_id"])
    assert record is not None
    assert record["intent"]["sector"] == "food_and_beverage"
    assert record["active_departments"] == [d.value for d in ALL_DEPARTMENTS]
    assert record["completed_at"] is not None
    assert record["status"] == state["metadata"].status.value


# =============================================================================
# Registry
# =============================================================================


def test_registry_has_a_runner_for_every_department() -> None:
    assert set(DEPARTMENT_RUNNERS) == set(Department)


@pytest.mark.asyncio
async def test_register_runner_replaces_placeholder() -> None:
    original = DEPARTMENT_RUNNERS[Department.BRANDING]
    try:

        async def custom(state):
            return apply_department_patch(
                state, Department.BRANDING, {"recommended_name": "Replaced"}
            )

        register_runner(Department.BRANDING, custom)
        state = new_state("s", "prompt")
        update = await DEPARTMENT_RUNNERS[Department.BRANDING](state)
        assert update["branding"].recommended_name == "Replaced"
    finally:
        register_runner(Department.BRANDING, original)


@pytest.mark.asyncio
async def test_placeholder_runner_returns_skipped_trace() -> None:
    runner = make_placeholder(Department.OPERATIONS)
    update = await runner(new_state("s", "prompt"))
    trace = update["agent_traces"][0]
    assert trace.status == "skipped"
    assert trace.department is Department.OPERATIONS
