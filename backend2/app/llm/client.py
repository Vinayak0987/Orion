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
    OpenAICompatProvider,
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


# OpenAI-compatible endpoints for the extra free providers.
_NIM_BASE = "https://integrate.api.nvidia.com/v1"
_CEREBRAS_BASE = "https://api.cerebras.ai/v1"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class LLMClient:
    def __init__(self, user_keys: dict | None = None):
        """user_keys: optional {groq_api_key, gemini_api_key, nvidia_nim_api_key,
        cerebras_api_key, openrouter_api_key, openai_api_key}."""
        self.user_keys = user_keys or {}

    def _build_chain(self) -> list:
        """Robust ordered fallback chain:
        Groq → NVIDIA NIM → Cerebras → OpenRouter → Gemini → local Ollama.
        Each cloud provider is added only when a key exists (user key preferred,
        then system key). Local Ollama is ALWAYS last — the no-rate-limit floor.
        """
        chain: list = []
        seen: set[str] = set()
        uk = self.user_keys

        def add_openai_compat(name, base, key, fast, reasoning, headers=None):
            if key and f"{name}:{key}" not in seen:
                chain.append(OpenAICompatProvider(name, base, key, fast, reasoning, headers))
                seen.add(f"{name}:{key}")

        # 1. Groq (user then system).
        for key in (uk.get("groq_api_key"), settings.groq_api_key if settings.groq_available else None):
            if key and f"groq:{key}" not in seen:
                chain.append(GroqProvider(key)); seen.add(f"groq:{key}")

        # 2. NVIDIA NIM — biggest free daily quota, strong tool-calling.
        #    Both NIM keys are chained under DISTINCT names so the rate-limit
        #    tracker treats them independently (key 2 is tried even if key 1 429s).
        nim_keys = [k for k in (uk.get("nvidia_nim_api_key"),
                                settings.nvidia_nim_api_key if settings.nvidia_nim_available else None,
                                settings.nvidia_nim_api_key_second) if k]
        for i, key in enumerate(dict.fromkeys(nim_keys)):
            add_openai_compat(f"nvidia_nim_{i+1}", _NIM_BASE, key,
                              settings.nvidia_nim_model_fast, settings.nvidia_nim_model_reasoning)

        # 3. Cerebras — very fast.
        for key in (uk.get("cerebras_api_key"), settings.cerebras_api_key if settings.cerebras_available else None):
            add_openai_compat("cerebras", _CEREBRAS_BASE, key,
                              settings.cerebras_model_fast, settings.cerebras_model_reasoning)

        # 4. OpenRouter — free model variants.
        for key in (uk.get("openrouter_api_key"), settings.openrouter_api_key if settings.openrouter_available else None):
            add_openai_compat("openrouter", _OPENROUTER_BASE, key,
                              settings.openrouter_model_fast, settings.openrouter_model_reasoning,
                              headers={"HTTP-Referer": "https://orion.local", "X-Title": "Orion"})

        # 5. Gemini (user then system).
        for key in (uk.get("gemini_api_key"), settings.gemini_api_key if settings.gemini_available else None):
            if key and f"gemini:{key}" not in seen:
                chain.append(GeminiProvider(key)); seen.add(f"gemini:{key}")

        # 6. Ollama ALWAYS last — primary strong local model, then the small
        #    fallback. The no-rate-limit floor that can still tool-call.
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
