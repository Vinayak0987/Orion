# Tests for department operating loops.
#
# The important assertions: a gated task appends nothing, a reflective lesson
# changes what gets proposed, and a full month of ticks advances the business
# without anyone prompting it.
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.generation.operating import departments as D
from app.generation.operating import governance as G
from app.generation.operating import ledger, memory as M
from app.generation.operating.anchors import AnchorSet
from app.generation.operating.constitution import ActionKind, ConstitutionContext
from app.generation.operating.ledger import EntryKind, LedgerEntry
from app.generation.operating.loops import default_graph
from app.generation.operating.memory import Memory, MemoryType
from app.generation.operating.scheduler import ManualClock, RunStatus, Scheduler
from app.generation.operating import scheduler as S

T0 = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
DAY = 86_400


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module
    f = tmp_path / "departments-test.db"
    monkeypatch.setattr(sqlite_module.settings.__class__, "sqlite_file",
                        property(lambda _self: f))
    ledger.init_ledger(); G.init_governance(); S.init_scheduler(); M.init_memory()
    yield


def seed(revenue=4_000_00, cogs=1_600_00, cash=15_00_000_00):
    if cash:
        ledger.append(LedgerEntry(company_id="c1", kind=EntryKind.CASH_IN,
                                  department="finance", actor="funding",
                                  amount_minor=cash, occurred_at=T0.isoformat()))
    if revenue:
        ledger.append(LedgerEntry(company_id="c1", kind=EntryKind.REVENUE,
                                  department="finance", actor="pl",
                                  amount_minor=revenue, occurred_at=T0.isoformat()))
    if cogs:
        ledger.append(LedgerEntry(company_id="c1", kind=EntryKind.COGS,
                                  department="operations", actor="supply",
                                  amount_minor=cogs, occurred_at=T0.isoformat()))


# ------------------------------------------------------------- profiles -------

def test_all_five_implemented_departments_have_profiles():
    assert set(D.PROFILES) == {"strategy", "finance", "branding", "marketing",
                               "operations"}


def test_every_profile_names_both_a_proxy_and_an_anchor():
    # Naming both is what makes proxy capture detectable.
    from app.generation.operating.anchors import ANCHOR_NAMES
    for name, prof in D.PROFILES.items():
        assert prof.proxy_metric
        assert prof.serves_anchor in ANCHOR_NAMES, name


def test_unknown_department_is_rejected():
    with pytest.raises(ValueError):
        D.run_tick("c1", "legal", T0)


# ------------------------------------------------------------- planning -------

def test_healthy_marketing_proposes_acquisition_spend():
    seed()
    tasks = D.rule_based_planner(D.PROFILES["marketing"],
                                 AnchorSet.compute("c1"), [], T0)
    assert len(tasks) == 1
    assert tasks[0].action_kind is ActionKind.SPEND
    assert "acquisition" in tasks[0].description


def test_a_reflective_lesson_suppresses_the_spend_task():
    # The one branch where memory changes behaviour. This is what makes
    # "the department learned something" checkable.
    seed()
    lesson = {"memory_type": str(MemoryType.REFLECTIVE),
              "content": "net margin fell over the period; volume gained without margin is not progress"}
    tasks = D.rule_based_planner(D.PROFILES["marketing"],
                                 AnchorSet.compute("c1"), [lesson], T0)
    assert tasks[0].action_kind is ActionKind.UPDATE_PLAYBOOK
    assert "retention" in tasks[0].description
    assert tasks[0].amount_minor == 0


def test_an_episodic_memory_does_not_suppress_spend():
    # Only a reflective lesson carries that weight; an anecdote does not.
    seed()
    anecdote = {"memory_type": str(MemoryType.EPISODIC),
                "content": "net margin fell last time we discounted"}
    tasks = D.rule_based_planner(D.PROFILES["marketing"],
                                 AnchorSet.compute("c1"), [anecdote], T0)
    assert tasks[0].action_kind is ActionKind.SPEND


def test_unhealthy_anchor_triggers_corrective_work():
    seed(revenue=1_000_00, cogs=990_00)  # margin near zero
    anchors = AnchorSet.compute("c1")
    assert anchors.value("net_margin_pct") < 10.0
    tasks = D.rule_based_planner(D.PROFILES["marketing"], anchors, [], T0)
    assert tasks[0].action_kind is ActionKind.UPDATE_PLAYBOOK


def test_every_department_plans_at_least_one_task():
    seed()
    anchors = AnchorSet.compute("c1")
    for name, prof in D.PROFILES.items():
        assert D.rule_based_planner(prof, anchors, [], T0), name


def test_declared_effects_are_present_on_every_task():
    seed()
    anchors = AnchorSet.compute("c1")
    for prof in D.PROFILES.values():
        for task in D.rule_based_planner(prof, anchors, [], T0):
            assert task.effects


# ------------------------------------------------------------ the tick --------

def test_a_tick_executes_and_appends_the_declared_effects():
    seed()
    before = ledger.entry_count("c1")
    result = D.run_tick("c1", "marketing", T0)
    assert result.executed == 1
    assert result.blocked == 0
    assert result.ledger_entries == 3
    assert ledger.entry_count("c1") == before + 3


def test_a_tick_writes_episodic_memory_for_executed_work_only():
    seed()
    D.run_tick("c1", "marketing", T0)
    assert M.stats("c1")["marketing"][str(MemoryType.EPISODIC)] == 1


def test_a_tick_reads_anchors_and_its_own_memory():
    seed()
    M.write(Memory(company_id="c1", department="marketing",
                   memory_type=MemoryType.EPISODIC,
                   content="acquire customers who stay via referral",
                   created_at=T0.isoformat()))
    result = D.run_tick("c1", "marketing", T0)
    assert result.anchors_read > 0
    assert result.memories_retrieved >= 1


def test_a_tick_cannot_see_another_departments_memory():
    seed()
    M.write(Memory(company_id="c1", department="finance",
                   memory_type=MemoryType.REFLECTIVE,
                   content="net margin fell; stop discounting",
                   created_at=T0.isoformat()))
    # finance's lesson must not reach marketing's planner
    result = D.run_tick("c1", "marketing", T0)
    assert result.executed == 1
    assert result.ledger_entries == 3  # the spend task ran, not the retention task


def test_a_task_over_the_review_threshold_is_queued_and_appends_nothing():
    seed()
    big = D.Task(task_id="marketing-big", department="marketing",
                 description="very large campaign",
                 action_kind=ActionKind.SPEND, amount_minor=9_000_00,
                 effects=((EntryKind.MARKETING_SPEND, 9_000_00, 0),))
    before = ledger.entry_count("c1")
    result = D.run_tick("c1", "marketing", T0,
                        planner=lambda *a, **k: [big])
    assert result.awaiting_review == 1
    assert result.executed == 0
    assert result.ledger_entries == 0
    assert ledger.entry_count("c1") == before
    assert [r["id"] for r in G.review_queue("c1")] == ["marketing-big"]


def test_a_constitution_violation_is_counted_blocked_and_appends_nothing():
    seed()
    forbidden = D.Task(task_id="marketing-delete", department="marketing",
                       description="purge lapsed customer records",
                       action_kind=ActionKind.DELETE_CUSTOMER_DATA,
                       effects=((EntryKind.TASK_COMPLETED, 0, 1),))
    before = ledger.entry_count("c1")
    result = D.run_tick("c1", "marketing", T0,
                        planner=lambda *a, **k: [forbidden])
    assert result.blocked + result.awaiting_review == 1
    assert result.executed == 0
    assert ledger.entry_count("c1") == before


def test_a_governance_refusal_does_not_raise():
    seed()
    forbidden = D.Task(task_id="m-del", department="marketing", description="purge",
                       action_kind=ActionKind.DELETE_CUSTOMER_DATA)
    result = D.run_tick("c1", "marketing", T0, planner=lambda *a, **k: [forbidden])
    assert isinstance(result, D.TickResult)  # returned, not raised


def test_spend_beyond_the_daily_cap_is_blocked():
    seed()
    tight = ConstitutionContext(daily_spend_cap_minor=1_00_00,
                                spent_today_minor=0)
    result = D.run_tick("c1", "marketing", T0, context=tight)
    assert result.executed == 0
    assert result.blocked == 1


def test_result_serialises_for_the_run_log():
    seed()
    payload = D.run_tick("c1", "finance", T0).as_dict()
    assert payload["department"] == "finance"
    assert set(payload) >= {"executed", "blocked", "awaiting_review",
                            "ledger_entries", "memories_written"}


# ----------------------------------------------------- scheduler wiring -------

def test_register_all_wires_the_five_departments():
    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0))
    wired = D.register_all(sched)
    assert set(wired) == set(D.PROFILES)
    for name in D.PROFILES:
        assert name in sched.handlers


def test_register_all_skips_departments_absent_from_the_graph():
    from app.generation.operating.loops import Loop, LoopGraph, LoopKind
    g = LoopGraph(validate_on_register=False)
    g.loops["marketing"] = Loop("marketing", LoopKind.EXECUTION,
                                evaluation_signal="m", cadence_seconds=DAY)
    sched = Scheduler(graph=g, clock=ManualClock(T0))
    assert D.register_all(sched) == ["marketing"]


def test_a_scheduled_tick_runs_the_department():
    seed()
    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0),
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched)
    runs = sched.run_due("c1", T0)
    assert runs
    completed = [r for r in runs if r.status is RunStatus.COMPLETED]
    assert {r.result["department"] for r in completed} == set(D.PROFILES)
    # The monitor and reflection loops are scheduled but have no handler yet, so
    # they are skipped rather than failed. That distinction matters: a missing
    # handler must never look like a crash.
    unwired = [r for r in runs if r.status is RunStatus.SKIPPED_NO_HANDLER]
    assert {r.loop_id for r in unwired} == {
        "goodhart_detector", "conflict_detector", "drift_monitor",
        "objective_review", "reflection"}
    assert not [r for r in runs if r.status is RunStatus.FAILED]


# --------------------------------------------- the autonomy milestone ---------

def test_the_business_advances_over_a_month_with_nobody_prompting_it():
    seed()
    clock = ManualClock(T0)
    sched = Scheduler(graph=default_graph(), clock=clock,
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched)

    opening_entries = ledger.entry_count("c1")
    for _ in range(30):
        sched.run_due("c1", clock.now())
        clock.advance(days=1)

    closing = AnchorSet.compute("c1")
    assert ledger.entry_count("c1") > opening_entries
    # work was actually done and recorded
    assert closing.value("tasks_completed") is not None
    assert closing.value("tasks_completed") >= 30
    # every department left a trace in its own memory
    stats = M.stats("c1")
    for name in D.PROFILES:
        assert name in stats, name
    # and every run is on the record
    assert len(S.run_history("c1", limit=1000)) >= 30


def test_one_failing_department_does_not_stop_the_others():
    seed()
    def explode(profile, anchors, memories, tick):
        if profile.name == "operations":
            raise RuntimeError("supplier feed unavailable")
        return D.rule_based_planner(profile, anchors, memories, tick)

    sched = Scheduler(graph=default_graph(), clock=ManualClock(T0),
                      respect_stagger=False, max_per_tick=99)
    D.register_all(sched, planner=explode)
    runs = sched.run_due("c1", T0)
    failed = [r for r in runs if r.status is RunStatus.FAILED]
    completed = [r for r in runs if r.status is RunStatus.COMPLETED]
    assert len(failed) == 1
    assert len(completed) == 4


def test_learning_changes_behaviour_across_ticks():
    # A department that records a margin lesson stops proposing discount spend.
    seed()
    first = D.run_tick("c1", "marketing", T0)
    assert first.executed == 1

    M.write(Memory(company_id="c1", department="marketing",
                   memory_type=MemoryType.REFLECTIVE,
                   content="net margin fell over the period; volume gained without margin is not progress",
                   confidence=0.7, created_at=T0.isoformat()))

    later = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)
    second = D.run_tick("c1", "marketing", later)
    assert second.executed == 1
    # the retention task declares one effect, the acquisition task declares three
    assert second.ledger_entries == 1


# ------------------------------------------- the learning path, end to end ----
#
# The test above passes even with its memory write deleted: the first tick's own
# spend drives net margin to -40%, `_anchor_unhealthy` latches, and the retention
# task is proposed for that reason alone. It therefore did not evidence that
# memory changes behaviour.
#
# The three tests below isolate the memory effect from the anchor-health effect by
# keeping the anchor HEALTHY throughout, so the only thing that can change the
# plan is the retrieved lesson. They fail if the retrieval query stops overlapping
# the vocabulary reflection actually writes.

#: The exact string reflection.derive_lessons emits for a net-margin decline.
#: Hard-coded here on purpose: if the template changes and this is not updated,
#: these tests fail, which is the alarm we want.
REAL_MARGIN_LESSON = (
    "net margin fell over the period; volume gained without margin is not "
    "progress (net_margin_pct -16.7)"
)


def _seed_comfortable(cid: str) -> None:
    """A book big enough that one campaign cannot make the margin unhealthy."""
    for kind, amt, dept in ((EntryKind.CASH_IN, 20_00_000_00, "finance"),
                            (EntryKind.REVENUE, 10_00_000_00, "finance"),
                            (EntryKind.COGS, 3_00_000_00, "operations")):
        ledger.append(LedgerEntry(company_id=cid, kind=kind, department=dept,
                                  actor="seed", amount_minor=amt,
                                  occurred_at=T0.isoformat()))


def test_healthy_anchor_alone_does_not_suppress_spend():
    # The control. Establishes that the anchor-health branch is NOT firing, so
    # the next test's result is attributable to memory and nothing else.
    _seed_comfortable("healthy-control")
    anchors = AnchorSet.compute("healthy-control")
    assert not D._anchor_unhealthy(D.PROFILES["marketing"], anchors)
    result = D.run_tick("healthy-control", "marketing", T0)
    assert result.ledger_entries == 3  # the acquisition task, with its 3 effects


def test_a_real_reflection_lesson_is_retrievable_by_the_planner():
    # The defect this pins: reflection writes in anchor vocabulary, and the
    # planner's retrieval query must overlap it or the lesson is dropped by
    # `_score` before the planner ever sees it.
    _seed_comfortable("retrievable")
    M.write(Memory(company_id="retrievable", department="marketing",
                   memory_type=MemoryType.REFLECTIVE,
                   content=REAL_MARGIN_LESSON,
                   confidence=0.7, created_at=T0.isoformat()))

    profile = D.PROFILES["marketing"]
    # The PRODUCTION query, not one this test invents. If run_tick's query stops
    # overlapping reflection's vocabulary, this fails.
    query = D.retrieval_query(profile)
    got = M.retrieve("retrievable", "marketing", query, limit=5, now=T0,
                     record_retrieval=False)
    assert any(REAL_MARGIN_LESSON in (m["content"] or "") for m in got), (
        "reflection's own lesson was not retrievable by the planner's query; "
        "the learning path is broken even though the branch is unit-tested"
    )
    assert D._warned_against_spend(got)


def test_memory_alone_changes_the_plan_while_the_anchor_stays_healthy():
    # The discriminating assertion. Same seed, same anchor state, same planner.
    # The ONLY difference between the two companies is the reflective lesson.
    for cid, write_lesson in (("mem-yes", True), ("mem-no", False)):
        _seed_comfortable(cid)
        if write_lesson:
            M.write(Memory(company_id=cid, department="marketing",
                           memory_type=MemoryType.REFLECTIVE,
                           content=REAL_MARGIN_LESSON,
                           confidence=0.7, created_at=T0.isoformat()))

    anchors_yes = AnchorSet.compute("mem-yes")
    anchors_no = AnchorSet.compute("mem-no")
    assert not D._anchor_unhealthy(D.PROFILES["marketing"], anchors_yes)
    assert not D._anchor_unhealthy(D.PROFILES["marketing"], anchors_no)

    with_lesson = D.run_tick("mem-yes", "marketing", T0)
    without_lesson = D.run_tick("mem-no", "marketing", T0)

    # retention task declares 1 effect; acquisition declares 3
    assert with_lesson.ledger_entries == 1, (
        "the lesson did not suppress the spend task; memory is not reaching "
        "the planner"
    )
    assert without_lesson.ledger_entries == 3
    assert with_lesson.ledger_entries != without_lesson.ledger_entries
