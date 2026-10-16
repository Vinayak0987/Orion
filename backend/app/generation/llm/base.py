"""Shared types + rate tracking for the LLM provider layer (F6-F9)."""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum


class ProviderName(StrEnum):
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class ModelTier(StrEnum):
    """Which class of model an agent needs.

    FAST      -> Llama 3.1 8B: creative/short tasks (branding, marketing copy)
    REASONING -> Llama 3.3 70B: numeric/analytical tasks (finance, strategy)
    STRUCTURED-> Gemini Flash: reliable JSON extraction (intent classifier)
    """

    FAST = "fast"
    REASONING = "reasoning"
    STRUCTURED = "structured"


@dataclass(slots=True)
class LLMRequest:
    prompt: str
    system: str = ""
    tier: ModelTier = ModelTier.FAST
    temperature: float = 0.4
    max_tokens: int = 2048
    json_mode: bool = False
    # Pin a specific model instead of letting the tier choose. F53 needs this:
    # the single-LLM baseline must run on a named, reported model, not on
    # whatever the fallback chain happens to reach.
    model: str | None = None


@dataclass(slots=True)
class LLMResponse:
    text: str
    provider: ProviderName
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    attempts: int = 1
    fallback_chain: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ProviderUnavailable(RuntimeError):
    """Provider has no credentials or is not reachable."""


class RateLimited(RuntimeError):
    """Provider free-tier limit hit. The chain should move to the next provider."""


class AllProvidersFailed(RuntimeError):
    """Every provider in the chain failed. Includes per-provider reasons."""

    def __init__(self, reasons: dict[str, str]) -> None:
        self.reasons = reasons
        detail = "; ".join(f"{k}: {v}" for k, v in reasons.items())
        super().__init__(f"All LLM providers failed -> {detail}")


class FreeTierTracker:
    """Thread-safe local counter for free-tier budgets (F6, F7).

    Tracks requests-per-day and requests-per-minute in memory. This is a guard
    to avoid *hitting* provider 429s, not a replacement for handling them.
    """

    def __init__(
        self,
        name: str,
        daily_request_limit: int | None = None,
        requests_per_minute: int | None = None,
        daily_token_limit: int | None = None,
    ) -> None:
        self.name = name
        self.daily_request_limit = daily_request_limit
        self.requests_per_minute = requests_per_minute
        self.daily_token_limit = daily_token_limit

        self._lock = threading.Lock()
        self._day: date = datetime.now(UTC).date()
        self._requests_today = 0
        self._tokens_today = 0
        self._minute_window: deque[float] = deque()

    def _roll_day(self) -> None:
        today = datetime.now(UTC).date()
        if today != self._day:
            self._day = today
            self._requests_today = 0
            self._tokens_today = 0

    def _prune_minute(self) -> None:
        cutoff = time.monotonic() - 60.0
        while self._minute_window and self._minute_window[0] < cutoff:
            self._minute_window.popleft()

    def has_budget(self) -> bool:
        with self._lock:
            self._roll_day()
            self._prune_minute()
            if (
                self.daily_request_limit is not None
                and self._requests_today >= self.daily_request_limit
            ):
                return False
            if (
                self.daily_token_limit is not None
                and self._tokens_today >= self.daily_token_limit
            ):
                return False
            if (
                self.requests_per_minute is not None
                and len(self._minute_window) >= self.requests_per_minute
            ):
                return False
            return True

    def seconds_until_free(self) -> float:
        """How long to wait for the per-minute window to open. 0 if free now."""
        with self._lock:
            self._prune_minute()
            if self.requests_per_minute is None:
                return 0.0
            if len(self._minute_window) < self.requests_per_minute:
                return 0.0
            oldest = self._minute_window[0]
            return max(0.0, 60.0 - (time.monotonic() - oldest))

    def record(self, tokens: int = 0) -> None:
        with self._lock:
            self._roll_day()
            self._requests_today += 1
            self._tokens_today += tokens
            self._minute_window.append(time.monotonic())

    def snapshot(self) -> dict[str, int | None]:
        with self._lock:
            self._roll_day()
            self._prune_minute()
            return {
                "requests_today": self._requests_today,
                "daily_request_limit": self.daily_request_limit,
                "tokens_today": self._tokens_today,
                "daily_token_limit": self.daily_token_limit,
                "requests_last_minute": len(self._minute_window),
                "requests_per_minute_limit": self.requests_per_minute,
            }


class LLMProvider(ABC):
    """Common interface. Agents never touch a vendor SDK directly."""

    name: ProviderName
    tracker: FreeTierTracker

    @abstractmethod
    async def is_available(self) -> bool:
        """Cheap check: credentials present and budget remaining."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Run one completion. Raise RateLimited or ProviderUnavailable on failure."""

    @abstractmethod
    def model_for(self, tier: ModelTier) -> str:
        """Map a ModelTier onto this provider's concrete model id."""
