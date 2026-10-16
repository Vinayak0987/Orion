"""Tests for the ExecutionPlan data model (Planner Subsystem, Step 1).

Pure shape tests - no database, no LLM, no agents. Fully offline.
"""

from __future__ import annotations

from app.generation.planning.plan_models import ExecutionPlan, NodeStatus, PlanNode


def _node(**overrides) -> PlanNode:
    base = {
        "id": "market_research",
        "department": "strategy",
        "stage": 1,
        "tier": "reasoning",
        "max_tokens": 900,
    }
    base.update(overrides)
    return PlanNode(**base)


def _plan(**overrides) -> ExecutionPlan:
    base = {
        "id": "plan00000001",
        "report_id": "rep000000001",
        "prompt": "Ice cream shop in Andheri, Rs 15L budget",
        "nodes": [_node()],
        "created_at": "2026-09-12T00:00:00+00:00",
        "updated_at": "2026-09-12T00:00:00+00:00",
    }
    base.update(overrides)
    return ExecutionPlan(**base)


def test_node_defaults() -> None:
    node = _node()
    assert node.status == NodeStatus.PENDING
    assert node.depends_on == []
    assert node.attempts == 0
    assert node.tokens_used == 0
    assert node.error is None


def test_node_status_is_string_enum() -> None:
    node = _node(status=NodeStatus.COMPLETED)
    assert node.status == "completed"
    assert node.status.value == "completed"


def test_plan_defaults_to_draft() -> None:
    plan = _plan()
    assert plan.status == "draft"
    assert len(plan.nodes) == 1


def test_plan_node_lookup() -> None:
    plan = _plan(
        nodes=[_node(id="market_research"), _node(id="risk_analysis", stage=2)]
    )
    assert plan.node("risk_analysis").stage == 2
    assert plan.node("missing") is None
    assert plan.node_ids() == {"market_research", "risk_analysis"}


def test_plan_roundtrips_through_json() -> None:
    """The plan is persisted whole as one JSON column, so it must survive a
    serialize -> deserialize cycle unchanged."""
    plan = _plan(
        nodes=[
            _node(id="market_research", stage=1),
            _node(id="business_planning", stage=2, depends_on=["market_research"]),
        ]
    )
    restored = ExecutionPlan.model_validate_json(plan.model_dump_json())
    assert restored == plan
    assert restored.node("business_planning").depends_on == ["market_research"]
