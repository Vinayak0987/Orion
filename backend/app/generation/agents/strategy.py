"""Strategy department - 5 agents (F17-F21).

Stage 1 (parallel)   market_research · competitive_analysis · location_intelligence
Stage 2 (parallel)   business_planning · risk_analysis

Stage 1 gathers external facts; Stage 2 reasons over them. Business Planning
therefore sizes the market against real research and Risk Analysis rates risks
against the competitor set that was actually found, rather than both inventing
their own view of the market.
"""

from __future__ import annotations

from pydantic import Field

from app.generation.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    Grounding,
    context_block,
    upstream_block,
)
from app.generation.agents.strategy_scoring import score_options
from app.generation.apis.cache import (
    COLLECTION_COMPETITORS,
    COLLECTION_MARKET_RESEARCH,
    cache_key,
    knowledge_cache,
)
from app.generation.apis.places import discover_competitors
from app.generation.apis.serper import MarketIntelligence, research_market
from app.generation.config import settings
from app.generation.llm.base import ModelTier
from app.generation.models.departments import (
    Competitor,
    EvidenceItem,
    MarketSize,
    Risk,
    StrategicOption,
    Swot,
)
from app.generation.models.state import ApiCallTrace, Department, SharedBusinessState

DEPT = Department.STRATEGY


# =============================================================================
# F20 - Market Research Agent
# =============================================================================


class MarketResearchOut(AgentOutput):
    market_overview: str = ""
    market_statistics: list[str] = Field(default_factory=list)
    industry_growth_rate_pct: float | None = None


class MarketResearchAgent(Agent):
    """F20 grounded by F39.

    With Serper available the agent receives real search snippets carrying
    citable figures; without it, it falls back to recalled statistics. The
    difference shows up directly in F54, because the revenue and cost agents
    downstream anchor on whatever market numbers this agent produces.
    """

    spec = AgentSpec(
        agent_id="market_research",
        department=DEPT,
        feature="F20",
        schema=MarketResearchOut,
        tier=ModelTier.REASONING,
        max_tokens=900,
    )
    system = (
        "You are a market research analyst covering Indian small and medium "
        "businesses. You cite concrete numbers and avoid generic filler."
    )

    async def gather_grounding(self, state: SharedBusinessState) -> Grounding:
        intent = state.get("intent")
        if intent is None:
            return Grounding()

        key = cache_key(
            "research", intent.business_type, intent.sector.value, intent.location.city
        )
        cached, freshness = knowledge_cache.get(COLLECTION_MARKET_RESEARCH, key)

        if cached is not None:
            intelligence = MarketIntelligence.model_validate(cached)
            traces: list[ApiCallTrace] = [
                ApiCallTrace(
                    api="serper",
                    endpoint="chromadb",
                    query=key,
                    result_count=len(intelligence.snippets),
                    cached=True,
                    retrieved_at=freshness.retrieved_at if freshness else "",
                )
            ]
        else:
            intelligence, traces, freshness = await research_market(intent)
            if not intelligence.is_empty:
                knowledge_cache.put(
                    COLLECTION_MARKET_RESEARCH,
                    key,
                    intelligence.model_dump(mode="json"),
                    source="serper",
                    searchable_text=" ".join(intelligence.queries),
                    extra_metadata={
                        "business_type": intent.business_type,
                        "sector": intent.sector.value,
                        "city": intent.location.city,
                        "snippets": len(intelligence.snippets),
                    },
                )

        block = intelligence.as_prompt_block(freshness)
        if not block:
            return Grounding(api_traces=traces)

        return Grounding(
            text=(
                f"{block}\n\nUse the figures above for market_statistics and "
                f"industry_growth_rate_pct. Quote each statistic with its source "
                f"domain. Do not substitute your own numbers where these apply."
            ),
            api_traces=traces,
        )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

Research this market and return JSON with these keys:
{{
  "market_overview": "3-4 sentences on demand, customer behaviour and trends for this business in this location",
  "market_statistics": ["4-6 specific statistics, each with a number and a unit"],
  "industry_growth_rate_pct": annual growth rate as a number, e.g. 12.5
}}"""

    def to_patch(self, parsed: MarketResearchOut, state: SharedBusinessState) -> dict:
        return {
            "market_overview": parsed.market_overview,
            "market_statistics": parsed.market_statistics,
            "industry_growth_rate_pct": parsed.industry_growth_rate_pct,
        }


# =============================================================================
# F19 - Competitive Analysis Agent
# =============================================================================


class CompetitorOut(AgentOutput):
    name: str = ""
    rating: float | None = None
    price_level: int | None = None
    note: str = ""


class CompetitiveOut(AgentOutput):
    competitors: list[CompetitorOut] = Field(default_factory=list)
    market_gaps: list[str] = Field(default_factory=list)
    positioning: str = ""


class CompetitiveAnalysisAgent(Agent):
    """F19 grounded by F38.

    When a places provider is available, the competitor list is replaced with
    verified nearby businesses and `Competitor.source` becomes `google_places`
    or `openstreetmap`. With no provider, the model's recalled names are kept
    with `source="llm_inferred"`.

    Those two conditions are the arms of RQ3, and the `source` field is what lets
    the F55 scorer tell a stored plan from one arm apart from the other.
    """

    spec = AgentSpec(
        agent_id="competitive_analysis",
        department=DEPT,
        feature="F19",
        schema=CompetitiveOut,
        tier=ModelTier.REASONING,
        max_tokens=1000,
    )
    system = (
        "You are a competitive intelligence analyst. You only name businesses you "
        "are reasonably confident exist in the stated location."
    )

    async def gather_grounding(self, state: SharedBusinessState) -> Grounding:
        intent = state.get("intent")
        if intent is None:
            return Grounding()

        key = cache_key("competitors", intent.business_type, intent.location.query_string)
        cached, freshness = knowledge_cache.get(COLLECTION_COMPETITORS, key)

        if cached is not None and cached.get("competitors"):
            competitors = [Competitor.model_validate(c) for c in cached["competitors"]]
            traces: list[ApiCallTrace] = [
                ApiCallTrace(
                    api=str(cached.get("source") or "cache"),
                    endpoint="chromadb",
                    query=key,
                    result_count=len(competitors),
                    cached=True,
                    retrieved_at=freshness.retrieved_at if freshness else "",
                )
            ]
        else:
            competitors, traces, freshness = await discover_competitors(intent)
            if competitors:
                knowledge_cache.put(
                    COLLECTION_COMPETITORS,
                    key,
                    {
                        "competitors": [c.model_dump(mode="json") for c in competitors],
                        "source": competitors[0].source,
                    },
                    source=competitors[0].source,
                    searchable_text=(
                        f"{intent.business_type_label or intent.business_type} "
                        f"competitors in {intent.location.query_string}"
                    ),
                    extra_metadata={
                        "business_type": intent.business_type,
                        "city": intent.location.city,
                        "count": len(competitors),
                    },
                )

        if not competitors:
            return Grounding(api_traces=traces)

        listing = "\n".join(
            "- "
            + c.name
            + (f" (rating {c.rating}" + (f", {c.review_count} reviews)" if c.review_count else ")") if c.rating else "")
            + (f" - {c.address}" if c.address else "")
            for c in competitors
        )
        provenance = f"({freshness.label()})\n" if freshness else ""
        rating_note = (
            ""
            if any(c.rating is not None for c in competitors)
            else "\nNo ratings are available for these listings; do not invent any."
        )

        return Grounding(
            text=(
                f"{provenance}These businesses were confirmed to exist near "
                f"{intent.location.query_string}:\n{listing}{rating_note}\n"
                f"Base your market_gaps and positioning on THESE businesses."
            ),
            # Verified competitors replace whatever the model produced.
            patch={"competitors": competitors},
            api_traces=traces,
        )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

Analyse the competitive landscape and return JSON with these keys:
{{
  "competitors": [{{"name": "business name", "rating": 4.2, "price_level": 2, "note": "one line on their offering"}}],
  "market_gaps": ["3-5 gaps competitors leave open"],
  "positioning": "2-3 sentences on how this business should position against them"
}}

List up to 6 competitors. price_level is 1 (budget) to 4 (premium)."""

    def to_patch(self, parsed: CompetitiveOut, state: SharedBusinessState) -> dict:
        competitors = [
            Competitor(
                name=c.name.strip(),
                rating=c.rating,
                price_level=c.price_level if c.price_level in (0, 1, 2, 3, 4) else None,
                source="llm_inferred",
                address=c.note[:200],
            )
            for c in parsed.competitors
            if c.name and c.name.strip()
        ]
        return {
            "competitors": competitors,
            "market_gaps": parsed.market_gaps,
            "positioning": parsed.positioning,
        }


# =============================================================================
# F21 - Location Intelligence Agent
# =============================================================================


class LocationOut(AgentOutput):
    location_score: float | None = None
    location_rationale: str = ""
    footfall_assessment: str = ""
    complementary_businesses: list[str] = Field(default_factory=list)
    accessibility_notes: list[str] = Field(default_factory=list)


class LocationIntelligenceAgent(Agent):
    spec = AgentSpec(
        agent_id="location_intelligence",
        department=DEPT,
        feature="F21",
        schema=LocationOut,
        tier=ModelTier.FAST,
        max_tokens=900,
    )
    system = (
        "You are a retail location analyst who knows Indian urban geography, "
        "metro connectivity and neighbourhood commercial character."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

Assess this location and return JSON with these keys:
{{
  "location_score": 0 to 10 rating for this business type at this location,
  "location_rationale": "2-3 sentences justifying the score",
  "footfall_assessment": "2 sentences on footfall volume and peak timings",
  "complementary_businesses": ["3-5 nearby business types that would drive shared traffic"],
  "accessibility_notes": ["3-4 notes on transport, parking and walkability"]
}}"""

    def to_patch(self, parsed: LocationOut, state: SharedBusinessState) -> dict:
        score = parsed.location_score
        if score is not None:
            score = max(0.0, min(10.0, float(score)))
        return {
            "location_score": score,
            "location_rationale": parsed.location_rationale,
            "footfall_assessment": parsed.footfall_assessment,
            "complementary_businesses": parsed.complementary_businesses,
            "accessibility_notes": parsed.accessibility_notes,
        }


# =============================================================================
# F17 - Business Planning Agent (stage 2 - reads stage 1)
# =============================================================================


class BusinessPlanningOut(AgentOutput):
    executive_summary: str = ""
    vision: str = ""
    mission: str = ""
    business_model_type: str = ""
    value_proposition: str = ""
    tam_inr: int | None = None
    sam_inr: int | None = None
    som_inr: int | None = None
    market_size_reasoning: str = ""


class BusinessPlanningAgent(Agent):
    spec = AgentSpec(
        agent_id="business_planning",
        department=DEPT,
        feature="F17",
        schema=BusinessPlanningOut,
        tier=ModelTier.REASONING,
        max_tokens=1200,
    )
    system = (
        "You are a business strategist. You produce concrete, location-specific "
        "plans and size markets with explicit arithmetic."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "market", "competitors")
        intent = state.get("intent")

        # Anchor SOM to the budget. Strategy runs before Finance, so it cannot
        # see the cost structure - and without an anchor it repeatedly produced a
        # SOM far below the cost base Finance then derived from the same budget
        # (observed: SOM Rs 9L/year against Rs 39.6L/year of operating cost).
        # That inconsistency is precisely what the Consistency Score (F57)
        # penalises, so the anchor is given rather than left implicit.
        if intent is not None and intent.budget.specified and intent.budget.amount > 0:
            low = int(intent.budget.amount * 2 / 100_000)
            high = int(intent.budget.amount * 4 / 100_000)
            anchor = (
                f"\nSANITY ANCHOR: a viable single outlet with a setup budget of "
                f"{intent.budget.display} normally turns over roughly Rs {low}L to "
                f"Rs {high}L per year once established. Your som_inr MUST fall inside "
                f"that range. Below Rs {low}L the business cannot cover its own "
                f"running costs; above Rs {high}L is not achievable from a single "
                f"outlet of this size."
            )
        else:
            anchor = (
                "\nSANITY ANCHOR: som_inr must be large enough to cover rent, "
                "salaries and inventory for a business of this scale."
            )

        return f"""{context_block(state)}

RESEARCH FROM THIS RUN:
{upstream or "(none available)"}

Write the business plan core and return JSON with these keys:
{{
  "executive_summary": "4-5 sentences a bank would accept",
  "vision": "one sentence",
  "mission": "one sentence",
  "business_model_type": "e.g. B2C retail, subscription, marketplace",
  "value_proposition": "2 sentences on why customers choose this over competitors",
  "tam_inr": total addressable market in INR per year for the city,
  "sam_inr": serviceable addressable market in INR per year for the locality,
  "som_inr": realistically obtainable revenue in INR for year 1,
  "market_size_reasoning": "show the arithmetic: population, penetration, spend per head"
}}

TAM must be greater than SAM, which must be greater than SOM.{anchor}"""

    def to_patch(self, parsed: BusinessPlanningOut, state: SharedBusinessState) -> dict:
        market: MarketSize | None = None
        if any(v is not None for v in (parsed.tam_inr, parsed.sam_inr, parsed.som_inr)):
            market = MarketSize(
                tam_inr=parsed.tam_inr,
                sam_inr=parsed.sam_inr,
                som_inr=parsed.som_inr,
                reasoning=parsed.market_size_reasoning,
            )
        return {
            "executive_summary": parsed.executive_summary,
            "vision": parsed.vision,
            "mission": parsed.mission,
            "business_model_type": parsed.business_model_type,
            "value_proposition": parsed.value_proposition,
            "market_size": market,
        }


# =============================================================================
# F18 - Risk Analysis Agent (stage 2 - reads stage 1)
# =============================================================================


class RiskOut(AgentOutput):
    category: str = "operational"
    description: str = ""
    severity: str = "medium"
    likelihood: str = "medium"
    mitigation: str = ""


class RiskAnalysisOut(AgentOutput):
    risks: list[RiskOut] = Field(default_factory=list)


_RISK_CATEGORIES = {"financial", "operational", "regulatory", "market", "competitive"}
_RISK_LEVELS = {"high", "medium", "low"}


class RiskAnalysisAgent(Agent):
    spec = AgentSpec(
        agent_id="risk_analysis",
        department=DEPT,
        feature="F18",
        schema=RiskAnalysisOut,
        tier=ModelTier.REASONING,
        max_tokens=1300,
    )
    system = (
        "You are a risk analyst for Indian SMEs. You name specific, actionable "
        "risks including Indian regulatory requirements, not generic ones."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "competitors", "market")
        return f"""{context_block(state)}

RESEARCH FROM THIS RUN:
{upstream or "(none available)"}

Identify the risks and return JSON with this key:
{{
  "risks": [
    {{
      "category": "one of financial, operational, regulatory, market, competitive",
      "description": "the specific risk for this business in this location",
      "severity": "high, medium or low",
      "likelihood": "high, medium or low",
      "mitigation": "one concrete mitigation step"
    }}
  ]
}}

Give 6 to 8 risks covering at least four different categories. Include the
Indian licences this business actually needs (for example FSSAI, Shop and
Establishment, GST) where relevant."""

    def to_patch(self, parsed: RiskAnalysisOut, state: SharedBusinessState) -> dict:
        risks = [
            Risk(
                category=r.category.strip().lower()
                if r.category.strip().lower() in _RISK_CATEGORIES
                else "operational",
                description=r.description.strip(),
                severity=r.severity.strip().lower()
                if r.severity.strip().lower() in _RISK_LEVELS
                else "medium",
                likelihood=r.likelihood.strip().lower()
                if r.likelihood.strip().lower() in _RISK_LEVELS
                else "medium",
                mitigation=r.mitigation.strip(),
            )
            for r in parsed.risks
            if r.description and r.description.strip()
        ]
        # Order by exposure (severity x likelihood) so the most serious risks are
        # first - the synthesis agent (F17b) cites the top risks, and a reader
        # sees the worst risks without scanning the whole list.
        risks.sort(key=_risk_exposure, reverse=True)
        return {"risks": risks}


_RISK_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _risk_exposure(risk: Risk) -> int:
    """severity x likelihood, both mapped high=3/medium=2/low=1."""
    return _RISK_WEIGHT.get(risk.severity, 2) * _RISK_WEIGHT.get(risk.likelihood, 2)


# =============================================================================
# F17a - Strategic Options Agent (stage 3 - reads all of stages 1 & 2)
# =============================================================================


class OptionOut(AgentOutput):
    name: str = ""
    thesis: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    est_setup_cost_inr: int | None = None
    strategic_fit: int | None = None
    cost_efficiency: int | None = None
    risk_level: int | None = None
    reversibility: int | None = None
    competitive_advantage: int | None = None


class StrategicOptionsOut(AgentOutput):
    options: list[OptionOut] = Field(default_factory=list)


class StrategicOptionsAgent(Agent):
    """F17a. Generates 2-3 distinct candidate strategies and rates each on five
    1-5 dimensions. The ranking is NOT decided by the model: the deterministic
    scorer (`strategy_scoring`) weights the ratings into a 0-100 score and picks
    the recommended option. This is what makes 'which strategy is best' an
    auditable computation rather than an LLM assertion.
    """

    spec = AgentSpec(
        agent_id="strategic_options",
        department=DEPT,
        feature="F17a",
        schema=StrategicOptionsOut,
        tier=ModelTier.REASONING,
        max_tokens=1400,
    )
    system = (
        "You are a strategy consultant. You propose genuinely distinct strategic "
        "options - not variations of one idea - and rate each honestly, including "
        "its weaknesses."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "market", "competitors")
        return f"""{context_block(state)}

RESEARCH FROM THIS RUN:
{upstream or "(none available)"}

Propose 2-3 DISTINCT strategic options for this business (e.g. premium-niche vs
value-volume vs delivery-first). Return JSON with this key:
{{
  "options": [
    {{
      "name": "short option name",
      "thesis": "one-line strategic thesis",
      "pros": ["2-4 concrete advantages"],
      "cons": ["2-4 honest disadvantages"],
      "est_setup_cost_inr": rough setup cost for this option as a plain integer,
      "strategic_fit": 1-5 (how well it fits this business/location/budget),
      "cost_efficiency": 1-5 (5 = cheapest to run),
      "risk_level": 1-5 (5 = lowest risk),
      "reversibility": 1-5 (5 = easiest to undo if it fails),
      "competitive_advantage": 1-5 (5 = hardest for rivals to copy)
    }}
  ]
}}

Rate honestly on the 1-5 scales; do not give every option 5s. Do NOT declare a
winner - the scores decide that."""

    def to_patch(self, parsed: StrategicOptionsOut, state: SharedBusinessState) -> dict:
        options = [
            StrategicOption(
                name=o.name.strip(),
                thesis=o.thesis.strip(),
                pros=o.pros,
                cons=o.cons,
                est_setup_cost_inr=o.est_setup_cost_inr,
                strategic_fit=_clamp5(o.strategic_fit),
                cost_efficiency=_clamp5(o.cost_efficiency),
                risk_level=_clamp5(o.risk_level),
                reversibility=_clamp5(o.reversibility),
                competitive_advantage=_clamp5(o.competitive_advantage),
            )
            for o in parsed.options
            if o.name and o.name.strip()
        ]
        # Deterministic scoring decides the ranking and the recommendation.
        ranked = score_options(options)
        recommended = ranked[0].name if ranked else None
        return {"strategic_options": ranked, "recommended_option": recommended}


def _clamp5(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, min(5, int(value)))


# =============================================================================
# F17b - Strategy Synthesis / Recommendation Agent (stage 3)
# =============================================================================


class EvidenceOut(AgentOutput):
    claim: str = ""
    kind: str = "assumption"
    confidence: float | None = None
    source: str = ""


class SynthesisOut(AgentOutput):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    rationale: str = ""
    evidence: list[EvidenceOut] = Field(default_factory=list)
    confidence: float | None = None


_EVIDENCE_KINDS = {"fact", "assumption", "inference", "prediction", "unknown"}


class StrategySynthesisAgent(Agent):
    """F17b. Synthesises a SWOT and a recommendation rationale, and tags each key
    claim as FACT / ASSUMPTION / INFERENCE / PREDICTION / UNKNOWN with a
    confidence. It reads the scored options and the recommended one from the
    options agent, so the rationale explains a decision the scorer already made
    rather than inventing its own winner.
    """

    spec = AgentSpec(
        agent_id="strategy_synthesis",
        department=DEPT,
        feature="F17b",
        schema=SynthesisOut,
        tier=ModelTier.REASONING,
        max_tokens=1300,
    )
    system = (
        "You are a strategy director writing the final recommendation. You are "
        "explicit about what is a verified fact versus an assumption, and you say "
        "plainly when something is unknown rather than inventing it."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "market", "competitors")
        strategy = state.get(DEPT.value)
        options_block = "(no options generated)"
        recommended = "(none)"
        if strategy is not None and strategy.strategic_options:
            recommended = strategy.recommended_option or "(none)"
            options_block = "\n".join(
                f"- {o.name} (score {o.score}): {o.thesis}" for o in strategy.strategic_options
            )
        risk_block = ""
        if strategy is not None and strategy.risks:
            risk_block = "TOP RISKS: " + "; ".join(
                f"{r.description} ({r.severity})" for r in strategy.risks[:4]
            )

        return f"""{context_block(state)}

RESEARCH FROM THIS RUN:
{upstream or "(none available)"}

SCORED STRATEGIC OPTIONS (the scorer already chose the recommendation):
{options_block}
RECOMMENDED OPTION: {recommended}
{risk_block}

Write the strategic synthesis for the RECOMMENDED option and return JSON:
{{
  "strengths": ["3-4 internal strengths"],
  "weaknesses": ["3-4 internal weaknesses"],
  "opportunities": ["3-4 external opportunities"],
  "threats": ["3-4 external threats"],
  "rationale": "3-4 sentences on why the recommended option is best, citing its scores",
  "evidence": [
    {{"claim": "a key claim behind the recommendation",
      "kind": "one of fact, assumption, inference, prediction, unknown",
      "confidence": 0.0 to 1.0,
      "source": "serper / places / budget_anchor / llm"}}
  ],
  "confidence": overall confidence in the recommendation, 0.0 to 1.0
}}

Tag anything you did not verify as 'assumption' or 'unknown'. Do not label a
guess as 'fact'."""

    def to_patch(self, parsed: SynthesisOut, state: SharedBusinessState) -> dict:
        swot = Swot(
            strengths=parsed.strengths,
            weaknesses=parsed.weaknesses,
            opportunities=parsed.opportunities,
            threats=parsed.threats,
        )
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
        return {
            "swot": swot,
            "strategic_rationale": parsed.rationale.strip() or None,
            "strategy_evidence": evidence,
            "strategy_confidence": _clamp_confidence(parsed.confidence),
        }


def _clamp_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


# =============================================================================
# Stage layout
# =============================================================================
#
# The baseline department is 5 agents (F17-F21) across two stages. When
# `enable_strategy_synthesis` is on, a third stage adds the two synthesis agents
# (F17a options, then F17b recommendation) so they can read everything stages 1
# and 2 produced. Options runs before synthesis because the recommendation
# explains the option the scorer chose.


def build_strategy_stages(*, synthesis: bool | None = None) -> tuple[tuple[Agent, ...], ...]:
    """Assemble the strategy stage tuple, honouring the synthesis flag.

    `synthesis=None` reads `settings.enable_strategy_synthesis` (the runtime
    default); tests pass an explicit bool to exercise both topologies.
    """
    if synthesis is None:
        synthesis = settings.enable_strategy_synthesis

    stages: list[tuple[Agent, ...]] = [
        (
            MarketResearchAgent(),
            CompetitiveAnalysisAgent(),
            LocationIntelligenceAgent(),
        ),
        (
            BusinessPlanningAgent(),
            RiskAnalysisAgent(),
        ),
    ]
    if synthesis:
        stages.append((StrategicOptionsAgent(),))
        stages.append((StrategySynthesisAgent(),))
    return tuple(stages)


STRATEGY_STAGES: tuple[tuple[Agent, ...], ...] = build_strategy_stages()
