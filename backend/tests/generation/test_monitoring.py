# Tests for monitor loop wiring.
#
# The headline test is test_a_captured_proxy_is_detected_by_the_scheduled_monitor:
# the whole system running unattended, catching a department that improved its
# proxy while the anchor it serves fell.
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.generation.operating import departments as D
from app.generation.operating import governance as G
from app.generation.operating import ledger, memory as M, monitors as mon
from app.generation.operating import monitoring as MO
from app.generation.operating import scheduler as S
from app.generation.operating.anchors import AnchorSet
from app.generation.operating.ledger import EntryKind, LedgerEntry
from app.generation.operating.loops import default_graph
from app.generation.operating.memory import MemoryType
from app.generation.operating.scheduler import ManualClock, RunStatus, Scheduler

T0 = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module
    f = tmp_path / "monitoring-test.db"
    monkeypatch.setattr(sqlite_module.settings.__class__, "sqlite_file",
                        property(lambda _self: f))
    ledger.init_ledger(); G.init_governance(); S.init_scheduler()
    M.init_memory(); MO.init_monitoring()
    yield


def rec(kind, amount=0, quantity=0, department="finance", when=None):
    ledger.append(LedgerEntry(
        company_id="c1", kind=kind, department=department, actor="x",
        amount_minor=amount, quantity=quantity,
        occurred_at=(when or T0).isoformat()))


# ------------------------------------------------- snapshots without storing ---

def test_anchors_are_recomputed_from_a_sequence_number_not_stored():
    rec(EntryKind.REVENUE, 1_000_00)
    rec(EntryKind.COGS, 400_00)
    early = MO._max_seq("c1")
    rec(EntryKind.COGS, 500_00)

    at_early = MO.anchors_at("c1", early)
    at_now = AnchorSet.compute("c1")
    assert at_early.value("gross_margin_pct") == 60.0
    assert at_now.value("gross_margin_pct") == 10.0


def test_no_anchor_values_are_persisted_anywhere():
    # The invariant: a stored anchor could drift from the ledger.
    rec(EntryKind.REVENUE, 1_000_00)
    from app.generation.db.sqlite import connection
    with connection() as conn:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert not any("anchor" in t.lower() for t in tables)
    with connection() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(period_marks)")}
    assert cols == {"company_id", "loop_id", "last_seq", "marked_at"}


def test_first_monitor_run_records_a_baseline_and_reports_no_findings():
    rec(EntryKind.REVENUE, 1_000_00)
    out = MO.goodhart_handler("c1", T0)
    assert out["findings"] == 0
    assert "baseline" in out["note"]


def test_a_period_with_no_new_entries_produces_nothing():
    rec(EntryKind.REVENUE, 1_000_00)
    MO.goodhart_handler("c1", T0)
    out = MO.goodhart_handler("c1", T0)
    assert out["findings"] == 0


# ------------------------------------------------------- goodhart detection ---

def test_a_captured_proxy_is_detected_by_the_scheduled_monitor():
    # Marketing completes work and acquires customers, but margin collapses.
    rec(EntryKind.REVENUE, 4_000_00)
    rec(EntryKind.COGS, 1_000_00)
    MO.goodhart_handler("c1", T0)          # baseline

    day2 = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    rec(EntryKind.REVENUE, 2_000_00, department="finance", when=day2)
    rec(EntryKind.COGS, 3_500_00, department="operations", when=day2)
    for _ in range(40):
        rec(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
            when=day2)

    out = MO.goodhart_handler("c1", day2)
    assert out["findings"] >= 1
    assert out["escalated"] >= 1

    rows = MO.open_findings("c1")
    assert rows[0]["severity"] == "critical"
    assert rows[0]["kind"] == "proxy_divergence"
    assert rows[0]["department"] == "marketing"
    assert rows[0]["anchor_delta"] < 0


def test_a_healthy_period_produces_no_findings():
    rec(EntryKind.REVENUE, 4_000_00)
    rec(EntryKind.COGS, 2_000_00)
    MO.goodhart_handler("c1", T0)
    day2 = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    rec(EntryKind.REVENUE, 4_000_00, when=day2)
    rec(EntryKind.COGS, 500_00, when=day2)
    for _ in range(20):
        rec(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
            when=day2)
    out = MO.goodhart_handler("c1", day2)
    assert out["findings"] == 0


def test_every_recorded_finding_cites_an_anchor():
    rec(EntryKind.REVENUE, 4_000_00)
    rec(EntryKind.COGS, 1_000_00)
    MO.goodhart_handler("c1", T0)
    day2 = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    rec(EntryKind.COGS, 3_500_00, when=day2)
    for _ in range(40):
        rec(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
            when=day2)
    MO.goodhart_handler("c1", day2)
    for row in MO.open_findings("c1"):
        assert row["anchor"]
        assert row["anchor_delta"] != 0


# ------------------------------------------------------------ other monitors --

def test_drift_monitor_flags_a_stale_threshold():
    rec(EntryKind.REVENUE, 1_000_00)
    rec(EntryKind.COGS, 400_00)
    th = mon.Threshold("sector_margin", "gross_margin_pct", 62.0,
                       calibrated_at=mon.stale_after(400, now=T0.isoformat()),
                       max_age_days=90)
    out = MO.drift_handler([th])("c1", T0)
    assert out["findings"] == 1


def test_drift_monitor_says_so_when_nothing_is_registered():
    out = MO.drift_handler(None)("c1", T0)
    assert out["findings"] == 0
    assert "no calibrated thresholds" in out["note"]


def test_objective_review_questions_a_stale_objective():
    rec(EntryKind.REVENUE, 1_000_00)
    rec(EntryKind.COGS, 300_00)
    obj = mon.Objective("o1", "marketing", "increase footfall",
                        "gross_margin_pct",
                        in_force_since=mon.stale_after(120, now=T0.isoformat()),
                        review_after_days=30)
    handler = MO.objective_review_handler([obj])
    handler("c1", T0)  # baseline
    day2 = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    rec(EntryKind.COGS, 600_00, when=day2)
    out = handler("c1", day2)
    assert out["findings"] == 1


def test_reflection_handler_reflects_for_every_department():
    rec(EntryKind.REVENUE, 1_000_00)
    rec(EntryKind.COGS, 300_00)
    handler = MO.reflection_handler()
    handler("c1", T0)  # baseline
    day2 = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    rec(EntryKind.COGS, 800_00, when=day2)
    out = handler("c1", day2)
    assert out["reflections"] == 5
    assert set(out["verdicts"]) == set(D.PROFILES)
    assert out["verdicts"]["marketing"] == "declined"


# ------------------------------------------------------------- full wiring ----

def test_register_all_wires_every_monitor_and_reflection():
    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0))
    wired = MO.register_all(sched)
    assert set(wired) == {"goodhart_detector", "conflict_detector",
                          "drift_monitor", "objective_review", "reflection"}


def test_no_loop_in_the_default_graph_is_left_without_a_handler():
    # The gap the department tests exposed is now closed.
    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0),
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched)
    MO.register_all(sched)
    missing = [l.id for l in sched.schedulable() if l.id not in sched.handlers]
    assert missing == []


def test_a_full_unattended_run_completes_every_loop():
    rec(EntryKind.CASH_IN, 15_00_000_00)
    rec(EntryKind.REVENUE, 4_000_00)
    rec(EntryKind.COGS, 1_600_00)
    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0),
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched)
    MO.register_all(sched)
    runs = sched.run_due("c1", T0)
    assert not [r for r in runs if r.status is RunStatus.SKIPPED_NO_HANDLER]
    assert not [r for r in runs if r.status is RunStatus.FAILED]
    assert len([r for r in runs if r.status is RunStatus.COMPLETED]) == 10


def test_a_simulated_quarter_runs_unattended_and_produces_findings():
    rec(EntryKind.CASH_IN, 50_00_000_00)
    rec(EntryKind.REVENUE, 4_000_00)
    rec(EntryKind.COGS, 1_600_00)

    clock = ManualClock(T0)
    sched = Scheduler(graph=default_graph(), clock=clock,
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched)
    MO.register_all(sched)

    for _ in range(45):
        sched.run_due("c1", clock.now())
        clock.advance(days=1)

    # the company kept operating
    assert ledger.entry_count("c1") > 100
    closing = AnchorSet.compute("c1")
    assert closing.value("tasks_completed") >= 45
    # every department has memory, including reflective lessons
    stats = M.stats("c1")
    assert set(stats) >= set(D.PROFILES)
    reflective = sum(v.get(str(MemoryType.REFLECTIVE), 0) for v in stats.values())
    assert reflective >= 1
    # every scheduled run is on the record
    # Monitors run on weekly and monthly cadences, so the total is well
    # below 45 x 10: that spread is the throughput guard working.
    history = S.run_history("c1", limit=5000)
    assert len(history) >= 45 * 5          # five departments, daily
    assert len(history) < 45 * 10          # monitors are not daily
