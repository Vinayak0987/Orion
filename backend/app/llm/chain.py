"""F9 - LLM Fallback Chain.

The single entry point for every LLM call in MABGP. Agents call
`llm_client.complete(...)` or `llm_client.complete_json(...)` and never touch a
vendor SDK.

Chain order depends on the requested ModelTier:

    STRUCTURED  -> Gemini, Groq(fast),      Ollama
    REASONING   -> Groq(70B), Gemini,       Ollama
    FAST        -> Groq(8B),  Gemini,       Ollama

Gemini leads for STRUCTURED because its `responseMimeType: application/json`
is the most reliable free-tier JSON mode - used by the Intent Classifier (F2).
Groq leads otherwise because it is the fastest and has the largest daily budget.

Every response records the chain that was walked, which feeds F46 (transparency)
and the cost/latency analysis in the research paper.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from app.llm.base import (
    AllProvidersFailed,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
    RateLimited,
)
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider

log = structlog.get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

# Retries per provider before moving to the next one.
ATTEMPTS_PER_PROVIDER = 2
BACKOFF_BASE_SECONDS = 1.5


class JSONParseError(RuntimeError):
    """LLM output could not be coerced into the requested Pydantic model."""


class LLMClient:
    """Provider-agnostic LLM facade with automatic free-tier fallback."""

    def __init__(
        self,
        groq: LLMProvider | None = None,
        gemini: LLMProvider | None = None,
        ollama: LLMProvider | None = None,
    ) -> None:
        self._providers: dict[ProviderName, LLMProvider] = {
            ProviderName.GROQ: groq or GroqProvider(),
            ProviderName.GEMINI: gemini or GeminiProvider(),
            ProviderName.OLLAMA: ollama or OllamaProvider(),
        }

    def chain_for(self, tier: ModelTier) -> list[ProviderName]:
        if tier is ModelTier.STRUCTURED:
            return [ProviderName.GEMINI, ProviderName.GROQ, ProviderName.OLLAMA]
        return [ProviderName.GROQ, ProviderName.GEMINI, ProviderName.OLLAMA]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Walk the fallback chain until one provider returns a completion."""
        chain = self.chain_for(request.tier)
        reasons: dict[str, str] = {}
        walked: list[str] = []

        for provider_name in chain:
            provider = self._providers[provider_name]
            walked.append(provider_name.value)

            if not await provider.is_available():
                reasons[provider_name.value] = "unavailable (no key or no budget)"
                log.info("llm.provider_skipped", provider=provider_name.value)
                continue

            for attempt in range(1, ATTEMPTS_PER_PROVIDER + 1):
                try:
                    response = await provider.complete(request)
                    response.attempts = attempt
                    response.fallback_chain = walked.copy()
                    log.info(
                        "llm.completed",
                        provider=provider_name.value,
                        model=response.model,
                        tier=request.tier.value,
                        tokens=response.total_tokens,
                        latency_ms=response.latency_ms,
                        attempt=attempt,
                    )
                    return response

                except RateLimited as exc:
                    reasons[provider_name.value] = f"rate limited: {exc}"
                    log.warning(
                        "llm.rate_limited", provider=provider_name.value, error=str(exc)
                    )
                    break  # no point retrying the same provider

                except ProviderUnavailable as exc:
                    reasons[provider_name.value] = str(exc)
                    log.warning(
                        "llm.provider_error",
                        provider=provider_name.value,
                        attempt=attempt,
                        error=str(exc),
                    )
                    if attempt < ATTEMPTS_PER_PROVIDER:
                        await asyncio.sleep(BACKOFF_BASE_SECONDS * attempt)

        raise AllProvidersFailed(reasons)

    async def complete_json(
        self,
        request: LLMRequest,
        schema: type[TModel],
        repair_attempts: int = 1,
    ) -> tuple[TModel, LLMResponse]:
        """Complete and validate against a Pydantic model.

        Never returns raw `json.loads` output - every LLM JSON payload in MABGP
        passes through Pydantic validation before touching SharedBusinessState.
        """
        request.json_mode = True
        response = await self.complete(request)

        last_error: Exception | None = None
        for attempt in range(repair_attempts + 1):
            try:
                payload = _extract_json_object(response.text)
                return schema.model_validate(payload), response
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                log.warning(
                    "llm.json_invalid",
                    schema=schema.__name__,
                    attempt=attempt,
                    error=str(exc)[:300],
                )
                if attempt >= repair_attempts:
                    break
                response = await self.complete(
                    LLMRequest(
                        prompt=_repair_prompt(response.text, schema, exc),
                        system="You output only valid JSON. No prose, no markdown fences.",
                        tier=request.tier,
                        temperature=0.0,
                        max_tokens=request.max_tokens,
                        json_mode=True,
                        # Carry the pinned model through. Dropping it meant a
                        # repaired response could come from a different model than
                        # the one the caller asked for - which silently
                        # invalidated the F53 baseline's reported model.
                        model=request.model,
                    )
                )

        raise JSONParseError(
            f"Could not coerce LLM output into {schema.__name__}: {last_error}"
        )

    async def health(self) -> dict[str, dict]:
        """F64 - per-provider availability and free-tier usage."""
        results: dict[str, dict] = {}
        for name, provider in self._providers.items():
            available = await provider.is_available()
            results[name.value] = {
                "available": available,
                "usage": provider.tracker.snapshot(),
            }
        return results

    async def aclose(self) -> None:
        for provider in self._providers.values():
            closer = getattr(provider, "aclose", None)
            if closer is not None:
                await closer()


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json_object(text: str) -> dict:
    """Pull a JSON object out of an LLM response.

    Handles three common shapes: bare JSON, fenced JSON, and JSON with leading
    or trailing prose.
    """
    candidate = text.strip()
    if not candidate:
        raise ValueError("empty LLM response")

    fenced = _FENCE_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def _repair_prompt(bad_output: str, schema: type[BaseModel], error: Exception) -> str:
    return (
        "Your previous output was not valid for the required schema.\n\n"
        f"PREVIOUS OUTPUT:\n{bad_output[:2000]}\n\n"
        f"VALIDATION ERROR:\n{str(error)[:800]}\n\n"
        f"REQUIRED JSON SCHEMA:\n{json.dumps(schema.model_json_schema(), indent=2)}\n\n"
        "Return ONLY the corrected JSON object. No markdown, no explanation."
    )


# Module-level singleton used by every agent.
llm_client = LLMClient()
