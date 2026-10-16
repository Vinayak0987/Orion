"""F7 - Google Gemini 1.5 Flash provider (free tier: 15 RPM, 1M tokens/day).

Endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
Docs:     https://ai.google.dev/api/generate-content

Called over plain REST via httpx rather than the SDK so that the request can be
mocked with respx in tests without live credentials.

Cost: FREE at this tier. Paid tier is opt-in only; we never send a billing header.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.generation.config import settings
from app.generation.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
    RateLimited,
)

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# Kept for readability in tests and logs.
GEMINI_BASE = f"{GEMINI_API_ROOT}/{settings.gemini_api_version}/models"


def gemini_endpoint(model: str, api_version: str | None = None) -> str:
    """Build a generateContent URL.

    The API version is configurable because model availability differs between
    `v1` and `v1beta`: the stable flash-lite models are served from `v1`, while
    preview models (and the `-latest` aliases) only exist on `v1beta`.
    """
    version = api_version or settings.gemini_api_version
    return f"{GEMINI_API_ROOT}/{version}/models/{model}:generateContent"


# Wait at most this long for the RPM window to reopen before giving up and
# letting the chain fall through to Ollama.
MAX_RPM_WAIT_SECONDS = 8.0


class GeminiProvider(LLMProvider):
    name = ProviderName.GEMINI

    def __init__(self) -> None:
        self.tracker = FreeTierTracker(
            name="gemini",
            requests_per_minute=settings.gemini_requests_per_minute,
            daily_token_limit=settings.gemini_daily_token_limit,
        )
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._api_version = settings.gemini_api_version
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    def model_for(self, tier: ModelTier) -> str:  # noqa: ARG002 - single free model
        return self._model

    async def is_available(self) -> bool:
        return bool(self._api_key.strip()) and self.tracker.has_budget()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key.strip():
            raise ProviderUnavailable("GEMINI_API_KEY not configured")

        # F7 request queuing: briefly wait out the per-minute window instead of
        # failing straight to the next provider.
        if not self.tracker.has_budget():
            wait = self.tracker.seconds_until_free()
            if 0 < wait <= MAX_RPM_WAIT_SECONDS:
                await asyncio.sleep(wait)
            if not self.tracker.has_budget():
                raise RateLimited(
                    f"Gemini free-tier budget exhausted (retry in {wait:.1f}s)"
                )

        model = request.model or self.model_for(request.tier)
        generation_config: dict[str, object] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        }
        if request.json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}

        started = time.perf_counter()
        try:
            response = await self._client.post(
                gemini_endpoint(model, self._api_version),
                params={"key": self._api_key},
                headers={"Content-Type": "application/json"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Gemini transport error: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code == 429:
            raise RateLimited(f"Gemini 429: {response.text[:200]}")
        if response.status_code in (401, 403):
            raise ProviderUnavailable(f"Gemini auth failed ({response.status_code})")
        if response.status_code >= 400:
            raise ProviderUnavailable(
                f"Gemini HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        text = _extract_text(data)
        if text is None:
            raise ProviderUnavailable(f"Gemini returned no candidates: {data}")

        usage = data.get("usageMetadata") or {}
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        completion_tokens = int(usage.get("candidatesTokenCount", 0))
        self.tracker.record(tokens=prompt_tokens + completion_tokens)

        return LLMResponse(
            text=text,
            provider=self.name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _extract_text(data: dict) -> str | None:
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    chunks = [p.get("text", "") for p in parts if isinstance(p, dict)]
    joined = "".join(chunks)
    return joined if joined else None
