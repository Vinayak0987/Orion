"""Tests for the loop registry and its two invariants.

The rejection cases matter more than the acceptance cases. An invariant that
never refuses anything is decoration, so each is tested against a topology it
must reject and a minimally different one it must accept.
"""

from __future__ import annotations

import pytest

from app.generation.operating.loops import (
    TERMINATING_KINDS,
    Loop,
    LoopGraph,
    LoopKind,
    TopologyViolation,
    default_graph,
)


def ex(loop_id: str, *sends_to: str, signal: str | None = None) -> Loop:
    return Loop(loop_id, LoopKind.EXECUTION, sends_to=sends_to,
                evaluation_signal=signal or f"{loop_id}_objective")


# ============================== I1 — TERMINATION ==============================


def test_agent_only_cycle_is_rejected():
    """A -> B -> C -> A with nothing external. The headline rejection case."""
    graph = LoopGraph(validate_on_register=False)
    graph.loops.update({
        l.id: l for l in [ex("a", "b"), ex("b", "c"), ex("c", "a")]
    })
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I1_TERMINATION"
    assert set(excinfo.value.path) >= {"a", "b", "c"}


def test_the_same_cycle_is_accepted_once_routed_through_an_anchor():
    graph = LoopGraph()
    graph.register_all([
        Loop("anchor", LoopKind.ANCHOR, sends_to=("a",)),
        ex("a", "b"),
        ex("b", "c"),
        ex("c", "anchor"),
    ])
    assert graph.unterminated_cycles() == []


def test_a_human_node_terminates_a_cycle_equally_well():
    graph = LoopGraph()
    graph.register_all([
        Loop("human", LoopKind.HUMAN, sends_to=("a",)),
        ex("a", "b"),
        ex("b", "human"),
    ])
    assert graph.unterminated_cycles() == []


def test_two_cycle_between_agents_is_rejected():
    graph = LoopGraph(validate_on_register=False)
    graph.loops.update({l.id: l for l in [ex("a", "b"), ex("b", "a")]})
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I1_TERMINATION"


def test_self_loop_on_an_execution_node_is_rejected():
    graph = LoopGraph(validate_on_register=False)
    graph.loops["a"] = ex("a", "a")
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I1_TERMINATION"


def test_acyclic_topology_needs_no_terminating_node():
    graph = LoopGraph()
    graph.register_all([ex("a", "b"), ex("b", "c"), ex("c")])
    assert graph.cycles() == []
    assert graph.unterminated_cycles() == []


def test_a_long_agent_cycle_is_still_rejected():
    ids = [f"n{i}" for i in range(12)]
    loops = [ex(ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids))]
    graph = LoopGraph(validate_on_register=False)
    graph.loops.update({l.id: l for l in loops})
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I1_TERMINATION"


def test_one_bad_cycle_among_good_ones_is_caught():
    graph = LoopGraph(validate_on_register=False)
    graph.loops.update({l.id: l for l in [
        Loop("anchor", LoopKind.ANCHOR, sends_to=("a",)),
        ex("a", "anchor"),
        ex("x", "y"),
        ex("y", "x"),   # the offender
    ]})
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert set(excinfo.value.path) >= {"x", "y"}


def test_registration_rejects_the_loop_that_closes_a_bad_cycle():
    """Validation happens on register, not later at run time."""
    graph = LoopGraph()
    graph.register(ex("a", "b"))
    graph.register(ex("b", "c"))
    with pytest.raises(TopologyViolation):
        graph.register(ex("c", "a"))
    assert "c" not in graph.loops  # the rejected loop is not retained


# ============================= I2 — INDEPENDENCE =============================


def test_monitor_sharing_its_subjects_signal_is_rejected():
    graph = LoopGraph(validate_on_register=False)
    graph.loops.update({l.id: l for l in [
        ex("marketing", signal="footfall"),
        Loop("watcher", LoopKind.MONITOR, monitors=("marketing",),
             evaluation_signal="footfall"),
    ]})
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I2_INDEPENDENCE"
    assert "footfall" in str(excinfo.value)


def test_monitor_with_a_disjoint_signal_is_accepted():
    graph = LoopGraph()
    graph.register_all([
        ex("marketing", signal="footfall"),
        Loop("watcher", LoopKind.MONITOR, monitors=("marketing",),
             evaluation_signal="detection_quality"),
    ])
    assert graph.loops["watcher"].evaluation_signal == "detection_quality"


def test_monitor_auditing_itself_is_rejected():
    graph = LoopGraph(validate_on_register=False)
    graph.loops["m"] = Loop("m", LoopKind.MONITOR, monitors=("m",),
                            evaluation_signal="q")
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "I2_INDEPENDENCE"


def test_monitor_with_no_signal_is_permitted():
    """A monitor that is not scored cannot share a score."""
    graph = LoopGraph()
    graph.register_all([
        ex("marketing", signal="footfall"),
        Loop("watcher", LoopKind.MONITOR, monitors=("marketing",)),
    ])
    assert graph.loops["watcher"].evaluation_signal is None


def test_only_a_monitor_may_declare_monitors():
    with pytest.raises(ValueError) as excinfo:
        Loop("a", LoopKind.EXECUTION, monitors=("b",))
    assert "only a MONITOR" in str(excinfo.value)


def test_terminating_node_may_not_carry_an_evaluation_signal():
    """An anchor judged by a metric would no longer be outside the game."""
    with pytest.raises(ValueError) as excinfo:
        Loop("anchors", LoopKind.ANCHOR, evaluation_signal="something")
    assert "must not carry an evaluation signal" in str(excinfo.value)

    with pytest.raises(ValueError):
        Loop("human", LoopKind.HUMAN, evaluation_signal="satisfaction")


# ================================ REFERENCES =================================


def test_dangling_send_target_is_rejected_on_full_validation():
    graph = LoopGraph(validate_on_register=False)
    graph.loops["a"] = ex("a", "nowhere")
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "REFERENCES"


def test_dangling_monitor_target_is_rejected():
    graph = LoopGraph(validate_on_register=False)
    graph.loops["m"] = Loop("m", LoopKind.MONITOR, monitors=("ghost",),
                            evaluation_signal="q")
    with pytest.raises(TopologyViolation) as excinfo:
        graph.validate()
    assert excinfo.value.invariant == "REFERENCES"


def test_forward_references_are_allowed_during_bulk_registration():
    graph = LoopGraph()
    graph.register_all([
        Loop("anchor", LoopKind.ANCHOR, sends_to=("a",)),
        ex("a", "anchor"),
    ])
    assert set(graph.loops) == {"anchor", "a"}


def test_bulk_registration_rolls_back_on_failure():
    graph = LoopGraph()
    graph.register(Loop("anchor", LoopKind.ANCHOR, sends_to=()))
    with pytest.raises(TopologyViolation):
        graph.register_all([ex("x", "y"), ex("y", "x")])
    assert set(graph.loops) == {"anchor"}


def test_duplicate_registration_is_rejected():
    graph = LoopGraph()
    graph.register(ex("a"))
    with pytest.raises(ValueError):
        graph.register(ex("a"))


def test_loop_requires_an_id():
    with pytest.raises(ValueError):
        Loop("   ", LoopKind.EXECUTION)


def test_loop_is_frozen():
    loop = ex("a")
    with pytest.raises(Exception):
        loop.id = "b"


# =============================== DEFAULT GRAPH ===============================


def test_default_graph_validates():
    graph = default_graph()
    graph.validate()
    assert graph.unterminated_cycles() == []


def test_default_graph_has_the_five_implemented_departments():
    graph = default_graph()
    departments = {l.id for l in graph.of_kind(LoopKind.EXECUTION)}
    assert departments == {"strategy", "finance", "branding", "marketing",
                           "operations"}


def test_default_graph_has_four_monitors():
    graph = default_graph()
    monitors = {l.id for l in graph.of_kind(LoopKind.MONITOR)}
    assert monitors == {"goodhart_detector", "conflict_detector",
                        "drift_monitor", "objective_review"}


def test_default_graph_monitors_are_all_independent():
    graph = default_graph()
    for monitor in graph.of_kind(LoopKind.MONITOR):
        for subject_id in monitor.monitors:
            subject = graph.loops[subject_id]
            assert monitor.evaluation_signal != subject.evaluation_signal


def test_default_graph_every_cycle_is_terminated():
    graph = default_graph()
    cycles = graph.cycles()
    assert cycles, "the default topology should contain cycles; it is a loop graph"
    for cycle in cycles:
        kinds = {graph.loops[node].kind for node in cycle}
        assert kinds & TERMINATING_KINDS, f"cycle {cycle} has no anchor or human"


def test_default_graph_anchor_carries_no_evaluation_signal():
    graph = default_graph()
    assert graph.loops["anchors"].evaluation_signal is None
    assert graph.loops["human_review"].evaluation_signal is None


def test_describe_reports_validity_and_cycles():
    graph = default_graph()
    described = graph.describe()
    assert described["valid"] is True
    assert described["unterminated_cycles"] == []
    # 1 anchor + 1 human + 5 execution + 4 monitors + 1 learning
    assert len(described["loops"]) == 12
    assert len(graph.of_kind(LoopKind.ANCHOR)) == 1
    assert len(graph.of_kind(LoopKind.HUMAN)) == 1
    assert len(graph.of_kind(LoopKind.EXECUTION)) == 5
    assert len(graph.of_kind(LoopKind.MONITOR)) == 4
    assert len(graph.of_kind(LoopKind.LEARNING)) == 1
    ids = {l["id"] for l in described["loops"]}
    assert "goodhart_detector" in ids


def test_monitors_run_less_often_than_execution_loops():
    """Throughput is bounded by local inference, so monitors are cheaper."""
    graph = default_graph()
    fastest_monitor = min(
        l.cadence_seconds for l in graph.of_kind(LoopKind.MONITOR)
        if l.cadence_seconds
    )
    fastest_execution = min(
        l.cadence_seconds for l in graph.of_kind(LoopKind.EXECUTION)
        if l.cadence_seconds
    )
    assert fastest_monitor >= fastest_execution
