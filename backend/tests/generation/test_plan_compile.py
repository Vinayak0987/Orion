"""Tests for compile_plan - report -> ExecutionPlan (Planner Subsystem, Step 2).

Deterministic and fully offline: it builds the agent roster from Orion's real
topology (service.build_agent_roster) so the dependency wiring is tested against
the actual DEPARTMENT_STAGES, then checks the compiler on that roster. No LLM,
no database.
"""

from __future__ import annotations

from app.generation.models.state import Department
from app.generation.planning.compile import compile_plan
from app.generation.planning.plan_models import NodeStatus
from app.generation.planning.service import build_agent_roster

# All five departments = a physical business (21 agents).
_PHYSICAL = (
    Department.STRATEGY,
    Department.FINANCE,
    Department.BRANDING,
    Department.MARKETING,
    Department.OPERATIONS,
)
# Operations omitted = a digital business (17 agents).
_DIGITAL = (
    Department.STRATEGY,
    Department.FINANCE,
    Department.BRANDING,
    Department.MARKETING,
)


def _report(active: tuple[Department, ...], prompt: str = "A test business") -> dict:
    """A minimal report row carrying a real roster for the active departments."""
    return {
        "id": "rep000000001",
        "raw_prompt": prompt,
        "agents": build_agent_roster(active),
    }


# =============================================================================
# node projection
# =============================================================================


def test_physical_report_compiles_to_21_nodes() -> None:
    plan = compile_plan(_report(_PHYSICAL))
    assert len(plan.nodes) == 21
    assert plan.status == "draft"
    assert all(n.status == NodeStatus.PENDING for n in plan.nodes)
    assert plan.report_id == "rep000000001"


def test_digital_report_compiles_to_17_nodes_no_operations() -> None:
    plan = compile_plan(_report(_DIGITAL))
    assert len(plan.nodes) == 17
    assert all(n.department != "operations" for n in plan.nodes)


def test_node_fields_copied_verbatim_from_roster() -> None:
    report = _report(_PHYSICAL)
    plan = compile_plan(report)
    roster = {a["agent_id"]: a for a in report["agents"]}

    for node in plan.nodes:
        entry = roster[node.id]
        assert node.department == entry["department"]
        assert node.stage == entry["department_stage"]
        assert node.tier == entry["tier"]
        assert node.max_tokens == entry["max_tokens"]
        assert node.grounding == entry["grounding"]


# =============================================================================
# dependency wiring
# =============================================================================


def test_stage_one_nodes_have_no_dependencies_except_operations_join() -> None:
    """Stage-1 nodes start with no predecessors - EXCEPT operations' entry
    stage, which is the cross-department join point (it waits for all of the
    other departments' stage 2, per build_graph's fan-in)."""
    plan = compile_plan(_report(_PHYSICAL))
    for node in plan.nodes:
        if node.stage == 1 and node.department != "operations":
            assert node.depends_on == [], f"{node.id} should have no deps"


def test_stage_two_depends_on_same_department_stage_one() -> None:
    plan = compile_plan(_report(_PHYSICAL))
    # business_planning (strategy, stage 2) depends on strategy stage-1 agents.
    bp = plan.node("business_planning")
    assert bp is not None and bp.stage == 2
    strategy_stage1 = {
        n.id for n in plan.nodes if n.department == "strategy" and n.stage == 1
    }
    assert set(bp.depends_on) == strategy_stage1
    # And never on a different department.
    assert all(plan.node(dep).department == "strategy" for dep in bp.depends_on)


def test_operations_joins_on_all_stage_two_across_departments() -> None:
    plan = compile_plan(_report(_PHYSICAL))
    ops_nodes = [n for n in plan.nodes if n.department == "operations"]
    assert ops_nodes, "physical plan must contain operations"

    stage2_other_depts = {
        n.id
        for n in plan.nodes
        if n.department != "operations" and n.stage == 2
    }
    # The join attaches to operations' ENTRY stage (its earliest stage) - the
    # nodes that receive build_graph's fan-in from stage 2.
    ops_entry_stage = min(n.stage for n in ops_nodes)
    for ops in ops_nodes:
        if ops.stage == ops_entry_stage:
            assert stage2_other_depts.issubset(set(ops.depends_on))
        else:
            # Later operations stages depend on their own earlier stage, which
            # transitively reaches stage 2 - they don't re-list it directly.
            ops_prev = {
                n.id
                for n in plan.nodes
                if n.department == "operations" and n.stage == ops.stage - 1
            }
            assert ops_prev.issubset(set(ops.depends_on))


def test_no_node_depends_on_itself_and_deps_are_unique() -> None:
    plan = compile_plan(_report(_PHYSICAL))
    for node in plan.nodes:
        assert node.id not in node.depends_on
        assert len(node.depends_on) == len(set(node.depends_on))


def test_every_dependency_is_a_real_node_in_the_plan() -> None:
    """No dangling edges - a dependency must point at a node that exists."""
    plan = compile_plan(_report(_PHYSICAL))
    ids = plan.node_ids()
    for node in plan.nodes:
        for dep in node.depends_on:
            assert dep in ids, f"{node.id} depends on unknown node {dep}"


def test_digital_plan_has_no_dangling_operations_edges() -> None:
    """Since operations is absent, no remaining node may reference it."""
    plan = compile_plan(_report(_DIGITAL))
    ids = plan.node_ids()
    for node in plan.nodes:
        for dep in node.depends_on:
            assert dep in ids


# =============================================================================
# determinism
# =============================================================================


def test_compile_is_deterministic_for_the_same_report() -> None:
    """Same report -> identical nodes+edges (ids/timestamps aside)."""
    report = _report(_PHYSICAL)
    a = compile_plan(report)
    b = compile_plan(report)

    def signature(plan):
        return sorted(
            (n.id, n.department, n.stage, tuple(sorted(n.depends_on))) for n in plan.nodes
        )

    assert signature(a) == signature(b)


def test_empty_roster_compiles_to_empty_plan() -> None:
    plan = compile_plan({"id": "r", "raw_prompt": "p", "agents": []})
    assert plan.nodes == []
    assert plan.status == "draft"
