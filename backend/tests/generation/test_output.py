"""Tests for F42-F46 - the output layer.

Offline. A fully-populated SharedBusinessState is built by hand, then rendered to
JSON, HTML and PDF so the assembly, templating and export paths are all exercised
without an LLM call.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.generation.models.departments import (
    BrandingOutput,
    FinanceOutput,
    MarketingOutput,
    OperationsOutput,
    StrategyOutput,
)
from app.generation.models.intent import Budget, BusinessIntent, Location, Sector
from app.generation.models.state import (
    AgentTrace,
    ApiCallTrace,
    Department,
    RunStatus,
    new_state,
)
from app.generation.output.html import _inr, render_html
from app.generation.output.package import build_metadata, build_package, business_name_for
from app.generation.output.pdf import PdfUnavailable, available_backend, pdf_health, render_pdf
from app.generation.output.sections import (
    SECTION_ORDER,
    SECTIONS,
    SECTIONS_BY_KEY,
    describe_sections,
    section_payload,
    sections_for,
)


# =============================================================================
# Fixture state
# =============================================================================


def populated_state():
    state = new_state("sess-out", "Ice cream shop in Andheri West, Rs 15L budget")
    state["intent"] = BusinessIntent(
        business_type="ice_cream_shop",
        business_type_label="Ice Cream Shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        location=Location(area="Andheri West"),
        budget=Budget(amount=1_500_000, specified=True),
        is_physical=True,
        requires_operations=True,
    )

    state["strategy"] = StrategyOutput(
        executive_summary="A premium gelato outlet in Andheri West targeting young families.",
        vision="Mumbai's most loved artisanal gelato brand.",
        mission="Serve honest frozen desserts made fresh daily.",
        business_model_type="B2C retail",
        value_proposition="Fresh small-batch gelato with a genuine sugar-free line.",
        market_size={"tam_inr": 24_000_000_000, "sam_inr": 480_000_000, "som_inr": 4_500_000,
                     "reasoning": "Population 1.2M x 4% penetration x INR 150 spend."},
        market_overview="Mumbai frozen dessert demand grew strongly among young families.",
        market_statistics=["14% CAGR", "INR 2400 crore market"],
        industry_growth_rate_pct=14.0,
        competitors=[
            {"name": "Naturals Ice Cream", "rating": 4.4, "review_count": 1832,
             "price_level": 2, "source": "google_places", "address": "Andheri West"},
            {"name": "Apsara Ice Creams", "source": "openstreetmap"},
        ],
        market_gaps=["no sugar-free range"],
        positioning="Premium artisanal gelato with a sugar-free line.",
        location_score=8.5,
        location_rationale="High footfall retail stretch near the metro.",
        footfall_assessment="Peak 6pm-10pm on weekends.",
        complementary_businesses=["multiplex", "cafes"],
        accessibility_notes=["metro 400m"],
        risks=[
            {"category": "regulatory", "description": "FSSAI licence delay",
             "severity": "high", "likelihood": "medium", "mitigation": "Apply 60 days early"}
        ],
    )

    state["finance"] = FinanceOutput(
        revenue_streams=[{"name": "Dine-in", "description": "walk-in scoops",
                          "monthly_estimate_inr": 400_000, "share_pct": 65}],
        pricing_strategy="Scoops at INR 120, tubs at INR 450.",
        avg_ticket_size_inr=260,
        projected_revenue_y1_inr=7_000_000,
        projected_revenue_y2_inr=9_500_000,
        projected_revenue_y3_inr=12_000_000,
        seasonality_notes="Peaks March to June.",
        setup_costs=[{"name": "Rent deposit", "category": "setup", "subcategory": "deposit",
                      "amount_inr": 450_000, "notes": "6 months"}],
        recurring_costs=[{"name": "Rent", "category": "recurring", "subcategory": "rent",
                          "amount_inr": 75_000}],
        total_setup_cost_inr=1_400_000,
        total_monthly_cost_inr=190_000,
        budget_utilization_pct=93.33,
        within_budget=True,
        funding_approach="Bootstrap INR 10L plus a Mudra Tarun loan.",
        funding_amount_inr=500_000,
        funding_schemes=["PMMY Mudra Tarun"],
        funding_timeline="Sanction expected in 6 weeks.",
        pl_forecast=[
            {"label": "Y1-M01", "revenue_inr": 300_000, "cogs_inr": 120_000,
             "operating_expense_inr": 190_000, "gross_profit_inr": 180_000,
             "net_profit_inr": -10_000, "gross_margin_pct": 60.0, "net_margin_pct": -3.33},
            {"label": "Y1-M02", "revenue_inr": 340_000, "cogs_inr": 136_000,
             "operating_expense_inr": 190_000, "gross_profit_inr": 204_000,
             "net_profit_inr": 14_000, "gross_margin_pct": 60.0, "net_margin_pct": 4.12},
        ],
        gross_margin_pct=60.0,
        net_margin_pct=18.0,
        break_even_month=2,
        benchmark_margin_pct=12.0,
    )

    state["branding"] = BrandingOutput(
        name_candidates=[{"name": "Barfi & Co", "rationale": "Indian rooted", "recommended": True}],
        recommended_name="Barfi & Co",
        personality_traits=["playful", "premium"],
        color_palette={"primary_hex": "#F2C4D0", "secondary_hex": "#2B2D42",
                       "accent_hex": "#C2703D", "rationale": "Soft pink reads as dessert."},
        heading_font="Playfair Display",
        body_font="Inter",
        tone="Warm, playful and confident.",
        taglines=["Small batch, big joy"],
        sample_social_post="New sugar-free pistachio just dropped.",
        voice_dos=["use sensory words"],
        voice_donts=["never use jargon"],
        logo_style="Combination mark",
        visual_mood="Soft pastel palette with generous whitespace.",
        signage_direction="Backlit acrylic sign.",
    )

    state["marketing"] = MarketingOutput(
        channels=[{"name": "Instagram", "budget_share_pct": 40, "monthly_budget_inr": 24_000,
                   "primary_kpi": "reach", "kpi_target": "50k/mo", "rationale": "visual product"}],
        total_marketing_budget_inr=60_000,
        channel_strategy_summary="Concentrate on local discovery first.",
        personas=[{"name": "Ananya the young parent", "age_range": "30-38", "gender": "female",
                   "income_range_inr": "1,20,000-2,00,000", "occupation": "marketing manager",
                   "location": "Andheri West", "values": ["quality"],
                   "pain_points": ["too much sugar for kids"], "buying_triggers": ["weekend treat"],
                   "objections": ["price"]}],
        campaign_phases=[{"phase": "pre_launch", "day_range": "Day 1-30",
                          "objective": "build anticipation", "activities": ["teaser reels"],
                          "budget_inr": 25_000}],
        launch_hook="Buy one get one free for the first 100 customers.",
        target_keywords=["gelato andheri west"],
        content_topics=["how gelato differs from ice cream"],
        content_frequency="Three reels per week.",
        content_formats=["Instagram Reels"],
    )

    state["operations"] = OperationsOutput(
        inventory_requirements=["milk 400L/week"],
        vendors=[{"category": "Dairy", "supplies": "milk and cream",
                  "sourcing_type": "local", "notes": "daily delivery"}],
        inventory_approach="Daily dairy delivery with two days of safety stock.",
        roles=[{"title": "Store manager", "headcount": 1, "monthly_salary_inr": 35_000,
                "hire_month": 1, "responsibilities": ["daily operations"]}],
        total_headcount_y1=4,
        total_monthly_payroll_inr=89_000,
        tools=[{"name": "Petpooja", "purpose": "POS", "cost": "paid", "monthly_cost_inr": 1_200}],
        total_tool_cost_monthly_inr=1_200,
        daily_workflow=[{"order": 1, "name": "Open store", "description": "unlock, check freezers",
                         "owner_role": "Store manager", "depends_on": []}],
        key_processes=["batch production"],
        quality_checkpoints=["freezer temperature log"],
    )

    state["agent_traces"] = [
        AgentTrace(agent_id="market_research", department=Department.STRATEGY, status="completed",
                   provider="groq", model="llama-3.3-70b-versatile",
                   prompt_tokens=120, completion_tokens=240, latency_ms=800),
        AgentTrace(agent_id="brand_naming", department=Department.BRANDING, status="completed",
                   provider="gemini", model="gemini-3.5-flash-lite",
                   prompt_tokens=80, completion_tokens=100, latency_ms=500),
        AgentTrace(agent_id="supply_chain", department=Department.OPERATIONS, status="failed",
                   error="provider down", latency_ms=200),
    ]
    state["api_traces"] = [
        ApiCallTrace(api="google_places", query="Ice Cream Shop in Andheri West",
                     result_count=2, latency_ms=340, retrieved_at=datetime.now(UTC).isoformat()),
        ApiCallTrace(api="serper", query="ice cream market size India",
                     result_count=5, cached=True, latency_ms=12,
                     retrieved_at="2024-01-01T00:00:00+00:00"),
    ]

    run = state["metadata"]
    run.status = RunStatus.COMPLETED
    run.active_departments = list(Department)
    run.skipped_departments = []
    run.routing_reason = "operations active: physical business"
    run.completeness_score = 96.15
    run.total_duration_ms = 9100
    run.completed_at = datetime.now(UTC).isoformat()
    run.validation_warnings = ["missing: finance.break_even_month", "Net margin looks high"]
    return state


# =============================================================================
# F45 - section registry
# =============================================================================


def test_nineteen_sections_registered() -> None:
    assert len(SECTIONS) == 19
    assert len(SECTION_ORDER) == 19


def test_section_keys_are_unique() -> None:
    assert len(set(SECTION_ORDER)) == len(SECTION_ORDER)


def test_every_section_field_exists_on_its_department_model() -> None:
    """Guards the frozen-field contract: the report cannot reference a field the
    schema does not have."""
    from app.generation.models.state import DEPARTMENT_MODELS

    for spec in SECTIONS:
        model_fields = set(DEPARTMENT_MODELS[spec.department].model_fields)
        unknown = set(spec.fields) - model_fields
        assert not unknown, f"{spec.key} references unknown {unknown}"


def test_every_department_contributes_sections() -> None:
    for department in Department:
        assert sections_for(department), department.value


def test_describe_sections_shape() -> None:
    described = describe_sections()
    assert len(described) == 19
    assert set(described[0]) == {"key", "title", "department", "description", "features", "fields"}


def test_section_payload_extracts_only_its_fields() -> None:
    payload = section_payload(populated_state(), "costs")
    assert payload is not None
    assert "total_setup_cost_inr" in payload
    assert "pl_forecast" not in payload  # belongs to projections


def test_section_payload_returns_none_for_empty_department() -> None:
    assert section_payload(new_state("s", "prompt"), "costs") is None


def test_section_payload_returns_none_for_unknown_key() -> None:
    assert section_payload(populated_state(), "nonexistent") is None


def test_section_payload_returns_none_when_all_fields_blank() -> None:
    state = new_state("s", "prompt")
    state["finance"] = FinanceOutput()  # all defaults
    assert section_payload(state, "costs") is None


# =============================================================================
# F42 - package assembly
# =============================================================================


def test_package_includes_all_populated_sections() -> None:
    package = build_package(populated_state())
    assert len(package.sections) == 19
    assert package.present_sections == list(SECTION_ORDER)


def test_package_omits_empty_sections() -> None:
    """A partial run (F52) yields a smaller package, not empty headings."""
    state = populated_state()
    del state["operations"]

    package = build_package(state)
    assert "staffing" not in package.sections
    assert "executive_summary" in package.sections
    assert len(package.sections) == 15


def test_business_name_prefers_the_chosen_brand() -> None:
    assert business_name_for(populated_state()) == "Barfi & Co"


def test_business_name_falls_back_to_intent_label() -> None:
    state = populated_state()
    state["branding"] = BrandingOutput()
    assert business_name_for(state) == "Ice Cream Shop"


def test_business_name_of_empty_state() -> None:
    assert business_name_for(new_state("s", "prompt")) == "Untitled Business"


def test_package_carries_prompt_and_intent() -> None:
    package = build_package(populated_state())
    assert "Andheri West" in package.prompt
    assert package.intent["sector"] == "food_and_beverage"


# =============================================================================
# F46 - generation metadata
# =============================================================================


def test_metadata_counts_agents_and_tokens() -> None:
    meta = build_metadata(populated_state())
    assert meta.agents_total == 3
    assert meta.agents_completed == 2
    assert meta.agents_failed == 1
    assert meta.total_tokens == 540
    assert meta.prompt_tokens == 200
    assert meta.completion_tokens == 340


def test_metadata_records_providers_and_models() -> None:
    meta = build_metadata(populated_state())
    assert meta.providers_used == {"groq": 1, "gemini": 1}
    assert "llama-3.3-70b-versatile" in meta.models_used
    assert "gemini-3.5-flash-lite" in meta.models_used


def test_metadata_attaches_feature_ids_to_agents() -> None:
    """Ties runtime telemetry back to the feature list in the spec."""
    meta = build_metadata(populated_state())
    by_id = {a.agent_id: a for a in meta.agents}
    assert by_id["market_research"].feature == "F20"
    assert by_id["brand_naming"].feature == "F26"


def test_metadata_marks_stale_api_data() -> None:
    """F41: a 2024 retrieval must be flagged, a fresh one must not."""
    meta = build_metadata(populated_state())
    by_api = {c.api: c for c in meta.api_calls}
    assert by_api["google_places"].stale is False
    assert by_api["serper"].stale is True
    assert by_api["serper"].cached is True


def test_metadata_labels_the_rq3_arm() -> None:
    meta = build_metadata(populated_state())
    assert meta.grounding["competitor_source"] == "google_places"
    assert meta.grounding["market_research_source"] == "serper"
    assert meta.grounding["rq3_arm"] == "grounded"


def test_metadata_labels_text_only_arm() -> None:
    state = populated_state()
    state["strategy"].competitors[0].source = "llm_inferred"
    state["api_traces"] = []

    meta = build_metadata(state)
    assert meta.grounding["rq3_arm"] == "text_only"
    assert meta.grounding["market_research_source"] == "llm_inferred"


def test_metadata_records_routing_decision() -> None:
    meta = build_metadata(populated_state())
    assert len(meta.active_departments) == 5
    assert meta.skipped_departments == []
    assert "physical" in meta.routing_reason


# =============================================================================
# F43 - HTML rendering
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_500_000, "15,00,000"),
        (450_000, "4,50,000"),
        (75_000, "75,000"),
        (900, "900"),
        (12_00_00_000, "12,00,00,000"),
        (-10_000, "-10,000"),
        (None, "—"),
        ("", "—"),
    ],
)
def test_inr_uses_indian_digit_grouping(value: object, expected: str) -> None:
    assert _inr(value) == expected


def rendered() -> str:
    return render_html(build_package(populated_state()))


def test_html_is_a_standalone_document() -> None:
    html = rendered()
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    # Self-contained: no external stylesheet or web font, so it works offline
    # and the PDF engine needs no network access.
    assert "<link" not in html
    assert "fonts.googleapis" not in html


def test_html_contains_every_section_title() -> None:
    """Titles are compared escaped, since autoescaping turns "SEO & Content" into
    "SEO &amp; Content"."""
    from html import escape

    html = rendered()
    for spec in SECTIONS:
        assert escape(spec.title) in html, spec.key


def test_html_uses_the_recommended_brand_palette() -> None:
    """The report is styled in the palette Branding chose (F27)."""
    assert "#F2C4D0" in rendered()


def test_html_falls_back_to_default_palette() -> None:
    state = populated_state()
    state["branding"] = BrandingOutput(recommended_name="Plain Name")
    html = render_html(build_package(state))
    assert "#1F3A5F" in html


def test_html_shows_business_name_and_tagline() -> None:
    html = rendered()
    assert "Barfi &amp; Co" in html or "Barfi & Co" in html
    assert "Small batch, big joy" in html


def test_html_renders_currency_with_indian_grouping() -> None:
    assert "15,00,000" in rendered() or "14,00,000" in rendered()


def test_html_includes_metadata_section() -> None:
    html = rendered()
    assert "How This Plan Was Generated" in html
    assert "llama-3.3-70b-versatile" in html
    assert "sess-out" in html


def test_html_labels_verified_competitor_data() -> None:
    assert "verified against" in rendered()


def test_html_labels_unverified_competitor_data() -> None:
    state = populated_state()
    for competitor in state["strategy"].competitors:
        competitor.source = "llm_inferred"
    html = render_html(build_package(state))
    assert "have not been" in html and "verified" in html


def test_html_surfaces_contradictions_but_not_missing_field_notes() -> None:
    html = render_html(build_package(populated_state()))
    assert "Net margin looks high" in html
    # "missing: x" entries are completeness bookkeeping, not reader-facing.
    assert "missing: finance.break_even_month" not in html


def test_html_renders_partial_package() -> None:
    state = populated_state()
    del state["operations"]
    del state["marketing"]
    html = render_html(build_package(state))
    assert "Executive Summary" in html
    assert "Staffing Plan" not in html


def test_html_renders_from_almost_empty_state() -> None:
    """Must not raise even when nearly everything is missing."""
    state = new_state("bare", "a prompt that is long enough")
    state["intent"] = BusinessIntent(business_type="cafe")
    html = render_html(build_package(state))
    assert "<!DOCTYPE html>" in html


def test_html_escapes_user_content() -> None:
    state = populated_state()
    state["branding"].recommended_name = "<script>alert('x')</script>"
    html = render_html(build_package(state))
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


# =============================================================================
# F44 - PDF export
# =============================================================================


def test_a_pdf_backend_is_available() -> None:
    """xhtml2pdf is pure Python, so this holds on any install."""
    assert available_backend() is not None


def test_pdf_health_shape() -> None:
    health = pdf_health()
    assert health["available"] is True
    assert health["backend"] in ("weasyprint", "xhtml2pdf")
    assert "browser" in health["fallback"]


def test_pdf_renders_valid_document() -> None:
    pdf, backend = render_pdf(rendered())
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 3000
    assert backend in ("weasyprint", "xhtml2pdf")


def test_pdf_unavailable_raises_with_guidance(monkeypatch) -> None:
    from app.generation.output import pdf as module

    monkeypatch.setattr(module, "BACKENDS", ())
    with pytest.raises(PdfUnavailable, match="print to PDF from a browser"):
        render_pdf("<html><body>x</body></html>")


def test_pdf_falls_through_to_the_next_backend(monkeypatch) -> None:
    from app.generation.output import pdf as module

    def broken(html: str) -> bytes:
        raise RuntimeError("native library missing")

    def working(html: str) -> bytes:
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(module, "BACKENDS", (("json", broken), ("io", working)))
    pdf, backend = render_pdf("<html></html>")
    assert backend == "io"
    assert pdf.startswith(b"%PDF")


def test_pdf_rejects_non_pdf_output(monkeypatch) -> None:
    from app.generation.output import pdf as module

    monkeypatch.setattr(module, "BACKENDS", (("io", lambda html: b"not a pdf"),))
    with pytest.raises(PdfUnavailable):
        render_pdf("<html></html>")
