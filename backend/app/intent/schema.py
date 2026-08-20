"""LLM-facing extraction schema for the Intent Classifier (F2).

Deliberately flat and lenient. The LLM is asked only for things it is good at
(naming the business, picking a sector) - never for normalized numbers, which
the deterministic parsers handle.

Every field has a default so a partial or sloppy LLM response still validates.
`complete_json` then never needs a repair round-trip for missing keys, which
saves free-tier quota.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.intent import Sector


class IntentExtraction(BaseModel):
    """Raw LLM output. Merged with deterministic parsers into BusinessIntent."""

    business_type: str = Field(default="", description="snake_case, e.g. ice_cream_shop")
    business_type_label: str = Field(default="", description="e.g. Ice Cream Shop")
    sector: str = Field(default="unspecified")

    # Location hints - only used when the gazetteer (F3) finds nothing.
    area: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")

    # Budget text is re-parsed by the deterministic parser (F4); the LLM is only
    # asked to quote the substring it believes is the budget.
    budget_text: str = Field(default="")

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("sector", mode="before")
    @classmethod
    def _coerce_sector(cls, v: object) -> str:
        """Map anything unrecognized onto 'unspecified' instead of failing."""
        if not isinstance(v, str):
            return Sector.UNSPECIFIED.value
        candidate = v.strip().lower().replace(" ", "_").replace("-", "_")
        valid = {s.value for s in Sector}
        return candidate if candidate in valid else Sector.UNSPECIFIED.value

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: object) -> float:
        try:
            return max(0.0, min(1.0, float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.5

    @property
    def sector_enum(self) -> Sector:
        return Sector(self.sector)
