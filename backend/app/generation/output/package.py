"""F42/F46 - JSON business package assembly and generation metadata.

Turns a finished `SharedBusinessState` into one self-describing document: the
plan itself, plus a full account of how it was produced.

The metadata block is not decoration. F46 requires that a reader can tell which
model wrote each section, which external APIs were consulted, how fresh that data
was, and what the run cost in tokens and time. That is what makes a generated
plan auditable and the paper's numbers reproducible from stored artefacts rather
than from re-running the pipeline.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.generation.apis.freshness import is_stale
from app.generation.models.state import Department, SharedBusinessState
from app.generation.output.sections import SECTION_ORDER, section_payload


class ApiCallSummary(BaseModel):
    """One external call, with its freshness verdict (F41)."""

    api: str
    query: str = ""
    result_count: int = 0
    cached: bool = False
    latency_ms: int = 0
    retrieved_at: str = ""
    stale: bool = False
    error: str | None = None


class AgentSummary(BaseModel):
    agent_id: str
    department: str
    feature: str = ""
    status: str
    provider: str = ""
    model: str = ""
    tokens: int = 0
    latency_ms: int = 0
    error: str | None = None


class GenerationMetadata(BaseModel):
    """F46 - the transparency block."""

    session_id: str
    status: str
    generated_at: str
    total_duration_ms: int | None = None
    completeness_score: float | None = None

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    agents_total: int = 0
    agents_completed: int = 0
    agents_failed: int = 0

    providers_used: dict[str, int] = Field(default_factory=dict)
    models_used: list[str] = Field(default_factory=list)

    active_departments: list[str] = Field(default_factory=list)
    skipped_departments: list[str] = Field(default_factory=list)
    dynamic_routing_used: bool = False
    routing_reason: str = ""

    api_calls: list[ApiCallSummary] = Field(default_factory=list)
    grounding: dict[str, str] = Field(default_factory=dict)

    agents: list[AgentSummary] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BusinessPackage(BaseModel):
    """F42 - the unified output document."""

    session_id: str
    business_name: str
    prompt: str
    intent: dict = Field(default_factory=dict)
    sections: dict[str, dict] = Field(default_factory=dict)
    metadata: GenerationMetadata

    @property
    def present_sections(self) -> list[str]:
        """Section keys with content, in report order."""
        return [key for key in SECTION_ORDER if key in self.sections]


# Feature ids live on the agent specs; resolved lazily to avoid a circular import.
def _feature_map() -> dict[str, str]:
    from app.generation.agents import all_agents

    return {agent.spec.agent_id: agent.spec.feature for agent in all_agents()}


def business_name_for(state: SharedBusinessState) -> str:
    """Prefer the brand the Branding department chose (F26)."""
    branding = state.get(Department.BRANDING.value)
    if branding is not None and branding.recommended_name:
        return branding.recommended_name

    intent = state.get("intent")
    if intent is not None:
        return intent.business_type_label or intent.business_type.replace("_", " ").title()
    return "Untitled Business"


def _grounding_summary(state: SharedBusinessState) -> dict[str, str]:
    """Which arm produced this plan - the RQ3 label (F38/F39)."""
    strategy = state.get(Department.STRATEGY.value)
    competitor_source = "none"
    if strategy is not None and strategy.competitors:
        competitor_source = strategy.competitors[0].source

    api_names = {trace.api for trace in state.get("api_traces") or []}
    research_source = "serper" if "serper" in api_names else "llm_inferred"

    return {
        "competitor_source": competitor_source,
        "market_research_source": research_source,
        "rq3_arm": "text_only"
        if competitor_source in ("none", "llm_inferred")
        else "grounded",
    }


def build_metadata(state: SharedBusinessState) -> GenerationMetadata:
    """F46 - assemble the transparency block from run telemetry."""
    run = state["metadata"]
    traces = state.get("agent_traces") or []
    features = _feature_map()

    agents = [
        AgentSummary(
            agent_id=trace.agent_id,
            department=trace.department.value,
            feature=features.get(trace.agent_id, ""),
            status=trace.status,
            provider=trace.provider,
            model=trace.model,
            tokens=trace.total_tokens,
            latency_ms=trace.latency_ms,
            error=trace.error,
        )
        for trace in traces
    ]

    api_calls = [
        ApiCallSummary(
            api=trace.api,
            query=trace.query,
            result_count=trace.result_count,
            cached=trace.cached,
            latency_ms=trace.latency_ms,
            retrieved_at=trace.retrieved_at,
            stale=is_stale(trace.retrieved_at) if trace.retrieved_at else False,
            error=trace.error,
        )
        for trace in state.get("api_traces") or []
    ]

    providers = Counter(t.provider for t in traces if t.provider)
    models = sorted({t.model for t in traces if t.model})

    return GenerationMetadata(
        session_id=state["session_id"],
        status=run.status.value,
        generated_at=run.completed_at or datetime.now(UTC).isoformat(),
        total_duration_ms=run.total_duration_ms,
        completeness_score=run.completeness_score,
        total_tokens=sum(t.total_tokens for t in traces),
        prompt_tokens=sum(t.prompt_tokens for t in traces),
        completion_tokens=sum(t.completion_tokens for t in traces),
        agents_total=len(traces),
        agents_completed=len([t for t in traces if t.status == "completed"]),
        agents_failed=len([t for t in traces if t.status == "failed"]),
        providers_used=dict(providers),
        models_used=models,
        active_departments=[d.value for d in run.active_departments],
        skipped_departments=[d.value for d in run.skipped_departments],
        dynamic_routing_used=run.dynamic_routing_used,
        routing_reason=run.routing_reason,
        api_calls=api_calls,
        grounding=_grounding_summary(state),
        agents=agents,
        validation_warnings=run.validation_warnings,
        errors=state.get("errors") or [],
    )


def build_package(state: SharedBusinessState) -> BusinessPackage:
    """F42 - assemble the complete business package.

    Only sections with content are included, so a partial run (F52) produces a
    valid, smaller package rather than one padded with empty headings.
    """
    intent = state.get("intent")

    sections: dict[str, dict] = {}
    for key in SECTION_ORDER:
        payload = section_payload(state, key)
        if payload is not None:
            sections[key] = payload

    return BusinessPackage(
        session_id=state["session_id"],
        business_name=business_name_for(state),
        prompt=state.get("raw_prompt", ""),
        intent=intent.model_dump(mode="json") if intent is not None else {},
        sections=sections,
        metadata=build_metadata(state),
    )
