"""Cadence scheduler — what makes the business run without being asked.

Design decision: the core is a **deterministic, clock-injected kernel**, not a
background thread.

    scheduler.run_due(company_id, now=<explicit timestamp>)

Time is a parameter. Nothing here sleeps, and no test waits. Two reasons, both
load-bearing:

* **Reproducibility.** The ablation planned for RQ4–RQ7 compares arms on paired
  seeds. If the schedule depended on wall-clock timing, two runs of the same seed
  would interleave differently and the comparison would be confounded by
  scheduling noise rather than by control topology.
* **Testability.** A scheduler that must be waited on cannot be tested at the
  scale the rest of the suite is, so it would end up thinly covered — which is
  exactly the wrong outcome for the component that decides what runs.

Real-time operation is a thin driver over this kernel (`run_forever`), not a
different implementation. The driver's only job is to decide what `now` is.

Restart safety
--------------
Last-run times are persisted. A company stopped mid-quarter and restarted resumes
its cadence instead of firing every loop at once, which would both distort the
schedule and burst the local inference budget.

Throughput
----------
Local inference bounds how much can run concurrently, so two mechanisms keep the
load flat: a per-loop **stagger offset** spreads same-cadence loops across the
window, and a **single-flight guard** prevents a slow loop from overlapping
itself. `max_per_tick` caps the work admitted in one pass.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Callable, Protocol

from app.db.sqlite import connection
from app.operating.loops import Loop, LoopGraph, LoopKind

# --------------------------------------------------------------------- schema --

SCHEDULER_SCHEMA = """
CREATE TABLE IF NOT EXISTS loop_state (
    company_id   TEXT NOT NULL,
    loop_id      TEXT NOT NULL,
    last_run_at  TEXT,
    last_status  TEXT,
    run_count    INTEGER NOT NULL DEFAULT 0,
    in_flight    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (company_id, loop_id)
);

CREATE TABLE IF NOT EXISTS loop_runs (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   TEXT NOT NULL,
    loop_id      TEXT NOT NULL,
    status       TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    duration_ms  INTEGER NOT NULL DEFAULT 0,
    detail       TEXT NOT NULL DEFAULT '',
    result_json  TEXT
);

CREATE INDEX IF NOT EXISTS idx_loop_runs_lookup
    ON loop_runs(company_id, loop_id, seq);
"""


def init_scheduler() -> None:
    """Idempotent."""
    with connection() as conn:
        conn.executescript(SCHEDULER_SCHEMA)


# --------------------------------------------------------------------- clocks --


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Wall clock. Used by the real-time driver only."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class ManualClock:
    """A clock the caller advances. Used by tests and by the ablation harness."""

    current: datetime

    def now(self) -> datetime:
        return self.current

    def advance(self, *, seconds: int = 0, days: int = 0) -> datetime:
        self.current = self.current + timedelta(seconds=seconds, days=days)
        return self.current


# --------------------------------------------------------------------- results --


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_IN_FLIGHT = "skipped_in_flight"
    SKIPPED_NO_HANDLER = "skipped_no_handler"


@dataclass(frozen=True, slots=True)
class LoopRun:
    """The outcome of one loop firing."""

    loop_id: str
    status: RunStatus
    at: str
    duration_ms: int = 0
    detail: str = ""
    result: object = None

    @property
    def ok(self) -> bool:
        return self.status is RunStatus.COMPLETED


#: A loop handler. Receives the company and the tick time; returns anything
#: JSON-serialisable for the run log, or None.
Handler = Callable[[str, datetime], object]


# ------------------------------------------------------------------ persistence --


def _read_state(company_id: str, loop_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM loop_state WHERE company_id = ? AND loop_id = ?",
            (company_id, loop_id),
        ).fetchone()
    return dict(row) if row else None


def _write_state(company_id: str, loop_id: str, **fields) -> None:
    allowed = {"last_run_at", "last_status", "run_count", "in_flight"}
    unknown = fields.keys() - allowed
    if unknown:
        raise ValueError(f"unknown loop_state column(s): {sorted(unknown)}")
    with connection() as conn:
        conn.execute(
            "INSERT INTO loop_state (company_id, loop_id) VALUES (?, ?) "
            "ON CONFLICT(company_id, loop_id) DO NOTHING",
            (company_id, loop_id),
        )
        assignments = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE loop_state SET {assignments} "  # noqa: S608 - keys whitelisted
            "WHERE company_id = ? AND loop_id = ?",
            (*fields.values(), company_id, loop_id),
        )


def _log_run(company_id: str, run: LoopRun) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO loop_runs (company_id, loop_id, status, started_at, "
            "duration_ms, detail, result_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                company_id, run.loop_id, str(run.status), run.at,
                run.duration_ms, run.detail,
                json.dumps(run.result, default=str) if run.result is not None
                else None,
            ),
        )


def run_history(company_id: str, loop_id: str | None = None,
                limit: int = 100) -> list[dict]:
    sql = "SELECT * FROM loop_runs WHERE company_id = ?"
    params: list[object] = [company_id]
    if loop_id:
        sql += " AND loop_id = ?"
        params.append(loop_id)
    sql += " ORDER BY seq DESC LIMIT ?"
    params.append(limit)
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- scheduler --


def stagger_offset(loop_id: str, cadence_seconds: int) -> int:
    """Deterministic offset spreading same-cadence loops across their window.

    Derived from the loop id rather than randomly, so the schedule is
    reproducible across processes and across runs of the ablation.
    """
    if cadence_seconds <= 0:
        return 0
    digest = 0
    for char in loop_id:
        digest = (digest * 131 + ord(char)) & 0xFFFFFFFF
    return digest % cadence_seconds


@dataclass
class Scheduler:
    """Drives the loops of one loop graph on their declared cadences."""

    graph: LoopGraph
    clock: Clock = field(default_factory=SystemClock)
    handlers: dict[str, Handler] = field(default_factory=dict)
    max_per_tick: int = 4
    respect_stagger: bool = True

    # ---------------------------------------------------------------- handlers

    def register_handler(self, loop_id: str, handler: Handler) -> None:
        if loop_id not in self.graph.loops:
            raise ValueError(
                f"cannot register a handler for unknown loop '{loop_id}'"
            )
        self.handlers[loop_id] = handler

    def schedulable(self) -> list[Loop]:
        """Loops with a cadence. Anchor and human nodes are not scheduled.

        An anchor is recomputed on read and a human acts when they choose;
        neither is something a timer drives.
        """
        return [
            loop for loop in self.graph.loops.values()
            if loop.cadence_seconds
            and loop.kind not in (LoopKind.ANCHOR, LoopKind.HUMAN)
        ]

    # ------------------------------------------------------------------- due?

    def due(self, company_id: str, now: datetime | None = None) -> list[Loop]:
        """Loops whose cadence has elapsed, soonest-overdue first."""
        moment = now or self.clock.now()
        overdue: list[tuple[float, Loop]] = []

        for loop in self.schedulable():
            state = _read_state(company_id, loop.id)
            cadence = loop.cadence_seconds or 0

            if state is None or not state.get("last_run_at"):
                # First sighting. Stagger is applied as a one-time phase shift,
                # not as a gate.
                #
                # An earlier version compared moment.timestamp() % cadence against
                # the offset and skipped when it was smaller. That is wrong: a
                # deployment ticking at a fixed time of day has a constant
                # remainder, so any loop with a larger offset was never due -
                # silently, forever. Two of five departments never ran.
                #
                # Instead the loop is given a synthetic last-run time placing its
                # first run `offset` seconds out. It is skipped now and becomes
                # due later, which spreads the cold start without ever excluding
                # anything.
                if self.respect_stagger:
                    offset = stagger_offset(loop.id, cadence)
                    if offset > 0:
                        synthetic = moment - timedelta(seconds=cadence - offset)
                        _write_state(company_id, loop.id,
                                     last_run_at=synthetic.isoformat())
                        continue
                overdue.append((float("inf"), loop))
                continue

            last = datetime.fromisoformat(state["last_run_at"])
            elapsed = (moment - last).total_seconds()
            if elapsed >= cadence:
                overdue.append((elapsed / cadence, loop))

        overdue.sort(key=lambda pair: -pair[0])
        return [loop for _, loop in overdue]

    # ------------------------------------------------------------------- tick

    def run_due(self, company_id: str,
                now: datetime | None = None) -> list[LoopRun]:
        """One pass. Runs at most `max_per_tick` due loops and returns outcomes."""
        moment = now or self.clock.now()
        runs: list[LoopRun] = []
        for loop in self.due(company_id, moment)[: self.max_per_tick]:
            runs.append(self.run_loop(company_id, loop.id, moment))
        return runs

    def run_loop(self, company_id: str, loop_id: str,
                 now: datetime | None = None) -> LoopRun:
        """Fire one loop, guarded and logged. Never raises.

        A handler that raises is recorded as FAILED and the tick continues. One
        department's failure must not stop the company.
        """
        moment = now or self.clock.now()
        stamp = moment.isoformat()
        state = _read_state(company_id, loop_id)

        if state and state.get("in_flight"):
            run = LoopRun(loop_id, RunStatus.SKIPPED_IN_FLIGHT, stamp,
                          detail="a previous run of this loop has not finished")
            _log_run(company_id, run)
            return run

        handler = self.handlers.get(loop_id)
        if handler is None:
            run = LoopRun(loop_id, RunStatus.SKIPPED_NO_HANDLER, stamp,
                          detail="no handler registered")
            _log_run(company_id, run)
            return run

        _write_state(company_id, loop_id, in_flight=1)
        started = datetime.now(UTC)
        try:
            result = handler(company_id, moment)
            status = RunStatus.COMPLETED
            detail = ""
        except Exception as exc:  # noqa: BLE001 - deliberate: isolate failures
            result = None
            status = RunStatus.FAILED
            detail = f"{type(exc).__name__}: {exc}"
            traceback.clear_frames(exc.__traceback__) if exc.__traceback__ else None
        finally:
            duration_ms = int(
                (datetime.now(UTC) - started).total_seconds() * 1000
            )
            _write_state(
                company_id, loop_id,
                in_flight=0,
                last_run_at=stamp,
                last_status=str(status),
                run_count=(state or {}).get("run_count", 0) + 1,
            )

        run = LoopRun(loop_id, status, stamp, duration_ms=duration_ms,
                      detail=detail, result=result)
        _log_run(company_id, run)
        return run

    # ------------------------------------------------------------- inspection

    def status(self, company_id: str) -> list[dict]:
        """Per-loop cadence state, for the activity view and for health."""
        out = []
        for loop in self.schedulable():
            state = _read_state(company_id, loop.id) or {}
            out.append({
                "loop_id": loop.id,
                "kind": str(loop.kind),
                "cadence_seconds": loop.cadence_seconds,
                "stagger_offset": stagger_offset(loop.id,
                                                 loop.cadence_seconds or 0),
                "last_run_at": state.get("last_run_at"),
                "last_status": state.get("last_status"),
                "run_count": state.get("run_count", 0),
                "in_flight": bool(state.get("in_flight")),
                "has_handler": loop.id in self.handlers,
            })
        return out

    def clear_stale_flights(self, company_id: str) -> int:
        """Release in-flight flags left set by a process that died mid-run.

        Without this a crash would silently retire a loop forever, which is the
        worst kind of failure: the business keeps running and quietly stops
        doing one thing.
        """
        with connection() as conn:
            cursor = conn.execute(
                "UPDATE loop_state SET in_flight = 0 "
                "WHERE company_id = ? AND in_flight = 1",
                (company_id,),
            )
        return cursor.rowcount

    # -------------------------------------------------------- real-time driver

    def run_forever(self, company_id: str, *, poll_seconds: int = 60,
                    max_passes: int | None = None) -> int:
        """Thin real-time driver over the deterministic kernel.

        Its only responsibility is deciding what `now` is; all the logic lives in
        `run_due`. `max_passes` bounds it so the same code path is exercisable in
        a test without waiting.
        """
        import time

        self.clear_stale_flights(company_id)
        passes = 0
        while max_passes is None or passes < max_passes:
            self.run_due(company_id)
            passes += 1
            if max_passes is not None and passes >= max_passes:
                break
            time.sleep(poll_seconds)
        return passes
