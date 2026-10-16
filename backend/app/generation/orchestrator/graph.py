"""F11/F12 - Execution DAG construction and parallel execution.

Builds a LangGraph `StateGraph` over `SharedBusinessState` from a RoutingDecision.

Topology for a physical business (all five departments active):

    START ──► strategy ──┬──► finance   ──┐
                         ├──► branding  ──┼──► operations ──► END
                         └──► marketing ──┘

Stage 2's three departments share a single superstep, so LangGraph runs them
concurrently. Operations has three inbound edges, which makes it a join: it does
not start until all of Stage 2 has finished. That is the barrier F12 requires.

For a digital business Operations is absent and Stage 2 fans directly into END:

    START ──► strategy ──┬──► finance   ──► END
                         ├──► branding  ──► END
                         └──► marketing ──► END

Concurrency safety: department nodes write only their own section plus the
reducer-backed telemetry lists (`agent_traces`, `api_traces`, `errors`). They
never write `metadata` or `intent`, which have no reducer and would raise
InvalidUpdateError on a concurrent write.
"""

from __future__ import annotations

import time

import structlog
from langgraph.graph import END, START, StateGraph

from app.generation.agents.registry import DepartmentRunner, get_runner
from app.generation.models.state import AgentTrace, Department, SharedBusinessState
from app.generation.orchestrator.progress import ProgressEmitter
from app.generation.orchestrator.routing import RoutingDecision

log = structlog.get_logger(__name__)


def node_name(department: Department) -> str:
    """Graph node id for a department.

    LangGraph rejects a node name that matches a state channel key, and every
    department already owns a channel named after itself ("strategy",
    "finance", ...), so node ids carry a `_dept` suffix.
    """
    return f"{department.value}_dept"


def _make_node(
    department: Department,
    runner: DepartmentRunner,
    emitter: ProgressEmitter,
):
    """Wrap a department runner with progress events and failure isolation."""

    async def node(state: SharedBusinessState) -> dict:
        await emitter.department_started(department)
        started = time.perf_counter()

        try:
            update = await runner(state)
        except Exception as exc:  # noqa: BLE001 - one department must not kill the run
            elapsed = int((time.perf_counter() - started) * 1000)
            log.warning(
                "department.failed",
                department=department.value,
                error=str(exc)[:300],
                latency_ms=elapsed,
            )
            await emitter.department_failed(department, str(exc))
            # F52: the run continues and reports partial results.
            return {
                "errors": [f"{department.value}: {exc}"],
                "agent_traces": [
                    AgentTrace(
                        agent_id=f"{department.value}_department",
                        department=department,
                        status="failed",
                        latency_ms=elapsed,
                        error=str(exc)[:500],
                    )
                ],
            }

        elapsed = int((time.perf_counter() - started) * 1000)
        log.info("department.completed", department=department.value, latency_ms=elapsed)
        await emitter.department_completed(department)
        return update or {}

    node.__name__ = f"{department.value}_node"
    return node


def build_graph(
    decision: RoutingDecision,
    emitter: ProgressEmitter,
    runners: dict[Department, DepartmentRunner] | None = None,
):
    """Compile the execution DAG for a routing decision.

    Args:
        decision: which departments run, and their stage layout (F10).
        emitter: progress sink (F12).
        runners: optional override map; tests inject fakes. Defaults to the
            registry in `app.generation.agents.registry`.

    Returns:
        A compiled LangGraph ready for `.ainvoke()` / `.astream()`.
    """
    builder: StateGraph = StateGraph(SharedBusinessState)
    stages = decision.stages

    if not stages:
        raise ValueError("RoutingDecision produced no executable stages")

    for stage in stages:
        for department in stage:
            runner = (runners or {}).get(department) or get_runner(department)
            builder.add_node(node_name(department), _make_node(department, runner, emitter))

    # Entry: every department in the first stage.
    for department in stages[0]:
        builder.add_edge(START, node_name(department))

    # Fan-out / fan-in between consecutive stages.
    for current, following in zip(stages, stages[1:], strict=False):
        for source in current:
            for target in following:
                builder.add_edge(node_name(source), node_name(target))

    # Exit: every department in the last stage.
    for department in stages[-1]:
        builder.add_edge(node_name(department), END)

    compiled = builder.compile()
    log.info(
        "graph.compiled",
        stages=[[d.value for d in stage] for stage in stages],
        active=[d.value for d in decision.active],
        skipped=[d.value for d in decision.skipped],
        dynamic=decision.dynamic,
    )
    return compiled


def describe_graph(decision: RoutingDecision) -> dict:
    """Human-readable DAG description. Surfaced by the API and used in the paper's
    architecture figure."""
    stages = decision.stages
    return {
        "stages": [
            {
                "stage": index + 1,
                "departments": [d.value for d in stage],
                "execution": "parallel" if len(stage) > 1 else "sequential",
            }
            for index, stage in enumerate(stages)
        ],
        "active_departments": [d.value for d in decision.active],
        "skipped_departments": [d.value for d in decision.skipped],
        "dynamic_routing": decision.dynamic,
        "routing_reason": decision.reason,
    }
