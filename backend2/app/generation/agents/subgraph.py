"""Department sub-graphs.

Each department is its own compiled LangGraph, nested inside the orchestrator's
graph as a single node. Agents are grouped into stages: agents in the same stage
share a superstep and run concurrently; a later stage can read what an earlier
stage wrote.

That staging is what makes intra-department dependencies work. In Finance, for
example, the P&L agent needs the revenue and cost agents to have finished:

    stage 1   revenue_model  ∥  cost_structure
    stage 2   funding_strategy  ∥  pl_forecast

The sub-graph is invoked with a *derived* state, not the parent state, so the
telemetry lists start empty. Otherwise the parent's `operator.add` reducer would
re-append traces that already existed and the token totals behind F58 would be
inflated.
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph

from app.generation.agents.base import Agent
from app.generation.llm.chain import LLMClient
from app.generation.models.state import Department, SharedBusinessState, has_content

log = structlog.get_logger(__name__)

AgentStages = tuple[tuple[Agent, ...], ...]


def _make_agent_node(agent: Agent, client: LLMClient | None):
    async def node(state: SharedBusinessState) -> dict:
        return await agent.run(state, client=client)

    node.__name__ = f"{agent.spec.agent_id}_node"
    return node


def build_department_subgraph(
    stages: AgentStages,
    client: LLMClient | None = None,
):
    """Compile a department sub-graph from staged agent groups."""
    builder: StateGraph = StateGraph(SharedBusinessState)

    non_empty = tuple(stage for stage in stages if stage)
    if not non_empty:
        raise ValueError("a department needs at least one agent")

    for stage in non_empty:
        for agent in stage:
            builder.add_node(agent.spec.agent_id, _make_agent_node(agent, client))

    for agent in non_empty[0]:
        builder.add_edge(START, agent.spec.agent_id)

    for current, following in zip(non_empty, non_empty[1:], strict=False):
        for source in current:
            for target in following:
                builder.add_edge(source.spec.agent_id, target.spec.agent_id)

    for agent in non_empty[-1]:
        builder.add_edge(agent.spec.agent_id, END)

    return builder.compile()


def _derive_substate(
    state: SharedBusinessState, department: Department
) -> SharedBusinessState:
    """Build the sub-graph's input: intent, prompt, and upstream sections only."""
    substate: SharedBusinessState = {
        "session_id": state.get("session_id", ""),
        "raw_prompt": state.get("raw_prompt", ""),
        "agent_traces": [],
        "api_traces": [],
        "errors": [],
    }
    intent = state.get("intent")
    if intent is not None:
        substate["intent"] = intent

    # Upstream departments are readable; this department starts from whatever the
    # parent already holds (normally nothing).
    for other in Department:
        section = state.get(other.value)
        if section is not None:
            substate[other.value] = section

    return substate


def make_department_runner(
    department: Department,
    stages: AgentStages,
    client: LLMClient | None = None,
):
    """Build the `DepartmentRunner` the orchestrator registry expects.

    Returns only this department's section plus new telemetry, so the parent
    graph never sees a write to another department's channel (F15) and never
    double-counts traces.
    """
    graph = build_department_subgraph(stages, client)
    agent_count = sum(len(stage) for stage in stages if stage)

    async def runner(state: SharedBusinessState) -> dict:
        result = await graph.ainvoke(_derive_substate(state, department))

        update: dict = {
            "agent_traces": result.get("agent_traces") or [],
            # api_traces must be forwarded too. Omitting them silently discarded
            # every external call record, so F46 transparency showed zero API
            # calls on a run whose competitors had come from OpenStreetMap.
            "api_traces": result.get("api_traces") or [],
            "errors": result.get("errors") or [],
        }
        # LangGraph seeds a reducer-backed channel with an all-defaults instance,
        # so an empty section must be suppressed rather than reported as output.
        section = result.get(department.value)
        if has_content(section):
            update[department.value] = section

        log.info(
            "department.subgraph_finished",
            department=department.value,
            agents=agent_count,
            completed=len(
                [t for t in update["agent_traces"] if t.status == "completed"]
            ),
            failed=len([t for t in update["agent_traces"] if t.status == "failed"]),
            api_calls=len(update["api_traces"]),
        )
        return update

    return runner


def describe_department(department: Department, stages: AgentStages) -> dict:
    """Sub-graph description for the API and the paper's architecture figure."""
    return {
        "department": department.value,
        "agent_count": sum(len(stage) for stage in stages if stage),
        "stages": [
            {
                "stage": index + 1,
                "agents": [a.spec.agent_id for a in stage],
                "features": [a.spec.feature for a in stage],
                "execution": "parallel" if len(stage) > 1 else "sequential",
            }
            for index, stage in enumerate(s for s in stages if s)
        ],
    }
