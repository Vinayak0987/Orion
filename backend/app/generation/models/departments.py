"""Department output schemas - the per-section slices of SharedBusinessState.

Every field is Optional so a partially-completed run is still a valid object
(F52 partial results, F16 completeness scoring).

Field names here are FROZEN: the evaluation metrics (F54-F57) and the report
templates (F43) both index into these names. Add new optional fields freely;
never rename an existing one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# =============================================================================
# STRATEGY (F17 - F21)
# =============================================================================


class MarketSize(BaseModel):
    """TAM/SAM/SOM. Feeds the Consistency Score (F57) against finance revenue."""

    tam_inr: int | None = Field(default=None, description="Total addressable market, INR/year")
    sam_inr: int | None = Field(default=None, description="Serviceable addressable market")
    som_inr: int | None = Field(default=None, description="Serviceable obtainable market, year 1")
    reasoning: str = ""
    sources: list[str] = Field(default_factory=list)


class Competitor(BaseModel):
    """One real competitor from Google Places (F19, F38)."""

    name: str
    address: str = ""
    rating: float | None = None
    review_count: int | None = None
    price_level: int | None = Field(default=None, ge=0, le=4)
    distance_m: int | None = None
    place_id: str = ""
    source: str = Field(default="google_places", description="google_places | llm_inferred")


class Risk(BaseModel):
    category: str  # financial | operational | regulatory | market | competitive
    description: str
    severity: str  # high | medium | low
    likelihood: str  # high | medium | low
    mitigation: str = ""


# --- F17a/F17b synthesis models (additive; the baseline 5 agents ignore them) ---


class StrategicOption(BaseModel):
    """One candidate strategy the business could pursue (F17a).

    The LLM supplies the qualitative content and 1-5 sub-ratings; `score` and
    `score_breakdown` are computed deterministically in Python by
    `app.generation.agents.strategy_scoring`, never asserted by the model - the same
    "totals computed in code" discipline the finance agents use.
    """

    name: str
    thesis: str = ""  # one-line strategic thesis
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    est_setup_cost_inr: int | None = None
    # 1 (worst) .. 5 (best) sub-ratings the model fills; the scorer weights them.
    strategic_fit: int | None = Field(default=None, ge=1, le=5)
    cost_efficiency: int | None = Field(default=None, ge=1, le=5)
    risk_level: int | None = Field(default=None, ge=1, le=5)  # 5 = low risk
    reversibility: int | None = Field(default=None, ge=1, le=5)  # 5 = easily reversed
    competitive_advantage: int | None = Field(default=None, ge=1, le=5)
    # Computed in Python:
    score: float | None = None  # 0-100 weighted score
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class Swot(BaseModel):
    """SWOT synthesis produced by the recommendation agent (F17b)."""

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """One evidence-tagged strategic claim (F17b).

    `kind` follows the FACT / ASSUMPTION / INFERENCE / UNKNOWN discipline so a
    reader can tell a grounded fact from a model guess, exactly like the
    planning layer's `inferences`.
    """

    claim: str
    kind: str = "assumption"  # fact | assumption | inference | prediction | unknown
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = ""  # e.g. "serper", "places", "llm", "budget_anchor"


class StrategyOutput(BaseModel):
    # F17 Business Planning
    executive_summary: str | None = None
    vision: str | None = None
    mission: str | None = None
    business_model_type: str | None = None
    market_size: MarketSize | None = None
    value_proposition: str | None = None

    # F18 Risk Analysis
    risks: list[Risk] = Field(default_factory=list)

    # F19 Competitive Analysis
    competitors: list[Competitor] = Field(default_factory=list)
    market_gaps: list[str] = Field(default_factory=list)
    positioning: str | None = None

    # F20 Market Research
    market_overview: str | None = None
    market_statistics: list[str] = Field(default_factory=list)
    industry_growth_rate_pct: float | None = None

    # F21 Location Intelligence
    location_score: float | None = Field(default=None, ge=0, le=10)
    location_rationale: str | None = None
    footfall_assessment: str | None = None
    complementary_businesses: list[str] = Field(default_factory=list)
    accessibility_notes: list[str] = Field(default_factory=list)

    # --- F17a Strategic Options (synthesis, opt-in) ---
    strategic_options: list[StrategicOption] = Field(default_factory=list)
    recommended_option: str | None = None

    # --- F17b Recommendation / Synthesis (opt-in) ---
    swot: Swot | None = None
    strategic_rationale: str | None = None
    strategy_evidence: list[EvidenceItem] = Field(default_factory=list)
    strategy_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


# =============================================================================
# FINANCE (F22 - F25)
# =============================================================================


class RevenueStream(BaseModel):
    name: str
    description: str = ""
    monthly_estimate_inr: int | None = None
    share_pct: float | None = None


class CostItem(BaseModel):
    name: str
    category: str  # setup | recurring
    subcategory: str = ""  # rent | salary | equipment | utilities | marketing | other
    amount_inr: int
    notes: str = ""


class PLPeriod(BaseModel):
    label: str  # "Y1-M01" | "Y2-Q1"
    revenue_inr: int
    cogs_inr: int = 0
    operating_expense_inr: int = 0
    gross_profit_inr: int | None = None
    net_profit_inr: int | None = None
    gross_margin_pct: float | None = None
    net_margin_pct: float | None = None


class CashFlowPeriod(BaseModel):
    """One month's closing cash position (F25a, opt-in).

    Computed deterministically in `app.generation.agents.finance_cashflow` from the P&L
    net-profit path plus opening capital, setup spend and external funding -
    never generated by the model. Answers "when does the business run lowest on
    cash", which the profit-only P&L does not surface.
    """

    label: str  # "M01" .. "M12"
    net_cash_flow_inr: int  # cash in - cash out for the month
    closing_cash_inr: int  # running balance at month end


class FinanceOutput(BaseModel):
    # F22 Revenue Model
    revenue_streams: list[RevenueStream] = Field(default_factory=list)
    pricing_strategy: str | None = None
    avg_ticket_size_inr: int | None = None
    projected_revenue_y1_inr: int | None = None
    projected_revenue_y2_inr: int | None = None
    projected_revenue_y3_inr: int | None = None
    seasonality_notes: str | None = None

    # F23 Cost Structure
    setup_costs: list[CostItem] = Field(default_factory=list)
    recurring_costs: list[CostItem] = Field(default_factory=list)
    total_setup_cost_inr: int | None = None
    total_monthly_cost_inr: int | None = None
    budget_utilization_pct: float | None = None
    within_budget: bool | None = None

    # F24 Funding Strategy
    funding_approach: str | None = None
    funding_amount_inr: int | None = None
    funding_schemes: list[str] = Field(default_factory=list)
    funding_timeline: str | None = None

    # F25 P&L Forecast — the MAPE source for F54
    pl_forecast: list[PLPeriod] = Field(default_factory=list)
    gross_margin_pct: float | None = None
    net_margin_pct: float | None = Field(
        default=None, description="Year-1 average net margin, including ramp-up"
    )
    steady_state_net_margin_pct: float | None = Field(
        default=None,
        description=(
            "Net margin once the business is ramped up (final forecast period). "
            "This is the figure comparable to a mature-business sector benchmark; "
            "the year-1 average includes start-up losses and is not."
        ),
    )
    break_even_month: int | None = None
    benchmark_margin_pct: float | None = Field(
        default=None, description="MSME industry benchmark used for comparison"
    )

    # --- F25a Cash-Flow & Unit Economics (synthesis, opt-in) ---
    cash_flow: list[CashFlowPeriod] = Field(default_factory=list)
    lowest_cash_month: int | None = None
    lowest_cash_inr: int | None = None
    runway_months: int | None = None
    contribution_margin_pct: float | None = None
    finance_summary: str | None = None
    finance_evidence: list[EvidenceItem] = Field(default_factory=list)


class BrandNameCandidate(BaseModel):
    name: str
    rationale: str = ""
    recommended: bool = False


class ColorPalette(BaseModel):
    primary_hex: str
    secondary_hex: str = ""
    accent_hex: str = ""
    rationale: str = ""


class BrandingOutput(BaseModel):
    # F26 Naming
    name_candidates: list[BrandNameCandidate] = Field(default_factory=list)
    recommended_name: str | None = None

    # F27 Identity
    personality_traits: list[str] = Field(default_factory=list)
    color_palette: ColorPalette | None = None
    heading_font: str | None = None
    body_font: str | None = None

    # F28 Voice
    tone: str | None = None
    taglines: list[str] = Field(default_factory=list)
    sample_social_post: str | None = None
    voice_dos: list[str] = Field(default_factory=list)
    voice_donts: list[str] = Field(default_factory=list)

    # F29 Visual Direction
    logo_style: str | None = None
    visual_mood: str | None = None
    signage_direction: str | None = None

    # --- F29a Brand Consistency & Accessibility (synthesis, opt-in) ---
    contrast_ratio: float | None = None
    contrast_rating: str | None = None  # AAA | AA | AA-large | fail
    name_collision: bool | None = None
    brand_warnings: list[str] = Field(default_factory=list)
    brand_summary: str | None = None
    brand_evidence: list[EvidenceItem] = Field(default_factory=list)


# =============================================================================
# MARKETING (F30 - F33)
# =============================================================================


class Channel(BaseModel):
    name: str
    budget_share_pct: float | None = None
    monthly_budget_inr: int | None = None
    primary_kpi: str = ""
    kpi_target: str = ""
    rationale: str = ""


class BuyerPersona(BaseModel):
    name: str
    age_range: str = ""
    gender: str = ""
    income_range_inr: str = ""
    occupation: str = ""
    location: str = ""
    values: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)


class CampaignPhase(BaseModel):
    phase: str  # pre_launch | launch | post_launch
    day_range: str  # "Day 1-30"
    objective: str = ""
    activities: list[str] = Field(default_factory=list)
    budget_inr: int | None = None


class MarketingOutput(BaseModel):
    # F30 Digital Plan
    channels: list[Channel] = Field(default_factory=list)
    total_marketing_budget_inr: int | None = None
    channel_strategy_summary: str | None = None

    # F31 Personas
    personas: list[BuyerPersona] = Field(default_factory=list)

    # F32 Campaign
    campaign_phases: list[CampaignPhase] = Field(default_factory=list)
    launch_hook: str | None = None

    # F33 SEO / Content
    target_keywords: list[str] = Field(default_factory=list)
    content_topics: list[str] = Field(default_factory=list)
    content_frequency: str | None = None
    content_formats: list[str] = Field(default_factory=list)

    # --- F33a Marketing Consistency & Unit Economics (synthesis, opt-in) ---
    budget_share_total_pct: float | None = None
    customers_needed_monthly: int | None = None
    allowable_cac_inr: int | None = None
    marketing_warnings: list[str] = Field(default_factory=list)
    marketing_summary: str | None = None
    marketing_evidence: list[EvidenceItem] = Field(default_factory=list)


# =============================================================================
# OPERATIONS (F34 - F37) — conditional department
# =============================================================================


class Vendor(BaseModel):
    category: str
    supplies: str = ""
    sourcing_type: str = ""  # local | wholesale | online | direct_manufacturer
    notes: str = ""


class Role(BaseModel):
    title: str
    headcount: int = 1
    monthly_salary_inr: int | None = None
    hire_month: int | None = None
    responsibilities: list[str] = Field(default_factory=list)


class ToolRecommendation(BaseModel):
    name: str
    purpose: str = ""
    cost: str = "free"  # free | freemium | paid
    monthly_cost_inr: int | None = None


class ProcessStep(BaseModel):
    order: int
    name: str
    description: str = ""
    owner_role: str = ""
    depends_on: list[str] = Field(default_factory=list)


class Licence(BaseModel):
    """One licence/permit an Indian SME needs (F34a, opt-in).

    `evidence_kind` follows the FACT/ASSUMPTION/INFERENCE/UNKNOWN discipline:
    'fact' means it came from the built-in sector gazetteer (a known requirement),
    'assumption'/'inference' means the LLM suggested it. Costs and applicability
    are jurisdiction- and time-sensitive, so `notes` always tells the operator to
    verify with the issuing authority.
    """

    name: str
    authority: str = ""
    when_required: str = ""
    est_cost_inr: int | None = None
    evidence_kind: str = "assumption"  # fact | assumption | inference | unknown
    notes: str = ""


class OperationsOutput(BaseModel):
    # F34 Supply Chain
    inventory_requirements: list[str] = Field(default_factory=list)
    vendors: list[Vendor] = Field(default_factory=list)
    inventory_approach: str | None = None

    # F35 Staffing
    roles: list[Role] = Field(default_factory=list)
    total_headcount_y1: int | None = None
    total_monthly_payroll_inr: int | None = None

    # F36 Tech Stack
    tools: list[ToolRecommendation] = Field(default_factory=list)
    total_tool_cost_monthly_inr: int | None = None

    # F37 Process Flow
    daily_workflow: list[ProcessStep] = Field(default_factory=list)
    key_processes: list[str] = Field(default_factory=list)
    quality_checkpoints: list[str] = Field(default_factory=list)

    # --- F34a Compliance & Licensing (synthesis, opt-in) ---
    licences: list[Licence] = Field(default_factory=list)
    compliance_notes: str | None = None

    # --- F37a Operations Feasibility (opt-in) ---
    feasibility_score: int | None = Field(default=None, ge=0, le=100)
    feasibility_warnings: list[str] = Field(default_factory=list)
    operations_summary: str | None = None
    operations_evidence: list[EvidenceItem] = Field(default_factory=list)
