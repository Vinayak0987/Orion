"""Tests for the strategy synthesis agents F17a/F17b (Phases 4-5).

Offline: a scripted LLM returns fixed JSON for each agent, so the deterministic
scorer and the evidence tagging are exercised without any network or quota.
"""

from __future__ import annotations

import json

import pytest

from app.generation.agents.strategy import (
    StrategicOptionsAgent,
    StrategySynthesisAgent,
    build_strategy_stages,
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
from app.generation.models.departments import StrategyOutput
from app.generation.models.intent import BusinessIntent, Budget, Sector
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
        return LLMResponse(
            text=json.dumps(self._payload),
            provider=self.name,
            model="gemini-scripted",
            prompt_tokens=30,
            completion_tokens=40,
        )


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
    return LLMClient(
        groq=_Dead(ProviderName.GROQ),
        gemini=_Scripted(payload),
        ollama=_Dead(ProviderName.OLLAMA),
    )


def _state():
    st = new_state("s", "Ice cream shop in Andheri, Rs 15L budget")
    st["intent"] = BusinessIntent(
        business_type="ice_cream_shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        budget=Budget(amount=1_500_000, specified=True),
    )
    return st


OPTIONS_PAYLOAD = {
    "options": [
        {
            "name": "Premium niche",
            "thesis": "Win on quality",
            "pros": ["higher margin"],
            "cons": ["smaller market"],
            "est_setup_cost_inr": 1400000,
            "strategic_fit": 5, "cost_efficiency": 3, "risk_level": 4,
            "reversibility": 4, "competitive_advantage": 5,
        },
        {
            "name": "Value volume",
            "thesis": "Win on price",
            "pros": ["big market"],
            "cons": ["thin margin"],
            "est_setup_cost_inr": 1200000,
            "strategic_fit": 3, "cost_efficiency": 4, "risk_level": 3,
            "reversibility": 3, "competitive_advantage": 2,
        },
    ]
}

SYNTHESIS_PAYLOAD = {
    "strengths": ["prime location"],
    "weaknesses": ["limited capital"],
    "opportunities": ["growing dessert demand"],
    "threats": ["established chains"],
    "rationale": "Premium niche scores highest on fit and advantage.",
    "evidence": [
        {"claim": "Dessert market growing 12%", "kind": "fact", "confidence": 0.8, "source": "serper"},
        {"claim": "Footfall will convert at 3%", "kind": "prediction", "confidence": 0.4, "source": "llm"},
        {"claim": "Rent is unknown", "kind": "made_up_kind", "confidence": 2.0, "source": "llm"},
    ],
    "confidence": 0.72,
}


# =============================================================================
# F17a - Strategic Options
# =============================================================================


@pytest.mark.asyncio
async def test_options_agent_scores_and_ranks() -> None:
    agent = StrategicOptionsAgent()
    update = await agent.run(_state(), client=_client(OPTIONS_PAYLOAD))

    section: StrategyOutput = update[Department.STRATEGY.value]
    assert len(section.strategic_options) == 2
    # Premium niche (higher fit + advantage) must outrank value volume, and the
    # score is computed by the Python scorer, not the model.
    assert section.strategic_options[0].name == "Premium niche"
    assert section.recommended_option == "Premium niche"
    assert section.strategic_options[0].score is not None
    assert section.strategic_options[0].score > section.strategic_options[1].score
    assert section.strategic_options[0].score_breakdown  # transparent breakdown


@pytest.mark.asyncio
async def test_options_agent_clamps_out_of_range_ratings() -> None:
    payload = {
        "options": [
            {"name": "X", "strategic_fit": 9, "risk_level": 0,
             "cost_efficiency": 3, "reversibility": 3, "competitive_advantage": 3}
        ]
    }
    update = await StrategicOptionsAgent().run(_state(), client=_client(payload))
    opt = update[Department.STRATEGY.value].strategic_options[0]
    assert opt.strategic_fit == 5  # clamped from 9
    assert opt.risk_level == 1  # clamped from 0


# =============================================================================
# F17b - Synthesis / Recommendation
# =============================================================================


@pytest.mark.asyncio
async def test_synthesis_agent_builds_swot_and_tags_evidence() -> None:
    update = await StrategySynthesisAgent().run(_state(), client=_client(SYNTHESIS_PAYLOAD))
    section: StrategyOutput = update[Department.STRATEGY.value]

    assert section.swot is not None
    assert section.swot.strengths == ["prime location"]
    assert section.swot.threats == ["established chains"]
    assert section.strategic_rationale.startswith("Premium niche")
    assert section.strategy_confidence == 0.72

    kinds = {e.kind for e in section.strategy_evidence}
    assert "fact" in kinds and "prediction" in kinds
    # An invalid kind is coerced to 'assumption'; a >1 confidence is clamped.
    bad = [e for e in section.strategy_evidence if e.claim.startswith("Rent")][0]
    assert bad.kind == "assumption"
    assert bad.confidence == 1.0


@pytest.mark.asyncio
async def test_synthesis_agent_handles_no_options() -> None:
    """Runs even if the options agent produced nothing (prompt says '(none)')."""
    update = await StrategySynthesisAgent().run(_state(), client=_client(SYNTHESIS_PAYLOAD))
    assert update[Department.STRATEGY.value].swot is not None


# =============================================================================
# Topology
# =============================================================================


def test_synthesis_off_is_five_agents() -> None:
    stages = build_strategy_stages(synthesis=False)
    assert sum(len(s) for s in stages) == 5


def test_synthesis_on_adds_two_agents_as_stages_3_and_4() -> None:
    stages = build_strategy_stages(synthesis=True)
    assert sum(len(s) for s in stages) == 7
    assert [a.spec.agent_id for a in stages[2]] == ["strategic_options"]
    assert [a.spec.agent_id for a in stages[3]] == ["strategy_synthesis"]
    features = [a.spec.feature for s in stages for a in s]
    assert "F17a" in features and "F17b" in features


def test_synthesis_on_yields_23_total_agents_via_registry() -> None:
    """With the flag on, the whole graph is 23 agents and the two new features
    appear exactly once. Verified by rebuilding the department stage map the
    same way the registry does, so it reflects the real topology."""
    from app.generation.agents.branding import BRANDING_STAGES
    from app.generation.agents.finance import FINANCE_STAGES
    from app.generation.agents.marketing import MARKETING_STAGES
    from app.generation.agents.operations import OPERATIONS_STAGES

    strategy_on = build_strategy_stages(synthesis=True)
    all_stages = [strategy_on, FINANCE_STAGES, BRANDING_STAGES, MARKETING_STAGES, OPERATIONS_STAGES]
    total = sum(len(stage) for stages in all_stages for stage in stages)
    features = [a.spec.feature for stages in all_stages for stage in stages for a in stage]

    assert total == 23
    assert features.count("F17a") == 1
    assert features.count("F17b") == 1
    # The original 21 features are all still present exactly once.
    for n in range(17, 38):
        assert features.count(f"F{n}") == 1

