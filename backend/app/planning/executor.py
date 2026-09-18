"""Plan executor - run an ExecutionPlan by reusing the existing orchestrator.

The planner does NOT re-implement graph execution. `orchestrate()`
(app/orchestrator/runner.py) already compiles and runs the staged DAG via
`astream`, isolates a failed department, and survives a timeout with partial
results (F52). This executor is a thin wrapper that:

    1. checks the plan against the ExecutionPolicy before spending anything;
    2. drives `orchestrate()` to completion (reusing the real engine);
    3. maps the returned `agent_traces` back onto the plan's nodes
       (trace.agent_id == node.id) - status and tokens per node;
    4. derives the plan's own status from the run's RunStatus;
    5. checkpoints the plan and appends an execution event.

Everything is offline-testable: `orchestrate` accepts a `runners` override and a
fake `client`, so a test drives a full plan run with zero network and zero quota.

`PlanExecutor` is a Protocol (AgentArea's `TaskExecutorInterface` seam) so an
in-process executor can later be swapped for a queue-backed one without touching
callers.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from app.agents.registry import DepartmentRunner
from app.llm.chain import LLMClient
from app.models.state import Department, RunStatus, SharedBusinessState
from app.orchestrator.runner import orchestrate
from app.planning import plan_store
from app.planning.plan_models import ExecutionPlan, NodeStatus
from app.planning.policy import ExecutionPolicy, default_policy

log = structlog.get_logger(__name__)

# RunStatus -> plan status. Anything short of a clean completion is 'partial'
# except an outright failure, so the operator sees an honest verdict.
_PLAN_STATUS = {
    RunStatus.COMPLETED: "completed",
    RunStatus.PARTIAL: "partial",
    RunStatus.TIMEOUT: "partial",
    RunStatus.FAILED: "failed",
}

# AgentTrace.status -> NodeStatus.
_NODE_STATUS = {
    "completed": NodeStatus.COMPLETED,
    "failed": NodeStatus.FAILED,
    "skipped": NodeStatus.SKIPPED,
}


class PlanExecutor(Protocol):
    async def run(
        self,
        plan: ExecutionPlan,
        *,
        policy: ExecutionPolicy | None = ...,
        client: LLMClient | None = ...,
        runners: dict[Department, DepartmentRunner] | None = ...,
        persist: bool = ...,
    ) -> ExecutionPlan: ...


class BudgetError(RuntimeError):
    """The plan's upper-bound token estimate exceeds the policy ceiling."""


def _estimated_tokens(plan: ExecutionPlan) -> int:
    """Upper bound: sum of per-node max_tokens (the report's own estimate)."""
    return sum(node.max_tokens for node in plan.nodes)


def _apply_traces(plan: ExecutionPlan, state: SharedBusinessState) -> None:
    """Map the run's agent traces onto plan nodes (in place)."""
    traces = {t.agent_id: t for t in (state.get("agent_traces") or [])}
    for node in plan.nodes:
        trace = traces.get(node.id)
        if trace is None:
            # No trace for this node: the department didn't report it (e.g. a
            # placeholder runner). Leave it PENDING - honest, not invented.
            continue
        node.status = _NODE_STATUS.get(trace.status, NodeStatus.FAILED)
        node.tokens_used = trace.total_tokens
        node.attempts += 1
        node.error = trace.error


async def run_plan(
    plan: ExecutionPlan,
    *,
    policy: ExecutionPolicy | None = None,
    client: LLMClient | None = None,
    runners: dict[Department, DepartmentRunner] | None = None,
    persist: bool = False,
) -> ExecutionPlan:
    """Execute a plan and return it with node statuses and tokens filled in.

    Args:
        plan: a stored ExecutionPlan (must already exist in plan_store when
            `persist=True`, so checkpoints have a row to update).
        policy: run limits; `default_policy()` if omitted (fail-closed).
        client: LLM client override (tests inject a fake / dead provider).
        runners: department runner overrides (tests inject fakes).
        persist: also persist the underlying generation session (F59).

    Raises:
        BudgetError: if the plan's upper-bound estimate exceeds the ceiling.
    """
    active_policy = (policy or default_policy()).runtime_contract()

    estimate = _estimated_tokens(plan)
    if estimate > active_policy.max_tokens:
        raise BudgetError(
            f"plan estimate {estimate} tokens exceeds policy ceiling "
            f"{active_policy.max_tokens} - refusing to start the run"
        )

    plan.status = "running"
    plan_store.save_plan_with_event(
        plan,
        "run_started",
        data={"nodes": len(plan.nodes), "estimate_max_tokens": estimate},
    )

    try:
        state = await orchestrate(
            plan.prompt,
            client=client,
            runners=runners,
            persist=persist,
        )
    except Exception as exc:  # noqa: BLE001 - a run failure must not lose the plan
        plan.status = "failed"
        plan_store.save_plan_with_event(plan, "run_failed", data={"error": str(exc)[:300]})
        log.warning("plan.run_failed", plan_id=plan.id, error=str(exc)[:300])
        raise

    _apply_traces(plan, state)
    run_status = state["metadata"].status
    plan.status = _PLAN_STATUS.get(run_status, "partial")

    completed = sum(1 for n in plan.nodes if n.status == NodeStatus.COMPLETED)
    plan_store.save_plan_with_event(
        plan,
        "run_finished",
        data={
            "run_status": run_status.value,
            "nodes_completed": completed,
            "tokens_used": sum(n.tokens_used for n in plan.nodes),
        },
    )
    log.info(
        "plan.run_finished",
        plan_id=plan.id,
        status=plan.status,
        nodes_completed=completed,
    )
    return plan
