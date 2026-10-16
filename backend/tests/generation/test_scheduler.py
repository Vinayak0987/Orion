"""Tests for the cadence scheduler.

Every test injects time explicitly. Nothing sleeps, and the whole file runs in
well under a second — which is the point of making the kernel clock-injected.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.generation.operating import scheduler as S
from app.generation.operating.loops import Loop, LoopGraph, LoopKind
from app.generation.operating.scheduler import (
    ManualClock,
    RunStatus,
    Scheduler,
    stagger_offset,
)

T0 = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
HOUR = 3600
DAY = 86_400


@pytest.fixture(autouse=True)
def sched_db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module

    db_file = tmp_path / "scheduler-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    S.init_scheduler()
    yield


def graph_of(*loops: Loop) -> LoopGraph:
    g = LoopGraph(validate_on_register=False)
    for loop in loops:
        g.loops[loop.id] = loop
    return g


def dept(loop_id: str, cadence: int = DAY) -> Loop:
    return Loop(loop_id, LoopKind.EXECUTION, cadence_seconds=cadence,
                evaluation_signal=f"{loop_id}_objective")


def scheduler_with(*loops: Loop, **kwargs) -> Scheduler:
    defaults = dict(clock=ManualClock(T0), respect_stagger=False, max_per_tick=10)
    defaults.update(kwargs)
    return Scheduler(graph=graph_of(*loops), **defaults)


# ------------------------------------------------------------- what is due -----


def test_a_loop_with_no_history_is_due_immediately():
    s = scheduler_with(dept("marketing"))
    assert [l.id for l in s.due("c1", T0)] == ["marketing"]


def test_a_loop_is_not_due_again_before_its_cadence_elapses():
    s = scheduler_with(dept("marketing", cadence=DAY))
    s.register_handler("marketing", lambda c, n: "ok")
    s.run_loop("c1", "marketing", T0)
    almost = T0.replace(hour=23)
    assert s.due("c1", almost) == []


def test_a_loop_is_due_once_its_cadence_elapses():
    s = scheduler_with(dept("marketing", cadence=DAY))
    s.register_handler("marketing", lambda c, n: "ok")
    s.run_loop("c1", "marketing", T0)
    later = T0.replace(day=2)
    assert [l.id for l in s.due("c1", later)] == ["marketing"]


def test_most_overdue_loop_is_offered_first():
    s = scheduler_with(dept("fast", cadence=HOUR), dept("slow", cadence=DAY))
    s.register_handler("fast", lambda c, n: None)
    s.register_handler("slow", lambda c, n: None)
    s.run_loop("c1", "fast", T0)
    s.run_loop("c1", "slow", T0)
    # after 2 days: fast is 48x overdue, slow is 2x
    later = T0.replace(day=3)
    assert [l.id for l in s.due("c1", later)] == ["fast", "slow"]


def test_anchor_and_human_nodes_are_never_scheduled():
    g = graph_of(
        dept("marketing"),
        Loop("anchors", LoopKind.ANCHOR, cadence_seconds=DAY),
        Loop("human_review", LoopKind.HUMAN, cadence_seconds=DAY),
    )
    s = Scheduler(graph=g, clock=ManualClock(T0), respect_stagger=False)
    assert [l.id for l in s.schedulable()] == ["marketing"]


def test_a_loop_without_a_cadence_is_event_driven_not_scheduled():
    g = graph_of(Loop("on_demand", LoopKind.EXECUTION,
                      evaluation_signal="x", cadence_seconds=None))
    s = Scheduler(graph=g, clock=ManualClock(T0))
    assert s.schedulable() == []


def test_due_is_company_scoped():
    s = scheduler_with(dept("marketing"))
    s.register_handler("marketing", lambda c, n: None)
    s.run_loop("c1", "marketing", T0)
    assert s.due("c1", T0) == []
    assert [l.id for l in s.due("c2", T0)] == ["marketing"]


# ------------------------------------------------------------------ running -----


def test_running_a_loop_calls_its_handler_with_company_and_time():
    seen = {}
    s = scheduler_with(dept("marketing"))
    s.register_handler("marketing",
                       lambda c, n: seen.update(company=c, now=n) or "done")
    run = s.run_loop("c1", "marketing", T0)
    assert run.ok
    assert seen == {"company": "c1", "now": T0}
    assert run.result == "done"


def test_a_loop_with_no_handler_is_skipped_not_failed():
    s = scheduler_with(dept("marketing"))
    run = s.run_loop("c1", "marketing", T0)
    assert run.status is RunStatus.SKIPPED_NO_HANDLER
    assert not run.ok


def test_a_failing_handler_is_recorded_and_does_not_raise():
    def explode(company, now):
        raise ValueError("supplier feed unavailable")

    s = scheduler_with(dept("operations"))
    s.register_handler("operations", explode)
    run = s.run_loop("c1", "operations", T0)
    assert run.status is RunStatus.FAILED
    assert "supplier feed unavailable" in run.detail


def test_one_failing_loop_does_not_stop_the_others():
    """A department failing must not stop the company."""
    calls = []

    def explode(company, now):
        raise RuntimeError("boom")

    s = scheduler_with(dept("a"), dept("b"), dept("c"))
    s.register_handler("a", explode)
    s.register_handler("b", lambda c, n: calls.append("b"))
    s.register_handler("c", lambda c, n: calls.append("c"))
    runs = s.run_due("c1", T0)
    assert len(runs) == 3
    assert sorted(calls) == ["b", "c"]
    assert sum(1 for r in runs if r.status is RunStatus.FAILED) == 1


def test_a_failed_run_still_advances_the_cadence():
    """Otherwise a permanently failing loop would be retried every tick."""
    s = scheduler_with(dept("a", cadence=DAY))
    s.register_handler("a", lambda c, n: (_ for _ in ()).throw(RuntimeError("x")))
    s.run_loop("c1", "a", T0)
    assert s.due("c1", T0) == []


# ------------------------------------------------------------ single flight ----


def test_a_loop_already_in_flight_is_skipped():
    s = scheduler_with(dept("marketing"))
    s.register_handler("marketing", lambda c, n: None)
    S._write_state("c1", "marketing", in_flight=1)
    run = s.run_loop("c1", "marketing", T0)
    assert run.status is RunStatus.SKIPPED_IN_FLIGHT


def test_a_reentrant_handler_cannot_overlap_itself():
    """The guard has to hold while the handler is executing, not after."""
    observed = []
    s = scheduler_with(dept("marketing"))

    def reentrant(company, now):
        observed.append(s.run_loop(company, "marketing", now).status)
        return "outer"

    s.register_handler("marketing", reentrant)
    outer = s.run_loop("c1", "marketing", T0)
    assert outer.ok
    assert observed == [RunStatus.SKIPPED_IN_FLIGHT]


def test_in_flight_is_released_after_a_failure():
    s = scheduler_with(dept("a"))
    s.register_handler("a", lambda c, n: (_ for _ in ()).throw(RuntimeError("x")))
    s.run_loop("c1", "a", T0)
    assert S._read_state("c1", "a")["in_flight"] == 0


def test_clear_stale_flights_releases_a_crashed_loop():
    s = scheduler_with(dept("a"), dept("b"))
    S._write_state("c1", "a", in_flight=1)
    S._write_state("c1", "b", in_flight=1)
    assert s.clear_stale_flights("c1") == 2
    assert S._read_state("c1", "a")["in_flight"] == 0


# ------------------------------------------------------------------ throughput --


def test_max_per_tick_caps_admitted_work():
    """Local inference is the bottleneck, so a tick admits a bounded amount."""
    loops = [dept(f"d{i}") for i in range(8)]
    s = scheduler_with(*loops, max_per_tick=3)
    for loop in loops:
        s.register_handler(loop.id, lambda c, n: None)
    runs = s.run_due("c1", T0)
    assert len(runs) == 3


def test_remaining_loops_run_on_the_next_tick():
    loops = [dept(f"d{i}") for i in range(5)]
    s = scheduler_with(*loops, max_per_tick=2)
    for loop in loops:
        s.register_handler(loop.id, lambda c, n: None)
    total = 0
    for _ in range(3):
        total += len(s.run_due("c1", T0))
    assert total == 5


def test_stagger_offset_is_deterministic():
    a = stagger_offset("marketing", DAY)
    b = stagger_offset("marketing", DAY)
    assert a == b
    assert 0 <= a < DAY


def test_stagger_offsets_differ_between_loops():
    offsets = {stagger_offset(name, DAY)
               for name in ("strategy", "finance", "branding", "marketing",
                            "operations")}
    assert len(offsets) >= 4  # they spread rather than colliding


def test_stagger_offset_is_zero_without_a_cadence():
    assert stagger_offset("marketing", 0) == 0


def test_stagger_prevents_a_cold_start_stampede():
    """With stagger on, not every loop fires on the first tick."""
    loops = [dept(f"d{i}", cadence=DAY) for i in range(12)]
    s = Scheduler(graph=graph_of(*loops), clock=ManualClock(T0),
                  respect_stagger=True, max_per_tick=99)
    assert len(s.due("c1", T0)) < len(loops)


def test_stagger_delays_a_loop_but_never_starves_it():
    """Regression. Stagger used to be a gate compared against
    moment.timestamp() % cadence. A deployment ticking at a fixed time of day has
    a constant remainder, so any loop with a larger offset was never due -
    silently, forever. Two of five departments never ran.
    """
    names = ["strategy", "finance", "branding", "marketing", "operations"]
    loops = [dept(n, cadence=DAY) for n in names]
    s = Scheduler(graph=graph_of(*loops), clock=ManualClock(T0),
                  respect_stagger=True, max_per_tick=99)
    ran = set()
    for loop in loops:
        s.register_handler(loop.id, lambda c, n, _i=loop.id: ran.add(_i))

    clock = ManualClock(T0)
    for _ in range(4):                      # four days, ticking at a fixed hour
        s.run_due("c1", clock.now())
        clock.advance(days=1)

    assert ran == set(names), f"starved: {set(names) - ran}"


def test_every_loop_runs_within_two_cadences_under_stagger():
    loops = [dept(f"d{i}", cadence=DAY) for i in range(12)]
    s = Scheduler(graph=graph_of(*loops), clock=ManualClock(T0),
                  respect_stagger=True, max_per_tick=99)
    ran = set()
    for loop in loops:
        s.register_handler(loop.id, lambda c, n, _i=loop.id: ran.add(_i))
    clock = ManualClock(T0)
    for _ in range(3):
        s.run_due("c1", clock.now())
        clock.advance(days=1)
    assert ran == {l.id for l in loops}


# -------------------------------------------------------------- restart safety --


def test_last_run_survives_a_new_scheduler_instance():
    first = scheduler_with(dept("marketing", cadence=DAY))
    first.register_handler("marketing", lambda c, n: None)
    first.run_loop("c1", "marketing", T0)

    # a fresh process: new Scheduler over the same database
    second = scheduler_with(dept("marketing", cadence=DAY))
    second.register_handler("marketing", lambda c, n: None)
    assert second.due("c1", T0.replace(hour=6)) == []
    assert [l.id for l in second.due("c1", T0.replace(day=2))] == ["marketing"]


def test_run_count_accumulates_across_instances():
    for _ in range(3):
        s = scheduler_with(dept("a", cadence=1))
        s.register_handler("a", lambda c, n: None)
        s.run_loop("c1", "a", T0)
    assert S._read_state("c1", "a")["run_count"] == 3


# ------------------------------------------------------------------- history ----


def test_every_run_is_logged_including_skips():
    s = scheduler_with(dept("a"), dept("b"))
    s.register_handler("a", lambda c, n: "fine")
    s.run_loop("c1", "a", T0)
    s.run_loop("c1", "b", T0)   # no handler
    history = S.run_history("c1")
    statuses = {row["loop_id"]: row["status"] for row in history}
    assert statuses["a"] == str(RunStatus.COMPLETED)
    assert statuses["b"] == str(RunStatus.SKIPPED_NO_HANDLER)


def test_history_can_be_filtered_by_loop():
    s = scheduler_with(dept("a"), dept("b"))
    s.register_handler("a", lambda c, n: None)
    s.register_handler("b", lambda c, n: None)
    s.run_loop("c1", "a", T0)
    s.run_loop("c1", "b", T0)
    assert {r["loop_id"] for r in S.run_history("c1", "a")} == {"a"}


def test_handler_result_is_recorded():
    s = scheduler_with(dept("a"))
    s.register_handler("a", lambda c, n: {"findings": 2})
    s.run_loop("c1", "a", T0)
    assert '"findings": 2' in S.run_history("c1", "a")[0]["result_json"]


# ------------------------------------------------------------------- status -----


def test_status_reports_cadence_and_handler_presence():
    s = scheduler_with(dept("a"), dept("b"))
    s.register_handler("a", lambda c, n: None)
    rows = {row["loop_id"]: row for row in s.status("c1")}
    assert rows["a"]["has_handler"] is True
    assert rows["b"]["has_handler"] is False
    assert rows["a"]["run_count"] == 0
    assert rows["a"]["cadence_seconds"] == DAY


def test_status_reflects_a_completed_run():
    s = scheduler_with(dept("a"))
    s.register_handler("a", lambda c, n: None)
    s.run_loop("c1", "a", T0)
    row = s.status("c1")[0]
    assert row["run_count"] == 1
    assert row["last_status"] == str(RunStatus.COMPLETED)
    assert row["in_flight"] is False


def test_registering_a_handler_for_an_unknown_loop_is_refused():
    s = scheduler_with(dept("a"))
    with pytest.raises(ValueError):
        s.register_handler("ghost", lambda c, n: None)


# ------------------------------------------------ continuous operation over time --


def test_the_business_advances_over_a_simulated_month():
    """The milestone: nobody prompts anything and work still happens."""
    clock = ManualClock(T0)
    daily = [dept(name, cadence=DAY)
             for name in ("strategy", "finance", "marketing", "operations")]
    weekly = [Loop("reflection", LoopKind.LEARNING, cadence_seconds=7 * DAY,
                   evaluation_signal="lesson_quality")]
    s = Scheduler(graph=graph_of(*daily, *weekly), clock=clock,
                  respect_stagger=False, max_per_tick=99)

    executed: list[tuple[str, str]] = []
    for loop in daily + weekly:
        s.register_handler(
            loop.id,
            lambda c, n, _id=loop.id: executed.append((_id, n.date().isoformat())),
        )

    for _ in range(30):
        s.run_due("c1", clock.now())
        clock.advance(days=1)

    by_loop: dict[str, int] = {}
    for loop_id, _ in executed:
        by_loop[loop_id] = by_loop.get(loop_id, 0) + 1

    # daily loops ran roughly every day
    for name in ("strategy", "finance", "marketing", "operations"):
        assert by_loop[name] == 30
    # the weekly loop ran far less often, on its own cadence
    assert 4 <= by_loop["reflection"] <= 5
    # and every run is on the record
    assert len(S.run_history("c1", limit=1000)) == len(executed)


def test_a_restart_mid_month_does_not_fire_everything_at_once():
    clock = ManualClock(T0)
    loops = [dept(f"d{i}", cadence=DAY) for i in range(4)]
    first = Scheduler(graph=graph_of(*loops), clock=clock,
                      respect_stagger=False, max_per_tick=99)
    for loop in loops:
        first.register_handler(loop.id, lambda c, n: None)
    first.run_due("c1", clock.now())

    # "restart" six hours later
    resumed = Scheduler(graph=graph_of(*loops), clock=ManualClock(T0),
                        respect_stagger=False, max_per_tick=99)
    for loop in loops:
        resumed.register_handler(loop.id, lambda c, n: None)
    assert resumed.run_due("c1", T0.replace(hour=6)) == []


def test_run_forever_is_bounded_for_testability():
    s = scheduler_with(dept("a", cadence=DAY))
    s.register_handler("a", lambda c, n: None)
    passes = s.run_forever("c1", poll_seconds=0, max_passes=3)
    assert passes == 3
