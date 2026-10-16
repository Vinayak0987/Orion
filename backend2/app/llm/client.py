"""LLMClient — the fallback chain.

Order: user keys first → system keys → Ollama. Skips rate-limited providers,
tries the next on 429/transport failure. Raises AllProvidersFailedError only if
every provider in the chain fails.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.llm.providers import (
    GeminiProvider,
    GroqProvider,
    LLMResult,
    OllamaProvider,
    ProviderError,
    RateLimitError,
)
from app.llm.ratelimit import tracker
from app.llm.repair import extract_json


class AllProvidersFailedError(RuntimeError):
    def __init__(self, reasons: dict[str, str]):
        self.reasons = reasons
        super().__init__("All LLM providers failed -> " + "; ".join(
            f"{k}: {v}" for k, v in reasons.items()
        ))


class LLMClient:
    def __init__(self, user_keys: dict | None = None):
        """user_keys: optional {groq_api_key, gemini_api_key, openai_api_key}."""
        self.user_keys = user_keys or {}

    def _build_chain(self) -> list:
        chain: list = []
        seen_keys: set[str] = set()

        # 1. User keys first.
        uk = self.user_keys
        if uk.get("groq_api_key") and uk["groq_api_key"] not in seen_keys:
            chain.append(GroqProvider(uk["groq_api_key"]))
            seen_keys.add(uk["groq_api_key"])
        if uk.get("gemini_api_key") and uk["gemini_api_key"] not in seen_keys:
            chain.append(GeminiProvider(uk["gemini_api_key"]))
            seen_keys.add(uk["gemini_api_key"])

        # 2. System keys.
        if settings.groq_available and settings.groq_api_key not in seen_keys:
            chain.append(GroqProvider(settings.groq_api_key))
            seen_keys.add(settings.groq_api_key)
        if settings.gemini_available and settings.gemini_api_key not in seen_keys:
            chain.append(GeminiProvider(settings.gemini_api_key))
            seen_keys.add(settings.gemini_api_key)

        # 3. Ollama always last — primary model, then an optional fallback model.
        #    If the primary errors (e.g. a cloud model is unavailable), the chain
        #    automatically tries the fallback local model.
        chain.append(OllamaProvider(model=settings.ollama_model))
        if settings.ollama_model_fallback and settings.ollama_model_fallback != settings.ollama_model:
            chain.append(OllamaProvider(model=settings.ollama_model_fallback))
        return chain

    async def call(self, messages: list[dict], tier: str = "fast",
                   temperature: float = 0.7) -> LLMResult:
        reasons: dict[str, str] = {}
        for provider in self._build_chain():
            if tracker.is_rate_limited(provider.name):
                reasons[provider.name] = "rate limited (local tracker)"
                continue
            try:
                result = await provider.call(messages, tier, temperature)
                tracker.record(provider.name, result.input_tokens + result.output_tokens)
                return result
            except RateLimitError as e:
                tracker.record(provider.name)
                reasons[provider.name] = str(e)
                continue
            except ProviderError as e:
                reasons[provider.name] = str(e)
                continue
        raise AllProvidersFailedError(reasons)

    async def call_text(self, prompt: str, system: str = "", tier: str = "fast",
                        temperature: float = 0.7) -> LLMResult:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.call(messages, tier, temperature)

    async def call_structured(self, prompt: str, system: str = "", tier: str = "fast") -> Any:
        """Call and parse JSON. Retries once with a repair instruction on failure."""
        result = await self.call_text(prompt, system, tier, temperature=0.2)
        try:
            return extract_json(result.text)
        except Exception:
            repair = await self.call_text(
                f"The following should be valid JSON but is not. "
                f"Return ONLY the corrected JSON, nothing else:\n\n{result.text}",
                tier="fast", temperature=0.0,
            )
            return extract_json(repair.text)  # raises if still broken
