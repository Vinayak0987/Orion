"""F45 - Section-level access.

One registry defines the report's sections: their order, titles, source department
and which fields belong to each. Everything downstream reads from it - the JSON
package (F42), the HTML report (F43), the PDF (F44) and the per-section API.

Keeping this in one place means a section cannot appear in the HTML but be missing
from the JSON, and the frontend can request `finance` alone without the backend
re-deriving what "finance" means.

Sections are finer-grained than departments: Strategy produces four distinct
report sections, which is what lets the frontend collapse them independently and
lets a caller re-fetch just the financial projections.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.generation.models.state import Department, SharedBusinessState, is_meaningful


@dataclass(frozen=True, slots=True)
class SectionSpec:
    key: str
    title: str
    department: Department
    fields: tuple[str, ...]
    description: str = ""
    features: tuple[str, ...] = field(default_factory=tuple)


SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec(
        key="executive_summary",
        title="Executive Summary",
        department=Department.STRATEGY,
        fields=("executive_summary", "vision", "mission", "value_proposition", "business_model_type"),
        description="What the business is and why it wins",
        features=("F17",),
    ),
    SectionSpec(
        key="market_analysis",
        title="Market Analysis",
        department=Department.STRATEGY,
        fields=("market_overview", "market_statistics", "industry_growth_rate_pct", "market_size"),
        description="Demand, trends and market sizing",
        features=("F17", "F20"),
    ),
    SectionSpec(
        key="competition",
        title="Competitive Landscape",
        department=Department.STRATEGY,
        fields=("competitors", "market_gaps", "positioning"),
        description="Who else is nearby and how to position against them",
        features=("F19", "F38"),
    ),
    SectionSpec(
        key="location",
        title="Location Intelligence",
        department=Department.STRATEGY,
        fields=(
            "location_score",
            "location_rationale",
            "footfall_assessment",
            "complementary_businesses",
            "accessibility_notes",
        ),
        description="Site suitability and accessibility",
        features=("F21",),
    ),
    SectionSpec(
        key="risks",
        title="Risk Assessment",
        department=Department.STRATEGY,
        fields=("risks",),
        description="What can go wrong and how to mitigate it",
        features=("F18",),
    ),
    SectionSpec(
        key="revenue",
        title="Revenue Model",
        department=Department.FINANCE,
        fields=(
            "revenue_streams",
            "pricing_strategy",
            "avg_ticket_size_inr",
            "projected_revenue_y1_inr",
            "projected_revenue_y2_inr",
            "projected_revenue_y3_inr",
            "seasonality_notes",
        ),
        description="How the business earns",
        features=("F22",),
    ),
    SectionSpec(
        key="costs",
        title="Cost Structure",
        department=Department.FINANCE,
        fields=(
            "setup_costs",
            "recurring_costs",
            "total_setup_cost_inr",
            "total_monthly_cost_inr",
            "budget_utilization_pct",
            "within_budget",
        ),
        description="Setup and running costs against the stated budget",
        features=("F23",),
    ),
    SectionSpec(
        key="funding",
        title="Funding Strategy",
        department=Department.FINANCE,
        fields=("funding_approach", "funding_amount_inr", "funding_schemes", "funding_timeline"),
        description="How to finance the setup",
        features=("F24",),
    ),
    SectionSpec(
        key="projections",
        title="Financial Projections",
        department=Department.FINANCE,
        fields=(
            "pl_forecast",
            "gross_margin_pct",
            "net_margin_pct",
            "break_even_month",
            "benchmark_margin_pct",
        ),
        description="Three-year P&L, margins and break-even",
        features=("F25",),
    ),
    SectionSpec(
        key="brand",
        title="Brand Identity",
        department=Department.BRANDING,
        fields=(
            "recommended_name",
            "name_candidates",
            "personality_traits",
            "color_palette",
            "heading_font",
            "body_font",
            "logo_style",
            "visual_mood",
            "signage_direction",
        ),
        description="Name, palette, typography and visual direction",
        features=("F26", "F27", "F29"),
    ),
    SectionSpec(
        key="brand_voice",
        title="Brand Voice",
        department=Department.BRANDING,
        fields=("tone", "taglines", "sample_social_post", "voice_dos", "voice_donts"),
        description="How the brand speaks",
        features=("F28",),
    ),
    SectionSpec(
        key="personas",
        title="Target Customers",
        department=Department.MARKETING,
        fields=("personas",),
        description="Who buys, and why",
        features=("F31",),
    ),
    SectionSpec(
        key="marketing",
        title="Marketing Plan",
        department=Department.MARKETING,
        fields=("channels", "total_marketing_budget_inr", "channel_strategy_summary"),
        description="Channel mix and budget allocation",
        features=("F30",),
    ),
    SectionSpec(
        key="campaign",
        title="Launch Campaign",
        department=Department.MARKETING,
        fields=("campaign_phases", "launch_hook"),
        description="The first 90 days",
        features=("F32",),
    ),
    SectionSpec(
        key="content",
        title="SEO & Content",
        department=Department.MARKETING,
        fields=("target_keywords", "content_topics", "content_frequency", "content_formats"),
        description="Organic discovery plan",
        features=("F33",),
    ),
    SectionSpec(
        key="supply_chain",
        title="Supply Chain",
        department=Department.OPERATIONS,
        fields=("inventory_requirements", "vendors", "inventory_approach"),
        description="Sourcing and inventory",
        features=("F34",),
    ),
    SectionSpec(
        key="staffing",
        title="Staffing Plan",
        department=Department.OPERATIONS,
        fields=("roles", "total_headcount_y1", "total_monthly_payroll_inr"),
        description="Roles, salaries and hiring sequence",
        features=("F35",),
    ),
    SectionSpec(
        key="tech_stack",
        title="Technology Stack",
        department=Department.OPERATIONS,
        fields=("tools", "total_tool_cost_monthly_inr"),
        description="Tools to run the business",
        features=("F36",),
    ),
    SectionSpec(
        key="operations",
        title="Daily Operations",
        department=Department.OPERATIONS,
        fields=("daily_workflow", "key_processes", "quality_checkpoints"),
        description="Workflow and quality control",
        features=("F37",),
    ),
)

SECTION_ORDER: tuple[str, ...] = tuple(spec.key for spec in SECTIONS)
SECTIONS_BY_KEY: dict[str, SectionSpec] = {spec.key: spec for spec in SECTIONS}


def sections_for(department: Department) -> list[SectionSpec]:
    return [spec for spec in SECTIONS if spec.department is department]


def section_payload(state: SharedBusinessState, key: str) -> dict | None:
    """Extract one section's fields from state.

    Returns None when the section has no meaningful content, so an incomplete run
    yields a smaller package instead of empty headings.
    """
    spec = SECTIONS_BY_KEY.get(key)
    if spec is None:
        return None

    source = state.get(spec.department.value)
    if source is None:
        return None

    dumped = source.model_dump(mode="json")
    payload = {name: dumped.get(name) for name in spec.fields if name in dumped}

    if not any(is_meaningful(value) for value in payload.values()):
        return None
    return payload


def describe_sections() -> list[dict]:
    """Section catalogue for the API and the frontend's tab layout."""
    return [
        {
            "key": spec.key,
            "title": spec.title,
            "department": spec.department.value,
            "description": spec.description,
            "features": list(spec.features),
            "fields": list(spec.fields),
        }
        for spec in SECTIONS
    ]
