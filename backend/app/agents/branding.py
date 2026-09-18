"""Branding department - 4 agents (F26-F29).

Stage 1 (sequential)  brand_naming
Stage 2 (parallel)    brand_identity ∥ brand_voice ∥ visual_design

Naming runs alone first because the other three all reference the chosen name.
Run in parallel with it, they would each invent a different brand.

These agents use the FAST tier (Llama 3.1 8B): naming and tone are creative
tasks where the 70B model's extra reasoning buys nothing but costs latency and
free-tier quota.
"""

from __future__ import annotations

import re

from pydantic import Field

from app.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    context_block,
    upstream_block,
)
from app.agents.branding_checks import check_brand, fallback_summary
from app.config import settings
from app.llm.base import ModelTier
from app.models.departments import BrandNameCandidate, ColorPalette, EvidenceItem
from app.models.state import Department, SharedBusinessState

DEPT = Department.BRANDING

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _clean_hex(value: str, fallback: str = "") -> str:
    candidate = (value or "").strip()
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    return candidate if _HEX_RE.match(candidate) else fallback


# =============================================================================
# F26 - Brand Naming Agent
# =============================================================================


class NameCandidateOut(AgentOutput):
    name: str = ""
    rationale: str = ""


class NamingOut(AgentOutput):
    candidates: list[NameCandidateOut] = Field(default_factory=list)
    recommended_name: str = ""


class BrandNamingAgent(Agent):
    spec = AgentSpec(
        agent_id="brand_naming",
        department=DEPT,
        feature="F26",
        schema=NamingOut,
        tier=ModelTier.FAST,
        temperature=0.8,  # naming is the one place we want variety
        max_tokens=1000,
    )
    system = (
        "You are a brand naming specialist for the Indian market. You avoid names "
        "that collide with existing national chains."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        upstream = upstream_block(state, "competitors")
        return f"""{context_block(state)}

{upstream}

Generate brand names and return JSON with these keys:
{{
  "candidates": [{{"name": "Brand Name", "rationale": "meaning, pronunciation, memorability"}}],
  "recommended_name": "the single best candidate"
}}

Give 6 to 8 candidates. Mix English and Indian-language-rooted options.
Do not reuse the name of any competitor listed above.
recommended_name must be one of the candidates."""

    def to_patch(self, parsed: NamingOut, state: SharedBusinessState) -> dict:
        recommended = parsed.recommended_name.strip()
        candidates = [
            BrandNameCandidate(
                name=c.name.strip(),
                rationale=c.rationale.strip(),
                recommended=c.name.strip().lower() == recommended.lower(),
            )
            for c in parsed.candidates
            if c.name and c.name.strip()
        ]
        if not recommended and candidates:
            recommended = candidates[0].name
            candidates[0].recommended = True
        return {"name_candidates": candidates, "recommended_name": recommended or None}


# =============================================================================
# F27 - Brand Identity Agent
# =============================================================================


class IdentityOut(AgentOutput):
    personality_traits: list[str] = Field(default_factory=list)
    primary_hex: str = ""
    secondary_hex: str = ""
    accent_hex: str = ""
    palette_rationale: str = ""
    heading_font: str = ""
    body_font: str = ""


class BrandIdentityAgent(Agent):
    spec = AgentSpec(
        agent_id="brand_identity",
        department=DEPT,
        feature="F27",
        schema=IdentityOut,
        tier=ModelTier.FAST,
        max_tokens=900,
    )
    system = (
        "You are a brand identity designer. You name only fonts available free on "
        "Google Fonts, and you give valid 6-digit hex colours."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "brand")}

Define the visual identity and return JSON with these keys:
{{
  "personality_traits": ["4-6 adjectives"],
  "primary_hex": "#RRGGBB",
  "secondary_hex": "#RRGGBB",
  "accent_hex": "#RRGGBB",
  "palette_rationale": "2 sentences on why these colours suit this business and audience",
  "heading_font": "a Google Font name",
  "body_font": "a Google Font name that pairs with it"
}}

Choose a primary colour dark or saturated enough that WHITE text remains legible
on it (it is used for coloured headers and buttons). heading_font and body_font
should differ so there is typographic contrast."""

    def to_patch(self, parsed: IdentityOut, state: SharedBusinessState) -> dict:
        primary = _clean_hex(parsed.primary_hex)
        palette = None
        if primary:
            palette = ColorPalette(
                primary_hex=primary,
                secondary_hex=_clean_hex(parsed.secondary_hex),
                accent_hex=_clean_hex(parsed.accent_hex),
                rationale=parsed.palette_rationale.strip(),
            )
        return {
            "personality_traits": parsed.personality_traits,
            "color_palette": palette,
            "heading_font": parsed.heading_font.strip() or None,
            "body_font": parsed.body_font.strip() or None,
        }


# =============================================================================
# F28 - Brand Voice Agent
# =============================================================================


class VoiceOut(AgentOutput):
    tone: str = ""
    taglines: list[str] = Field(default_factory=list)
    sample_social_post: str = ""
    voice_dos: list[str] = Field(default_factory=list)
    voice_donts: list[str] = Field(default_factory=list)


class BrandVoiceAgent(Agent):
    spec = AgentSpec(
        agent_id="brand_voice",
        department=DEPT,
        feature="F28",
        schema=VoiceOut,
        tier=ModelTier.FAST,
        temperature=0.7,
        max_tokens=1000,
    )
    system = "You are a brand copywriter writing for an Indian urban audience."

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "brand")}

Define the brand voice and return JSON with these keys:
{{
  "tone": "2 sentences describing the communication tone",
  "taglines": ["4-5 tagline options, each under 8 words"],
  "sample_social_post": "an Instagram caption in this voice, with hashtags",
  "voice_dos": ["3-4 things the brand always does in its writing"],
  "voice_donts": ["3-4 things it never does"]
}}"""

    def to_patch(self, parsed: VoiceOut, state: SharedBusinessState) -> dict:
        return {
            "tone": parsed.tone,
            "taglines": parsed.taglines,
            "sample_social_post": parsed.sample_social_post,
            "voice_dos": parsed.voice_dos,
            "voice_donts": parsed.voice_donts,
        }


# =============================================================================
# F29 - Visual Design Direction Agent
# =============================================================================


class VisualOut(AgentOutput):
    logo_style: str = ""
    visual_mood: str = ""
    signage_direction: str = ""


class VisualDesignAgent(Agent):
    spec = AgentSpec(
        agent_id="visual_design",
        department=DEPT,
        feature="F29",
        schema=VisualOut,
        tier=ModelTier.FAST,
        max_tokens=700,
    )
    system = "You are an art director briefing a designer."

    def build_prompt(self, state: SharedBusinessState) -> str:
        intent = state.get("intent")
        physical = intent is not None and intent.is_physical
        signage = (
            "signage and packaging direction for the physical outlet"
            if physical
            else "app icon, website hero and social template direction"
        )
        return f"""{context_block(state)}

{upstream_block(state, "brand")}

Write the visual direction and return JSON with these keys:
{{
  "logo_style": "wordmark, lettermark, icon or combination, with 2 sentences of reasoning",
  "visual_mood": "3-4 sentences describing the visual mood so a designer could execute it",
  "signage_direction": "2-3 sentences on {signage}"
}}"""

    def to_patch(self, parsed: VisualOut, state: SharedBusinessState) -> dict:
        return {
            "logo_style": parsed.logo_style,
            "visual_mood": parsed.visual_mood,
            "signage_direction": parsed.signage_direction,
        }


# =============================================================================
# F29a - Brand Consistency & Accessibility Agent (stage 3 - synthesis, opt-in)
# =============================================================================


class EvidenceOut(AgentOutput):
    claim: str = ""
    kind: str = "assumption"
    confidence: float | None = None
    source: str = ""


class BrandCheckOut(AgentOutput):
    brand_summary: str = ""
    evidence: list[EvidenceOut] = Field(default_factory=list)


_EVIDENCE_KINDS = {"fact", "assumption", "inference", "prediction", "unknown"}


class BrandConsistencyAgent(Agent):
    """F29a. Runs the deterministic brand checker over the completed branding
    section - WCAG colour contrast, name collision, coherence warnings - then
    writes a short evidence-tagged summary. The checks are computed in Python
    (real, verifiable properties), never asserted by the model; the LLM only
    explains them. Falls back to a deterministic summary if the LLM is down."""

    spec = AgentSpec(
        agent_id="brand_consistency",
        department=DEPT,
        feature="F29a",
        schema=BrandCheckOut,
        tier=ModelTier.FAST,
        max_tokens=700,
    )
    system = (
        "You are a brand reviewer. You explain computed accessibility and "
        "consistency results plainly and are explicit about what is verified "
        "versus assumed."
    )

    def _result(self, state: SharedBusinessState) -> dict:
        branding = state.get(DEPT.value)
        if branding is None:
            return {}
        return check_brand(branding, state)

    def build_prompt(self, state: SharedBusinessState) -> str:
        result = self._result(state)
        rating = result.get("contrast_rating")
        collision = result.get("name_collision")
        warnings = result.get("brand_warnings") or []
        computed = (
            f"COLOUR CONTRAST (white text on primary): {result.get('contrast_ratio')} "
            f"({rating})\n"
            f"NAME COLLISION: {'yes' if collision else 'no'}\n"
            f"WARNINGS:\n" + ("\n".join(f"- {w}" for w in warnings) or "- (none)")
            if result
            else "No branding output was available to check."
        )
        return f"""{context_block(state)}

{upstream_block(state, "brand")}

A deterministic check produced this brand accessibility/consistency result:
{computed}

Explain it and return JSON with these keys:
{{
  "brand_summary": "2-3 sentences on the brand's accessibility and consistency, citing the contrast rating and any collision",
  "evidence": [
    {{"claim": "a key brand claim",
      "kind": "one of fact, assumption, inference, prediction, unknown",
      "confidence": 0.0 to 1.0,
      "source": "contrast_check / name_check / palette / llm"}}
  ]
}}

Contrast and collision results are computed facts - tag them 'fact'. Tag taste
judgements as 'assumption'."""

    def to_patch(self, parsed: BrandCheckOut, state: SharedBusinessState) -> dict:
        result = self._result(state)
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
        summary = parsed.brand_summary.strip() or fallback_summary(result)
        return {
            **result,  # contrast_ratio, contrast_rating, name_collision, brand_warnings
            "brand_summary": summary,
            "brand_evidence": evidence,
        }


def _clamp_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


# =============================================================================
# Stage layout
# =============================================================================
#
# Baseline is 4 agents: naming alone (stage 1), then identity/voice/visual in
# parallel (stage 2). When `enable_branding_synthesis` is on, a third stage adds
# the consistency/accessibility agent (F29a), which runs last so it can check the
# completed palette, name and voice.


def build_branding_stages(*, synthesis: bool | None = None) -> tuple[tuple[Agent, ...], ...]:
    """Assemble the branding stage tuple, honouring the synthesis flag.

    `synthesis=None` reads `settings.enable_branding_synthesis`; tests pass an
    explicit bool to exercise both topologies.
    """
    if synthesis is None:
        synthesis = settings.enable_branding_synthesis

    stages: list[tuple[Agent, ...]] = [
        (BrandNamingAgent(),),
        (
            BrandIdentityAgent(),
            BrandVoiceAgent(),
            VisualDesignAgent(),
        ),
    ]
    if synthesis:
        stages.append((BrandConsistencyAgent(),))
    return tuple(stages)


BRANDING_STAGES: tuple[tuple[Agent, ...], ...] = build_branding_stages()
