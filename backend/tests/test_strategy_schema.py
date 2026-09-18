"""Strategy schema additions (Phase 1) - frozen-safe field checks.

Proves the new synthesis fields are additive: every existing StrategyOutput
field is untouched and still defaults as before, and the new fields default to
empty/None so a baseline run (synthesis off) produces an identical section.
Fully offline - pure Pydantic.
"""

from __future__ import annotations

from app.models.departments import (
    EvidenceItem,
    StrategicOption,
    StrategyOutput,
    Swot,
)


def test_existing_strategy_fields_unchanged() -> None:
    """The 5-agent baseline fields still exist and default exactly as before."""
    s = StrategyOutput()
    assert s.executive_summary is None
    assert s.vision is None
    assert s.mission is None
    assert s.business_model_type is None
    assert s.market_size is None
    assert s.value_proposition is None
    assert s.risks == []
    assert s.competitors == []
    assert s.market_gaps == []
    assert s.positioning is None
    assert s.market_overview is None
    assert s.market_statistics == []
    assert s.industry_growth_rate_pct is None
    assert s.location_score is None
    assert s.location_rationale is None
    assert s.footfall_assessment is None
    assert s.complementary_businesses == []
    assert s.accessibility_notes == []


def test_new_synthesis_fields_default_empty() -> None:
    """A baseline section (synthesis off) has empty synthesis fields, so the
    stored plan is byte-identical to today when the flag is off."""
    s = StrategyOutput()
    assert s.strategic_options == []
    assert s.recommended_option is None
    assert s.swot is None
    assert s.strategic_rationale is None
    assert s.strategy_evidence == []
    assert s.strategy_confidence is None


def test_strategic_option_model() -> None:
    opt = StrategicOption(
        name="Premium niche",
        thesis="Win on quality, not price",
        pros=["higher margin"],
        cons=["smaller market"],
        est_setup_cost_inr=1_400_000,
        strategic_fit=5,
        cost_efficiency=3,
        risk_level=4,
        reversibility=4,
        competitive_advantage=5,
    )
    assert opt.score is None  # scorer fills this later, not the model
    assert opt.score_breakdown == {}
    assert 1 <= opt.strategic_fit <= 5


def test_strategic_option_rejects_out_of_range_ratings() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StrategicOption(name="bad", strategic_fit=9)


def test_swot_defaults_empty() -> None:
    sw = Swot()
    assert sw.strengths == [] and sw.weaknesses == []
    assert sw.opportunities == [] and sw.threats == []


def test_evidence_item_defaults_to_assumption() -> None:
    e = EvidenceItem(claim="Footfall is high near the metro")
    assert e.kind == "assumption"
    assert e.confidence is None
    assert e.source == ""


def test_strategy_output_roundtrips_with_synthesis_fields() -> None:
    s = StrategyOutput(
        positioning="value-led",
        strategic_options=[StrategicOption(name="A", score=72.5)],
        recommended_option="A",
        swot=Swot(strengths=["brand"]),
        strategic_rationale="A scores highest on fit and advantage.",
        strategy_evidence=[EvidenceItem(claim="market growing", kind="fact", confidence=0.8, source="serper")],
        strategy_confidence=0.7,
    )
    restored = StrategyOutput.model_validate_json(s.model_dump_json())
    assert restored == s
    assert restored.strategic_options[0].score == 72.5
    assert restored.strategy_evidence[0].kind == "fact"
