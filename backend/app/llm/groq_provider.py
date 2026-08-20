"""F6 - Groq API provider (free tier: 14,400 requests/day).

Endpoint: POST https://api.groq.com/openai/v1/chat/completions
Docs:     https://console.groq.com/docs/api-reference

Cost: FREE. No credit card required for the developer tier.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings
from app.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
    RateLimited,
)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    name = ProviderName.GROQ

    def __init__(self) -> None:
        self.tracker = FreeTierTracker(
            name="groq",
            daily_request_limit=settings.groq_daily_request_limit,
        )
        self._api_key = settings.groq_api_key
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    def model_for(self, tier: ModelTier) -> str:
        if tier is ModelTier.REASONING:
            return settings.groq_model_reasoning
        # Groq has no dedicated structured model; the fast model handles JSON well
        # with response_format=json_object.
        return settings.groq_model_fast

    async def is_available(self) -> bool:
        return bool(self._api_key.strip()) and self.tracker.has_budget()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key.strip():
            raise ProviderUnavailable("GROQ_API_KEY not configured")
        if not self.tracker.has_budget():
            raise RateLimited("Groq daily free-tier request budget exhausted")

        model = request.model or self.model_for(request.tier)
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        try:
            response = await self._client.post(
                GROQ_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Groq transport error: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code == 429:
            raise RateLimited(f"Groq 429: {response.text[:200]}")
        if response.status_code in (401, 403):
            raise ProviderUnavailable(f"Groq auth failed ({response.status_code})")
        if response.status_code >= 400:
            raise ProviderUnavailable(
                f"Groq HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise ProviderUnavailable(f"Groq malformed response: {data}") from exc

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
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
