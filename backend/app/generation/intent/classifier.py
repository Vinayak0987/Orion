"""F1/F2 - Intent Classifier.

The first stage of the pipeline. Turns one free-form prompt into a validated
`BusinessIntent` that the Business Orchestrator (F10) routes on.

Hybrid extraction strategy:

    LLM (semantic)          business_type, business_type_label, sector,
                            location hints, confidence
    Deterministic (exact)   budget amount + scale (F4)
                            location normalization (F3)
                            is_physical / requires_operations (F5, F10)

The split is deliberate. The routing flags and the budget are the two values that
downstream metrics are anchored to, so they must be identical on every run and on
every provider. Everything the LLM contributes is descriptive, not numeric.

If all three providers are unavailable, `classify_intent` degrades to a
keyword-only heuristic instead of raising, so the pipeline always produces a
routable intent.
"""

from __future__ import annotations

import structlog

from app.generation.intent.budget_parser import parse_budget
from app.generation.intent.location_parser import parse_location
from app.generation.intent.schema import IntentExtraction
from app.generation.intent.taxonomy import (
    classify_sector,
    derive_routing_flags,
    fallback_business_type,
)
from app.generation.llm.base import AllProvidersFailed, LLMRequest, ModelTier
from app.generation.llm.chain import JSONParseError, LLMClient, llm_client
from app.generation.models.intent import BusinessIntent, Sector

log = structlog.get_logger(__name__)

MIN_PROMPT_LENGTH = 10
MAX_PROMPT_LENGTH = 500

HEURISTIC_CONFIDENCE = 0.35

SYSTEM_PROMPT = (
    "You extract structured business intent from a single sentence written by an "
    "Indian entrepreneur. You return only JSON. You never invent a budget figure "
    "and never invent a locality that is not mentioned."
)

USER_PROMPT_TEMPLATE = """Extract the business intent from this prompt.

PROMPT: "{prompt}"

Return a JSON object with exactly these keys:
{{
  "business_type":       "snake_case type, e.g. ice_cream_shop",
  "business_type_label": "Human readable, e.g. Ice Cream Shop",
  "sector":              "one of: {sectors}",
  "area":                "locality mentioned, or empty string if none",
  "city":                "city mentioned, or empty string if none",
  "state":               "state if mentioned, else empty string",
  "budget_text":         "the exact budget substring from the prompt, or empty string",
  "confidence":          0.0 to 1.0
}}

Rules:
- Copy "budget_text" verbatim from the prompt. Do NOT convert it to a number.
- Leave "area" and "city" empty rather than guessing.
- Pick the single best sector. Use "unspecified" only if genuinely unclear.
"""


class PromptValidationError(ValueError):
    """F1 - the prompt failed length or content validation."""


def validate_prompt(prompt: str) -> str:
    """F1 - validate and normalize the raw prompt. Returns the cleaned prompt."""
    if prompt is None:
        raise PromptValidationError("Prompt is required")

    cleaned = " ".join(prompt.split())

    if len(cleaned) < MIN_PROMPT_LENGTH:
        raise PromptValidationError(
            f"Prompt must be at least {MIN_PROMPT_LENGTH} characters "
            f"(got {len(cleaned)}). Describe the business and, ideally, "
            f"a location and budget."
        )
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise PromptValidationError(
            f"Prompt must be at most {MAX_PROMPT_LENGTH} characters (got {len(cleaned)})."
        )
    return cleaned


async def classify_intent(
    prompt: str,
    client: LLMClient | None = None,
) -> BusinessIntent:
    """F2 - full intent extraction pipeline.

    Args:
        prompt: raw user prompt.
        client: LLM client override (tests inject a fake one).

    Returns:
        A validated BusinessIntent, always routable.

    Raises:
        PromptValidationError: if the prompt fails F1 validation.
    """
    cleaned = validate_prompt(prompt)
    active_client = client or llm_client

    extraction = await _extract_with_llm(cleaned, active_client)
    return _merge(cleaned, extraction)


async def _extract_with_llm(prompt: str, client: LLMClient) -> IntentExtraction | None:
    """Returns None when every provider failed, triggering heuristic fallback."""
    request = LLMRequest(
        prompt=USER_PROMPT_TEMPLATE.format(
            prompt=prompt,
            sectors=", ".join(s.value for s in Sector),
        ),
        system=SYSTEM_PROMPT,
        tier=ModelTier.STRUCTURED,  # Gemini first - best free-tier JSON mode
        temperature=0.0,  # deterministic: same prompt -> same intent
        max_tokens=600,
    )

    try:
        extraction, response = await client.complete_json(request, IntentExtraction)
    except (AllProvidersFailed, JSONParseError) as exc:
        log.warning("intent.llm_failed_using_heuristic", error=str(exc)[:300])
        return None

    log.info(
        "intent.extracted",
        provider=response.provider.value,
        model=response.model,
        tokens=response.total_tokens,
        latency_ms=response.latency_ms,
        confidence=extraction.confidence,
    )
    return extraction


def _merge(prompt: str, extraction: IntentExtraction | None) -> BusinessIntent:
    """Combine LLM semantics with deterministic parsing into the final intent."""
    # --- F4 budget: always from the raw prompt first -------------------------
    budget = parse_budget(prompt)
    if not budget.specified and extraction is not None and extraction.budget_text:
        budget = parse_budget(extraction.budget_text)

    # --- F5 sector: LLM if it committed to one, else keyword vote ------------
    keyword_sector, matched_keyword = classify_sector(prompt)
    if extraction is not None and extraction.sector_enum is not Sector.UNSPECIFIED:
        sector = extraction.sector_enum
    else:
        sector = keyword_sector

    # --- F3 location ---------------------------------------------------------
    location = parse_location(
        prompt,
        llm_area=extraction.area if extraction else "",
        llm_city=extraction.city if extraction else "",
        llm_state=extraction.state if extraction else "",
    )

    # --- F5/F10 routing flags: deterministic, never from the LLM -------------
    is_physical, requires_operations = derive_routing_flags(prompt, sector)

    # --- business type -------------------------------------------------------
    if extraction is not None and extraction.business_type.strip():
        business_type = extraction.business_type.strip()
        label = extraction.business_type_label.strip() or _label_from_snake(business_type)
        confidence = extraction.confidence
    else:
        business_type, label = fallback_business_type(prompt, matched_keyword)
        confidence = HEURISTIC_CONFIDENCE

    unspecified: list[str] = []
    if not budget.specified:
        unspecified.append("budget")
    if location.area == "unspecified":
        unspecified.append("location_area")
    if sector is Sector.UNSPECIFIED:
        unspecified.append("sector")

    intent = BusinessIntent(
        business_type=business_type,
        business_type_label=label,
        location=location,
        sector=sector,
        budget=budget,
        is_physical=is_physical,
        requires_operations=requires_operations,
        raw_prompt=prompt,
        confidence=confidence,
        unspecified_fields=unspecified,
    )

    log.info(
        "intent.resolved",
        business_type=intent.business_type,
        sector=intent.sector.value,
        area=intent.location.area,
        city=intent.location.city,
        budget=intent.budget.display if intent.budget.specified else "unspecified",
        scale=intent.scale.value,
        is_physical=intent.is_physical,
        requires_operations=intent.requires_operations,
        unspecified=unspecified,
    )
    return intent


def _label_from_snake(snake: str) -> str:
    return " ".join(word.capitalize() for word in snake.split("_"))
