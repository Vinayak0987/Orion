"""Department runner registry (F17-F37).

The orchestrator (F11) resolves department nodes through this registry instead of
importing sub-graphs directly, so a department can be swapped or stubbed without
touching the DAG.

A runner is:

    async def runner(state: SharedBusinessState) -> dict

It returns a LangGraph partial-state update built with `apply_department_patch`,
so the append-only contract (F15) is enforced.

It must NOT return `metadata` or `intent`: those are single-writer channels with
no reducer, and a parallel-stage write to them raises InvalidUpdateError.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.agents.base import Agent
from app.agents.branding import BRANDING_STAGES
from app.agents.finance import FINANCE_STAGES
from app.agents.marketing import MARKETING_STAGES
from app.agents.operations import OPERATIONS_STAGES
from app.agents.strategy import STRATEGY_STAGES
from app.agents.subgraph import describe_department, make_department_runner
from app.models.state import AgentTrace, Department, SharedBusinessState

DepartmentRunner = Callable[[SharedBusinessState], Awaitable[dict]]

# Department -> staged agent groups. Agents in the same tuple run concurrently.
DEPARTMENT_STAGES: dict[Department, tuple[tuple[Agent, ...], ...]] = {
    Department.STRATEGY: STRATEGY_STAGES,
    Department.FINANCE: FINANCE_STAGES,
    Department.BRANDING: BRANDING_STAGES,
    Department.MARKETING: MARKETING_STAGES,
    Department.OPERATIONS: OPERATIONS_STAGES,
}

TOTAL_AGENT_COUNT = sum(
    len(stage) for stages in DEPARTMENT_STAGES.values() for stage in stages
)

DEPARTMENT_RUNNERS: dict[Department, DepartmentRunner] = {
    department: make_department_runner(department, stages)
    for department, stages in DEPARTMENT_STAGES.items()
}


def make_placeholder(department: Department) -> DepartmentRunner:
    """A runner that writes nothing. Useful for isolating one department in tests
    and for measuring orchestration overhead without LLM cost."""

    async def runner(state: SharedBusinessState) -> dict:
        return {
            "agent_traces": [
                AgentTrace(
                    agent_id=f"{department.value}_placeholder",
                    department=department,
                    status="skipped",
                    error="placeholder runner - no agents executed",
                )
            ]
        }

    return runner


def register_runner(department: Department, runner: DepartmentRunner) -> None:
    """Replace a department's runner. Used by tests and ablation experiments."""
    DEPARTMENT_RUNNERS[department] = runner


def get_runner(department: Department) -> DepartmentRunner:
    return DEPARTMENT_RUNNERS[department]


def agents_for(department: Department) -> list[Agent]:
    return [agent for stage in DEPARTMENT_STAGES[department] for agent in stage]


def all_agents() -> list[Agent]:
    return [agent for department in Department for agent in agents_for(department)]


def describe_all_departments() -> list[dict]:
    """Full agent topology. Surfaced by the API and used in the paper's figure."""
    return [
        describe_department(department, stages)
        for department, stages in DEPARTMENT_STAGES.items()
    ]
