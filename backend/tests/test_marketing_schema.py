"""Marketing schema additions (Phase 1) - frozen-safe field checks.

Proves the new consistency/unit-economics fields are additive: every existing
MarketingOutput field is untouched and defaults as before, and the new fields
default empty/None so a baseline run (synthesis off) produces an identical
section. Fully offline - pure Pydantic.
"""

from __future__ import annotations

from app.models.departments import (
    BuyerPersona,
    Channel,
    EvidenceItem,
    MarketingOutput,
)


def test_existing_marketing_fields_unchanged() -> None:
    m = MarketingOutput()
    assert m.channels == []
    assert m.total_marketing_budget_inr is None
    assert m.channel_strategy_summary is None
    assert m.personas == []
    assert m.campaign_phases == []
    assert m.launch_hook is None
    assert m.target_keywords == []
    assert m.content_topics == []
    assert m.content_frequency is None
    assert m.content_formats == []


def test_new_synthesis_fields_default_empty() -> None:
    m = MarketingOutput()
    assert m.budget_share_total_pct is None
    assert m.customers_needed_monthly is None
    assert m.allowable_cac_inr is None
    assert m.marketing_warnings == []
    assert m.marketing_summary is None
    assert m.marketing_evidence == []


def test_marketing_output_roundtrips_with_new_fields() -> None:
    m = MarketingOutput(
        channels=[Channel(name="Instagram", budget_share_pct=60.0)],
        total_marketing_budget_inr=50_000,
        personas=[BuyerPersona(name="Urban Aditi")],
        budget_share_total_pct=100.0,
        customers_needed_monthly=420,
        allowable_cac_inr=119,
        marketing_warnings=["channel shares sum to 90%, not 100%"],
        marketing_summary="Plan needs ~420 customers/month at Rs 119 CAC; mix sums to 100%.",
        marketing_evidence=[EvidenceItem(claim="420 customers/month needed", kind="inference", confidence=0.6)],
    )
    restored = MarketingOutput.model_validate_json(m.model_dump_json())
    assert restored == m
    assert restored.allowable_cac_inr == 119
    assert restored.customers_needed_monthly == 420
    assert restored.marketing_evidence[0].kind == "inference"
