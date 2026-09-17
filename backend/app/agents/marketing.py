"""Marketing department - 4 agents (F30-F33).

Stage 1 (sequential)  buyer_persona
Stage 2 (parallel)    digital_plan ∥ campaign_plan ∥ seo_content

The persona agent runs first because the other three all target it. This is the
clearest example of why the shared state matters: the campaign agent writes
launch activities aimed at the specific persona the persona agent produced,
which is the kind of internal coherence the Consistency Score (F57) measures and
a single-LLM baseline tends to lose across a long response.
"""

from __future__ import annotations

from pydantic import Field

from app.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    context_block,
    upstream_block,
)
from app.agents.marketing_checks import check_marketing, fallback_summary
from app.config import settings
from app.llm.base import ModelTier
from app.models.departments import BuyerPersona, CampaignPhase, Channel, EvidenceItem
from app.models.state import Department, SharedBusinessState

DEPT = Department.MARKETING


# =============================================================================
# F31 - Buyer Persona Agent
# =============================================================================


class PersonaOut(AgentOutput):
    name: str = ""
    age_range: str = ""
    gender: str = ""
    income_range_inr: str = ""
    occupation: str = ""
    location: str = ""
    values: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)


class PersonasOut(AgentOutput):
    personas: list[PersonaOut] = Field(default_factory=list)


class BuyerPersonaAgent(Agent):
    spec = AgentSpec(
        agent_id="buyer_persona",
        department=DEPT,
        feature="F31",
        schema=PersonasOut,
        tier=ModelTier.REASONING,
        max_tokens=1500,
    )
    system = (
        "You are a consumer researcher who profiles Indian urban customers with "
        "realistic income bands and specific behaviours."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "market", "revenue")}

Build buyer personas and return JSON with this key:
{{
  "personas": [
    {{
      "name": "a realistic Indian first name plus a descriptor",
      "age_range": "e.g. 25-34",
      "gender": "male, female or mixed",
      "income_range_inr": "monthly household income band, e.g. 60,000-1,20,000",
      "occupation": "typical job",
      "location": "where they live or work relative to this business",
      "values": ["3-4 values"],
      "pain_points": ["3-4 specific frustrations this business solves"],
      "buying_triggers": ["3 things that make them buy"],
      "objections": ["2-3 reasons they might not buy"]
    }}
  ]
}}

Give exactly 3 distinct personas."""

    def to_patch(self, parsed: PersonasOut, state: SharedBusinessState) -> dict:
        personas = [
            BuyerPersona(
                name=p.name.strip(),
                age_range=p.age_range.strip(),
                gender=p.gender.strip(),
                income_range_inr=p.income_range_inr.strip(),
                occupation=p.occupation.strip(),
                location=p.location.strip(),
                values=p.values,
                pain_points=p.pain_points,
                buying_triggers=p.buying_triggers,
                objections=p.objections,
            )
            for p in parsed.personas
            if p.name and p.name.strip()
        ]
        return {"personas": personas}


# =============================================================================
# F30 - Digital Marketing Plan Agent
# =============================================================================


class ChannelOut(AgentOutput):
    name: str = ""
    budget_share_pct: float | None = None
    primary_kpi: str = ""
    kpi_target: str = ""
    rationale: str = ""


class DigitalPlanOut(AgentOutput):
    channels: list[ChannelOut] = Field(default_factory=list)
    total_marketing_budget_inr: int | None = None
    channel_strategy_summary: str = ""


class DigitalPlanAgent(Agent):
    spec = AgentSpec(
        agent_id="digital_plan",
        department=DEPT,
        feature="F30",
        schema=DigitalPlanOut,
        tier=ModelTier.REASONING,
        max_tokens=1300,
    )
    system = (
        "You are a performance marketer working with Indian SME budgets. You "
        "recommend channels Indian small businesses actually convert on, including "
        "WhatsApp Business, Instagram, Google Business Profile and Zomato/Swiggy "
        "where relevant."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "personas", "costs", "brand")}

Build the digital plan and return JSON with these keys:
{{
  "channels": [{{"name": "channel", "budget_share_pct": 35, "primary_kpi": "metric", "kpi_target": "e.g. 3% CTR", "rationale": "one line"}}],
  "total_marketing_budget_inr": recommended monthly marketing spend in INR,
  "channel_strategy_summary": "3 sentences on the overall channel approach"
}}

Give 4 to 6 channels whose budget_share_pct values sum to EXACTLY 100.
total_marketing_budget_inr MUST stay below the monthly operating cost shown above."""

    def to_patch(self, parsed: DigitalPlanOut, state: SharedBusinessState) -> dict:
        total = parsed.total_marketing_budget_inr
        channels: list[Channel] = []
        for c in parsed.channels:
            if not c.name or not c.name.strip():
                continue
            share = c.budget_share_pct
            monthly = (
                int(round(total * share / 100.0))
                if total is not None and share is not None
                else None
            )
            channels.append(
                Channel(
                    name=c.name.strip(),
                    budget_share_pct=share,
                    monthly_budget_inr=monthly,
                    primary_kpi=c.primary_kpi.strip(),
                    kpi_target=c.kpi_target.strip(),
                    rationale=c.rationale.strip(),
                )
            )
        return {
            "channels": channels,
            "total_marketing_budget_inr": total,
            "channel_strategy_summary": parsed.channel_strategy_summary,
        }


# =============================================================================
# F32 - Campaign Plan Agent
# =============================================================================


class CampaignPhaseOut(AgentOutput):
    phase: str = ""
    day_range: str = ""
    objective: str = ""
    activities: list[str] = Field(default_factory=list)
    budget_inr: int | None = None


class CampaignOut(AgentOutput):
    campaign_phases: list[CampaignPhaseOut] = Field(default_factory=list)
    launch_hook: str = ""


_PHASES = {"pre_launch", "launch", "post_launch"}


class CampaignPlanAgent(Agent):
    spec = AgentSpec(
        agent_id="campaign_plan",
        department=DEPT,
        feature="F32",
        schema=CampaignOut,
        tier=ModelTier.FAST,
        temperature=0.6,
        max_tokens=1300,
    )
    system = "You are a campaign planner for Indian local businesses."

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "personas", "brand")}

Plan a 90-day launch campaign and return JSON with these keys:
{{
  "campaign_phases": [
    {{
      "phase": "pre_launch, launch or post_launch",
      "day_range": "e.g. Day 1-30",
      "objective": "one sentence",
      "activities": ["3-4 concrete activities"],
      "budget_inr": phase budget in INR
    }}
  ],
  "launch_hook": "the single strongest launch offer or hook, in 2 sentences"
}}

Give exactly 3 phases: pre_launch, launch, post_launch.
The three phase budgets together should roughly match 3 months of the marketing budget."""

    def to_patch(self, parsed: CampaignOut, state: SharedBusinessState) -> dict:
        phases = [
            CampaignPhase(
                phase=p.phase.strip().lower().replace("-", "_").replace(" ", "_")
                if p.phase.strip().lower().replace("-", "_").replace(" ", "_") in _PHASES
                else "launch",
                day_range=p.day_range.strip(),
                objective=p.objective.strip(),
                activities=p.activities,
                budget_inr=p.budget_inr,
            )
            for p in parsed.campaign_phases
            if p.objective or p.activities
        ]
        return {"campaign_phases": phases, "launch_hook": parsed.launch_hook}


# =============================================================================
# F33 - SEO & Content Strategy Agent
# =============================================================================


class SEOOut(AgentOutput):
    target_keywords: list[str] = Field(default_factory=list)
    content_topics: list[str] = Field(default_factory=list)
    content_frequency: str = ""
    content_formats: list[str] = Field(default_factory=list)


class SEOContentAgent(Agent):
    spec = AgentSpec(
        agent_id="seo_content",
        department=DEPT,
        feature="F33",
        schema=SEOOut,
        tier=ModelTier.FAST,
        max_tokens=1000,
    )
    system = (
        "You are a local SEO strategist. You favour location-qualified long-tail "
        "keywords that an Indian local business can realistically rank for."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "personas")}

Build the SEO and content strategy and return JSON with these keys:
{{
  "target_keywords": ["12-15 keywords, most including the locality or city name"],
  "content_topics": ["8-10 content ideas mapped to search intent"],
  "content_frequency": "one sentence on cadence per format",
  "content_formats": ["3-5 formats, e.g. Instagram Reels, Google Posts, blog"]
}}"""

    def to_patch(self, parsed: SEOOut, state: SharedBusinessState) -> dict:
        return {
            "target_keywords": parsed.target_keywords,
            "content_topics": parsed.content_topics,
            "content_frequency": parsed.content_frequency,
            "content_formats": parsed.content_formats,
        }


# =============================================================================
# F33a - Marketing Consistency & Unit-Economics Agent (stage 3 - synthesis, opt-in)
# =============================================================================


class EvidenceOut(AgentOutput):
    claim: str = ""
    kind: str = "assumption"
    confidence: float | None = None
    source: str = ""


class MarketingCheckOut(AgentOutput):
    marketing_summary: str = ""
    evidence: list[EvidenceOut] = Field(default_factory=list)


_EVIDENCE_KINDS = {"fact", "assumption", "inference", "prediction", "unknown"}


class MarketingConsistencyAgent(Agent):
    """F33a. Runs the deterministic marketing checker over the completed marketing
    and finance sections - channel-share sum, marketing-vs-operating-cost, CAC and
    customers-needed reconciliation, campaign-budget coherence - then writes a
    short evidence-tagged summary. The numbers are computed in Python (they must
    reconcile with Finance), never asserted by the model; the LLM only explains
    them. Falls back to a deterministic summary if the LLM is down."""

    spec = AgentSpec(
        agent_id="marketing_consistency",
        department=DEPT,
        feature="F33a",
        schema=MarketingCheckOut,
        tier=ModelTier.FAST,
        max_tokens=800,
    )
    system = (
        "You are a growth analyst. You explain computed marketing unit economics "
        "and consistency results plainly and are explicit about what is verified "
        "versus assumed."
    )

    def _result(self, state: SharedBusinessState) -> dict:
        marketing = state.get(DEPT.value)
        if marketing is None:
            return {}
        return check_marketing(marketing, state)

    def build_prompt(self, state: SharedBusinessState) -> str:
        result = self._result(state)
        warnings = result.get("marketing_warnings") or []
        computed = (
            f"CHANNEL SHARE TOTAL: {result.get('budget_share_total_pct')}%\n"
            f"CUSTOMERS NEEDED / MONTH: {result.get('customers_needed_monthly')}\n"
            f"ALLOWABLE CAC: Rs {result.get('allowable_cac_inr')}\n"
            f"WARNINGS:\n" + ("\n".join(f"- {w}" for w in warnings) or "- (none)")
            if result
            else "No marketing output was available to check."
        )
        return f"""{context_block(state)}

{upstream_block(state, "personas", "revenue", "costs")}

A deterministic check produced this marketing unit-economics/consistency result:
{computed}

Explain it and return JSON with these keys:
{{
  "marketing_summary": "2-3 sentences on the plan's unit economics and consistency, citing customers-needed and allowable CAC",
  "evidence": [
    {{"claim": "a key marketing claim",
      "kind": "one of fact, assumption, inference, prediction, unknown",
      "confidence": 0.0 to 1.0,
      "source": "share_check / finance / campaign / llm"}}
  ]
}}

The share sum and CAC are computed from the plan and Finance - tag them 'fact' or
'inference'. Tag channel-choice judgements as 'assumption'."""

    def to_patch(self, parsed: MarketingCheckOut, state: SharedBusinessState) -> dict:
        result = self._result(state)
        evidence = [
            EvidenceItem(
                claim=e.claim.strip(),
                kind=e.kind.strip().lower()
                if e.kind.strip().lower() in _EVIDENCE_KINDS
                else "assumption",
                confidence=_clamp_confidence(e.confidence),
                source=e.source.strip()[:40],
            )
            for e in parsed.evidence
            if e.claim and e.claim.strip()
        ]
        summary = parsed.marketing_summary.strip() or fallback_summary(result)
        return {
            **result,  # budget_share_total_pct, customers_needed_monthly, allowable_cac_inr, marketing_warnings
            "marketing_summary": summary,
            "marketing_evidence": evidence,
        }


def _clamp_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


# =============================================================================
# Stage layout
# =============================================================================
#
# Baseline is 4 agents: persona alone (stage 1), then digital/campaign/seo in
# parallel (stage 2). When `enable_marketing_synthesis` is on, a third stage adds
# the consistency/unit-economics agent (F33a), which runs last so it can check the
# completed channel plan and campaign against Finance's revenue and cost figures.


def build_marketing_stages(*, synthesis: bool | None = None) -> tuple[tuple[Agent, ...], ...]:
    """Assemble the marketing stage tuple, honouring the synthesis flag.

    `synthesis=None` reads `settings.enable_marketing_synthesis`; tests pass an
    explicit bool to exercise both topologies.
    """
    if synthesis is None:
        synthesis = settings.enable_marketing_synthesis

    stages: list[tuple[Agent, ...]] = [
        (BuyerPersonaAgent(),),
        (
            DigitalPlanAgent(),
            CampaignPlanAgent(),
            SEOContentAgent(),
        ),
    ]
    if synthesis:
        stages.append((MarketingConsistencyAgent(),))
    return tuple(stages)


MARKETING_STAGES: tuple[tuple[Agent, ...], ...] = build_marketing_stages()
