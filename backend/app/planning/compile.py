"""Compile a confirmed planning report into an explicit ExecutionPlan.

This is the heart of the Planner Subsystem, and it is deterministic: it reuses
the flattened agent roster the report already carries (service.build_agent_roster,
itself a projection of agents/registry.py:DEPARTMENT_STAGES) and turns the
implicit staging into explicit `depends_on` edges. No LLM call. No topology is
re-derived - the plan is COMPUTED from the report exactly as anchors are computed
from the ledger (the project's central invariant).

Dependency rule (mirrors orchestrator/graph.py:build_graph):
    - A node in stage N depends on every node of the SAME department in stage N-1.
    - Operations is a cross-department join: because build_graph fans all of
      stage 2 into operations, every operations node additionally depends on
      every stage-2 node in the other departments.

Because the edges come straight from the report's own staging, a physical prompt
yields 21 nodes and a digital prompt yields 17 (operations absent) with no extra
logic - the same single source of truth the report used.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.state import Department
from app.planning.plan_models import ExecutionPlan, PlanNode

# The department that runs last as a cross-department join (graph.py topology).
_OPERATIONS = Department.OPERATIONS.value


def new_plan_id() -> str:
    """Same shape as report/session ids (uuid4().hex[:12])."""
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _node_from_roster_entry(entry: dict) -> PlanNode:
    """One roster entry (service.build_agent_roster shape) -> one PlanNode.

    Values are copied verbatim; nothing is inferred here.
    """
    return PlanNode(
        id=entry["agent_id"],
        department=entry["department"],
        stage=entry["department_stage"],
        feature=entry.get("feature"),
        execution=entry.get("execution", "sequential"),
        tier=entry.get("tier", "reasoning"),
        max_tokens=entry.get("max_tokens", 0),
        grounding=entry.get("grounding"),
    )


def _wire_dependencies(nodes: list[PlanNode]) -> None:
    """Fill each node's `depends_on` in place, from stage layout alone."""
    # The entry stage of each department (its earliest stage). The cross-
    # department operations join attaches only to operations' entry stage - the
    # nodes that actually receive build_graph's fan-in from stage 2. Later
    # operations stages reach stage 2 transitively via the same-department rule.
    entry_stage_by_dept: dict[str, int] = {}
    for node in nodes:
        entry_stage_by_dept[node.department] = min(
            entry_stage_by_dept.get(node.department, node.stage), node.stage
        )

    for node in nodes:
        deps: list[str] = []

        if node.stage > 1:
            # Same-department predecessors one stage earlier.
            deps.extend(
                other.id
                for other in nodes
                if other.department == node.department
                and other.stage == node.stage - 1
            )

        if (
            node.department == _OPERATIONS
            and node.stage == entry_stage_by_dept[_OPERATIONS]
        ):
            # The cross-department join: operations' ENTRY stage waits for all of
            # stage 2 in every OTHER department (build_graph fans stage 2 into
            # the operations node).
            deps.extend(
                other.id
                for other in nodes
                if other.department != _OPERATIONS and other.stage == 2
            )

        # Deduplicate while preserving order, and never depend on self.
        seen: set[str] = set()
        node.depends_on = [
            dep for dep in deps if dep != node.id and not (dep in seen or seen.add(dep))
        ]


def compile_plan(report: dict) -> ExecutionPlan:
    """Project a confirmed planning report into an ExecutionPlan.

    Args:
        report: a stored report row (store.get_report shape). Only `id`,
            `raw_prompt` and `agents` are read; the caller is responsible for
            checking the report is confirmed before compiling (plan_api.py).

    Returns:
        A `draft` ExecutionPlan with every node PENDING and edges wired.
    """
    nodes = [_node_from_roster_entry(entry) for entry in report.get("agents", [])]
    _wire_dependencies(nodes)

    now = _now()
    return ExecutionPlan(
        id=new_plan_id(),
        report_id=report["id"],
        prompt=report.get("raw_prompt") or report.get("prompt") or "",
        nodes=nodes,
        status="draft",
        created_at=now,
        updated_at=now,
    )
