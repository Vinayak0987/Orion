"""Tests for the deterministic brand checker (Phase 2). Offline, hand-checked."""

from __future__ import annotations

from app.generation.agents.branding_checks import (
    best_text_contrast,
    check_brand,
    check_name_collision,
    coherence_warnings,
    contrast_ratio,
    contrast_rating,
    fallback_summary,
)
from app.generation.models.departments import BrandingOutput, BrandNameCandidate, ColorPalette, Competitor
from app.generation.models.state import Department, new_state


# =============================================================================
# WCAG contrast (canonical values)
# =============================================================================


def test_black_on_white_is_exactly_21() -> None:
    assert contrast_ratio("#000000", "#FFFFFF") == 21.0
    assert contrast_ratio("#000", "#fff") == 21.0  # 3-digit shorthand


def test_same_colour_is_ratio_1() -> None:
    assert contrast_ratio("#123456", "#123456") == 1.0


def test_invalid_hex_returns_none() -> None:
    assert contrast_ratio("nothex", "#FFFFFF") is None
    assert contrast_ratio("#GG0000", "#FFFFFF") is None


def test_white_text_contrast_flags_pale_primary() -> None:
    # A dark navy fill with white text reads well (high ratio).
    dark = best_text_contrast("#0A1A3A")
    assert dark is not None and dark > 7.0
    # A pale yellow reads best on black text -> best_text_contrast is high...
    pale = best_text_contrast("#FFFDE0")
    assert pale is not None and pale > 7.0
    # ...but WHITE text on that pale fill genuinely fails - the actionable risk.
    from app.generation.agents.branding_checks import white_text_contrast
    assert white_text_contrast("#FFFDE0") < 1.5


def test_contrast_rating_bands() -> None:
    assert contrast_rating(21.0) == "AAA"
    assert contrast_rating(7.0) == "AAA"
    assert contrast_rating(4.5) == "AA"
    assert contrast_rating(3.0) == "AA-large"
    assert contrast_rating(2.9) == "fail"
    assert contrast_rating(None) is None


# =============================================================================
# name collision
# =============================================================================


def _state_with_competitors(names: list[str]):
    st = new_state("s", "prompt")
    from app.generation.models.departments import StrategyOutput

    st[Department.STRATEGY.value] = StrategyOutput(
        competitors=[Competitor(name=n) for n in names]
    )
    return st


def test_collision_with_national_chain() -> None:
    b = BrandingOutput(recommended_name="Amul")
    assert check_name_collision(b, new_state("s", "p")) is True


def test_collision_with_competitor() -> None:
    b = BrandingOutput(recommended_name="Sharma Sweets")
    st = _state_with_competitors(["Sharma Sweets", "Gupta Dairy"])
    assert check_name_collision(b, st) is True


def test_no_collision_for_distinct_name() -> None:
    b = BrandingOutput(recommended_name="Frostbyte")
    st = _state_with_competitors(["Sharma Sweets"])
    assert check_name_collision(b, st) is False


def test_no_collision_when_no_name() -> None:
    assert check_name_collision(BrandingOutput(), new_state("s", "p")) is False


# =============================================================================
# coherence warnings
# =============================================================================


def test_coherence_all_good_produces_no_warnings() -> None:
    b = BrandingOutput(
        recommended_name="Frostbyte",
        name_candidates=[BrandNameCandidate(name="Frostbyte")],
        color_palette=ColorPalette(primary_hex="#0A1A3A"),
        personality_traits=["fun", "fresh", "modern"],
        taglines=["Cool by nature"],
        heading_font="Poppins",
        body_font="Inter",
    )
    assert coherence_warnings(b) == []


def test_coherence_flags_recommended_not_in_candidates() -> None:
    b = BrandingOutput(recommended_name="Ghost", name_candidates=[BrandNameCandidate(name="Other")])
    assert any("not in the candidate list" in w for w in coherence_warnings(b))


def test_coherence_flags_identical_fonts() -> None:
    b = BrandingOutput(
        recommended_name="X", name_candidates=[BrandNameCandidate(name="X")],
        color_palette=ColorPalette(primary_hex="#0A1A3A"),
        personality_traits=["a", "b", "c"], taglines=["t"],
        heading_font="Inter", body_font="inter",
    )
    assert any("identical" in w for w in coherence_warnings(b))


# =============================================================================
# top-level check_brand + fallback
# =============================================================================


def test_check_brand_bundles_everything() -> None:
    b = BrandingOutput(
        recommended_name="Frostbyte",
        name_candidates=[BrandNameCandidate(name="Frostbyte")],
        color_palette=ColorPalette(primary_hex="#0A1A3A"),
        personality_traits=["fun", "fresh", "modern"],
        taglines=["Cool by nature"],
        heading_font="Poppins", body_font="Inter",
    )
    result = check_brand(b, new_state("s", "p"))
    assert result["contrast_rating"] in {"AAA", "AA", "AA-large", "fail"}
    assert result["name_collision"] is False
    assert isinstance(result["brand_warnings"], list)
    # deterministic
    assert check_brand(b, new_state("s", "p")) == result


def test_check_brand_flags_failing_contrast() -> None:
    # A pale primary with white text is illegible -> fails contrast rating.
    b = BrandingOutput(
        recommended_name="X", name_candidates=[BrandNameCandidate(name="X")],
        color_palette=ColorPalette(primary_hex="#FFF3B0"),  # pale yellow
        personality_traits=["a", "b", "c"], taglines=["t"],
    )
    result = check_brand(b, new_state("s", "p"))
    assert result["contrast_rating"] in {"fail", "AA-large"}
    assert any("contrast" in w for w in result["brand_warnings"])


def test_fallback_summary_variants() -> None:
    clean = {"contrast_rating": "AA", "brand_warnings": []}
    assert "consistent" in fallback_summary(clean)
    issues = {"contrast_rating": "fail", "brand_warnings": ["primary colour fails"]}
    assert "Issues" in fallback_summary(issues)
