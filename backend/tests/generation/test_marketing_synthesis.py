"""Tests for the marketing synthesis agent F33a (Phases 4-5). Offline."""

from __future__ import annotations

import json

import pytest

from app.generation.agents.marketing import MarketingConsistencyAgent, build_marketing_stages
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
from app.generation.models.departments import Channel, FinanceOutput, MarketingOutput
from app.generation.models.intent import BusinessIntent, Sector
from app.generation.models.state import Department, new_state


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


def _state(*, shares=(60.0, 40.0), budget=100_000, revenue=8_400_000, ticket=500,
           op_cost=200_000):
    st = new_state("s", "Ice cream shop in Andheri, Rs 15L budget")
    st["intent"] = BusinessIntent(business_type="ice_cream_shop", sector=Sector.FOOD_AND_BEVERAGE)
    st[Department.FINANCE.value] = FinanceOutput(
        projected_revenue_y1_inr=revenue, avg_ticket_size_inr=ticket,
        total_monthly_cost_inr=op_cost,
    )
    st[Department.MARKETING.value] = MarketingOutput(
        channels=[Channel(name=f"c{i}", budget_share_pct=s) for i, s in enumerate(shares)],
        total_marketing_budget_inr=budget,
    )
    return st


SUMMARY_PAYLOAD = {
    "marketing_summary": "Plan needs ~1400 customers/month at Rs 71 CAC; mix sums to 100%.",
    "evidence": [
        {"claim": "1400 customers/month needed", "kind": "inference", "confidence": 0.6, "source": "finance"},
        {"claim": "Instagram is the best channel", "kind": "made_up", "confidence": 2.0, "source": "llm"},
    ],
}


@pytest.mark.asyncio
async def test_marketing_agent_computes_econ_and_tags_evidence() -> None:
    update = await MarketingConsistencyAgent().run(_state(), client=_client(SUMMARY_PAYLOAD))
    section: MarketingOutput = update[Department.MARKETING.value]

    assert section.budget_share_total_pct == 100.0
    assert section.customers_needed_monthly == 1400  # 8.4M/12/500
    assert section.allowable_cac_inr == 71  # 100k/1400
    assert section.marketing_summary.startswith("Plan needs")
    kinds = {e.kind for e in section.marketing_evidence}
    assert "inference" in kinds
    bad = next(e for e in section.marketing_evidence if e.claim.startswith("Instagram"))
    assert bad.kind == "assumption"  # invalid kind coerced
    assert bad.confidence == 1.0  # clamped


@pytest.mark.asyncio
async def test_marketing_agent_flags_shares_off_100() -> None:
    update = await MarketingConsistencyAgent().run(
        _state(shares=(50.0, 30.0)), client=_client(SUMMARY_PAYLOAD)
    )
    section = update[Department.MARKETING.value]
    assert section.budget_share_total_pct == 80.0
    assert any("80" in w for w in section.marketing_warnings)


@pytest.mark.asyncio
async def test_marketing_agent_flags_over_budget() -> None:
    update = await MarketingConsistencyAgent().run(
        _state(budget=500_000, op_cost=200_000), client=_client(SUMMARY_PAYLOAD)
    )
    section = update[Department.MARKETING.value]
    assert any("exceeds" in w for w in section.marketing_warnings)


@pytest.mark.asyncio
async def test_marketing_agent_uses_fallback_when_blank() -> None:
    blank = {"marketing_summary": "", "evidence": []}
    update = await MarketingConsistencyAgent().run(_state(), client=_client(blank))
    section = update[Department.MARKETING.value]
    assert section.marketing_summary  # deterministic fallback substituted
    assert section.customers_needed_monthly == 1400


@pytest.mark.asyncio
async def test_marketing_agent_records_failed_trace_when_all_providers_down() -> None:
    dead = LLMClient(groq=_Dead(ProviderName.GROQ), gemini=_Dead(ProviderName.GEMINI),
                     ollama=_Dead(ProviderName.OLLAMA))
    update = await MarketingConsistencyAgent().run(_state(), client=dead)
    assert Department.MARKETING.value not in update
    assert update["agent_traces"][0].status == "failed"


# =============================================================================
# Topology
# =============================================================================


def test_marketing_synthesis_off_is_four_agents() -> None:
    assert sum(len(s) for s in build_marketing_stages(synthesis=False)) == 4


def test_marketing_synthesis_on_adds_one_agent_as_stage_3() -> None:
    stages = build_marketing_stages(synthesis=True)
    assert sum(len(s) for s in stages) == 5
    assert [a.spec.agent_id for a in stages[2]] == ["marketing_consistency"]
    assert "F33a" in [a.spec.feature for s in stages for a in s]


def test_marketing_synthesis_on_yields_22_total_agents_via_registry() -> None:
    """With only marketing synthesis on, the whole graph is 22 agents and F33a
    appears exactly once, alongside the untouched F17-F37."""
    from app.generation.agents.branding import BRANDING_STAGES
    from app.generation.agents.finance import FINANCE_STAGES
    from app.generation.agents.operations import OPERATIONS_STAGES
    from app.generation.agents.strategy import STRATEGY_STAGES

    mkt_on = build_marketing_stages(synthesis=True)
    all_stages = [STRATEGY_STAGES, FINANCE_STAGES, BRANDING_STAGES, mkt_on, OPERATIONS_STAGES]
    total = sum(len(stage) for stages in all_stages for stage in stages)
    features = [a.spec.feature for stages in all_stages for stage in stages for a in stage]

    assert total == 22
    assert features.count("F33a") == 1
    for n in range(17, 38):
        assert features.count(f"F{n}") == 1
