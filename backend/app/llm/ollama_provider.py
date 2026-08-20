"""F8 - Ollama local fallback (zero cost, zero rate limits).

Endpoint: POST {OLLAMA_BASE_URL}/api/chat
Docs:     https://github.com/ollama/ollama/blob/main/docs/api.md

This is the terminal link in the fallback chain. If Groq and Gemini are both
rate-limited, generation still completes - slower, but it completes. That
guarantee is what lets the evaluation harness (F53-F58) run 30+ prompts back to
back without hitting a wall.

Cost: FREE. Runs on the local machine / Docker container.
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
)


class OllamaProvider(LLMProvider):
    name = ProviderName.OLLAMA

    def __init__(self) -> None:
        # No limits to track, but keep a tracker so telemetry is uniform.
        self.tracker = FreeTierTracker(name="ollama")
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        # Local inference on 8 GB RAM is slow; allow a generous timeout.
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    def model_for(self, tier: ModelTier) -> str:  # noqa: ARG002 - one local model
        return self._model

    async def is_available(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags", timeout=5.0)
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    async def complete(self, request: LLMRequest) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        model = request.model or self._model
        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.json_mode:
            payload["format"] = "json"

        started = time.perf_counter()
        try:
            response = await self._client.post(
                f"{self._base_url}/api/chat", json=payload
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Ollama not reachable: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise ProviderUnavailable(
                f"Ollama HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        text = (data.get("message") or {}).get("content", "")
        if not text:
            raise ProviderUnavailable(f"Ollama returned empty content: {data}")

        prompt_tokens = int(data.get("prompt_eval_count", 0))
        completion_tokens = int(data.get("eval_count", 0))
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
