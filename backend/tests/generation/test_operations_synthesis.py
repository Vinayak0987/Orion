"""Tests for the operations synthesis agents F34a/F37a (Phases 4-5). Offline."""

from __future__ import annotations

import json

import pytest

from app.generation.agents.operations import (
    ComplianceLicensingAgent,
    OperationsFeasibilityAgent,
    build_operations_stages,
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
from app.generation.models.departments import OperationsOutput, ProcessStep, Role, ToolRecommendation
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


def _dead_client() -> LLMClient:
    return LLMClient(groq=_Dead(ProviderName.GROQ), gemini=_Dead(ProviderName.GEMINI),
                     ollama=_Dead(ProviderName.OLLAMA))


def _state(with_ops: bool = False):
    st = new_state("s", "Ice cream shop in Andheri, Rs 15L budget")
    st["intent"] = BusinessIntent(
        business_type="ice_cream_shop", sector=Sector.FOOD_AND_BEVERAGE,
        budget=Budget(amount=1_500_000, specified=True),
    )
    if with_ops:
        st[Department.OPERATIONS.value] = OperationsOutput(
            roles=[Role(title="Manager", headcount=1), Role(title="Cashier", headcount=2)],
            total_monthly_payroll_inr=60_000,
            tools=[ToolRecommendation(name="Vyapar", purpose="billing pos inventory"),
                   ToolRecommendation(name="Khatabook", purpose="accounting"),
                   ToolRecommendation(name="WhatsApp", purpose="communication")],
            total_tool_cost_monthly_inr=0,
            daily_workflow=[ProcessStep(order=i, name=f"step{i}", owner_role="Manager") for i in range(1, 5)],
            quality_checkpoints=["hygiene", "cash", "stock"],
        )
    return st


# =============================================================================
# F34a - Compliance & Licensing
# =============================================================================


COMPLIANCE_PAYLOAD = {
    "licences": [
        {"name": "Eating House Licence", "authority": "Police Commissioner",
         "when_required": "serving food for consumption on premises", "est_cost_inr": None, "notes": ""},
        {"name": "GST Registration", "authority": "GST Dept", "when_required": "dup", "notes": "dup"},  # dedup
    ],
    "compliance_notes": "Obtain FSSAI first, then GST.",
}


@pytest.mark.asyncio
async def test_compliance_seeds_sector_licences_as_facts() -> None:
    update = await ComplianceLicensingAgent().run(_state(), client=_client(COMPLIANCE_PAYLOAD))
    section: OperationsOutput = update[Department.OPERATIONS.value]

    names = {lic.name for lic in section.licences}
    assert "FSSAI Food Licence" in names  # seeded
    assert "GST Registration" in names
    fssai = next(l for l in section.licences if l.name == "FSSAI Food Licence")
    assert fssai.evidence_kind == "fact"
    assert "verify" in fssai.notes.lower()


@pytest.mark.asyncio
async def test_compliance_adds_llm_licence_as_assumption_and_dedups() -> None:
    update = await ComplianceLicensingAgent().run(_state(), client=_client(COMPLIANCE_PAYLOAD))
    section: OperationsOutput = update[Department.OPERATIONS.value]

    eating = next(l for l in section.licences if l.name == "Eating House Licence")
    assert eating.evidence_kind == "assumption"
    assert "verify" in eating.notes.lower()
    # GST appears once (seeded), not duplicated by the LLM entry.
    assert sum(1 for l in section.licences if l.name == "GST Registration") == 1
    assert section.compliance_notes == "Obtain FSSAI first, then GST."


# =============================================================================
# F37a - Feasibility
# =============================================================================


FEASIBILITY_PAYLOAD = {
    "operations_summary": "Staffing fits the budget and every step is owned; low operational risk.",
    "evidence": [
        {"claim": "payroll within budget", "kind": "inference", "confidence": 0.7, "source": "budget"},
        {"claim": "demand is steady", "kind": "made_up", "confidence": 2.0, "source": "llm"},
    ],
}


@pytest.mark.asyncio
async def test_feasibility_computes_score_and_tags_evidence() -> None:
    update = await OperationsFeasibilityAgent().run(_state(with_ops=True), client=_client(FEASIBILITY_PAYLOAD))
    section: OperationsOutput = update[Department.OPERATIONS.value]

    assert section.feasibility_score == 100  # the good ops fixture passes all checks
    assert section.feasibility_warnings == []
    assert section.operations_summary.startswith("Staffing fits")
    kinds = {e.kind for e in section.operations_evidence}
    assert "inference" in kinds
    bad = next(e for e in section.operations_evidence if e.claim.startswith("demand"))
    assert bad.kind == "assumption"  # invalid kind coerced
    assert bad.confidence == 1.0  # clamped


@pytest.mark.asyncio
async def test_feasibility_flags_orphan_owner_role() -> None:
    st = _state(with_ops=True)
    st[Department.OPERATIONS.value].daily_workflow.append(
        ProcessStep(order=5, name="deliver", owner_role="Driver")  # not a staffed role
    )
    update = await OperationsFeasibilityAgent().run(st, client=_client(FEASIBILITY_PAYLOAD))
    section = update[Department.OPERATIONS.value]
    assert section.feasibility_score == 75
    assert any("Driver" in w for w in section.feasibility_warnings)


@pytest.mark.asyncio
async def test_feasibility_uses_deterministic_summary_when_llm_returns_blank() -> None:
    """If the LLM responds but omits the summary, the deterministic
    fallback_summary is used - the score/warnings still come from Python."""
    blank = {"operations_summary": "", "evidence": []}
    update = await OperationsFeasibilityAgent().run(_state(with_ops=True), client=_client(blank))
    section = update[Department.OPERATIONS.value]
    assert section.feasibility_score == 100
    # fallback summary was substituted for the empty LLM summary.
    assert "consistent" in section.operations_summary.lower()


@pytest.mark.asyncio
async def test_feasibility_records_failed_trace_when_all_providers_down() -> None:
    """All providers down -> the agent records a failed trace and writes no
    section, so the run continues with partial results (F52)."""
    update = await OperationsFeasibilityAgent().run(_state(with_ops=True), client=_dead_client())
    assert Department.OPERATIONS.value not in update
    assert update["agent_traces"][0].status == "failed"


# =============================================================================
# Topology
# =============================================================================


def test_operations_synthesis_off_is_four_agents() -> None:
    assert sum(len(s) for s in build_operations_stages(synthesis=False)) == 4


def test_operations_synthesis_on_adds_two_agents_as_stages_3_and_4() -> None:
    stages = build_operations_stages(synthesis=True)
    assert sum(len(s) for s in stages) == 6
    assert [a.spec.agent_id for a in stages[2]] == ["compliance_licensing"]
    assert [a.spec.agent_id for a in stages[3]] == ["operations_feasibility"]
    features = [a.spec.feature for s in stages for a in s]
    assert "F34a" in features and "F37a" in features


def test_operations_synthesis_on_yields_23_total_agents_via_registry() -> None:
    """With the flag on, the whole graph is 23 agents and the two new operations
    features appear exactly once, alongside the untouched F17-F37."""
    from app.generation.agents.branding import BRANDING_STAGES
    from app.generation.agents.finance import FINANCE_STAGES
    from app.generation.agents.marketing import MARKETING_STAGES
    from app.generation.agents.strategy import STRATEGY_STAGES  # baseline (strategy synthesis off)

    ops_on = build_operations_stages(synthesis=True)
    all_stages = [STRATEGY_STAGES, FINANCE_STAGES, BRANDING_STAGES, MARKETING_STAGES, ops_on]
    total = sum(len(stage) for stages in all_stages for stage in stages)
    features = [a.spec.feature for stages in all_stages for stage in stages for a in stage]

    assert total == 23
    assert features.count("F34a") == 1
    assert features.count("F37a") == 1
    for n in range(17, 38):
        assert features.count(f"F{n}") == 1
