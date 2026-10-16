"""Agent base class - shared machinery for all 21 department agents (F17-F37).

Every agent supplies four things and inherits the rest:

    spec          agent id, department, model tier, output schema
    system        role instruction
    build_prompt  renders the task from SharedBusinessState
    to_patch      maps validated LLM output onto department fields

The base class owns the LLM call, JSON validation, timing, token accounting,
trace creation and failure isolation. An agent that fails records a failed trace
and returns no patch, so its department - and the run - continues (F52).

No agent imports a vendor SDK. Every call goes through `app.generation.llm.llm_client`,
which is what makes the provider/latency/token table in the paper reproducible.
"""

from __future__ import annotations

import time
import types
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Union, get_args, get_origin

import structlog
from pydantic import BaseModel, model_validator

from app.generation.llm.base import AllProvidersFailed, LLMRequest, ModelTier
from app.generation.llm.chain import JSONParseError, LLMClient, llm_client
from app.generation.models.state import (
    AgentTrace,
    ApiCallTrace,
    Department,
    SharedBusinessState,
    apply_department_patch,
)

log = structlog.get_logger(__name__)


# =============================================================================
# Lenient LLM output coercion
# =============================================================================
#
# Small local models are loosely typed in predictable ways. Observed against
# llama3.2:3b on a real run:
#
#   list[str] field  <- [["Cream", "Milk powder"], "Sugar"]   (nested list)
#   str field        <- null
#   int field        <- "Rs 1,50,000"
#
# Each of those raised ValidationError, burning a repair round-trip and
# sometimes losing the agent's whole contribution. Coercing them is strictly
# better than retrying: the information was present, only the shape was wrong.
#
# This is deliberately confined to agent output schemas. It never touches
# BusinessIntent or the department models, so the frozen field contract and the
# metric inputs keep their strict validation.


def _flatten_to_str(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, (list, tuple, set)):
        return ", ".join(part for part in (_flatten_to_str(i) for i in item) if part)
    if isinstance(item, dict):
        return "; ".join(f"{k}: {_flatten_to_str(v)}" for k, v in item.items())
    return str(item)


def coerce_str_list(value: Any) -> Any:
    """Normalize anything list-shaped into a flat list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        return [f"{k}: {_flatten_to_str(v)}" for k, v in value.items()]
    if isinstance(value, (list, tuple, set)):
        return [text for text in (_flatten_to_str(i) for i in value) if text]
    return [str(value)]


def coerce_number(value: Any) -> Any:
    """Pull a number out of strings like 'Rs 1,50,000' or '12.5%'."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if not isinstance(value, str):
        return value
    cleaned = value.strip().lower()
    for token in ("inr", "rs.", "rs", "₹", ",", "%", "per month", "/month", "approx"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned) if "." in cleaned else int(cleaned)
    except ValueError:
        return value  # let Pydantic report it


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return (inner_annotation, allows_none)."""
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        allows_none = len(args) != len(get_args(annotation))
        return (args[0] if len(args) == 1 else annotation), allows_none
    return annotation, False


def _coerce_field(annotation: Any, value: Any) -> Any:
    inner, allows_none = _unwrap_optional(annotation)

    if get_origin(inner) is list:
        if get_args(inner) == (str,):
            return coerce_str_list(value)
        # list of nested models: a null becomes an empty list rather than an error
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value

    if inner is str:
        if value is None:
            return None if allows_none else ""
        if not isinstance(value, str):
            return _flatten_to_str(value)
        return value

    if inner in (int, float):
        return coerce_number(value)

    return value


class AgentOutput(BaseModel):
    """Base class for the 21 agent output schemas.

    Applies best-effort type coercion before validation so a well-formed answer
    in a slightly wrong shape is kept rather than discarded.
    """

    @model_validator(mode="before")
    @classmethod
    def _coerce_loose_types(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        coerced = dict(data)
        for name, field in cls.model_fields.items():
            if name in coerced:
                coerced[name] = _coerce_field(field.annotation, coerced[name])
        return coerced


@dataclass(frozen=True, slots=True)
class AgentSpec:
    agent_id: str
    department: Department
    feature: str  # e.g. "F17" - ties runtime telemetry back to the spec
    schema: type[BaseModel]
    tier: ModelTier = ModelTier.FAST
    temperature: float = 0.3
    max_tokens: int = 1100


def context_block(state: SharedBusinessState) -> str:
    """The shared business facts every agent reads from state.

    Rendered once here so all 21 agents see an identical description of the
    business. If each agent restated the intent in its own words, cross-department
    disagreement would be a prompt artefact rather than a real signal, and the
    Consistency Score (F57) would be measuring noise.
    """
    intent = state.get("intent")
    if intent is None:
        return "BUSINESS: unspecified"

    budget = (
        f"{intent.budget.display} (INR {intent.budget.amount:,})"
        if intent.budget.specified
        else "not specified"
    )
    return (
        f"BUSINESS: {intent.business_type_label or intent.business_type}\n"
        f"SECTOR: {intent.sector.value}\n"
        f"LOCATION: {intent.location.query_string}\n"
        f"BUDGET: {budget}\n"
        f"SCALE: {intent.scale.value}\n"
        f"PHYSICAL PREMISES: {'yes' if intent.is_physical else 'no'}\n"
        f"ORIGINAL REQUEST: {state.get('raw_prompt', '')}"
    )


def upstream_block(state: SharedBusinessState, *sections: str) -> str:
    """Render selected upstream department findings for a dependent agent.

    This is the mechanism behind the multi-agent claim in RQ1: a Finance agent
    prices against the competitor set Strategy actually found, rather than
    re-imagining the market on its own.
    """
    lines: list[str] = []
    strategy = state.get(Department.STRATEGY.value)
    finance = state.get(Department.FINANCE.value)
    branding = state.get(Department.BRANDING.value)
    marketing = state.get(Department.MARKETING.value)

    if "market" in sections and strategy is not None:
        if strategy.market_size is not None:
            m = strategy.market_size
            lines.append(
                f"MARKET SIZE: TAM {m.tam_inr}, SAM {m.sam_inr}, SOM {m.som_inr} (INR/year)"
            )
        if strategy.market_overview:
            lines.append(f"MARKET OVERVIEW: {strategy.market_overview[:400]}")
        if strategy.positioning:
            lines.append(f"POSITIONING: {strategy.positioning[:300]}")

    if "competitors" in sections and strategy is not None and strategy.competitors:
        names = ", ".join(
            f"{c.name}"
            + (f" (rating {c.rating})" if c.rating else "")
            + (f" (price level {c.price_level})" if c.price_level is not None else "")
            for c in strategy.competitors[:8]
        )
        lines.append(f"NEARBY COMPETITORS: {names}")
        if strategy.market_gaps:
            lines.append(f"MARKET GAPS: {'; '.join(strategy.market_gaps[:5])}")

    if "revenue" in sections and finance is not None:
        if finance.projected_revenue_y1_inr is not None:
            lines.append(f"YEAR-1 REVENUE (INR): {finance.projected_revenue_y1_inr:,}")
        if finance.avg_ticket_size_inr is not None:
            lines.append(f"AVERAGE TICKET (INR): {finance.avg_ticket_size_inr:,}")
        if finance.pricing_strategy:
            lines.append(f"PRICING STRATEGY: {finance.pricing_strategy[:250]}")

    if "costs" in sections and finance is not None:
        if finance.total_setup_cost_inr is not None:
            lines.append(f"TOTAL SETUP COST (INR): {finance.total_setup_cost_inr:,}")
        if finance.total_monthly_cost_inr is not None:
            lines.append(f"TOTAL MONTHLY COST (INR): {finance.total_monthly_cost_inr:,}")

    if "brand" in sections and branding is not None:
        if branding.recommended_name:
            lines.append(f"BRAND NAME: {branding.recommended_name}")
        if branding.personality_traits:
            lines.append(f"BRAND PERSONALITY: {', '.join(branding.personality_traits[:6])}")
        if branding.tone:
            lines.append(f"BRAND TONE: {branding.tone[:150]}")

    if "personas" in sections and marketing is not None and marketing.personas:
        for persona in marketing.personas[:2]:
            lines.append(
                f"PERSONA {persona.name}: {persona.age_range}, {persona.occupation}, "
                f"pains {'; '.join(persona.pain_points[:3])}"
            )

    if "staffing" in sections:
        operations = state.get(Department.OPERATIONS.value)
        if operations is not None and operations.roles:
            lines.append(
                "ROLES: " + ", ".join(f"{r.title} x{r.headcount}" for r in operations.roles[:8])
            )

    return "\n".join(lines) if lines else ""


JSON_ONLY_SUFFIX = (
    "\n\nReturn ONLY a single valid JSON object matching the required keys. "
    "No markdown fences, no commentary. Use null for values you cannot determine. "
    "All monetary amounts are plain integers in INR with no symbols, commas or units."
)


@dataclass(slots=True)
class Grounding:
    """Verified external data fetched for an agent before it prompts the model.

    Three payloads, all optional:

      text        prepended to the prompt as a VERIFIED EXTERNAL DATA block
      patch       merged over `to_patch()` output, so real data wins over
                  anything the model generated for the same field
      api_traces  recorded on the run for F46 transparency and F55 scoring

    `patch` overriding the model is the mechanism behind RQ3. When Places returns
    six real competitors, they replace whatever names the model recalled, and
    `Competitor.source` records which arm produced the stored plan.
    """

    text: str = ""
    patch: dict = field(default_factory=dict)
    api_traces: list[ApiCallTrace] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.text and not self.patch


class Agent(ABC):
    """One specialized agent. Subclasses define the prompt and the field mapping."""

    spec: AgentSpec
    system: str = "You are a business analyst producing structured JSON output."

    async def gather_grounding(self, state: SharedBusinessState) -> Grounding:
        """Fetch verified external data before prompting (F38-F41).

        Default is no grounding, so 19 of the 21 agents are unaffected. Only the
        Competitive Analysis and Market Research agents override this.

        Must never raise: a failed API call degrades to LLM-only recall, which is
        the RQ3 control condition rather than an error.
        """
        return Grounding()

    @abstractmethod
    def build_prompt(self, state: SharedBusinessState) -> str:
        """Render the task. Must read business facts from state, never re-guess them."""

    @abstractmethod
    def to_patch(self, parsed: BaseModel, state: SharedBusinessState) -> dict:
        """Map validated LLM output onto this department's frozen field names."""

    async def run(
        self,
        state: SharedBusinessState,
        client: LLMClient | None = None,
    ) -> dict:
        """Execute the agent and return a LangGraph partial-state update.

        Never raises: a failure is recorded as a failed AgentTrace so the
        department and the overall run continue with partial results (F52).
        """
        active = client or llm_client
        started = time.perf_counter()

        try:
            grounding = await self.gather_grounding(state)
        except Exception as exc:  # noqa: BLE001 - grounding is an enhancement
            log.warning(
                "agent.grounding_failed", agent=self.spec.agent_id, error=str(exc)[:250]
            )
            grounding = Grounding()

        prompt = self.build_prompt(state)
        if grounding.text:
            prompt += (
                "\n\nVERIFIED EXTERNAL DATA (retrieved this run - prefer this over "
                f"your own recollection):\n{grounding.text}"
            )

        request = LLMRequest(
            prompt=prompt + JSON_ONLY_SUFFIX,
            system=self.system,
            tier=self.spec.tier,
            temperature=self.spec.temperature,
            max_tokens=self.spec.max_tokens,
        )

        try:
            parsed, response = await active.complete_json(request, self.spec.schema)
        except (AllProvidersFailed, JSONParseError) as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            log.warning(
                "agent.failed",
                agent=self.spec.agent_id,
                feature=self.spec.feature,
                error=str(exc)[:300],
                latency_ms=elapsed,
            )
            failure: dict = {
                "agent_traces": [
                    AgentTrace(
                        agent_id=self.spec.agent_id,
                        department=self.spec.department,
                        status="failed",
                        latency_ms=elapsed,
                        error=str(exc)[:500],
                    )
                ],
                "errors": [f"{self.spec.agent_id}: {str(exc)[:200]}"],
            }
            if grounding.api_traces:
                failure["api_traces"] = grounding.api_traces
            return failure

        elapsed = int((time.perf_counter() - started) * 1000)
        trace = AgentTrace(
            agent_id=self.spec.agent_id,
            department=self.spec.department,
            status="completed",
            provider=response.provider.value,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=elapsed,
        )

        try:
            patch = self.to_patch(parsed, state)
            # Verified data wins over generated data for the same field.
            patch.update(grounding.patch)
            update = apply_department_patch(state, self.spec.department, patch)
        except Exception as exc:  # noqa: BLE001 - mapping bug must not kill the run
            # Includes StateContractViolation: an agent that names a field outside
            # its own department fails alone, its siblings still write.
            log.warning("agent.mapping_failed", agent=self.spec.agent_id, error=str(exc)[:300])
            trace.status = "failed"
            trace.error = f"field mapping failed: {exc}"[:500]
            return {"agent_traces": [trace], "errors": [f"{self.spec.agent_id}: {exc}"]}

        log.info(
            "agent.completed",
            agent=self.spec.agent_id,
            feature=self.spec.feature,
            provider=response.provider.value,
            tokens=response.total_tokens,
            latency_ms=elapsed,
            grounded=bool(grounding.patch or grounding.text),
            fields=sorted(patch),
        )

        update["agent_traces"] = [trace]
        if grounding.api_traces:
            update["api_traces"] = grounding.api_traces
        return update
