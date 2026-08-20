"""F14/F15/F16 - Shared Business State.

The single object every agent reads from and appends to. This is the LangGraph
state channel type.

Append-only contract (F15):
    An agent MAY write only to its own department's section and to the
    shared telemetry lists. Writing to another department's section is a
    contract violation and is rejected by `apply_department_patch`.

Why this matters for the paper: because no agent can overwrite another's output,
the Consistency Score (F57) measures genuine cross-department agreement rather
than last-writer-wins artefacts.
"""

from __future__ import annotations

import operator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

from app.models.departments import (
    BrandingOutput,
    FinanceOutput,
    MarketingOutput,
    OperationsOutput,
    StrategyOutput,
)
from app.models.intent import BusinessIntent


class Department(StrEnum):
    STRATEGY = "strategy"
    FINANCE = "finance"
    BRANDING = "branding"
    MARKETING = "marketing"
    OPERATIONS = "operations"


ALWAYS_ACTIVE: tuple[Department, ...] = (
    Department.STRATEGY,
    Department.FINANCE,
    Department.BRANDING,
    Department.MARKETING,
)
CONDITIONAL: tuple[Department, ...] = (Department.OPERATIONS,)


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"


# =============================================================================
# Telemetry (F46, F58, F64)
# =============================================================================


class AgentTrace(BaseModel):
    """One agent execution record. Aggregated for F46 transparency and F58
    routing-efficiency measurements."""

    agent_id: str
    department: Department
    status: str = "completed"  # completed | failed | skipped
    provider: str = ""  # groq | gemini | ollama
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ApiCallTrace(BaseModel):
    """External API call record (F38, F39, F41)."""

    api: str  # google_places | serper
    endpoint: str = ""
    query: str = ""
    result_count: int = 0
    latency_ms: int = 0
    cached: bool = False
    retrieved_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: str | None = None


class RunMetadata(BaseModel):
    session_id: str
    status: RunStatus = RunStatus.PENDING
    active_departments: list[Department] = Field(default_factory=list)
    skipped_departments: list[Department] = Field(default_factory=list)
    routing_reason: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    total_duration_ms: int | None = None
    completeness_score: float | None = None
    validation_warnings: list[str] = Field(default_factory=list)

    @property
    def dynamic_routing_used(self) -> bool:
        return bool(self.skipped_departments)


# =============================================================================
# F14 - the state schema
# =============================================================================


def is_meaningful(value: Any) -> bool:
    """True when a value carries real content, not a schema default."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict, set, str)):
        return len(value) > 0
    return True


def has_content(section: Any) -> bool:
    """True when a department section has at least one populated field.

    LangGraph initializes a reducer-backed channel with a default instance, so an
    all-defaults section is indistinguishable from an absent one unless checked.
    """
    if section is None:
        return False
    return any(is_meaningful(v) for v in section.model_dump().values())


def merge_section(left: Any, right: Any) -> Any:
    """Reducer for the five department channels (F15).

    Agents inside one department run in the same LangGraph superstep, so several
    of them write to the same channel concurrently. Without a reducer LangGraph
    raises InvalidUpdateError; with a naive one, an agent that leaves a field at
    its default would erase a sibling agent's output.

    So the merge is additive: only meaningful values from `right` overwrite
    `left`. Each agent fills its own fields and leaves the rest at defaults,
    which makes the whole department section the union of its agents' work.
    """
    if left is None:
        return right
    if right is None:
        return left

    base = left.model_dump()
    incoming = {k: v for k, v in right.model_dump().items() if is_meaningful(v)}
    base.update(incoming)
    return type(left).model_validate(base)


class SharedBusinessState(TypedDict, total=False):
    """LangGraph state channel.

    Two reducer families keep concurrent writes safe:

    * `operator.add` on the telemetry lists - parallel branches concatenate
      instead of clobbering each other (F12).
    * `merge_section` on the department sections - the agents inside one
      department each contribute their own fields to a shared section (F15).
    """

    # Input
    session_id: str
    raw_prompt: str

    # Intent (written once by the classifier)
    intent: BusinessIntent

    # Department sections — written only by that department's own agents
    strategy: Annotated[StrategyOutput, merge_section]
    finance: Annotated[FinanceOutput, merge_section]
    branding: Annotated[BrandingOutput, merge_section]
    marketing: Annotated[MarketingOutput, merge_section]
    operations: Annotated[OperationsOutput, merge_section]

    # Shared append-only telemetry
    agent_traces: Annotated[list[AgentTrace], operator.add]
    api_traces: Annotated[list[ApiCallTrace], operator.add]
    errors: Annotated[list[str], operator.add]

    # Run bookkeeping
    metadata: RunMetadata


DEPARTMENT_MODELS: dict[Department, type[BaseModel]] = {
    Department.STRATEGY: StrategyOutput,
    Department.FINANCE: FinanceOutput,
    Department.BRANDING: BrandingOutput,
    Department.MARKETING: MarketingOutput,
    Department.OPERATIONS: OperationsOutput,
}


def new_state(session_id: str, raw_prompt: str) -> SharedBusinessState:
    """F13 - initialize a fresh state object for one generation run."""
    return SharedBusinessState(
        session_id=session_id,
        raw_prompt=raw_prompt,
        agent_traces=[],
        api_traces=[],
        errors=[],
        metadata=RunMetadata(session_id=session_id, status=RunStatus.PENDING),
    )


class StateContractViolation(RuntimeError):
    """Raised when an agent tries to write outside its own department (F15)."""


def apply_department_patch(
    state: SharedBusinessState,
    department: Department,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """F15 - the ONLY sanctioned way for an agent to write department output.

    Merges `patch` into the given department's section and returns a LangGraph
    node update dict. Enforces two rules:

    1. The patch may not name another department's section.
    2. The patch may only contain fields declared on that department's schema.

    Returns:
        A partial state dict suitable for returning from a LangGraph node.

    Raises:
        StateContractViolation: if the patch violates the append-only contract.
    """
    other_sections = {d.value for d in Department} - {department.value}
    trespass = other_sections & patch.keys()
    if trespass:
        raise StateContractViolation(
            f"Agent in department '{department}' attempted to write to "
            f"{sorted(trespass)}. Departments are append-only and isolated (F15)."
        )

    model_cls = DEPARTMENT_MODELS[department]
    allowed = set(model_cls.model_fields)
    unknown = patch.keys() - allowed - {department.value}
    if unknown:
        raise StateContractViolation(
            f"Unknown field(s) {sorted(unknown)} for {model_cls.__name__}. "
            f"Field names are frozen - see app/models/departments.py."
        )

    current = state.get(department.value)
    if current is None:
        merged = model_cls.model_validate(patch)
    else:
        # Merge: patch values win, but only for the keys actually supplied.
        base = current.model_dump()
        base.update({k: v for k, v in patch.items() if k in allowed})
        merged = model_cls.model_validate(base)

    return {department.value: merged}
