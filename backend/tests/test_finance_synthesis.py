"""Tests for the finance synthesis agent F25a (Phases 5-6). Offline."""

from __future__ import annotations

import json

import pytest

from app.agents.finance import CashFlowAgent, build_finance_stages
from app.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.llm.chain import LLMClient
from app.models.departments import FinanceOutput, PLPeriod
from app.models.intent import BusinessIntent, Budget, Sector
from app.models.state import Department, new_state


class _Scripted(LLMProvider):
    def __init__(self, payload: dict) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self._payload = payload

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-scripted"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=json.dumps(self._payload), provider=self.name,
                           model="gemini-scripted", prompt_tokens=30, completion_tokens=40)


class _Dead(LLMProvider):
    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "dead"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable("dead")


def _client(payload: dict) -> LLMClient:
    return LLMClient(groq=_Dead(ProviderName.GROQ), gemini=_Scripted(payload),
                     ollama=_Dead(ProviderName.OLLAMA))


def _state():
    st = new_state("s", "Ice cream shop in Andheri, Rs 15L budget")
    st["intent"] = BusinessIntent(
        business_type="ice_cream_shop", sector=Sector.FOOD_AND_BEVERAGE,
        budget=Budget(amount=1_500_000, specified=True),
    )
    st[Department.FINANCE.value] = FinanceOutput(
        total_setup_cost_inr=400_000,
        funding_amount_inr=0,
        gross_margin_pct=60.0,
        pl_forecast=[
            PLPeriod(label=f"Y1-M{i + 1:02d}", revenue_inr=100_000,
                     net_profit_inr=net)
            for i, net in enumerate([-100_000, -50_000, 0, 50_000, 80_000, 100_000,
                                     100_000, 100_000, 100_000, 100_000, 100_000, 100_000])
        ],
    )
    return st


SUMMARY_PAYLOAD = {
    "finance_summary": "Cash dips lowest in month 3; arrange a buffer before then.",
    "evidence": [
        {"claim": "runway covers year 1", "kind": "inference", "confidence": 0.7, "source": "pl_forecast"},
        {"claim": "demand ramps as assumed", "kind": "made_up", "confidence": 2.0, "source": "llm"},
    ],
}


@pytest.mark.asyncio
async def test_cash_flow_agent_computes_position_and_tags_evidence() -> None:
    update = await CashFlowAgent().run(_state(), client=_client(SUMMARY_PAYLOAD))
    section: FinanceOutput = update[Department.FINANCE.value]

    assert len(section.cash_flow) == 12
    assert section.lowest_cash_month is not None
    assert section.contribution_margin_pct == 60.0
    assert section.finance_summary.startswith("Cash dips")
    kinds = {e.kind for e in section.finance_evidence}
    assert "inference" in kinds
    bad = next(e for e in section.finance_evidence if e.claim.startswith("demand"))
    assert bad.kind == "assumption"  # invalid kind coerced
    assert bad.confidence == 1.0  # clamped


@pytest.mark.asyncio
async def test_cash_flow_agent_uses_fallback_summary_when_blank() -> None:
    blank = {"finance_summary": "", "evidence": []}
    update = await CashFlowAgent().run(_state(), client=_client(blank))
    section = update[Department.FINANCE.value]
    assert len(section.cash_flow) == 12
    # deterministic fallback substituted for the empty LLM summary
    assert section.finance_summary
    assert "month" in section.finance_summary.lower()


@pytest.mark.asyncio
async def test_cash_flow_agent_records_failed_trace_when_all_providers_down() -> None:
    dead = LLMClient(groq=_Dead(ProviderName.GROQ), gemini=_Dead(ProviderName.GEMINI),
                     ollama=_Dead(ProviderName.OLLAMA))
    update = await CashFlowAgent().run(_state(), client=dead)
    assert Department.FINANCE.value not in update
    assert update["agent_traces"][0].status == "failed"


# =============================================================================
# Topology
# =============================================================================


def test_finance_synthesis_off_is_four_agents() -> None:
    assert sum(len(s) for s in build_finance_stages(synthesis=False)) == 4


def test_finance_synthesis_on_adds_one_agent_as_stage_3() -> None:
    stages = build_finance_stages(synthesis=True)
    assert sum(len(s) for s in stages) == 5
    assert [a.spec.agent_id for a in stages[2]] == ["cash_flow"]
    assert "F25a" in [a.spec.feature for s in stages for a in s]


def test_finance_synthesis_on_yields_22_total_agents_via_registry() -> None:
    """With only finance synthesis on, the whole graph is 22 agents and F25a
    appears exactly once, alongside the untouched F17-F37."""
    from app.agents.branding import BRANDING_STAGES
    from app.agents.marketing import MARKETING_STAGES
    from app.agents.operations import OPERATIONS_STAGES  # baseline (ops synth off)
    from app.agents.strategy import STRATEGY_STAGES  # baseline (strategy synth off)

    fin_on = build_finance_stages(synthesis=True)
    all_stages = [STRATEGY_STAGES, fin_on, BRANDING_STAGES, MARKETING_STAGES, OPERATIONS_STAGES]
    total = sum(len(stage) for stages in all_stages for stage in stages)
    features = [a.spec.feature for stages in all_stages for stage in stages for a in stage]

    assert total == 22
    assert features.count("F25a") == 1
    for n in range(17, 38):
        assert features.count(f"F{n}") == 1
