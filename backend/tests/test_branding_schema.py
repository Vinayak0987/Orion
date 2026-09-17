"""Branding schema additions (Phase 1) - frozen-safe field checks.

Proves the new brand-consistency/accessibility fields are additive: every
existing BrandingOutput field is untouched and defaults as before, and the new
fields default empty/None so a baseline run (synthesis off) produces an
identical section. Fully offline - pure Pydantic.
"""

from __future__ import annotations

from app.models.departments import (
    BrandNameCandidate,
    BrandingOutput,
    ColorPalette,
    EvidenceItem,
)


def test_existing_branding_fields_unchanged() -> None:
    b = BrandingOutput()
    assert b.name_candidates == []
    assert b.recommended_name is None
    assert b.personality_traits == []
    assert b.color_palette is None
    assert b.heading_font is None
    assert b.body_font is None
    assert b.tone is None
    assert b.taglines == []
    assert b.sample_social_post is None
    assert b.voice_dos == []
    assert b.voice_donts == []
    assert b.logo_style is None
    assert b.visual_mood is None
    assert b.signage_direction is None


def test_new_synthesis_fields_default_empty() -> None:
    b = BrandingOutput()
    assert b.contrast_ratio is None
    assert b.contrast_rating is None
    assert b.name_collision is None
    assert b.brand_warnings == []
    assert b.brand_summary is None
    assert b.brand_evidence == []


def test_branding_output_roundtrips_with_new_fields() -> None:
    b = BrandingOutput(
        recommended_name="Frostbyte",
        name_candidates=[BrandNameCandidate(name="Frostbyte", recommended=True)],
        color_palette=ColorPalette(primary_hex="#0B5", secondary_hex="#FFF"),
        contrast_ratio=4.8,
        contrast_rating="AA",
        name_collision=False,
        brand_warnings=["heading and body font are identical"],
        brand_summary="Primary colour passes AA; name is distinct from competitors.",
        brand_evidence=[EvidenceItem(claim="contrast 4.8 passes AA", kind="fact", confidence=1.0)],
    )
    restored = BrandingOutput.model_validate_json(b.model_dump_json())
    assert restored == b
    assert restored.contrast_rating == "AA"
    assert restored.name_collision is False
    assert restored.brand_evidence[0].kind == "fact"
