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
from app.llm.base import ModelTier
from app.models.departments import BuyerPersona, CampaignPhase, Channel
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

Give 4 to 6 channels whose budget_share_pct values sum to 100.
Keep total_marketing_budget_inr below the monthly operating cost shown above."""

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

Give exactly 3 phases: pre_launch, launch, post_launch."""

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
# Stage layout
# =============================================================================

MARKETING_STAGES: tuple[tuple[Agent, ...], ...] = (
    (BuyerPersonaAgent(),),
    (
        DigitalPlanAgent(),
        CampaignPlanAgent(),
        SEOContentAgent(),
    ),
)
