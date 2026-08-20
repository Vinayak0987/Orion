"""Tests for F6-F9 - LLM provider chain and fallback behaviour.

All providers are faked, so this suite runs offline with zero API keys and
zero cost. This is what proves the acceptance criterion "feature works when the
primary LLM provider is rate-limited".
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.llm.base import (
    AllProvidersFailed,
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
    RateLimited,
)
from app.llm.chain import JSONParseError, LLMClient, _extract_json_object


class FakeProvider(LLMProvider):
    """Scriptable stand-in for Groq / Gemini / Ollama."""

    def __init__(
        self,
        name: ProviderName,
        *,
        available: bool = True,
        raises: type[Exception] | None = None,
        text: str = "ok",
    ) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)
        self._available = available
        self._raises = raises
        self._text = text
        self.call_count = 0

    def model_for(self, tier: ModelTier) -> str:
        return f"{self.name.value}-{tier.value}"

    async def is_available(self) -> bool:
        return self._available

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        if self._raises is not None:
            raise self._raises(f"{self.name.value} scripted failure")
        return LLMResponse(
            text=self._text,
            provider=self.name,
            model=self.model_for(request.tier),
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=5,
        )


def build_client(**kwargs: LLMProvider) -> LLMClient:
    defaults: dict[str, LLMProvider] = {
        "groq": FakeProvider(ProviderName.GROQ),
        "gemini": FakeProvider(ProviderName.GEMINI),
        "ollama": FakeProvider(ProviderName.OLLAMA),
    }
    defaults.update(kwargs)
    return LLMClient(**defaults)  # type: ignore[arg-type]


# =============================================================================
# Chain ordering
# =============================================================================


def test_structured_tier_prefers_gemini() -> None:
    chain = build_client().chain_for(ModelTier.STRUCTURED)
    assert chain[0] is ProviderName.GEMINI


def test_reasoning_and_fast_tiers_prefer_groq() -> None:
    client = build_client()
    assert client.chain_for(ModelTier.REASONING)[0] is ProviderName.GROQ
    assert client.chain_for(ModelTier.FAST)[0] is ProviderName.GROQ


def test_ollama_is_always_last() -> None:
    client = build_client()
    for tier in ModelTier:
        assert client.chain_for(tier)[-1] is ProviderName.OLLAMA


# =============================================================================
# F9 - fallback behaviour
# =============================================================================


@pytest.mark.asyncio
async def test_uses_primary_provider_when_healthy() -> None:
    groq = FakeProvider(ProviderName.GROQ, text="from groq")
    response = await build_client(groq=groq).complete(LLMRequest(prompt="hi"))

    assert response.provider is ProviderName.GROQ
    assert response.text == "from groq"
    assert groq.call_count == 1


@pytest.mark.asyncio
async def test_falls_back_to_gemini_when_groq_rate_limited() -> None:
    groq = FakeProvider(ProviderName.GROQ, raises=RateLimited)
    gemini = FakeProvider(ProviderName.GEMINI, text="from gemini")

    response = await build_client(groq=groq, gemini=gemini).complete(LLMRequest(prompt="hi"))

    assert response.provider is ProviderName.GEMINI
    assert response.fallback_chain == ["groq", "gemini"]
    # RateLimited must not be retried on the same provider.
    assert groq.call_count == 1


@pytest.mark.asyncio
async def test_falls_all_the_way_to_ollama() -> None:
    """The zero-cost guarantee: generation completes even with both APIs exhausted."""
    client = build_client(
        groq=FakeProvider(ProviderName.GROQ, raises=RateLimited),
        gemini=FakeProvider(ProviderName.GEMINI, raises=RateLimited),
        ollama=FakeProvider(ProviderName.OLLAMA, text="from ollama"),
    )
    response = await client.complete(LLMRequest(prompt="hi"))

    assert response.provider is ProviderName.OLLAMA
    assert response.fallback_chain == ["groq", "gemini", "ollama"]


@pytest.mark.asyncio
async def test_skips_providers_reporting_unavailable() -> None:
    groq = FakeProvider(ProviderName.GROQ, available=False)
    gemini = FakeProvider(ProviderName.GEMINI, text="from gemini")

    response = await build_client(groq=groq, gemini=gemini).complete(LLMRequest(prompt="hi"))

    assert response.provider is ProviderName.GEMINI
    assert groq.call_count == 0


@pytest.mark.asyncio
async def test_all_providers_failed_reports_every_reason() -> None:
    client = build_client(
        groq=FakeProvider(ProviderName.GROQ, raises=RateLimited),
        gemini=FakeProvider(ProviderName.GEMINI, available=False),
        ollama=FakeProvider(ProviderName.OLLAMA, raises=ProviderUnavailable),
    )
    with pytest.raises(AllProvidersFailed) as exc_info:
        await client.complete(LLMRequest(prompt="hi"))

    assert set(exc_info.value.reasons) == {"groq", "gemini", "ollama"}


# =============================================================================
# JSON extraction + Pydantic validation
# =============================================================================


class IntentStub(BaseModel):
    business_type: str
    budget: int


@pytest.mark.asyncio
async def test_complete_json_validates_into_pydantic_model() -> None:
    payload = '{"business_type": "ice_cream_shop", "budget": 1500000}'
    client = build_client(groq=FakeProvider(ProviderName.GROQ, text=payload))

    parsed, response = await client.complete_json(LLMRequest(prompt="x"), IntentStub)

    assert parsed.business_type == "ice_cream_shop"
    assert parsed.budget == 1_500_000
    assert response.provider is ProviderName.GROQ


@pytest.mark.asyncio
async def test_complete_json_raises_when_unrepairable() -> None:
    client = build_client(groq=FakeProvider(ProviderName.GROQ, text="not json at all"))

    with pytest.raises(JSONParseError):
        await client.complete_json(LLMRequest(prompt="x"), IntentStub, repair_attempts=0)


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Here is the result:\n{"a": 1}\nHope that helps!',
    ],
)
def test_extract_json_handles_common_llm_output_shapes(raw: str) -> None:
    assert _extract_json_object(raw) == {"a": 1}


def test_extract_json_rejects_non_object() -> None:
    with pytest.raises(ValueError, match="expected a JSON object"):
        _extract_json_object("[1, 2, 3]")


# =============================================================================
# F6/F7 - free-tier budget tracking
# =============================================================================


def test_tracker_blocks_after_daily_limit() -> None:
    tracker = FreeTierTracker("groq", daily_request_limit=2)

    assert tracker.has_budget()
    tracker.record()
    tracker.record()
    assert not tracker.has_budget()


def test_tracker_blocks_after_rpm_limit() -> None:
    tracker = FreeTierTracker("gemini", requests_per_minute=2)

    tracker.record()
    tracker.record()
    assert not tracker.has_budget()
    assert tracker.seconds_until_free() > 0


def test_tracker_blocks_after_token_limit() -> None:
    tracker = FreeTierTracker("gemini", daily_token_limit=100)

    tracker.record(tokens=100)
    assert not tracker.has_budget()


def test_tracker_snapshot_exposes_usage_for_health() -> None:
    tracker = FreeTierTracker("groq", daily_request_limit=10)
    tracker.record(tokens=42)

    snapshot = tracker.snapshot()
    assert snapshot["requests_today"] == 1
    assert snapshot["tokens_today"] == 42
    assert snapshot["daily_request_limit"] == 10
