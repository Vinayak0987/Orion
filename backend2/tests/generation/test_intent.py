"""Tests for F1-F5 - Intent Classification Layer.

Fully offline. The LLM is faked, so the deterministic parsers are tested in
isolation and the classifier's merge logic is tested against known LLM output.
"""

from __future__ import annotations

import json

import pytest

from app.generation.intent.budget_parser import parse_budget
from app.generation.intent.classifier import (
    MAX_PROMPT_LENGTH,
    PromptValidationError,
    classify_intent,
    validate_prompt,
)
from app.generation.intent.location_parser import parse_location
from app.generation.intent.schema import IntentExtraction
from app.generation.intent.taxonomy import classify_sector, derive_routing_flags
from app.generation.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.generation.llm.chain import LLMClient
from app.generation.models.intent import Scale, Sector


# =============================================================================
# Fake LLM plumbing
# =============================================================================


class ScriptedProvider(LLMProvider):
    """Returns a fixed JSON payload, or fails, on demand."""

    def __init__(self, payload: dict | None, *, fail: bool = False) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self._payload = payload
        self._fail = fail
        self.last_request: LLMRequest | None = None

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-1.5-flash"

    async def is_available(self) -> bool:
        return not self._fail

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        if self._fail:
            raise ProviderUnavailable("scripted failure")
        return LLMResponse(
            text=json.dumps(self._payload),
            provider=self.name,
            model="gemini-1.5-flash",
            prompt_tokens=50,
            completion_tokens=60,
        )


class DeadProvider(LLMProvider):
    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "dead"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable("dead")


def client_returning(payload: dict) -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=ScriptedProvider(payload),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


def dead_client() -> LLMClient:
    return LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=DeadProvider(ProviderName.GEMINI),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )


ICE_CREAM_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri",
    "city": "Mumbai",
    "state": "Maharashtra",
    "budget_text": "Rs 15L",
    "confidence": 0.93,
}


# =============================================================================
# F1 - prompt validation
# =============================================================================


def test_validate_prompt_collapses_whitespace() -> None:
    assert validate_prompt("  Ice   cream\nshop in Andheri  ") == "Ice cream shop in Andheri"


@pytest.mark.parametrize("bad", ["", "   ", "cafe", "shop x"])
def test_validate_prompt_rejects_too_short(bad: str) -> None:
    with pytest.raises(PromptValidationError, match="at least 10 characters"):
        validate_prompt(bad)


def test_validate_prompt_rejects_too_long() -> None:
    with pytest.raises(PromptValidationError, match="at most 500"):
        validate_prompt("a" * (MAX_PROMPT_LENGTH + 1))


def test_validate_prompt_rejects_none() -> None:
    with pytest.raises(PromptValidationError, match="required"):
        validate_prompt(None)  # type: ignore[arg-type]


# =============================================================================
# F4 - budget parsing (the table that anchors F54 Financial Accuracy)
# =============================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Indian lakh notation
        ("Ice cream shop in Andheri, ₹15L budget", 1_500_000),
        ("bakery with 15 lakh budget", 1_500_000),
        ("salon, 15 lakhs", 1_500_000),
        ("cafe with 8 lac investment", 800_000),
        ("Rs 12.5 lakh capital", 1_250_000),
        # Crore notation
        ("factory with 1.5 crore budget", 15_000_000),
        ("manufacturing unit, 2Cr", 20_000_000),
        ("plant with 3 crores", 30_000_000),
        # Thousands / millions
        ("tiffin service with 50k budget", 50_000),
        ("startup with 2 million funding", 2_000_000),
        # Plain numbers with currency prefix
        ("grocery store ₹50,000", 50_000),
        ("shop with Rs 1500000", 1_500_000),
        ("kirana store INR 250000", 250_000),
        # Budget keyword context, no symbol
        ("open a gym, budget of 500000", 500_000),
        ("coaching centre with capital 250000", 250_000),
        # Indian comma grouping
        ("boutique ₹15,00,000", 1_500_000),
    ],
)
def test_parse_budget_amounts(text: str, expected: int) -> None:
    budget = parse_budget(text)
    assert budget.specified is True
    assert budget.amount == expected
    assert budget.currency == "INR"


@pytest.mark.parametrize(
    "text",
    [
        "I want to open an ice cream shop in Andheri",
        "start a salon in Bandra",
        "",
        "cloud kitchen operational in 15 months",  # 'months' must not parse as millions
        "gym open 12 hours daily",
        "call me on 9876543210",  # bare phone number must not parse
    ],
)
def test_parse_budget_returns_unspecified_when_absent(text: str) -> None:
    budget = parse_budget(text)
    assert budget.specified is False
    assert budget.amount == 0
    assert budget.scale is Scale.UNSPECIFIED


def test_parse_budget_records_raw_substring() -> None:
    assert "15L" in parse_budget("shop with ₹15L budget").raw


@pytest.mark.parametrize(
    ("text", "expected_scale"),
    [
        ("shop with 5 lakh", Scale.MICRO),
        ("shop with 15 lakh", Scale.SMALL),
        ("shop with 80 lakh", Scale.MEDIUM),
        ("shop with 5 crore", Scale.LARGE),
    ],
)
def test_budget_scale_derived_from_parsed_amount(text: str, expected_scale: Scale) -> None:
    assert parse_budget(text).scale is expected_scale


# =============================================================================
# F3 - location parsing
# =============================================================================


def test_known_mumbai_locality_implies_mumbai() -> None:
    location = parse_location("ice cream shop in Andheri")
    assert location.area == "Andheri"
    assert location.city == "Mumbai"
    assert location.state == "Maharashtra"


def test_directional_suffix_is_part_of_locality() -> None:
    assert parse_location("cafe in Andheri West").area == "Andheri West"


def test_longest_locality_wins() -> None:
    """'Bandra Kurla Complex' must not be truncated to 'Bandra'."""
    assert parse_location("office in Bandra Kurla Complex").area == "Bandra Kurla Complex"


def test_near_station_phrasing() -> None:
    assert parse_location("bakery near Dadar station").area == "Dadar"


def test_other_city_is_resolved_with_state() -> None:
    location = parse_location("coaching centre in Pune")
    assert location.city == "Pune"
    assert location.state == "Maharashtra"


def test_non_maharashtra_city() -> None:
    location = parse_location("saas startup in Bangalore")
    assert location.city == "Bengaluru"
    assert location.state == "Karnataka"


def test_llm_area_used_only_when_gazetteer_misses() -> None:
    location = parse_location("shop in Kalyani Nagar", llm_area="Kalyani Nagar", llm_city="Pune")
    assert location.area == "Kalyani Nagar"
    assert location.city == "Pune"


def test_gazetteer_overrides_llm_hint() -> None:
    location = parse_location("shop in Andheri", llm_area="Wrongplace")
    assert location.area == "Andheri"


def test_defaults_to_mumbai_when_nothing_found() -> None:
    location = parse_location("start an online tutoring platform")
    assert location.area == "unspecified"
    assert location.city == "Mumbai"


def test_query_string_used_by_places_api() -> None:
    assert parse_location("cafe in Bandra").query_string == "Bandra, Mumbai, Maharashtra"


# =============================================================================
# F5 - sector classification
# =============================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ice cream shop in Andheri", Sector.FOOD_AND_BEVERAGE),
        ("open a bakery in Dadar", Sector.FOOD_AND_BEVERAGE),
        ("cloud kitchen in Powai", Sector.FOOD_AND_BEVERAGE),
        ("kirana store in Mulund", Sector.RETAIL),
        ("clothing store in Bandra", Sector.RETAIL),
        ("unisex salon in Khar", Sector.SERVICES),
        ("gym in Goregaon", Sector.SERVICES),
        ("saas platform for logistics", Sector.TECHNOLOGY),
        ("neet coaching institute in Dadar", Sector.EDUCATION),
        ("dental clinic in Chembur", Sector.HEALTHCARE),
        ("garment unit in Bhiwandi", Sector.MANUFACTURING),
        ("interior design studio in Worli", Sector.CREATIVE),
    ],
)
def test_classify_sector(text: str, expected: Sector) -> None:
    sector, _ = classify_sector(text)
    assert sector is expected


def test_classify_sector_unknown_returns_unspecified() -> None:
    sector, keyword = classify_sector("something completely undefined here")
    assert sector is Sector.UNSPECIFIED
    assert keyword == ""


# =============================================================================
# F5/F10 - routing flags (the RQ2 experiment depends on these being stable)
# =============================================================================


@pytest.mark.parametrize(
    ("text", "sector", "is_physical", "requires_ops"),
    [
        ("ice cream shop in Andheri", Sector.FOOD_AND_BEVERAGE, True, True),
        ("kirana store in Mulund", Sector.RETAIL, True, True),
        ("dental clinic in Chembur", Sector.HEALTHCARE, True, True),
        ("garment unit in Bhiwandi", Sector.MANUFACTURING, True, True),
        ("salon in Khar", Sector.SERVICES, True, True),
        # Digital: Operations must be skipped
        ("online tutoring platform", Sector.EDUCATION, False, False),
        ("saas platform for logistics", Sector.TECHNOLOGY, False, False),
        ("remote consulting agency", Sector.SERVICES, False, False),
        ("mobile app for fitness", Sector.TECHNOLOGY, False, False),
        # Digital marker overridden by physical fulfilment
        ("online store with warehouse delivery", Sector.RETAIL, True, True),
        ("cloud kitchen in Powai", Sector.FOOD_AND_BEVERAGE, True, True),
    ],
)
def test_derive_routing_flags(
    text: str, sector: Sector, is_physical: bool, requires_ops: bool
) -> None:
    assert derive_routing_flags(text, sector) == (is_physical, requires_ops)


def test_routing_flags_are_deterministic_across_calls() -> None:
    """RQ2 compares dynamic routing against all-departments on the same prompts.
    The routing decision must not vary between the two arms."""
    prompt = "online tutoring platform for CBSE students"
    results = {derive_routing_flags(prompt, Sector.EDUCATION) for _ in range(20)}
    assert len(results) == 1


# =============================================================================
# F2 - end-to-end classifier
# =============================================================================


@pytest.mark.asyncio
async def test_classify_intent_full_extraction() -> None:
    intent = await classify_intent(
        "Ice cream shop in Andheri, ₹15L budget", client=client_returning(ICE_CREAM_PAYLOAD)
    )

    assert intent.business_type == "ice_cream_shop"
    assert intent.business_type_label == "Ice Cream Shop"
    assert intent.sector is Sector.FOOD_AND_BEVERAGE
    assert intent.location.area == "Andheri"
    assert intent.location.city == "Mumbai"
    assert intent.budget.amount == 1_500_000
    assert intent.scale is Scale.SMALL
    assert intent.is_physical is True
    assert intent.requires_operations is True
    assert intent.confidence == 0.93
    assert intent.unspecified_fields == []


@pytest.mark.asyncio
async def test_classifier_uses_structured_tier_for_json() -> None:
    provider = ScriptedProvider(ICE_CREAM_PAYLOAD)
    client = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=provider,
        ollama=DeadProvider(ProviderName.OLLAMA),
    )

    await classify_intent("Ice cream shop in Andheri, ₹15L", client=client)

    assert provider.last_request is not None
    assert provider.last_request.tier is ModelTier.STRUCTURED
    assert provider.last_request.temperature == 0.0  # reproducibility
    assert provider.last_request.json_mode is True


@pytest.mark.asyncio
async def test_deterministic_budget_overrides_llm_budget_text() -> None:
    """The LLM claims a wrong figure; the regex parse of the prompt must win."""
    payload = dict(ICE_CREAM_PAYLOAD, budget_text="500 rupees")
    intent = await classify_intent(
        "Ice cream shop in Andheri, ₹15L budget", client=client_returning(payload)
    )
    assert intent.budget.amount == 1_500_000


@pytest.mark.asyncio
async def test_llm_budget_text_used_when_prompt_parse_fails() -> None:
    payload = dict(ICE_CREAM_PAYLOAD, budget_text="15 lakh")
    intent = await classify_intent(
        "Ice cream shop in Andheri with fifteen lakh rupees",
        client=client_returning(payload),
    )
    assert intent.budget.amount == 1_500_000


@pytest.mark.asyncio
async def test_routing_flags_ignore_llm_and_stay_deterministic() -> None:
    """Even though the payload describes a physical shop, an explicitly online
    prompt must skip Operations."""
    payload = dict(
        ICE_CREAM_PAYLOAD,
        business_type="online_tutoring_platform",
        sector="education",
        area="",
        city="",
    )
    intent = await classify_intent(
        "Start an online tutoring platform for CBSE students",
        client=client_returning(payload),
    )
    assert intent.is_physical is False
    assert intent.requires_operations is False


@pytest.mark.asyncio
async def test_unspecified_fields_are_reported() -> None:
    payload = dict(
        ICE_CREAM_PAYLOAD, budget_text="", area="", city="", sector="unspecified"
    )
    intent = await classify_intent(
        "I want to start some kind of venture", client=client_returning(payload)
    )
    assert "budget" in intent.unspecified_fields
    assert "location_area" in intent.unspecified_fields
    assert "sector" in intent.unspecified_fields


@pytest.mark.asyncio
async def test_falls_back_to_heuristic_when_all_providers_fail() -> None:
    """The pipeline must still produce a routable intent with zero LLM access."""
    intent = await classify_intent(
        "Ice cream shop in Andheri, ₹15L budget", client=dead_client()
    )

    assert intent.sector is Sector.FOOD_AND_BEVERAGE  # keyword vote
    assert intent.location.area == "Andheri"  # gazetteer
    assert intent.budget.amount == 1_500_000  # regex
    assert intent.is_physical is True
    assert intent.confidence == pytest.approx(0.35)
    assert intent.business_type == "ice_cream"


@pytest.mark.asyncio
async def test_malformed_llm_json_still_yields_intent() -> None:
    class GarbageProvider(ScriptedProvider):
        async def complete(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text="I am not JSON",
                provider=ProviderName.GEMINI,
                model="gemini-1.5-flash",
            )

    client = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=GarbageProvider(None),
        ollama=DeadProvider(ProviderName.OLLAMA),
    )
    intent = await classify_intent("Bakery in Dadar with 10 lakh budget", client=client)

    assert intent.sector is Sector.FOOD_AND_BEVERAGE
    assert intent.budget.amount == 1_000_000
    assert intent.location.area == "Dadar"


@pytest.mark.asyncio
async def test_prompt_validation_runs_before_any_llm_call() -> None:
    provider = ScriptedProvider(ICE_CREAM_PAYLOAD)
    client = LLMClient(
        groq=DeadProvider(ProviderName.GROQ),
        gemini=provider,
        ollama=DeadProvider(ProviderName.OLLAMA),
    )

    with pytest.raises(PromptValidationError):
        await classify_intent("cafe", client=client)

    assert provider.last_request is None  # no free-tier quota spent


# =============================================================================
# Extraction schema leniency
# =============================================================================


def test_extraction_coerces_unknown_sector() -> None:
    assert IntentExtraction(sector="quantum_farming").sector == "unspecified"


def test_extraction_normalizes_sector_spacing() -> None:
    assert IntentExtraction(sector="Food And Beverage").sector == "food_and_beverage"


def test_extraction_clamps_bad_confidence() -> None:
    assert IntentExtraction(confidence=5.0).confidence == 1.0
    assert IntentExtraction(confidence="high").confidence == 0.5  # type: ignore[arg-type]


def test_extraction_accepts_empty_payload() -> None:
    """Saves a repair round-trip (and free-tier quota) on sloppy LLM output."""
    extraction = IntentExtraction()
    assert extraction.sector_enum is Sector.UNSPECIFIED
    assert extraction.business_type == ""
