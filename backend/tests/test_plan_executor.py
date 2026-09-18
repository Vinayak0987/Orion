"""Tests for the plan executor (Planner Subsystem, Step 4).

Fully offline: a scripted LLM provider answers the intent classification, and
fake department runners emit real AgentTraces (with the actual agent_ids) so the
trace -> node mapping is genuinely exercised. No network, no quota.
"""

from __future__ import annotations

import json

import pytest

from app.agents.registry import agents_for
from app.db import sqlite
from app.llm.base import (
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.llm.chain import LLMClient
from app.models.state import AgentTrace, Department
from app.planning import plan_store
from app.planning.compile import compile_plan
from app.planning.executor import BudgetError, run_plan
from app.planning.plan_models import NodeStatus
from app.planning.policy import ExecutionPolicy
from app.planning.service import build_agent_roster

_PHYSICAL = (
    Department.STRATEGY,
    Department.FINANCE,
    Department.BRANDING,
    Department.MARKETING,
    Department.OPERATIONS,
)

PHYSICAL_PAYLOAD = {
    "business_type": "ice_cream_shop",
    "business_type_label": "Ice Cream Shop",
    "sector": "food_and_beverage",
    "area": "Andheri",
    "city": "Mumbai",
    "budget_text": "Rs 15L",
    "confidence": 0.9,
}


# --- offline LLM client (mirrors test_orchestrator.py) -----------------------


class _Scripted(LLMProvider):
    def __init__(self, payload: dict) -> None:
        self.name = ProviderName.GEMINI
        self.tracker = FreeTierTracker(name="gemini")
        self._payload = payload

    def model_for(self, tier: ModelTier) -> str:
        return "gemini-1.5-flash"

    async def is_available(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self._payload),
            provider=self.name,
            model="gemini-1.5-flash",
            prompt_tokens=40,
            completion_tokens=30,
        )


class _Dead(LLMProvider):
    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "dead"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable("dead")


def _client() -> LLMClient:
    return LLMClient(
        groq=_Dead(ProviderName.GROQ),
        gemini=_Scripted(PHYSICAL_PAYLOAD),
        ollama=_Dead(ProviderName.OLLAMA),
    )


def _completing_runner(department: Department, *, fail: bool = False):
    """A fake department runner that emits one COMPLETED (or FAILED) trace per
    real agent in the department, so trace.agent_id == node.id."""

    async def runner(state):
        traces = []
        for agent in agents_for(department):
            traces.append(
                AgentTrace(
                    agent_id=agent.spec.agent_id,
                    department=department,
                    status="failed" if fail else "completed",
                    completion_tokens=0 if fail else 50,
                    error="boom" if fail else None,
                )
            )
        return {"agent_traces": traces}

    return runner


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    plan_store.init_plans()


def _stored_plan():
    report = {
        "id": "rep000000001",
        "raw_prompt": "Ice cream shop in Andheri, Rs 15L budget",
        "agents": build_agent_roster(_PHYSICAL),
    }
    plan = compile_plan(report)
    plan_store.create_plan(plan)
    return plan


def _lenient_policy() -> ExecutionPolicy:
    return ExecutionPolicy(max_tokens=10_000_000, max_repair_rounds=1, node_timeout_s=120.0)


# =============================================================================
# happy path - every node completes
# =============================================================================


@pytest.mark.asyncio
async def test_run_plan_marks_all_nodes_completed() -> None:
    plan = _stored_plan()
    runners = {d: _completing_runner(d) for d in _PHYSICAL}

    result = await run_plan(
        plan, policy=_lenient_policy(), client=_client(), runners=runners
    )

    # Every node's trace mapped to COMPLETED with its tokens (the executor's job).
    assert all(n.status == NodeStatus.COMPLETED for n in result.nodes)
    assert all(n.tokens_used == 50 for n in result.nodes)
    assert all(n.attempts == 1 for n in result.nodes)
    # The plan status mirrors orchestrate's honest verdict. Fake runners emit
    # traces but write no section content, so completeness is 0 and the run
    # finalizes 'partial' - the executor faithfully reflects that, it does not
    # invent 'completed'. (Real agents write content; see the full pipeline.)
    assert result.status == "partial"


@pytest.mark.asyncio
async def test_run_plan_checkpoints_to_store() -> None:
    plan = _stored_plan()
    runners = {d: _completing_runner(d) for d in _PHYSICAL}

    await run_plan(plan, policy=_lenient_policy(), client=_client(), runners=runners)

    reloaded = plan_store.get_plan(plan.id)
    assert reloaded.status == "partial"  # persisted verdict matches the run
    assert all(n.status == NodeStatus.COMPLETED for n in reloaded.nodes)


@pytest.mark.asyncio
async def test_run_plan_emits_start_and_finish_events() -> None:
    plan = _stored_plan()
    runners = {d: _completing_runner(d) for d in _PHYSICAL}

    await run_plan(plan, policy=_lenient_policy(), client=_client(), runners=runners)

    events = plan_store.get_events(plan.id)
    types = [e["event_type"] for e in events]
    assert types[0] == "run_started"
    assert types[-1] == "run_finished"
    assert events[-1]["data"]["nodes_completed"] == 21


# =============================================================================
# partial - a department fails, run continues (F52)
# =============================================================================


@pytest.mark.asyncio
async def test_run_plan_partial_when_a_department_fails() -> None:
    plan = _stored_plan()
    runners = {d: _completing_runner(d) for d in _PHYSICAL}
    runners[Department.FINANCE] = _completing_runner(Department.FINANCE, fail=True)

    result = await run_plan(
        plan, policy=_lenient_policy(), client=_client(), runners=runners
    )

    assert result.status == "partial"
    finance_nodes = [n for n in result.nodes if n.department == "finance"]
    assert all(n.status == NodeStatus.FAILED for n in finance_nodes)
    strategy_nodes = [n for n in result.nodes if n.department == "strategy"]
    assert all(n.status == NodeStatus.COMPLETED for n in strategy_nodes)


# =============================================================================
# budget guard
# =============================================================================


@pytest.mark.asyncio
async def test_run_plan_rejects_when_estimate_exceeds_budget() -> None:
    plan = _stored_plan()
    tiny = ExecutionPolicy(max_tokens=100, max_repair_rounds=1, node_timeout_s=120.0)

    with pytest.raises(BudgetError, match="exceeds policy ceiling"):
        await run_plan(plan, policy=tiny, client=_client())

    # The plan was never marked running - the guard fires before any run.
    reloaded = plan_store.get_plan(plan.id)
    assert reloaded.status == "draft"
