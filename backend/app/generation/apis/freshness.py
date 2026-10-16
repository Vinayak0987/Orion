"""F41 - Data freshness and validity tagging.

Every piece of externally retrieved data carries the timestamp at which it was
fetched, and anything older than `STALE_AFTER_DAYS` is marked potentially stale.

Retrieval time, not publication time, is the basis for this. Serper's organic
results return `date: null` on essentially every Indian market query we issue, so
there is no publication date to key off. Claiming freshness from a field that is
absent would be worse than admitting the data is only as fresh as the fetch.

The tag ends up in the run metadata (F46), so a reader of the generated plan - and
a reviewer of the paper - can tell how current the grounding was.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

STALE_AFTER_DAYS = 30


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def age_days(retrieved_at: str, *, reference: datetime | None = None) -> float | None:
    """Age of a retrieval timestamp in days, or None if unparseable."""
    moment = parse_iso(retrieved_at)
    if moment is None:
        return None
    delta = (reference or datetime.now(UTC)) - moment
    return delta.total_seconds() / 86400.0


def is_stale(retrieved_at: str, *, reference: datetime | None = None) -> bool:
    """True when data is older than the staleness threshold.

    Unparseable timestamps count as stale: unknown provenance is not fresh.
    """
    age = age_days(retrieved_at, reference=reference)
    if age is None:
        return True
    return age > STALE_AFTER_DAYS


@dataclass(frozen=True, slots=True)
class Freshness:
    """Provenance stamp attached to externally sourced data."""

    source: str
    retrieved_at: str
    cached: bool = False

    @classmethod
    def live(cls, source: str) -> Freshness:
        return cls(source=source, retrieved_at=now_iso(), cached=False)

    @classmethod
    def from_cache(cls, source: str, retrieved_at: str) -> Freshness:
        return cls(source=source, retrieved_at=retrieved_at, cached=True)

    @property
    def stale(self) -> bool:
        return is_stale(self.retrieved_at)

    @property
    def age_days(self) -> float | None:
        return age_days(self.retrieved_at)

    def label(self) -> str:
        """Short human-readable provenance, embedded in agent prompts."""
        age = self.age_days
        if age is None:
            return f"{self.source} (retrieval time unknown, treat as stale)"
        origin = "cached" if self.cached else "live"
        note = ", POTENTIALLY STALE" if self.stale else ""
        return f"{self.source}, {origin}, {age:.1f} days old{note}"

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "retrieved_at": self.retrieved_at,
            "cached": self.cached,
            "stale": self.stale,
            "age_days": round(self.age_days, 3) if self.age_days is not None else None,
        }


def cutoff_iso(days: int = STALE_AFTER_DAYS) -> str:
    """Oldest retrieval timestamp still considered fresh."""
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()
