"""Orion operating layer.

The generation layer (app.generation.agents, app.generation.orchestrator) produces a company's opening
state. This package operates that state onward.

    ledger        append-only record of what happened; the only writable substrate
    anchors       metrics derived from the ledger; readable everywhere, writable nowhere
    constitution  hard constraints enforced in the call path, not in prompts
    governance    the gate chain and the append-only audit trail
    loops         loop registry and the two topology invariants
    monitors      the four loops that check the work
    scheduler     clock-injected cadence kernel; what makes the business continue
    memory        one isolated store per department, four typed
    reflection    learning grounded in measured anchor deltas, not self-report
    departments   the five department loops the scheduler drives
    monitoring    wires the four monitors and reflection into the scheduler

Design rule for anything added here: if a number is used to judge a department's
performance, it must be computed from the ledger by code. A department may append
events. It may not report its own score.

The two principles this package generalises were both established empirically by
the generation layer and are recorded in PAPER.md §4.4 and §7.2:

    derived figures override asserted ones
    cross-agent constraints hold only when enforced in code
"""

from app.generation.operating import (
    anchors,
    constitution,
    departments,
    governance,
    ledger,
    loops,
    memory,
    monitoring,
    monitors,
    reflection,
    scheduler,
)

__all__ = [
    "ledger",
    "anchors",
    "constitution",
    "governance",
    "loops",
    "monitors",
    "scheduler",
    "memory",
    "reflection",
    "departments",
    "monitoring",
]


def init_all() -> None:
    """Create every operating-layer table. Idempotent.

    Call alongside app.generation.db.sqlite.init_db() on startup.
    """
    ledger.init_ledger()
    governance.init_governance()
    scheduler.init_scheduler()
    memory.init_memory()
    monitoring.init_monitoring()


def build_scheduler(clock=None, *, thresholds=None, objectives=None):
    # A fully wired scheduler: five department loops, four monitors, reflection.
    #
    # This is the assembled operating layer. After calling init_all() and this,
    # scheduler.run_due(company_id) advances the business with nothing else
    # prompting it.
    from app.generation.operating.loops import default_graph
    from app.generation.operating.scheduler import Scheduler, SystemClock

    # max_per_tick defaults to the number of schedulable loops because the
    # rule-based planners perform no inference. Lower it when LLM-backed planning
    # is wired, since the throughput guard exists for that case.
    graph = default_graph()
    sched = Scheduler(graph=graph, clock=clock or SystemClock(),
                      max_per_tick=len(graph.loops))
    departments.register_all(sched)
    monitoring.register_all(sched, thresholds=thresholds, objectives=objectives)
    return sched
