"""Tests for F17-F37 - the 21 department agents.

Fully offline. A `ScriptedClient` stands in for the LLM and returns a canned
payload per agent schema, so this suite verifies:

  * every agent maps its output onto real, frozen department field names
  * the computed-arithmetic contract (costs, P&L, payroll, channel budgets)
  * value coercion of untrusted LLM strings (hex colours, enums, categories)
  * sub-graph staging, intra-department parallelism and trace accounting
  * per-agent failure isolation
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.agents import all_agents, describe_all_departments
from app.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    coerce_number,
    context_block,
    upstream_block,
)
from app.agents.benchmarks import gross_margin_benchmark, net_margin_benchmark
from app.agents.branding import (
    BRANDING_STAGES,
    BrandIdentityAgent,
    BrandNamingAgent,
    BrandVoiceAgent,
    IdentityOut,
    NamingOut,
    VisualDesignAgent,
    VisualOut,
    VoiceOut,
    _clean_hex,
)
from app.agents.finance import (
    FINANCE_STAGES,
    CostStructureAgent,
    CostStructureOut,
    FundingOut,
    FundingStrategyAgent,
    PLDriversOut,
    PLForecastAgent,
    RevenueModelAgent,
    RevenueModelOut,
    _build_pl,
)
from app.agents.marketing import (
    MARKETING_STAGES,
    BuyerPersonaAgent,
    CampaignOut,
    CampaignPlanAgent,
    DigitalPlanAgent,
    DigitalPlanOut,
    PersonasOut,
    SEOContentAgent,
    SEOOut,
)
from app.agents.operations import (
    OPERATIONS_STAGES,
    ProcessFlowAgent,
    ProcessFlowOut,
    StaffingOut,
    StaffingPlanAgent,
    SupplyChainAgent,
    SupplyChainOut,
    TechStackAgent,
    TechStackOut,
)
from app.agents.registry import DEPARTMENT_STAGES, TOTAL_AGENT_COUNT, agents_for
from app.agents.strategy import (
    STRATEGY_STAGES,
    BusinessPlanningAgent,
    BusinessPlanningOut,
    CompetitiveAnalysisAgent,
    CompetitiveOut,
    LocationIntelligenceAgent,
    LocationOut,
    MarketResearchAgent,
    MarketResearchOut,
    RiskAnalysisAgent,
    RiskAnalysisOut,
)
from app.agents.subgraph import build_department_subgraph, make_department_runner
from app.llm.base import AllProvidersFailed, LLMResponse, ProviderName
from app.models.departments import FinanceOutput, MarketSize, StrategyOutput
from app.models.intent import Budget, BusinessIntent, Location, Sector
from app.models.state import (
    DEPARTMENT_MODELS,
    Department,
    SharedBusinessState,
    merge_section,
    new_state,
)

# =============================================================================
# Scripted LLM client
# =============================================================================


PAYLOADS: dict[type, dict] = {
    MarketResearchOut: {
        "market_overview": "Mumbai frozen dessert demand is growing steadily among "
        "young families, with premium gelato outperforming mass-market ice cream.",
        "market_statistics": ["14% CAGR", "INR 2400 crore market", "38% premium share"],
        "industry_growth_rate_pct": 14.0,
    },
    CompetitiveOut: {
        "competitors": [
            {"name": "Naturals Ice Cream", "rating": 4.4, "price_level": 2, "note": "fruit led"},
            {"name": "Bachelorr's", "rating": 4.1, "price_level": 2, "note": "late night"},
            {"name": "", "rating": None, "price_level": None, "note": "blank must drop"},
            {"name": "Gelato Vinto", "rating": 4.6, "price_level": 9, "note": "bad price level"},
        ],
        "market_gaps": ["no sugar-free range", "no late delivery"],
        "positioning": "Premium artisanal gelato with a sugar-free line.",
    },
    LocationOut: {
        "location_score": 14.0,  # out of range on purpose - must clamp to 10
        "location_rationale": "High footfall retail stretch near the metro station.",
        "footfall_assessment": "Peak 6pm-10pm on weekends.",
        "complementary_businesses": ["multiplex", "cafes", "gyms"],
        "accessibility_notes": ["metro 400m", "paid parking"],
    },
    BusinessPlanningOut: {
        "executive_summary": "A premium gelato outlet in Andheri West targeting "
        "young families and office workers with an artisanal sugar-free range.",
        "vision": "Mumbai's most loved artisanal gelato brand.",
        "mission": "Serve honest frozen desserts made fresh daily.",
        "business_model_type": "B2C retail",
        "value_proposition": "Fresh small-batch gelato with a genuine sugar-free line.",
        "tam_inr": 24_000_000_000,
        "sam_inr": 480_000_000,
        "som_inr": 7_200_000,
        "market_size_reasoning": "Population 1.2M x 4% penetration x INR 150 spend.",
    },
    RiskAnalysisOut: {
        "risks": [
            {
                "category": "regulatory",
                "description": "FSSAI licence delay blocks opening",
                "severity": "high",
                "likelihood": "medium",
                "mitigation": "Apply 60 days before fit-out completes",
            },
            {
                "category": "nonsense_category",
                "description": "Cold chain failure spoils stock",
                "severity": "extreme",
                "likelihood": "sometimes",
                "mitigation": "Backup inverter for freezers",
            },
            {
                "category": "market",
                "description": "",
                "severity": "low",
                "likelihood": "low",
                "mitigation": "blank description must drop",
            },
        ]
    },
    RevenueModelOut: {
        "revenue_streams": [
            {"name": "Dine-in", "description": "walk-in scoops", "monthly_estimate_inr": 400000, "share_pct": 65},
            {"name": "Delivery", "description": "Swiggy and Zomato", "monthly_estimate_inr": 215000, "share_pct": 35},
            {"name": "", "description": "drop me", "monthly_estimate_inr": 0, "share_pct": 0},
        ],
        "pricing_strategy": "Scoops at INR 120, tubs at INR 450, premium tier at INR 180.",
        "avg_ticket_size_inr": 260,
        "projected_revenue_y1_inr": 7_000_000,
        "projected_revenue_y2_inr": 9_500_000,
        "projected_revenue_y3_inr": 12_000_000,
        "seasonality_notes": "Peaks March to June, dips in monsoon.",
    },
    CostStructureOut: {
        "setup_costs": [
            {"name": "Rent deposit", "subcategory": "deposit", "amount_inr": 450000, "notes": "6 months"},
            {"name": "Gelato machine", "subcategory": "equipment", "amount_inr": 600000, "notes": "imported"},
            {"name": "Interiors", "subcategory": "interiors", "amount_inr": 300000, "notes": ""},
            {"name": "Licences", "subcategory": "made_up_thing", "amount_inr": 50000, "notes": "FSSAI"},
            {"name": "", "subcategory": "other", "amount_inr": 99999, "notes": "drop me"},
        ],
        "recurring_costs": [
            {"name": "Rent", "subcategory": "rent", "amount_inr": 75000, "notes": "per month"},
            {"name": "Salaries", "subcategory": "salary", "amount_inr": 90000, "notes": "4 staff"},
            {"name": "Utilities", "subcategory": "utilities", "amount_inr": 25000, "notes": ""},
        ],
    },
    FundingOut: {
        "funding_approach": "Bootstrap INR 10L and raise INR 5L via a Mudra Tarun loan.",
        "funding_amount_inr": 500_000,
        "funding_schemes": ["PMMY Mudra Tarun", "CGTMSE"],
        "funding_timeline": "Apply in month -2, sanction expected in 6 weeks.",
    },
    PLDriversOut: {
        "month_1_revenue_inr": 300_000,
        "month_12_revenue_inr": 740_000,
        "cogs_pct_of_revenue": 40.0,
        "monthly_fixed_opex_inr": 190_000,
        "y2_growth_pct": 35.0,
        "y3_growth_pct": 25.0,
        "assumptions": "Ramp driven by word of mouth and delivery listings.",
    },
    NamingOut: {
        "candidates": [
            {"name": "Frostbite Gelato", "rationale": "memorable and playful"},
            {"name": "Barfi & Co", "rationale": "Indian rooted wordplay"},
            {"name": "", "rationale": "drop me"},
        ],
        "recommended_name": "Barfi & Co",
    },
    IdentityOut: {
        "personality_traits": ["playful", "premium", "honest", "fresh"],
        "primary_hex": "F2C4D0",  # missing '#' on purpose
        "secondary_hex": "#2B2D42",
        "accent_hex": "not-a-colour",  # must be dropped
        "palette_rationale": "Soft pink reads as dessert while navy adds premium weight.",
        "heading_font": "Playfair Display",
        "body_font": "Inter",
    },
    VoiceOut: {
        "tone": "Warm, playful and confident without being childish.",
        "taglines": ["Small batch, big joy", "Gelato, honestly made"],
        "sample_social_post": "New sugar-free pistachio just dropped. #AndheriEats",
        "voice_dos": ["use sensory words", "name the ingredients"],
        "voice_donts": ["never use corporate jargon"],
    },
    VisualOut: {
        "logo_style": "Combination mark pairing a wordmark with a scoop icon.",
        "visual_mood": "Soft pastel palette, generous whitespace, close-up macro "
        "photography of texture, warm daylight.",
        "signage_direction": "Backlit acrylic sign with brass detailing.",
    },
    PersonasOut: {
        "personas": [
            {
                "name": "Ananya the young parent",
                "age_range": "30-38",
                "gender": "female",
                "income_range_inr": "1,20,000-2,00,000",
                "occupation": "marketing manager",
                "location": "Andheri West",
                "values": ["quality", "convenience"],
                "pain_points": ["too much sugar for kids", "long delivery waits"],
                "buying_triggers": ["weekend treat", "birthday"],
                "objections": ["price"],
            },
            {
                "name": "Rohit the office worker",
                "age_range": "24-30",
                "gender": "male",
                "income_range_inr": "50,000-90,000",
                "occupation": "analyst",
                "location": "SEEPZ",
                "values": ["value"],
                "pain_points": ["nothing open late"],
                "buying_triggers": ["post-dinner walk"],
                "objections": ["distance"],
            },
            {"name": "", "age_range": "", "gender": "", "income_range_inr": "",
             "occupation": "", "location": "", "values": [], "pain_points": [],
             "buying_triggers": [], "objections": []},
        ]
    },
    DigitalPlanOut: {
        "channels": [
            {"name": "Instagram", "budget_share_pct": 40, "primary_kpi": "reach", "kpi_target": "50k/mo", "rationale": "visual product"},
            {"name": "Google Business Profile", "budget_share_pct": 25, "primary_kpi": "direction requests", "kpi_target": "600/mo", "rationale": "local intent"},
            {"name": "Swiggy ads", "budget_share_pct": 35, "primary_kpi": "orders", "kpi_target": "900/mo", "rationale": "delivery volume"},
            {"name": "", "budget_share_pct": 0, "primary_kpi": "", "kpi_target": "", "rationale": "drop me"},
        ],
        "total_marketing_budget_inr": 60_000,
        "channel_strategy_summary": "Concentrate on local discovery and delivery apps first.",
    },
    CampaignOut: {
        "campaign_phases": [
            {"phase": "pre-launch", "day_range": "Day 1-30", "objective": "build anticipation",
             "activities": ["teaser reels", "influencer seeding"], "budget_inr": 25000},
            {"phase": "launch", "day_range": "Day 31-60", "objective": "drive trial",
             "activities": ["opening offer", "free tasting"], "budget_inr": 45000},
            {"phase": "weird_phase", "day_range": "Day 61-90", "objective": "retain",
             "activities": ["loyalty card"], "budget_inr": 20000},
        ],
        "launch_hook": "Buy one get one free for the first 100 customers each day.",
    },
    SEOOut: {
        "target_keywords": ["gelato andheri west", "best ice cream andheri", "sugar free gelato mumbai"],
        "content_topics": ["how gelato differs from ice cream", "sugar-free dessert guide"],
        "content_frequency": "Three reels and one blog post per week.",
        "content_formats": ["Instagram Reels", "Google Posts", "blog"],
    },
    SupplyChainOut: {
        "inventory_requirements": ["milk 400L/week", "pistachio paste 8kg/month"],
        "vendors": [
            {"category": "Dairy", "supplies": "milk and cream", "sourcing_type": "local", "notes": "daily delivery"},
            {"category": "Nuts", "supplies": "pistachio paste", "sourcing_type": "DIRECT MANUFACTURER", "notes": "bulk"},
            {"category": "Packaging", "supplies": "tubs", "sourcing_type": "invalid_type", "notes": ""},
            {"category": "", "supplies": "drop me", "sourcing_type": "local", "notes": ""},
        ],
        "inventory_approach": "Daily dairy delivery with two days of safety stock on dry goods.",
    },
    StaffingOut: {
        "roles": [
            {"title": "Store manager", "headcount": 1, "monthly_salary_inr": 35000, "hire_month": 1,
             "responsibilities": ["daily operations"]},
            {"title": "Scoop staff", "headcount": 3, "monthly_salary_inr": 18000, "hire_month": 1,
             "responsibilities": ["service", "cleaning"]},
            {"title": "", "headcount": 0, "monthly_salary_inr": 99999, "hire_month": 1,
             "responsibilities": []},
        ]
    },
    TechStackOut: {
        "tools": [
            {"name": "Petpooja", "purpose": "POS and billing", "cost": "paid", "monthly_cost_inr": 1200},
            {"name": "Zoho Books Free", "purpose": "accounting", "cost": "free", "monthly_cost_inr": 0},
            {"name": "WhatsApp Business", "purpose": "customer messaging", "cost": "invalid", "monthly_cost_inr": 0},
            {"name": "", "purpose": "drop me", "cost": "free", "monthly_cost_inr": 0},
        ]
    },
    ProcessFlowOut: {
        "daily_workflow": [
            {"order": 3, "name": "Evening peak service", "description": "all hands on counter",
             "owner_role": "Scoop staff", "depends_on": ["Open store"]},
            {"order": 1, "name": "Open store", "description": "unlock, check freezers",
             "owner_role": "Store manager", "depends_on": []},
            {"order": 0, "name": "Close and reconcile", "description": "cash count",
             "owner_role": "Store manager", "depends_on": ["Evening peak service"]},
            {"order": 5, "name": "", "description": "drop me", "owner_role": "", "depends_on": []},
        ],
        "key_processes": ["batch production", "wastage logging"],
        "quality_checkpoints": ["freezer temperature log", "daily taste check"],
    },
}


class ScriptedClient:
    """Stands in for LLMClient. Returns a canned payload per requested schema."""

    def __init__(self, fail_schemas: set[type] | None = None, delay: float = 0.0) -> None:
        self.fail_schemas = fail_schemas or set()
        self.delay = delay
        self.calls: list[type] = []
        self.windows: dict[type, tuple[float, float]] = {}

    async def complete_json(self, request, schema, repair_attempts: int = 1):
        start = time.perf_counter()
        self.calls.append(schema)
        if self.delay:
            await asyncio.sleep(self.delay)
        self.windows[schema] = (start, time.perf_counter())

        if schema in self.fail_schemas:
            raise AllProvidersFailed({"groq": "rate limited", "gemini": "rate limited"})

        payload = PAYLOADS.get(schema)
        if payload is None:
            raise AssertionError(f"no scripted payload for {schema.__name__}")
        return schema.model_validate(payload), LLMResponse(
            text="{}",
            provider=ProviderName.GROQ,
            model="llama-3.1-8b-instant",
            prompt_tokens=120,
            completion_tokens=240,
            latency_ms=5,
        )


def base_state() -> SharedBusinessState:
    state = new_state("sess-agents", "Ice cream shop in Andheri West, Rs 15L budget")
    state["intent"] = BusinessIntent(
        business_type="ice_cream_shop",
        business_type_label="Ice Cream Shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        location=Location(area="Andheri West"),
        budget=Budget(amount=1_500_000, specified=True),
        is_physical=True,
        requires_operations=True,
    )
    return state


@pytest.fixture(autouse=True)
def no_external_apis(monkeypatch):
    """Force every agent's grounding hook (F38-F40) into its disabled path.

    Without this, `test_every_agent_maps_onto_frozen_field_names` and every
    sub-graph test would issue live Serper searches and Overpass queries on each
    run - spending free-tier credits from the test suite and making results
    depend on the network. Grounding is tested explicitly in the F38/F39 sections
    below, against mocked HTTP.
    """
    from app.agents import strategy as strategy_module
    from app.apis import cache as cache_module
    from app.apis import places as places_module
    from app.apis import serper as serper_module

    for module in (places_module, serper_module, cache_module, strategy_module):
        settings_obj = getattr(module, "settings", None)
        if settings_obj is not None:
            monkeypatch.setattr(settings_obj, "enable_serper_api", False, raising=False)
            monkeypatch.setattr(settings_obj, "enable_places_api", False, raising=False)
            monkeypatch.setattr(settings_obj, "enable_overpass", False, raising=False)
            monkeypatch.setattr(settings_obj, "enable_chroma_cache", False, raising=False)

    # The module-level cache may already hold a live client from another test.
    monkeypatch.setattr(cache_module.knowledge_cache, "_enabled", False, raising=False)
    monkeypatch.setattr(cache_module.knowledge_cache, "_client", None, raising=False)
    monkeypatch.setattr(cache_module.knowledge_cache, "_attempted", True, raising=False)


async def run_agent(agent: Agent, state: SharedBusinessState | None = None, **kwargs) -> dict:
    return await agent.run(state or base_state(), client=ScriptedClient(**kwargs))


# =============================================================================
# Topology
# =============================================================================


def test_twenty_one_agents_registered() -> None:
    assert TOTAL_AGENT_COUNT == 21


def test_agent_ids_are_unique() -> None:
    ids = [a.spec.agent_id for a in all_agents()]
    assert len(ids) == len(set(ids))


def test_every_feature_f17_to_f37_is_covered() -> None:
    features = {a.spec.feature for a in all_agents()}
    expected = {f"F{n}" for n in range(17, 38)}
    assert features == expected


@pytest.mark.parametrize(
    ("department", "count"),
    [
        (Department.STRATEGY, 5),
        (Department.FINANCE, 4),
        (Department.BRANDING, 4),
        (Department.MARKETING, 4),
        (Department.OPERATIONS, 4),
    ],
)
def test_agent_count_per_department(department: Department, count: int) -> None:
    assert len(agents_for(department)) == count


def test_agents_only_belong_to_their_own_department() -> None:
    for department in Department:
        for agent in agents_for(department):
            assert agent.spec.department is department


def test_every_agent_declares_a_pydantic_schema() -> None:
    for agent in all_agents():
        assert issubclass(agent.spec.schema, __import__("pydantic").BaseModel)


def test_describe_all_departments_shape() -> None:
    described = describe_all_departments()
    assert len(described) == 5
    assert sum(d["agent_count"] for d in described) == 21


# =============================================================================
# Prompt construction
# =============================================================================


def test_context_block_contains_all_business_facts() -> None:
    block = context_block(base_state())
    for token in ("Ice Cream Shop", "food_and_beverage", "Andheri West", "15.0 L", "1,500,000"):
        assert token in block


def test_context_block_handles_missing_intent() -> None:
    assert "unspecified" in context_block(new_state("s", "prompt"))


def test_upstream_block_renders_competitors_for_dependent_agent() -> None:
    state = base_state()
    state["strategy"] = StrategyOutput(
        competitors=[{"name": "Naturals", "rating": 4.4}],
        market_gaps=["no sugar-free"],
        market_size=MarketSize(som_inr=7_200_000),
    )
    block = upstream_block(state, "competitors", "market")
    assert "Naturals" in block
    assert "no sugar-free" in block
    assert "7200000" in block


def test_upstream_block_is_empty_when_nothing_upstream() -> None:
    assert upstream_block(base_state(), "competitors", "revenue") == ""


def test_every_agent_prompt_includes_business_context() -> None:
    state = base_state()
    for agent in all_agents():
        prompt = agent.build_prompt(state)
        assert "Ice Cream Shop" in prompt, agent.spec.agent_id
        assert len(prompt) > 200, agent.spec.agent_id


# =============================================================================
# Field mapping - every agent writes only real department fields
# =============================================================================


@pytest.mark.asyncio
async def test_every_agent_maps_onto_frozen_field_names() -> None:
    """Guards against an agent inventing a field name the metrics cannot read."""
    for agent in all_agents():
        update = await run_agent(agent)
        traces = update["agent_traces"]
        assert traces[0].status == "completed", (
            f"{agent.spec.agent_id} failed: {traces[0].error}"
        )
        section_key = agent.spec.department.value
        assert section_key in update, f"{agent.spec.agent_id} wrote no section"
        allowed = set(DEPARTMENT_MODELS[agent.spec.department].model_fields)
        written = {
            k for k, v in update[section_key].model_dump().items() if v not in (None, [], "")
        }
        assert written <= allowed


@pytest.mark.asyncio
async def test_agent_records_provider_and_token_telemetry() -> None:
    update = await run_agent(MarketResearchAgent())
    trace = update["agent_traces"][0]
    assert trace.provider == "groq"
    assert trace.total_tokens == 360
    assert trace.department is Department.STRATEGY
    assert trace.agent_id == "market_research"


# =============================================================================
# Strategy agents
# =============================================================================


@pytest.mark.asyncio
async def test_market_research_agent() -> None:
    section = (await run_agent(MarketResearchAgent()))["strategy"]
    assert section.industry_growth_rate_pct == 14.0
    assert len(section.market_statistics) == 3


@pytest.mark.asyncio
async def test_competitive_agent_drops_blanks_and_clamps_price_level() -> None:
    section = (await run_agent(CompetitiveAnalysisAgent()))["strategy"]
    names = [c.name for c in section.competitors]
    assert "" not in names
    assert len(section.competitors) == 3
    bad = next(c for c in section.competitors if c.name == "Gelato Vinto")
    assert bad.price_level is None  # 9 is out of the 0-4 range
    assert all(c.source == "llm_inferred" for c in section.competitors)


@pytest.mark.asyncio
async def test_location_agent_clamps_score_to_ten() -> None:
    section = (await run_agent(LocationIntelligenceAgent()))["strategy"]
    assert section.location_score == 10.0


@pytest.mark.asyncio
async def test_business_planning_agent_builds_market_size() -> None:
    section = (await run_agent(BusinessPlanningAgent()))["strategy"]
    assert section.market_size is not None
    assert section.market_size.som_inr == 7_200_000
    assert section.market_size.tam_inr > section.market_size.sam_inr
    assert section.business_model_type == "B2C retail"


@pytest.mark.asyncio
async def test_risk_agent_coerces_invalid_enums_and_drops_blanks() -> None:
    section = (await run_agent(RiskAnalysisAgent()))["strategy"]
    assert len(section.risks) == 2  # blank description dropped
    coerced = next(r for r in section.risks if "Cold chain" in r.description)
    assert coerced.category == "operational"  # nonsense_category -> default
    assert coerced.severity == "medium"  # "extreme" -> default
    assert coerced.likelihood == "medium"
    valid = next(r for r in section.risks if "FSSAI" in r.description)
    assert valid.category == "regulatory"
    assert valid.severity == "high"


# =============================================================================
# Finance agents - computed arithmetic
# =============================================================================


@pytest.mark.asyncio
async def test_revenue_agent_drops_blank_streams() -> None:
    section = (await run_agent(RevenueModelAgent()))["finance"]
    assert len(section.revenue_streams) == 2
    assert section.projected_revenue_y1_inr == 7_000_000


@pytest.mark.asyncio
async def test_cost_agent_computes_totals_in_code() -> None:
    section = (await run_agent(CostStructureAgent()))["finance"]

    # 450000 + 600000 + 300000 + 50000 (blank-name row excluded)
    assert section.total_setup_cost_inr == 1_400_000
    # 75000 + 90000 + 25000
    assert section.total_monthly_cost_inr == 190_000
    assert len(section.setup_costs) == 4


@pytest.mark.asyncio
async def test_cost_agent_computes_budget_utilization_against_intent() -> None:
    section = (await run_agent(CostStructureAgent()))["finance"]
    # 1,400,000 of a 1,500,000 budget
    assert section.budget_utilization_pct == pytest.approx(93.33, abs=0.01)
    assert section.within_budget is True


@pytest.mark.asyncio
async def test_cost_agent_flags_budget_overshoot() -> None:
    state = base_state()
    state["intent"] = BusinessIntent(
        business_type="ice_cream_shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        budget=Budget(amount=1_000_000, specified=True),
    )
    section = (await run_agent(CostStructureAgent(), state))["finance"]
    assert section.within_budget is False
    assert section.budget_utilization_pct == 140.0


@pytest.mark.asyncio
async def test_cost_agent_coerces_unknown_subcategory() -> None:
    section = (await run_agent(CostStructureAgent()))["finance"]
    licences = next(c for c in section.setup_costs if c.name == "Licences")
    assert licences.subcategory == "other"
    assert all(c.category == "setup" for c in section.setup_costs)
    assert all(c.category == "recurring" for c in section.recurring_costs)


@pytest.mark.asyncio
async def test_funding_agent() -> None:
    section = (await run_agent(FundingStrategyAgent()))["finance"]
    assert section.funding_amount_inr == 500_000
    assert "PMMY Mudra Tarun" in section.funding_schemes


@pytest.mark.asyncio
async def test_pl_agent_generates_twenty_periods_and_computes_margins() -> None:
    section = (await run_agent(PLForecastAgent()))["finance"]

    assert len(section.pl_forecast) == 20  # 12 monthly + 8 quarterly
    assert section.pl_forecast[0].label == "Y1-M01"
    assert section.pl_forecast[11].label == "Y1-M12"
    assert section.pl_forecast[12].label == "Y2-Q1"
    assert section.pl_forecast[-1].label == "Y3-Q4"

    # COGS is 40%, so gross margin must be 60% by construction.
    assert section.gross_margin_pct == pytest.approx(60.0, abs=0.1)
    assert section.net_margin_pct is not None
    assert section.net_margin_pct < section.gross_margin_pct


@pytest.mark.asyncio
async def test_pl_agent_derives_break_even_month() -> None:
    section = (await run_agent(PLForecastAgent()))["finance"]
    # Opex 190k, gross margin 60%: break-even needs revenue > 316,667.
    # Ramp is 300k -> 740k over 12 months (+40k/month), so month 2 is the first.
    assert section.break_even_month == 2


@pytest.mark.asyncio
async def test_pl_agent_reports_a_steady_state_margin() -> None:
    """F54 compares against a mature-business benchmark, so the agent must expose
    a ramped-up margin alongside the year-1 average."""
    section = (await run_agent(PLForecastAgent()))["finance"]

    assert section.steady_state_net_margin_pct is not None
    assert section.steady_state_net_margin_pct == section.pl_forecast[-1].net_margin_pct
    # Year 1 includes ramp-up, so it is the weaker of the two.
    assert section.steady_state_net_margin_pct >= section.net_margin_pct


@pytest.mark.asyncio
async def test_pl_agent_records_sector_benchmark_for_f54() -> None:
    section = (await run_agent(PLForecastAgent()))["finance"]
    assert section.benchmark_margin_pct == net_margin_benchmark(Sector.FOOD_AND_BEVERAGE)


@pytest.mark.asyncio
async def test_pl_agent_falls_back_to_cost_agent_opex() -> None:
    """When the model omits fixed opex, the cost agent's figure is used."""
    state = base_state()
    state["finance"] = FinanceOutput(total_monthly_cost_inr=190_000)

    class NoOpexClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.monthly_fixed_opex_inr = None
            return parsed, response

    update = await PLForecastAgent().run(state, client=NoOpexClient())
    assert len(update["finance"].pl_forecast) == 20


def test_build_pl_is_deterministic() -> None:
    kwargs = dict(
        start=300_000, end=740_000, cogs_pct=40.0, monthly_opex=190_000,
        y2_growth_pct=35.0, y3_growth_pct=25.0,
    )
    first = [p.model_dump() for p in _build_pl(**kwargs)]
    second = [p.model_dump() for p in _build_pl(**kwargs)]
    assert first == second


def test_build_pl_arithmetic_is_internally_consistent() -> None:
    for period in _build_pl(
        start=300_000, end=740_000, cogs_pct=40.0, monthly_opex=190_000,
        y2_growth_pct=35.0, y3_growth_pct=25.0,
    ):
        assert period.gross_profit_inr == period.revenue_inr - period.cogs_inr
        assert period.net_profit_inr == period.gross_profit_inr - period.operating_expense_inr


def test_build_pl_ramps_revenue_upward() -> None:
    periods = _build_pl(
        start=300_000, end=740_000, cogs_pct=40.0, monthly_opex=190_000,
        y2_growth_pct=35.0, y3_growth_pct=25.0,
    )
    assert periods[0].revenue_inr == 300_000
    assert periods[11].revenue_inr == 740_000


def test_build_pl_forecast_does_not_go_backwards_into_year_two() -> None:
    """Year 2 must grow from the year-1 EXIT rate, not the year-1 total.

    The total is the sum of a ramp and averages well below the month-12 run rate,
    so growing it made revenue fall entering year 2 whenever growth was modest. A
    salon exiting year 1 at Rs 4L/month showed Rs 7.5L year-2 quarters against
    Rs 11L in its own final year-1 quarter, and steady-state margin came out
    negative while month 12 was +20%.
    """
    periods = _build_pl(
        start=100_000, end=400_000, cogs_pct=45.0, monthly_opex=140_000,
        y2_growth_pct=0.0, y3_growth_pct=0.0,
    )
    y1_final_quarter = sum(p.revenue_inr for p in periods[9:12])
    y2_q1 = next(p for p in periods if p.label == "Y2-Q1")

    assert y2_q1.revenue_inr >= y1_final_quarter * 0.9
    # With zero growth the steady-state margin equals the month-12 margin.
    assert periods[-1].net_margin_pct == pytest.approx(periods[11].net_margin_pct, abs=0.5)


def test_build_pl_applies_growth_to_the_exit_rate() -> None:
    periods = _build_pl(
        start=200_000, end=400_000, cogs_pct=40.0, monthly_opex=100_000,
        y2_growth_pct=50.0, y3_growth_pct=0.0,
    )
    # exit rate 400k/month -> 4.8M/year -> +50% = 7.2M -> 1.8M per quarter
    y2_q1 = next(p for p in periods if p.label == "Y2-Q1")
    assert y2_q1.revenue_inr == pytest.approx(1_800_000, rel=0.01)


# =============================================================================
# Branding agents
# =============================================================================


def test_clean_hex_normalizes_and_rejects() -> None:
    assert _clean_hex("F2C4D0") == "#F2C4D0"
    assert _clean_hex("#2B2D42") == "#2B2D42"
    assert _clean_hex("#abc") == "#abc"
    assert _clean_hex("not-a-colour") == ""
    assert _clean_hex("") == ""


@pytest.mark.asyncio
async def test_naming_agent_marks_recommended_candidate() -> None:
    section = (await run_agent(BrandNamingAgent()))["branding"]
    assert section.recommended_name == "Barfi & Co"
    assert len(section.name_candidates) == 2  # blank dropped
    recommended = [c for c in section.name_candidates if c.recommended]
    assert len(recommended) == 1
    assert recommended[0].name == "Barfi & Co"


@pytest.mark.asyncio
async def test_identity_agent_repairs_and_drops_hex_values() -> None:
    section = (await run_agent(BrandIdentityAgent()))["branding"]
    assert section.color_palette is not None
    assert section.color_palette.primary_hex == "#F2C4D0"  # '#' added
    assert section.color_palette.secondary_hex == "#2B2D42"
    assert section.color_palette.accent_hex == ""  # invalid dropped
    assert section.heading_font == "Playfair Display"


@pytest.mark.asyncio
async def test_voice_agent() -> None:
    section = (await run_agent(BrandVoiceAgent()))["branding"]
    assert len(section.taglines) == 2
    assert "#AndheriEats" in section.sample_social_post


@pytest.mark.asyncio
async def test_visual_agent_prompt_adapts_to_physical_vs_digital() -> None:
    physical = VisualDesignAgent().build_prompt(base_state())
    assert "physical outlet" in physical

    digital_state = base_state()
    digital_state["intent"] = BusinessIntent(
        business_type="online_tutoring", sector=Sector.EDUCATION, is_physical=False
    )
    assert "app icon" in VisualDesignAgent().build_prompt(digital_state)


# =============================================================================
# Marketing agents
# =============================================================================


@pytest.mark.asyncio
async def test_persona_agent_drops_blank_persona() -> None:
    section = (await run_agent(BuyerPersonaAgent()))["marketing"]
    assert len(section.personas) == 2
    assert section.personas[0].name.startswith("Ananya")


@pytest.mark.asyncio
async def test_digital_plan_agent_derives_per_channel_budget() -> None:
    section = (await run_agent(DigitalPlanAgent()))["marketing"]
    assert section.total_marketing_budget_inr == 60_000
    assert len(section.channels) == 3
    instagram = next(c for c in section.channels if c.name == "Instagram")
    assert instagram.monthly_budget_inr == 24_000  # 40% of 60,000
    assert sum(c.monthly_budget_inr for c in section.channels) == 60_000


@pytest.mark.asyncio
async def test_campaign_agent_coerces_phase_names() -> None:
    section = (await run_agent(CampaignPlanAgent()))["marketing"]
    phases = [p.phase for p in section.campaign_phases]
    assert phases == ["pre_launch", "launch", "launch"]  # "weird_phase" -> launch
    assert section.launch_hook.startswith("Buy one")


@pytest.mark.asyncio
async def test_seo_agent() -> None:
    section = (await run_agent(SEOContentAgent()))["marketing"]
    assert any("andheri" in k.lower() for k in section.target_keywords)


# =============================================================================
# Operations agents
# =============================================================================


@pytest.mark.asyncio
async def test_supply_chain_agent_normalizes_sourcing_type() -> None:
    section = (await run_agent(SupplyChainAgent()))["operations"]
    assert len(section.vendors) == 3
    nuts = next(v for v in section.vendors if v.category == "Nuts")
    assert nuts.sourcing_type == "direct_manufacturer"  # uppercased+spaced input
    packaging = next(v for v in section.vendors if v.category == "Packaging")
    assert packaging.sourcing_type == "local"  # invalid -> default


@pytest.mark.asyncio
async def test_staffing_agent_computes_headcount_and_payroll() -> None:
    section = (await run_agent(StaffingPlanAgent()))["operations"]
    assert len(section.roles) == 2
    assert section.total_headcount_y1 == 4  # 1 manager + 3 staff
    assert section.total_monthly_payroll_inr == 89_000  # 35000 + 3*18000


@pytest.mark.asyncio
async def test_tech_stack_agent_totals_cost_and_coerces_kind() -> None:
    section = (await run_agent(TechStackAgent()))["operations"]
    assert len(section.tools) == 3
    assert section.total_tool_cost_monthly_inr == 1_200
    whatsapp = next(t for t in section.tools if t.name == "WhatsApp Business")
    assert whatsapp.cost == "paid"  # invalid kind -> conservative default


@pytest.mark.asyncio
async def test_process_flow_agent_sorts_steps_and_fills_missing_order() -> None:
    section = (await run_agent(ProcessFlowAgent()))["operations"]
    assert len(section.daily_workflow) == 3
    orders = [s.order for s in section.daily_workflow]
    assert orders == sorted(orders)
    assert section.daily_workflow[0].name == "Open store"


def test_process_flow_prompt_includes_staffing_roles() -> None:
    state = base_state()
    state["operations"] = __import__(
        "app.models.departments", fromlist=["OperationsOutput"]
    ).OperationsOutput(roles=[{"title": "Store manager", "headcount": 1}])
    assert "Store manager" in ProcessFlowAgent().build_prompt(state)


# =============================================================================
# Failure isolation
# =============================================================================


@pytest.mark.asyncio
async def test_failed_agent_records_trace_and_no_section() -> None:
    update = await run_agent(MarketResearchAgent(), fail_schemas={MarketResearchOut})
    trace = update["agent_traces"][0]
    assert trace.status == "failed"
    assert "strategy" not in update
    assert update["errors"]


@pytest.mark.asyncio
async def test_agent_never_raises_on_provider_failure() -> None:
    for agent in all_agents():
        update = await run_agent(agent, fail_schemas={agent.spec.schema})
        assert update["agent_traces"][0].status == "failed"


@pytest.mark.asyncio
async def test_bad_field_mapping_isolates_to_one_agent() -> None:
    class RogueAgent(MarketResearchAgent):
        spec = AgentSpec(
            agent_id="rogue",
            department=Department.STRATEGY,
            feature="F20",
            schema=MarketResearchOut,
        )

        def to_patch(self, parsed, state):
            return {"finance": {"break_even_month": 1}}  # cross-department write

    update = await run_agent(RogueAgent())
    assert update["agent_traces"][0].status == "failed"
    assert "field mapping failed" in (update["agent_traces"][0].error or "")
    assert "finance" not in update


# =============================================================================
# merge_section reducer
# =============================================================================


def test_merge_section_unions_disjoint_agent_output() -> None:
    left = StrategyOutput(executive_summary="A premium gelato outlet in Andheri West.")
    right = StrategyOutput(location_score=8.5)
    merged = merge_section(left, right)
    assert merged.executive_summary.startswith("A premium")
    assert merged.location_score == 8.5


def test_merge_section_does_not_erase_with_defaults() -> None:
    """The core reason the reducer exists: a sibling agent's empty fields must not
    wipe out output another agent already wrote."""
    left = StrategyOutput(
        executive_summary="A premium gelato outlet in Andheri West.",
        competitors=[{"name": "Naturals"}],
    )
    merged = merge_section(left, StrategyOutput())
    assert merged.executive_summary.startswith("A premium")
    assert len(merged.competitors) == 1


def test_merge_section_later_value_wins() -> None:
    merged = merge_section(StrategyOutput(location_score=5.0), StrategyOutput(location_score=9.0))
    assert merged.location_score == 9.0


def test_merge_section_handles_none_sides() -> None:
    section = StrategyOutput(location_score=7.0)
    assert merge_section(None, section) is section
    assert merge_section(section, None) is section


# =============================================================================
# Lenient coercion of real LLM output
# =============================================================================
#
# Every shape in this section was observed on an actual llama3.2:3b run and
# raised ValidationError before the AgentOutput coercion layer existed.


def test_nested_list_flattens_into_str_list() -> None:
    """Observed: inventory_requirements <- [["Cream","Milk powder"], "Sugar"]"""
    parsed = SupplyChainOut.model_validate(
        {"inventory_requirements": [["Cream", "Milk powder"], "Sugar 40kg"]}
    )
    assert parsed.inventory_requirements == ["Cream, Milk powder", "Sugar 40kg"]


def test_null_and_dict_items_are_handled_in_str_list() -> None:
    parsed = SupplyChainOut.model_validate(
        {"inventory_requirements": [None, {"nuts": "8kg"}, "", "Milk"]}
    )
    assert parsed.inventory_requirements == ["nuts: 8kg", "Milk"]


def test_bare_string_becomes_single_item_list() -> None:
    parsed = ProcessFlowOut.model_validate({"quality_checkpoints": "freezer log"})
    assert parsed.quality_checkpoints == ["freezer log"]


def test_null_list_becomes_empty_list() -> None:
    """Observed: recurring_costs <- null"""
    parsed = CostStructureOut.model_validate(
        {"setup_costs": None, "recurring_costs": None}
    )
    assert parsed.setup_costs == []
    assert parsed.recurring_costs == []


def test_null_string_field_becomes_empty_string() -> None:
    """Observed: owner_role <- null, which broke the whole process_flow agent."""
    parsed = ProcessFlowOut.model_validate(
        {"daily_workflow": [{"order": 1, "name": "Open", "owner_role": None, "description": None}]}
    )
    assert parsed.daily_workflow[0].owner_role == ""
    assert parsed.daily_workflow[0].description == ""


def test_list_value_in_string_field_is_joined() -> None:
    parsed = SupplyChainOut.model_validate(
        {"vendors": [{"category": "Dairy", "supplies": ["milk", "cream"]}]}
    )
    assert parsed.vendors[0].supplies == "milk, cream"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Rs 4,50,000", 450_000),
        ("₹1,50,000", 150_000),
        ("INR 75000", 75_000),
        ("60000 per month", 60_000),
        ("12.5", 12.5),
        ("40%", 40),
        (250_000, 250_000),
        (None, None),
    ],
)
def test_number_strings_are_coerced(raw: object, expected: object) -> None:
    assert coerce_number(raw) == expected


def test_numeric_string_coerced_inside_agent_schema() -> None:
    parsed = CostStructureOut.model_validate(
        {"setup_costs": [{"name": "Deposit", "amount_inr": "Rs 4,50,000"}]}
    )
    assert parsed.setup_costs[0].amount_inr == 450_000


def test_string_order_coerced_to_int() -> None:
    parsed = ProcessFlowOut.model_validate(
        {"daily_workflow": [{"order": "3", "name": "Close"}]}
    )
    assert parsed.daily_workflow[0].order == 3


def test_all_agent_schemas_inherit_lenient_base() -> None:
    """A schema on plain BaseModel would reject the shapes above."""
    for agent in all_agents():
        assert issubclass(agent.spec.schema, AgentOutput), agent.spec.agent_id


def test_unparseable_number_is_left_for_pydantic() -> None:
    assert coerce_number("not a number") == "not a number"


# =============================================================================
# P&L driver fallbacks
# =============================================================================


@pytest.mark.asyncio
async def test_pl_agent_reconstructs_missing_revenue_drivers() -> None:
    """Observed: the model returned no month_1/month_12 revenue, so the whole
    statement was skipped and F54 had nothing to score."""
    state = base_state()
    state["finance"] = FinanceOutput(
        projected_revenue_y1_inr=6_300_000, total_monthly_cost_inr=190_000
    )

    class NoRevenueDriversClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.month_1_revenue_inr = None
            parsed.month_12_revenue_inr = None
            return parsed, response

    section = (await PLForecastAgent().run(state, client=NoRevenueDriversClient()))["finance"]

    assert len(section.pl_forecast) == 20
    # annual/18 and annual/9
    assert section.pl_forecast[0].revenue_inr == 350_000
    assert section.pl_forecast[11].revenue_inr == 700_000
    # The reconstructed ramp reproduces the annual figure it came from.
    y1 = sum(p.revenue_inr for p in section.pl_forecast[:12])
    assert y1 == pytest.approx(6_300_000, rel=0.01)


@pytest.mark.asyncio
async def test_pl_agent_falls_back_to_sector_cogs_benchmark() -> None:
    state = base_state()
    state["finance"] = FinanceOutput(total_monthly_cost_inr=190_000)

    class NoCogsClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.cogs_pct_of_revenue = None
            return parsed, response

    section = (await PLForecastAgent().run(state, client=NoCogsClient()))["finance"]
    # F&B gross benchmark is 60%, so COGS defaults to 40% and margin back to 60%.
    assert section.gross_margin_pct == pytest.approx(
        gross_margin_benchmark(Sector.FOOD_AND_BEVERAGE), abs=0.1
    )


@pytest.mark.asyncio
async def test_pl_agent_gives_up_only_when_nothing_is_available() -> None:
    state = base_state()  # no finance section at all

    class NoDriversClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.month_1_revenue_inr = None
            parsed.month_12_revenue_inr = None
            parsed.monthly_fixed_opex_inr = None
            return parsed, response

    section = (await PLForecastAgent().run(state, client=NoDriversClient()))["finance"]
    assert section.pl_forecast == []
    assert section.benchmark_margin_pct == net_margin_benchmark(Sector.FOOD_AND_BEVERAGE)


# =============================================================================
# P&L opex reconciliation (found by the first evaluation sweep)
# =============================================================================


def test_recurring_opex_excludes_inventory() -> None:
    """COGS is applied separately as a % of revenue, so counting stock purchases
    in opex too would double-charge them."""
    from app.agents.finance import _recurring_opex

    finance = FinanceOutput(
        recurring_costs=[
            {"name": "Rent", "category": "recurring", "subcategory": "rent", "amount_inr": 75_000},
            {"name": "Salaries", "category": "recurring", "subcategory": "salary", "amount_inr": 90_000},
            {"name": "Stock", "category": "recurring", "subcategory": "inventory", "amount_inr": 200_000},
        ],
        total_monthly_cost_inr=365_000,
    )
    assert _recurring_opex(finance) == 165_000


def test_opex_reconciliation_overrides_an_implausible_model_figure() -> None:
    """The sweep showed the P&L agent returning an opex far below the cost base
    its sibling agent had derived, inflating net margin to ~48% against a 12%
    benchmark and driving F54's MAPE into the hundreds."""
    from app.agents.finance import _resolve_opex

    finance = FinanceOutput(
        recurring_costs=[
            {"name": "Rent", "category": "recurring", "subcategory": "rent", "amount_inr": 165_000}
        ]
    )
    assert _resolve_opex(50_000, finance) == 165_000


def test_opex_reconciliation_keeps_a_plausible_model_figure() -> None:
    """Within tolerance the model's judgement about which costs are fixed is kept."""
    from app.agents.finance import _resolve_opex

    finance = FinanceOutput(
        recurring_costs=[
            {"name": "Rent", "category": "recurring", "subcategory": "rent", "amount_inr": 165_000}
        ]
    )
    assert _resolve_opex(160_000, finance) == 160_000


def test_opex_falls_back_to_derived_when_model_omits_it() -> None:
    from app.agents.finance import _resolve_opex

    finance = FinanceOutput(total_monthly_cost_inr=190_000)
    assert _resolve_opex(None, finance) == 190_000


def test_opex_keeps_model_figure_when_no_cost_data_exists() -> None:
    from app.agents.finance import _resolve_opex

    assert _resolve_opex(120_000, None) == 120_000
    assert _resolve_opex(120_000, FinanceOutput()) == 120_000


# =============================================================================
# P&L revenue reconciliation (found by the second evaluation sweep)
# =============================================================================


def test_revenue_ramp_is_clamped() -> None:
    """Observed live: a Rs 12 lakh salon whose month-12 revenue was 180x its
    month-1 figure (Rs 9 crore/month), which made fixed opex negligible and
    floated net margin to 54.7%."""
    from app.agents.finance import MAX_FIRST_YEAR_RAMP, _reconcile_revenue

    start, end = _reconcile_revenue(500_000, 90_000_000, FinanceOutput())
    assert end == start * MAX_FIRST_YEAR_RAMP


def test_revenue_is_rescaled_to_the_revenue_agents_projection() -> None:
    """A linear ramp a->b over 12 months sums to 6*(a+b), so the rescale is exact."""
    from app.agents.finance import _reconcile_revenue

    finance = FinanceOutput(projected_revenue_y1_inr=7_200_000)
    start, end = _reconcile_revenue(500_000, 90_000_000, finance)

    assert 6 * (start + end) == pytest.approx(7_200_000, rel=0.01)
    assert start == 240_000
    assert end == 960_000


def test_plausible_revenue_drivers_pass_through_untouched() -> None:
    from app.agents.finance import _reconcile_revenue

    finance = FinanceOutput(projected_revenue_y1_inr=7_200_000)
    assert _reconcile_revenue(350_000, 850_000, finance) == (350_000, 850_000)


def test_revenue_reconciliation_needs_no_target() -> None:
    from app.agents.finance import _reconcile_revenue

    assert _reconcile_revenue(300_000, 600_000, None) == (300_000, 600_000)


def test_revenue_reconciliation_rejects_a_falling_ramp() -> None:
    from app.agents.finance import _reconcile_revenue

    start, end = _reconcile_revenue(600_000, 100_000, None)
    assert end >= start


@pytest.mark.asyncio
async def test_pl_agent_produces_a_plausible_margin_after_reconciliation() -> None:
    """End-to-end guard on the whole class of bug: absurd drivers must not yield
    an absurd margin."""
    state = base_state()
    state["finance"] = FinanceOutput(
        projected_revenue_y1_inr=7_200_000,
        total_monthly_cost_inr=330_000,
        recurring_costs=[
            {"name": "Rent", "category": "recurring", "subcategory": "rent", "amount_inr": 330_000}
        ],
    )

    class AbsurdRampClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.month_1_revenue_inr = 500_000
            parsed.month_12_revenue_inr = 90_000_000
            return parsed, response

    section = (await PLForecastAgent().run(state, client=AbsurdRampClient()))["finance"]

    y1_revenue = sum(p.revenue_inr for p in section.pl_forecast[:12])
    assert y1_revenue == pytest.approx(7_200_000, rel=0.02)
    # A margin in a defensible range rather than 54.7%.
    assert -50.0 < section.steady_state_net_margin_pct < 50.0


@pytest.mark.asyncio
async def test_pl_agent_uses_the_reconciled_opex() -> None:
    """End-to-end: the resulting statement must agree with the cost structure, so
    the F57 pl_opex_matches_cost_structure check passes."""
    state = base_state()
    state["finance"] = FinanceOutput(
        recurring_costs=[
            {"name": "Rent", "category": "recurring", "subcategory": "rent", "amount_inr": 190_000}
        ],
        total_monthly_cost_inr=190_000,
    )

    class LowOpexClient(ScriptedClient):
        async def complete_json(self, request, schema, repair_attempts: int = 1):
            parsed, response = await super().complete_json(request, schema, repair_attempts)
            parsed.monthly_fixed_opex_inr = 20_000  # implausibly low
            return parsed, response

    section = (await PLForecastAgent().run(state, client=LowOpexClient()))["finance"]

    assert section.pl_forecast[0].operating_expense_inr == 190_000
    # And the margin is now realistic rather than inflated.
    assert section.net_margin_pct is not None
    assert section.net_margin_pct < section.gross_margin_pct


# =============================================================================
# Department sub-graphs
# =============================================================================


@pytest.mark.parametrize(
    ("department", "stages"),
    [
        (Department.STRATEGY, STRATEGY_STAGES),
        (Department.FINANCE, FINANCE_STAGES),
        (Department.BRANDING, BRANDING_STAGES),
        (Department.MARKETING, MARKETING_STAGES),
        (Department.OPERATIONS, OPERATIONS_STAGES),
    ],
)
def test_every_department_subgraph_compiles(department: Department, stages) -> None:
    assert build_department_subgraph(stages, ScriptedClient()) is not None


def test_empty_department_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one agent"):
        build_department_subgraph(())


@pytest.mark.asyncio
async def test_department_runner_forwards_api_traces() -> None:
    """Observed on a live run: competitors came from OpenStreetMap but the package
    reported zero API calls, because the sub-graph runner returned only
    agent_traces and errors. F46 transparency and F55 scoring both need these."""
    from app.agents.base import Agent, AgentSpec, Grounding
    from app.models.state import ApiCallTrace

    class GroundedAgent(Agent):
        spec = AgentSpec(
            agent_id="market_research",
            department=Department.STRATEGY,
            feature="F20",
            schema=MarketResearchOut,
        )

        async def gather_grounding(self, state):
            return Grounding(
                text="verified figure",
                api_traces=[ApiCallTrace(api="serper", result_count=5)],
            )

        def build_prompt(self, state):
            return "prompt with enough length to look real"

        def to_patch(self, parsed, state):
            return {"market_overview": parsed.market_overview}

    runner = make_department_runner(
        Department.STRATEGY, ((GroundedAgent(),),), client=ScriptedClient()
    )
    update = await runner(base_state())

    assert len(update["api_traces"]) == 1
    assert update["api_traces"][0].api == "serper"


@pytest.mark.asyncio
async def test_department_runner_merges_all_agent_output() -> None:
    runner = make_department_runner(
        Department.STRATEGY, STRATEGY_STAGES, client=ScriptedClient()
    )
    update = await runner(base_state())

    section = update["strategy"]
    # All five strategy agents contributed to one section.
    assert section.executive_summary  # F17
    assert section.risks  # F18
    assert section.competitors  # F19
    assert section.market_overview  # F20
    assert section.location_score  # F21
    assert len(update["agent_traces"]) == 5
    assert all(t.status == "completed" for t in update["agent_traces"])


@pytest.mark.asyncio
async def test_department_runner_returns_only_its_own_section() -> None:
    runner = make_department_runner(
        Department.FINANCE, FINANCE_STAGES, client=ScriptedClient()
    )
    update = await runner(base_state())
    section_keys = {k for k in update if k in {d.value for d in Department}}
    assert section_keys == {"finance"}


@pytest.mark.asyncio
async def test_department_runner_does_not_duplicate_pre_existing_traces() -> None:
    """The sub-graph runs on a derived state, so the parent's `operator.add`
    reducer cannot re-append traces that already existed - which would inflate the
    token totals behind F58."""
    from app.models.state import AgentTrace

    state = base_state()
    state["agent_traces"] = [
        AgentTrace(agent_id="earlier", department=Department.STRATEGY, prompt_tokens=999)
    ]

    runner = make_department_runner(
        Department.BRANDING, BRANDING_STAGES, client=ScriptedClient()
    )
    update = await runner(state)

    ids = [t.agent_id for t in update["agent_traces"]]
    assert "earlier" not in ids
    assert len(ids) == 4


@pytest.mark.asyncio
async def test_subgraph_stage_two_agents_run_concurrently() -> None:
    """Branding stage 2 has three agents; they must overlap in time."""
    client = ScriptedClient(delay=0.12)
    runner = make_department_runner(Department.BRANDING, BRANDING_STAGES, client=client)

    started = time.perf_counter()
    await runner(base_state())
    wall_ms = (time.perf_counter() - started) * 1000

    stage2 = [IdentityOut, VoiceOut, VisualOut]
    for i in range(len(stage2)):
        for j in range(i + 1, len(stage2)):
            a_start, a_end = client.windows[stage2[i]]
            b_start, b_end = client.windows[stage2[j]]
            assert a_start < b_end and b_start < a_end

    # 4 agents x 120 ms sequential = 480 ms; two stages should be ~240 ms.
    assert wall_ms < 420, f"expected staged concurrency, took {wall_ms:.0f}ms"


@pytest.mark.asyncio
async def test_subgraph_stage_two_sees_stage_one_output() -> None:
    """Finance stage 2's P&L agent depends on stage 1's cost agent."""
    runner = make_department_runner(
        Department.FINANCE, FINANCE_STAGES, client=ScriptedClient()
    )
    section = (await runner(base_state()))["finance"]

    assert section.total_setup_cost_inr == 1_400_000  # stage 1
    assert len(section.pl_forecast) == 20  # stage 2
    assert section.break_even_month == 2


@pytest.mark.asyncio
async def test_subgraph_survives_one_failing_agent() -> None:
    client = ScriptedClient(fail_schemas={CompetitiveOut})
    runner = make_department_runner(Department.STRATEGY, STRATEGY_STAGES, client=client)
    update = await runner(base_state())

    statuses = {t.agent_id: t.status for t in update["agent_traces"]}
    assert statuses["competitive_analysis"] == "failed"
    assert statuses["market_research"] == "completed"
    assert statuses["business_planning"] == "completed"
    assert update["strategy"].market_overview  # siblings still wrote
    assert update["strategy"].competitors == []


@pytest.mark.asyncio
async def test_subgraph_survives_all_agents_failing() -> None:
    client = ScriptedClient(fail_schemas=set(PAYLOADS))
    runner = make_department_runner(Department.MARKETING, MARKETING_STAGES, client=client)
    update = await runner(base_state())

    assert all(t.status == "failed" for t in update["agent_traces"])
    assert "marketing" not in update
    assert len(update["errors"]) == 4
