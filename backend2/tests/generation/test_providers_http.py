"""Integration tests for the real provider classes (F6, F7, F8).

The HTTP layer is mocked with respx, so these tests verify the ACTUAL request
payloads and response parsing of GroqProvider / GeminiProvider / OllamaProvider
without any API key and without spending a single free-tier request.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.generation.config import settings
from app.generation.llm.base import ModelTier, ProviderName, ProviderUnavailable, RateLimited
from app.generation.llm.chain import LLMClient, LLMRequest
from app.generation.llm.gemini_provider import GeminiProvider, gemini_endpoint
from app.generation.llm.groq_provider import GROQ_ENDPOINT, GroqProvider
from app.generation.llm.ollama_provider import OllamaProvider


def groq_payload(text: str = "Groq says hi") -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 22},
    }


def gemini_payload(text: str = "Gemini says hi") -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"promptTokenCount": 33, "candidatesTokenCount": 44},
    }


def ollama_payload(text: str = "Ollama says hi") -> dict:
    return {
        "message": {"role": "assistant", "content": text},
        "prompt_eval_count": 55,
        "eval_count": 66,
    }


# =============================================================================
# F6 - Groq
# =============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_groq_sends_correct_payload_and_parses_usage() -> None:
    route = respx.post(GROQ_ENDPOINT).mock(
        return_value=httpx.Response(200, json=groq_payload())
    )
    provider = GroqProvider()
    provider._api_key = "test-key"  # noqa: SLF001 - injecting a fake credential

    response = await provider.complete(
        LLMRequest(prompt="Plan a bakery", system="You are an analyst", tier=ModelTier.REASONING)
    )

    sent = route.calls.last.request
    body = sent.read().decode()
    assert sent.headers["authorization"] == "Bearer test-key"
    assert '"role":"system"' in body.replace(" ", "")
    assert "llama-3.3-70b-versatile" in body  # REASONING tier -> 70B

    assert response.provider is ProviderName.GROQ
    assert response.text == "Groq says hi"
    assert response.prompt_tokens == 11
    assert response.completion_tokens == 22
    assert response.total_tokens == 33


@respx.mock
@pytest.mark.asyncio
async def test_groq_fast_tier_uses_8b_model() -> None:
    route = respx.post(GROQ_ENDPOINT).mock(
        return_value=httpx.Response(200, json=groq_payload())
    )
    provider = GroqProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    await provider.complete(LLMRequest(prompt="tagline", tier=ModelTier.FAST))

    assert "llama-3.1-8b-instant" in route.calls.last.request.read().decode()


@respx.mock
@pytest.mark.asyncio
async def test_groq_json_mode_sets_response_format() -> None:
    route = respx.post(GROQ_ENDPOINT).mock(
        return_value=httpx.Response(200, json=groq_payload('{"ok":true}'))
    )
    provider = GroqProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    await provider.complete(LLMRequest(prompt="x", json_mode=True))

    assert "json_object" in route.calls.last.request.read().decode()


@respx.mock
@pytest.mark.asyncio
async def test_groq_429_raises_rate_limited() -> None:
    respx.post(GROQ_ENDPOINT).mock(return_value=httpx.Response(429, text="slow down"))
    provider = GroqProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    with pytest.raises(RateLimited):
        await provider.complete(LLMRequest(prompt="x"))


@respx.mock
@pytest.mark.asyncio
async def test_groq_401_raises_provider_unavailable() -> None:
    respx.post(GROQ_ENDPOINT).mock(return_value=httpx.Response(401, text="bad key"))
    provider = GroqProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    with pytest.raises(ProviderUnavailable):
        await provider.complete(LLMRequest(prompt="x"))


@pytest.mark.asyncio
async def test_groq_without_key_raises_provider_unavailable() -> None:
    provider = GroqProvider()
    provider._api_key = ""  # noqa: SLF001

    assert await provider.is_available() is False
    with pytest.raises(ProviderUnavailable, match="GROQ_API_KEY"):
        await provider.complete(LLMRequest(prompt="x"))


# =============================================================================
# F7 - Gemini
# =============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_gemini_sends_correct_payload_and_parses_usage() -> None:
    url = gemini_endpoint(settings.gemini_model)
    route = respx.post(url).mock(return_value=httpx.Response(200, json=gemini_payload()))
    provider = GeminiProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    response = await provider.complete(
        LLMRequest(prompt="Extract intent", system="Return JSON", tier=ModelTier.STRUCTURED)
    )

    sent = route.calls.last.request
    assert sent.url.params["key"] == "test-key"
    assert "systemInstruction" in sent.read().decode()

    assert response.provider is ProviderName.GEMINI
    assert response.text == "Gemini says hi"
    assert response.prompt_tokens == 33
    assert response.completion_tokens == 44


@respx.mock
@pytest.mark.asyncio
async def test_gemini_json_mode_sets_response_mime_type() -> None:
    url = gemini_endpoint(settings.gemini_model)
    route = respx.post(url).mock(
        return_value=httpx.Response(200, json=gemini_payload('{"ok":true}'))
    )
    provider = GeminiProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    await provider.complete(LLMRequest(prompt="x", json_mode=True))

    assert "application/json" in route.calls.last.request.read().decode()


@respx.mock
@pytest.mark.asyncio
async def test_gemini_empty_candidates_raises() -> None:
    url = gemini_endpoint(settings.gemini_model)
    respx.post(url).mock(return_value=httpx.Response(200, json={"candidates": []}))
    provider = GeminiProvider()
    provider._api_key = "test-key"  # noqa: SLF001

    with pytest.raises(ProviderUnavailable, match="no candidates"):
        await provider.complete(LLMRequest(prompt="x"))


# =============================================================================
# F8 - Ollama
# =============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_ollama_sends_correct_payload_and_parses_usage() -> None:
    provider = OllamaProvider()
    route = respx.post(f"{provider._base_url}/api/chat").mock(  # noqa: SLF001
        return_value=httpx.Response(200, json=ollama_payload())
    )

    response = await provider.complete(LLMRequest(prompt="Plan a cafe"))

    body = route.calls.last.request.read().decode()
    assert '"stream":false' in body.replace(" ", "")
    assert response.provider is ProviderName.OLLAMA
    assert response.prompt_tokens == 55
    assert response.completion_tokens == 66


@respx.mock
@pytest.mark.asyncio
async def test_ollama_unreachable_raises_provider_unavailable() -> None:
    provider = OllamaProvider()
    respx.post(f"{provider._base_url}/api/chat").mock(  # noqa: SLF001
        side_effect=httpx.ConnectError("connection refused")
    )

    with pytest.raises(ProviderUnavailable, match="not reachable"):
        await provider.complete(LLMRequest(prompt="x"))


@respx.mock
@pytest.mark.asyncio
async def test_ollama_is_available_probes_api_tags() -> None:
    provider = OllamaProvider()
    respx.get(f"{provider._base_url}/api/tags").mock(  # noqa: SLF001
        return_value=httpx.Response(200, json={"models": []})
    )

    assert await provider.is_available() is True


# =============================================================================
# F9 - real providers wired into the chain
# =============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_real_chain_falls_from_groq_429_to_gemini() -> None:
    """End-to-end fallback using the real provider classes over mocked HTTP."""
    respx.post(GROQ_ENDPOINT).mock(return_value=httpx.Response(429, text="limit"))
    gemini_url = gemini_endpoint(settings.gemini_model)
    respx.post(gemini_url).mock(return_value=httpx.Response(200, json=gemini_payload()))

    groq, gemini, ollama = GroqProvider(), GeminiProvider(), OllamaProvider()
    groq._api_key = "k"  # noqa: SLF001
    gemini._api_key = "k"  # noqa: SLF001

    client = LLMClient(groq=groq, gemini=gemini, ollama=ollama)
    response = await client.complete(LLMRequest(prompt="x", tier=ModelTier.FAST))

    assert response.provider is ProviderName.GEMINI
    assert response.fallback_chain == ["groq", "gemini"]


@respx.mock
@pytest.mark.asyncio
async def test_real_chain_reaches_ollama_when_both_apis_rate_limited() -> None:
    """The zero-cost guarantee, exercised through the real HTTP client code."""
    respx.post(GROQ_ENDPOINT).mock(return_value=httpx.Response(429, text="limit"))
    gemini_url = gemini_endpoint(settings.gemini_model)
    respx.post(gemini_url).mock(return_value=httpx.Response(429, text="limit"))

    groq, gemini, ollama = GroqProvider(), GeminiProvider(), OllamaProvider()
    groq._api_key = "k"  # noqa: SLF001
    gemini._api_key = "k"  # noqa: SLF001
    respx.get(f"{ollama._base_url}/api/tags").mock(  # noqa: SLF001
        return_value=httpx.Response(200, json={"models": []})
    )
    respx.post(f"{ollama._base_url}/api/chat").mock(  # noqa: SLF001
        return_value=httpx.Response(200, json=ollama_payload())
    )

    client = LLMClient(groq=groq, gemini=gemini, ollama=ollama)
    response = await client.complete(LLMRequest(prompt="x", tier=ModelTier.FAST))

    assert response.provider is ProviderName.OLLAMA
    assert response.fallback_chain == ["groq", "gemini", "ollama"]
    assert response.total_tokens == 121
