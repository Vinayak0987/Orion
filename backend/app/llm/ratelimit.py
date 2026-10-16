"""In-memory rate-limit tracking for the free-tier LLM providers.

Not persisted — limits reset on their own schedule anyway, and a restart simply
re-opens the budget. The goal is to AVOID hitting provider 429s, not to replace
handling them (the chain still catches real 429s).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import settings


class RateLimitTracker:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.groq_requests_today = 0
        self.groq_daily_reset = _tomorrow(now)
        self.gemini_requests_this_minute = 0
        self.gemini_minute_reset = now + timedelta(minutes=1)
        self.gemini_tokens_today = 0
        self.gemini_daily_token_reset = _tomorrow(now)

    def is_rate_limited(self, provider: str) -> bool:
        now = datetime.now(UTC)
        if provider == "groq":
            if now > self.groq_daily_reset:
                self.groq_requests_today = 0
                self.groq_daily_reset = _tomorrow(now)
            return self.groq_requests_today >= settings.groq_daily_request_limit
        if provider == "gemini":
            if now > self.gemini_minute_reset:
                self.gemini_requests_this_minute = 0
                self.gemini_minute_reset = now + timedelta(minutes=1)
            if now > self.gemini_daily_token_reset:
                self.gemini_tokens_today = 0
                self.gemini_daily_token_reset = _tomorrow(now)
            return (
                self.gemini_requests_this_minute >= settings.gemini_requests_per_minute
                or self.gemini_tokens_today >= settings.gemini_daily_token_limit
            )
        return False  # ollama / openai: not tracked

    def record(self, provider: str, tokens: int = 0) -> None:
        if provider == "groq":
            self.groq_requests_today += 1
        elif provider == "gemini":
            self.gemini_requests_this_minute += 1
            self.gemini_tokens_today += tokens

    def snapshot(self) -> dict:
        return {
            "groq": {
                "requests_today": self.groq_requests_today,
                "limit": settings.groq_daily_request_limit,
            },
            "gemini": {
                "requests_this_minute": self.gemini_requests_this_minute,
                "rpm_limit": settings.gemini_requests_per_minute,
                "tokens_today": self.gemini_tokens_today,
                "token_limit": settings.gemini_daily_token_limit,
            },
        }


def _tomorrow(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


# Module-level singleton.
tracker = RateLimitTracker()
