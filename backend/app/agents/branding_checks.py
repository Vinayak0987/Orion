"""Deterministic brand consistency & accessibility checks (F29a support).

Pure Python, no LLM, no I/O. Branding is a creative department, so this module
deliberately checks only OBJECTIVE, verifiable properties - never taste:

  * WCAG colour contrast  - the W3C relative-luminance formula, a real
    accessibility standard, computed exactly (black-on-white == 21.0).
  * name collision        - does the recommended name reuse a competitor's name
    or a well-known national chain? (best-effort signal, not a trademark search).
  * coherence warnings    - internal-consistency checks (recommended name is in
    the candidate list, palette present, enough traits, heading != body font).

Same discipline as the other departments' scorers: computed here, never asserted
by the model, so it is deterministic and unit-testable. It intentionally does NOT
produce a subjective "brand quality" score - that would not be verifiable.
"""

from __future__ import annotations

from app.models.departments import BrandingOutput
from app.models.state import Department, SharedBusinessState

# A small best-effort denylist of major Indian/national chains a new brand should
# not accidentally reuse. NOT a trademark search - flagged as best-effort.
_CHAIN_DENYLIST: frozenset[str] = frozenset(
    {
        "amul", "haldiram", "haldiram's", "bikanervala", "barista", "chaayos",
        "cafe coffee day", "ccd", "dominos", "domino's", "mcdonalds", "mcdonald's",
        "kfc", "subway", "starbucks", "reliance", "dmart", "big bazaar", "zudio",
        "tanishq", "lenskart", "fabindia", "patanjali", "nykaa", "lakme", "lakmé",
    }
)


# =============================================================================
# WCAG contrast
# =============================================================================


def _hex_to_rgb(hex_colour: str) -> tuple[int, int, int] | None:
    """Parse '#RGB' or '#RRGGBB' into (r, g, b) 0-255, or None if invalid."""
    h = (hex_colour or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.x relative luminance. Channels linearized, then weighted."""

    def channel(value: int) -> float:
        c = value / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float | None:
    """WCAG contrast ratio between two colours, 1.0-21.0, or None if unparseable.

    (L_lighter + 0.05) / (L_darker + 0.05). Black vs white == 21.0 exactly.
    """
    rgb_a, rgb_b = _hex_to_rgb(hex_a), _hex_to_rgb(hex_b)
    if rgb_a is None or rgb_b is None:
        return None
    la, lb = _relative_luminance(rgb_a), _relative_luminance(rgb_b)
    lighter, darker = max(la, lb), min(la, lb)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def best_text_contrast(primary_hex: str) -> float | None:
    """Best contrast of the primary colour against white OR black text.

    A brand picks whichever text colour reads best on its primary, so the
    accessible rating is the better of the two.
    """
    white = contrast_ratio(primary_hex, "#FFFFFF")
    black = contrast_ratio(primary_hex, "#000000")
    ratios = [r for r in (white, black) if r is not None]
    return max(ratios) if ratios else None


def white_text_contrast(primary_hex: str) -> float | None:
    """Contrast of WHITE text on a primary-colour fill.

    This is the realistic accessibility risk for a brand: coloured header/button
    with white text. A pale primary fails it even though `best_text_contrast`
    (which is free to choose black text) would pass - so the rating below is
    computed from this, the stricter and more actionable of the two.
    """
    return contrast_ratio(primary_hex, "#FFFFFF")


def contrast_rating(ratio: float | None) -> str | None:
    """WCAG rating band for a contrast ratio (normal-size text thresholds).

    AAA >= 7.0, AA >= 4.5, AA-large >= 3.0 (large/bold text only), else fail.
    """
    if ratio is None:
        return None
    if ratio >= 7.0:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3.0:
        return "AA-large"
    return "fail"


# =============================================================================
# name collision
# =============================================================================


def _competitor_names(state: SharedBusinessState) -> set[str]:
    strategy = state.get(Department.STRATEGY.value)
    if strategy is None or not strategy.competitors:
        return set()
    return {c.name.strip().lower() for c in strategy.competitors if c.name.strip()}


def check_name_collision(branding: BrandingOutput, state: SharedBusinessState) -> bool:
    """True if the recommended name reuses a competitor name or a known chain.

    Comparison is case-insensitive and whole-name (substring collisions on very
    short names are avoided to prevent false positives)."""
    name = (branding.recommended_name or "").strip().lower()
    if not name:
        return False
    if name in _CHAIN_DENYLIST or name in _competitor_names(state):
        return True
    return False


# =============================================================================
# coherence warnings + top-level check
# =============================================================================


def coherence_warnings(branding: BrandingOutput) -> list[str]:
    warnings: list[str] = []

    if branding.recommended_name:
        names = {c.name.strip().lower() for c in branding.name_candidates}
        if branding.recommended_name.strip().lower() not in names:
            warnings.append("recommended name is not in the candidate list")
    else:
        warnings.append("no recommended brand name was produced")

    if branding.color_palette is None:
        warnings.append("no colour palette was produced")

    if len(branding.personality_traits) < 3:
        warnings.append("fewer than 3 personality traits defined")

    if not branding.taglines:
        warnings.append("no taglines were produced")

    if (
        branding.heading_font
        and branding.body_font
        and branding.heading_font.strip().lower() == branding.body_font.strip().lower()
    ):
        warnings.append("heading and body font are identical (no typographic contrast)")

    return warnings


def check_brand(branding: BrandingOutput, state: SharedBusinessState) -> dict:
    """Everything F29a writes, computed deterministically. Returns a dict of the
    frozen field names so the agent's to_patch is a thin pass-through."""
    primary = branding.color_palette.primary_hex if branding.color_palette else ""
    # Rate white text on the primary fill - the realistic brand risk (a pale
    # primary with white text is illegible even if black text would have worked).
    ratio = white_text_contrast(primary)
    rating = contrast_rating(ratio)

    warnings = coherence_warnings(branding)
    if rating == "fail":
        warnings.append(
            f"primary colour {primary} fails WCAG contrast (ratio {ratio}) - "
            f"text on it will be hard to read"
        )
    elif rating == "AA-large":
        warnings.append(
            f"primary colour {primary} only meets AA for large text (ratio {ratio})"
        )

    collision = check_name_collision(branding, state)
    if collision:
        warnings.append(
            f"recommended name '{branding.recommended_name}' collides with a known "
            f"competitor or national chain"
        )

    return {
        "contrast_ratio": ratio,
        "contrast_rating": rating,
        "name_collision": collision,
        "brand_warnings": warnings,
    }


def fallback_summary(result: dict) -> str:
    """Deterministic summary used when the LLM synthesis pass is unavailable."""
    rating = result.get("contrast_rating")
    warnings = result.get("brand_warnings") or []
    contrast_part = (
        f"primary colour contrast rates {rating}"
        if rating
        else "colour contrast could not be assessed"
    )
    if not warnings:
        return f"Brand is internally consistent; {contrast_part}."
    return f"{contrast_part.capitalize()}. Issues: " + "; ".join(warnings[:3]) + "."
