"""LLM provider implementations.

Three providers, one interface. Groq (primary, fast), Gemini (fallback),
Ollama (last resort, local). All use httpx against REST endpoints — no vendor
SDKs — so they behave identically and are trivial to mock in tests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(slots=True)
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class RateLimitError(RuntimeError):
    """Provider free-tier limit hit — the chain should try the next provider."""


class ProviderError(RuntimeError):
    """Provider failed (down, timeout, bad response) — try the next provider."""


# Cost per 1K tokens (USD). Free tiers cost $0 in practice; these estimate paid usage.
COST_PER_1K = {
    "groq/llama-3.1-8b-instant": {"in": 0.00005, "out": 0.00008},
    "groq/llama-3.3-70b-versatile": {"in": 0.00059, "out": 0.00079},
    "gemini/gemini-2.0-flash-lite": {"in": 0.000075, "out": 0.0003},
    "gemini/gemini-2.0-flash": {"in": 0.0001, "out": 0.0004},
    "openai/gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
    "ollama/llama3.1:8b": {"in": 0.0, "out": 0.0},
}


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_PER_1K.get(f"{provider}/{model}", {"in": 0.0, "out": 0.0})
    return (input_tokens * rates["in"] + output_tokens * rates["out"]) / 1000


import re as _re

# Qwen3 / reasoning models wrap chain-of-thought in <think>...</think>. That
# breaks our tool-call JSON parser, so strip it from the visible content.
_THINK_RE = _re.compile(r"<think>.*?</think>", _re.DOTALL | _re.IGNORECASE)


def strip_think(text: str) -> str:
    if not text:
        return text
    cleaned = _THINK_RE.sub("", text)
    # If an opening <think> had no close (truncated), drop everything up to the
    # last close we can find, else drop a leading dangling think block.
    if "<think>" in cleaned.lower() and "</think>" not in cleaned.lower():
        cleaned = _re.split(r"<think>", cleaned, flags=_re.IGNORECASE)[0]
    return cleaned.strip()


class OpenAICompatProvider:
    """Generic provider for any OpenAI-compatible /chat/completions endpoint.
    Used for NVIDIA NIM, Cerebras, and OpenRouter — same request/response shape
    as Groq, only the base URL, auth header and model names differ."""

    def __init__(self, name: str, base_url: str, api_key: str,
                 model_fast: str, model_reasoning: str, extra_headers: dict | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self._model_fast = model_fast
        self._model_reasoning = model_reasoning
        self._extra = extra_headers or {}

    def model_for(self, tier: str) -> str:
        return self._model_fast if tier == "fast" else self._model_reasoning

    async def call(self, messages: list[dict], tier: str, temperature: float = 0.7) -> LLMResult:
        model = self.model_for(tier)
        started = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}", **self._extra}
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    self.base_url, headers=headers,
                    json={"model": model, "messages": messages, "temperature": temperature},
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name} transport: {e}") from e

        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code == 429:
            raise RateLimitError(f"{self.name} 429")
        if resp.status_code >= 400:
            raise ProviderError(f"{self.name} {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            msg = data["choices"][0]["message"]
            # Some reasoning models (e.g. NVIDIA nemotron) put the answer in
            # reasoning_content when content is null — fall back to it.
            text = msg.get("content") or msg.get("reasoning_content") or ""
        except (KeyError, IndexError) as e:
            raise ProviderError(f"{self.name} malformed response: {e}") from e
        if not text.strip():
            raise ProviderError(f"{self.name} returned empty content")
        text = strip_think(text)
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        return LLMResult(
            text=text, provider=self.name, model=model,
            input_tokens=in_tok, output_tokens=out_tok, cost_usd=0.0, latency_ms=latency,
        )


class GroqProvider:
    name = "groq"
    BASE = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def model_for(self, tier: str) -> str:
        return settings.groq_model_fast if tier == "fast" else settings.groq_model_reasoning

    async def call(self, messages: list[dict], tier: str, temperature: float = 0.7) -> LLMResult:
        model = self.model_for(tier)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.BASE,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": model, "messages": messages, "temperature": temperature},
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"groq transport: {e}") from e

        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code == 429:
            raise RateLimitError("groq 429")
        if resp.status_code >= 400:
            raise ProviderError(f"groq {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        text = strip_think(data["choices"][0]["message"]["content"])
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        return LLMResult(
            text=text, provider="groq", model=model,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_usd=calculate_cost("groq", model, in_tok, out_tok), latency_ms=latency,
        )


class GeminiProvider:
    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def model_for(self, tier: str) -> str:
        return settings.gemini_model_fast if tier == "fast" else settings.gemini_model_reasoning

    async def call(self, messages: list[dict], tier: str, temperature: float = 0.7) -> LLMResult:
        model = self.model_for(tier)
        # Convert OpenAI-style messages to Gemini contents.
        contents, system = [], ""
        for m in messages:
            if m["role"] == "system":
                system += m["content"] + "\n"
            else:
                role = "user" if m["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
        body: dict = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.BASE}/{model}:generateContent?key={self.api_key}", json=body
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"gemini transport: {e}") from e

        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code == 429:
            raise RateLimitError("gemini 429")
        if resp.status_code >= 400:
            raise ProviderError(f"gemini {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"gemini malformed response: {e}") from e
        usage = data.get("usageMetadata", {})
        in_tok = usage.get("promptTokenCount", 0)
        out_tok = usage.get("candidatesTokenCount", 0)
        return LLMResult(
            text=text, provider="gemini", model=model,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_usd=calculate_cost("gemini", model, in_tok, out_tok), latency_ms=latency,
        )


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        # Distinct name per model so the rate-limit tracker treats the primary
        # and fallback models independently.
        self.name = f"ollama:{self.model}"

    def model_for(self, tier: str) -> str:
        return self.model

    async def call(self, messages: list[dict], tier: str, temperature: float = 0.7) -> LLMResult:
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": False,
                          "options": {"temperature": temperature}},
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"ollama transport (is it running?): {e}") from e

        latency = int((time.monotonic() - started) * 1000)
        if resp.status_code >= 400:
            raise ProviderError(f"ollama {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        text = strip_think(data.get("message", {}).get("content", ""))
        in_tok = data.get("prompt_eval_count", 0)
        out_tok = data.get("eval_count", 0)
        return LLMResult(
            text=text, provider="ollama", model=self.model,
            input_tokens=in_tok, output_tokens=out_tok, cost_usd=0.0, latency_ms=latency,
        )
