"""Tests for the execution_plans + plan_events store (Planner Subsystem, Step 3).

Temporary database per test, same pattern as test_planning_store.py. Fully
offline - no LLM, no agents.
"""

from __future__ import annotations

import pytest

from app.generation.db import sqlite
from app.generation.planning import plan_store
from app.generation.planning.plan_models import ExecutionPlan, NodeStatus, PlanNode


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(
        sqlite.settings.__class__, "sqlite_file", property(lambda _self: db_file)
    )
    sqlite.init_db()
    plan_store.init_plans()


def _plan(**overrides) -> ExecutionPlan:
    base = {
        "id": "plan00000001",
        "report_id": "rep000000001",
        "prompt": "Ice cream shop in Andheri",
        "nodes": [
            PlanNode(id="market_research", department="strategy", stage=1, max_tokens=900),
            PlanNode(
                id="business_planning",
                department="strategy",
                stage=2,
                max_tokens=1200,
                depends_on=["market_research"],
            ),
        ],
        "status": "draft",
        "created_at": "2026-09-12T00:00:00+00:00",
        "updated_at": "2026-09-12T00:00:00+00:00",
    }
    base.update(overrides)
    return ExecutionPlan(**base)


# =============================================================================
# create / get roundtrip
# =============================================================================


def test_create_and_get_roundtrip() -> None:
    plan = plan_store.create_plan(_plan())
    fetched = plan_store.get_plan(plan.id)

    assert fetched is not None
    assert fetched.id == plan.id
    assert fetched.report_id == "rep000000001"
    assert len(fetched.nodes) == 2
    assert fetched.node("business_planning").depends_on == ["market_research"]
    assert all(n.status == NodeStatus.PENDING for n in fetched.nodes)


def test_get_missing_returns_none() -> None:
    assert plan_store.get_plan("nope") is None


def test_init_plans_is_idempotent() -> None:
    plan_store.init_plans()
    plan_store.init_plans()
    plan = plan_store.create_plan(_plan())
    assert plan_store.get_plan(plan.id) is not None


# =============================================================================
# save_plan - the checkpoint
# =============================================================================


def test_save_plan_persists_node_status_changes() -> None:
    plan = plan_store.create_plan(_plan())

    plan.node("market_research").status = NodeStatus.COMPLETED
    plan.node("market_research").tokens_used = 850
    plan.status = "running"
    plan_store.save_plan(plan)

    reloaded = plan_store.get_plan(plan.id)
    assert reloaded.status == "running"
    assert reloaded.node("market_research").status == NodeStatus.COMPLETED
    assert reloaded.node("market_research").tokens_used == 850
    assert reloaded.node("business_planning").status == NodeStatus.PENDING


def test_save_plan_bumps_updated_at() -> None:
    plan = plan_store.create_plan(_plan())
    original = plan.updated_at
    plan.status = "running"
    plan_store.save_plan(plan)
    assert plan_store.get_plan(plan.id).updated_at != original


# =============================================================================
# list / unfinished
# =============================================================================


def test_list_plans_summary_only_newest_first() -> None:
    for i in range(3):
        plan_store.create_plan(
            _plan(id=f"p{i}", created_at=f"2026-09-1{i}T09:00:00+00:00")
        )
    rows = plan_store.list_plans(limit=10)
    assert [r["id"] for r in rows] == ["p2", "p1", "p0"]
    assert rows[0]["node_count"] == 2
    assert "nodes" not in rows[0]  # summary only


def test_list_unfinished_returns_running_plans_only() -> None:
    running = plan_store.create_plan(_plan(id="running1", status="running"))
    plan_store.save_plan(running)  # ensure status column reflects 'running'
    plan_store.create_plan(_plan(id="done1", status="draft"))

    unfinished = plan_store.list_unfinished_plans()
    assert [p.id for p in unfinished] == ["running1"]


# =============================================================================
# events - append-only, same-transaction
# =============================================================================


def test_add_and_get_events_oldest_first() -> None:
    plan = plan_store.create_plan(_plan())
    plan_store.add_event(plan.id, "run_started")
    plan_store.add_event(
        plan.id, "node_completed", node_id="market_research", data={"tokens": 850}
    )

    events = plan_store.get_events(plan.id)
    assert [e["event_type"] for e in events] == ["run_started", "node_completed"]
    assert events[1]["node_id"] == "market_research"
    assert events[1]["data"] == {"tokens": 850}


def test_save_plan_with_event_commits_both_together() -> None:
    plan = plan_store.create_plan(_plan())
    plan.node("market_research").status = NodeStatus.COMPLETED
    plan.status = "running"

    plan_store.save_plan_with_event(
        plan, "node_completed", node_id="market_research", data={"tokens": 900}
    )

    reloaded = plan_store.get_plan(plan.id)
    events = plan_store.get_events(plan.id)
    # State change and its trace entry are both present.
    assert reloaded.node("market_research").status == NodeStatus.COMPLETED
    assert len(events) == 1
    assert events[0]["event_type"] == "node_completed"
    assert events[0]["node_id"] == "market_research"


def test_get_events_empty_for_unknown_plan() -> None:
    assert plan_store.get_events("nope") == []
