"""Intent schema - the structured output of the Intent Classifier (F2-F5).

This is the contract between the Input Layer and the Business Orchestrator.
Every downstream agent reads from BusinessIntent, never from the raw prompt.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Sector(StrEnum):
    """F5 - fixed sector taxonomy. Keep this list closed so routing rules and
    evaluation benchmarks stay comparable across runs."""

    FOOD_AND_BEVERAGE = "food_and_beverage"
    RETAIL = "retail"
    SERVICES = "services"
    TECHNOLOGY = "technology"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    CREATIVE = "creative"
    UNSPECIFIED = "unspecified"


class Scale(StrEnum):
    """F4 - budget-derived scale bands (INR)."""

    MICRO = "micro"      # < 10 lakh
    SMALL = "small"      # 10 lakh - 50 lakh
    MEDIUM = "medium"    # 50 lakh - 2 crore
    LARGE = "large"      # > 2 crore
    UNSPECIFIED = "unspecified"


class Location(BaseModel):
    """F3 - normalized location."""

    area: str = Field(default="unspecified", description="Locality, e.g. 'Andheri'")
    city: str = Field(default="Mumbai")
    state: str = Field(default="Maharashtra")
    country: str = Field(default="India")
    raw: str = Field(default="", description="Original location text from the prompt")

    @property
    def query_string(self) -> str:
        """Formatted for Google Places / Serper queries (F38, F39)."""
        parts = [p for p in (self.area, self.city, self.state) if p and p != "unspecified"]
        return ", ".join(parts)


class Budget(BaseModel):
    """F4 - normalized budget."""

    amount: int = Field(default=0, ge=0, description="Absolute amount in INR")
    currency: str = Field(default="INR")
    raw: str = Field(default="", description="Original budget text from the prompt")
    specified: bool = Field(default=False, description="False if inferred, not stated")

    @property
    def scale(self) -> Scale:
        if not self.specified or self.amount <= 0:
            return Scale.UNSPECIFIED
        if self.amount < 1_000_000:
            return Scale.MICRO
        if self.amount < 5_000_000:
            return Scale.SMALL
        if self.amount < 20_000_000:
            return Scale.MEDIUM
        return Scale.LARGE

    @property
    def display(self) -> str:
        """Human-readable Indian format, e.g. 'Rs 15.0 L'."""
        if self.amount >= 10_000_000:
            return f"Rs {self.amount / 10_000_000:.2f} Cr"
        if self.amount >= 100_000:
            return f"Rs {self.amount / 100_000:.1f} L"
        return f"Rs {self.amount:,}"


class BusinessIntent(BaseModel):
    """F2 - full extracted intent. Produced by the Intent Classifier, consumed by
    the Business Orchestrator's routing rules (F10)."""

    business_type: str = Field(
        default="unspecified",
        description="Snake_case business type, e.g. 'ice_cream_shop'",
    )
    business_type_label: str = Field(
        default="", description="Human-readable, e.g. 'Ice Cream Shop'"
    )
    location: Location = Field(default_factory=Location)
    sector: Sector = Field(default=Sector.UNSPECIFIED)
    budget: Budget = Field(default_factory=Budget)
    scale: Scale = Field(default=Scale.UNSPECIFIED)

    # --- Routing flags (drive F10) -------------------------------------------
    is_physical: bool = Field(
        default=True, description="Requires physical premises / inventory"
    )
    requires_operations: bool = Field(
        default=True, description="Activates the Operations department"
    )

    # --- Provenance ----------------------------------------------------------
    raw_prompt: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    unspecified_fields: list[str] = Field(default_factory=list)

    @field_validator("business_type")
    @classmethod
    def _normalize_business_type(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_").replace("-", "_") or "unspecified"

    def model_post_init(self, __context: object) -> None:
        # Keep scale consistent with budget unless explicitly provided.
        if self.scale == Scale.UNSPECIFIED:
            object.__setattr__(self, "scale", self.budget.scale)
