"""Execution plan data model - the explicit dependency DAG (Planner Subsystem).

A planning *report* (store.py) answers "what WOULD run". An `ExecutionPlan`
answers "what IS the graph, and what is the state of each node". It is the same
agent roster the report already carries (service.build_agent_roster), but
written as explicit nodes with `depends_on` edges and a mutable per-node status,
so the run can be inspected, monitored, checkpointed and resumed.

These are plain shapes - no logic lives here. `compile.py` builds a plan from a
confirmed report; `plan_store.py` persists it; `executor.py` runs it.

Grounded in the verified codebase:
    - node ids are agent_ids from `agents/registry.py:DEPARTMENT_STAGES`;
    - `stage`, `tier`, `max_tokens`, `grounding` are copied verbatim from the
      report's roster entry - topology is NEVER re-derived here (design.md §8,
      the anchor discipline: the plan is computed from topology, not asserted).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """Per-node lifecycle. A subset of AgentArea's task status set, matched to
    Orion's needs (no multi-tenant/HITL states in v1)."""

    PENDING = "pending"  # not started
    RUNNING = "running"  # executing now
    COMPLETED = "completed"  # finished successfully
    FAILED = "failed"  # ran and errored (run may still continue - F52)
    SKIPPED = "skipped"  # not run (e.g. an upstream dependency failed)


# A plan's own lifecycle. Mirrors RunMetadata.status verbs (state.py) so the two
# surfaces stay comparable.
PlanStatus = str  # "draft" | "ready" | "running" | "completed" | "partial" | "failed"


class PlanNode(BaseModel):
    """One agent in the plan, with its dependency edges and live status."""

    id: str  # == agent_id, e.g. "market_research"
    department: str  # "strategy", "finance", ...
    stage: int  # department stage (1-based), from DEPARTMENT_STAGES
    feature: str | None = None  # "F20", carried through for telemetry
    execution: str = "sequential"  # "parallel" if it shares its stage, else "sequential"
    tier: str = "reasoning"  # copied from AgentSpec via the report roster
    max_tokens: int = 0  # copied from AgentSpec via the report roster
    grounding: str | None = None  # "serper" / "places" / None (report roster)

    # The genuinely new capability: explicit dependency edges. A node may only
    # start once every id listed here has reached COMPLETED (or SKIPPED).
    depends_on: list[str] = Field(default_factory=list)

    # Mutable execution state (updated by the executor, checkpointed each step).
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    tokens_used: int = 0
    error: str | None = None


class ExecutionPlan(BaseModel):
    """The self-contained plan document: nodes + edges + status.

    Persisted whole as one JSON column (plan_store.py). Re-saving it after every
    node is the checkpoint that gives crash recovery with no external infra.
    """

    id: str
    report_id: str  # the CONFIRMED planning_report this was compiled from
    prompt: str
    nodes: list[PlanNode] = Field(default_factory=list)

    status: PlanStatus = "draft"
    created_at: str
    updated_at: str

    # Convenience accessors (no logic beyond lookups) --------------------------

    def node(self, node_id: str) -> PlanNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}
