"""Department agents (F17-F37) - 21 specialized agents across 5 sub-graphs."""

from app.generation.agents.base import Agent, AgentSpec, context_block, upstream_block
from app.generation.agents.registry import (
    DEPARTMENT_RUNNERS,
    DEPARTMENT_STAGES,
    TOTAL_AGENT_COUNT,
    DepartmentRunner,
    agents_for,
    all_agents,
    describe_all_departments,
    get_runner,
    make_placeholder,
    register_runner,
)
from app.generation.agents.subgraph import build_department_subgraph, make_department_runner

__all__ = [
    "DEPARTMENT_RUNNERS",
    "DEPARTMENT_STAGES",
    "TOTAL_AGENT_COUNT",
    "Agent",
    "AgentSpec",
    "DepartmentRunner",
    "agents_for",
    "all_agents",
    "build_department_subgraph",
    "context_block",
    "describe_all_departments",
    "get_runner",
    "make_department_runner",
    "make_placeholder",
    "register_runner",
    "upstream_block",
]
