"""Tests for the branding synthesis agent F29a (Phases 4-5). Offline."""

from __future__ import annotations

import json

import pytest

from app.agents.branding import BrandConsistencyAgent, build_branding_stages
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
from app.models.departments import BrandingOutput, BrandNameCandidate, ColorPalette
from app.models.intent import BusinessIntent, Sector
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


def _state(primary: str = "#0A1A3A", name: str = "Frostbyte"):
    st = new_state("s", "Ice cream shop in Andheri, Rs 15L budget")
    st["intent"] = BusinessIntent(business_type="ice_cream_shop", sector=Sector.FOOD_AND_BEVERAGE)
    st[Department.BRANDING.value] = BrandingOutput(
        recommended_name=name,
        name_candidates=[BrandNameCandidate(name=name)],
        color_palette=ColorPalette(primary_hex=primary),
        personality_traits=["fun", "fresh", "modern"],
        taglines=["Cool by nature"],
        heading_font="Poppins",
        body_font="Inter",
    )
    return st


SUMMARY_PAYLOAD = {
    "brand_summary": "Primary passes AAA for white text; the name is distinct.",
    "evidence": [
        {"claim": "contrast rated AAA", "kind": "fact", "confidence": 1.0, "source": "contrast_check"},
        {"claim": "name feels premium", "kind": "made_up", "confidence": 2.0, "source": "llm"},
    ],
}


@pytest.mark.asyncio
async def test_brand_agent_computes_checks_and_tags_evidence() -> None:
    update = await BrandConsistencyAgent().run(_state(), client=_client(SUMMARY_PAYLOAD))
    section: BrandingOutput = update[Department.BRANDING.value]

    assert section.contrast_rating == "AAA"  # white text on dark navy
    assert section.name_collision is False
    assert section.brand_summary.startswith("Primary passes")
    kinds = {e.kind for e in section.brand_evidence}
    assert "fact" in kinds
    bad = next(e for e in section.brand_evidence if e.claim.startswith("name feels"))
    assert bad.kind == "assumption"  # invalid kind coerced
    assert bad.confidence == 1.0  # clamped


@pytest.mark.asyncio
async def test_brand_agent_flags_failing_contrast() -> None:
    update = await BrandConsistencyAgent().run(_state(primary="#FFF3B0"), client=_client(SUMMARY_PAYLOAD))
    section = update[Department.BRANDING.value]
    assert section.contrast_rating in {"fail", "AA-large"}
    assert any("contrast" in w for w in section.brand_warnings)


@pytest.mark.asyncio
async def test_brand_agent_flags_name_collision() -> None:
    update = await BrandConsistencyAgent().run(_state(name="Amul"), client=_client(SUMMARY_PAYLOAD))
    section = update[Department.BRANDING.value]
    assert section.name_collision is True
    assert any("collides" in w for w in section.brand_warnings)


@pytest.mark.asyncio
async def test_brand_agent_uses_fallback_when_blank() -> None:
    blank = {"brand_summary": "", "evidence": []}
    update = await BrandConsistencyAgent().run(_state(), client=_client(blank))
    section = update[Department.BRANDING.value]
    assert section.brand_summary  # deterministic fallback substituted
    assert section.contrast_rating is not None


@pytest.mark.asyncio
async def test_brand_agent_records_failed_trace_when_all_providers_down() -> None:
    dead = LLMClient(groq=_Dead(ProviderName.GROQ), gemini=_Dead(ProviderName.GEMINI),
                     ollama=_Dead(ProviderName.OLLAMA))
    update = await BrandConsistencyAgent().run(_state(), client=dead)
    assert Department.BRANDING.value not in update
    assert update["agent_traces"][0].status == "failed"


# =============================================================================
# Topology
# =============================================================================


def test_branding_synthesis_off_is_four_agents() -> None:
    assert sum(len(s) for s in build_branding_stages(synthesis=False)) == 4


def test_branding_synthesis_on_adds_one_agent_as_stage_3() -> None:
    stages = build_branding_stages(synthesis=True)
    assert sum(len(s) for s in stages) == 5
    assert [a.spec.agent_id for a in stages[2]] == ["brand_consistency"]
    assert "F29a" in [a.spec.feature for s in stages for a in s]


def test_branding_synthesis_on_yields_22_total_agents_via_registry() -> None:
    """With only branding synthesis on, the whole graph is 22 agents and F29a
    appears exactly once, alongside the untouched F17-F37."""
    from app.agents.finance import FINANCE_STAGES
    from app.agents.marketing import MARKETING_STAGES
    from app.agents.operations import OPERATIONS_STAGES
    from app.agents.strategy import STRATEGY_STAGES

    brand_on = build_branding_stages(synthesis=True)
    all_stages = [STRATEGY_STAGES, FINANCE_STAGES, brand_on, MARKETING_STAGES, OPERATIONS_STAGES]
    total = sum(len(stage) for stages in all_stages for stage in stages)
    features = [a.spec.feature for stages in all_stages for stage in stages for a in stage]

    assert total == 22
    assert features.count("F29a") == 1
    for n in range(17, 38):
        assert features.count(f"F{n}") == 1
