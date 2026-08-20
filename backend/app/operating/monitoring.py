# Monitor loop wiring - gives the four monitors and reflection a scheduler handler.
#
# A monitor compares one period against the previous one, so it needs a baseline.
# Anchors are never stored (see anchors.py), so a "snapshot" here records only the
# ledger sequence number the period ended at. The anchor set is recomputed from
# the ledger up to that point whenever it is needed.
#
# That indirection is deliberate. Storing the anchor values would create exactly
# the writable copy the invariant exists to prevent: a stored number can drift
# from the ledger, and once it can drift it can be wrong in a direction someone
# prefers. A sequence number cannot.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db.sqlite import connection
from app.operating import ledger as ledger_module
from app.operating import memory as memory_module
from app.operating import monitors as mon
from app.operating import reflection as refl
from app.operating.anchors import AnchorSet
from app.operating.departments import PROFILES
from app.operating.ledger import EntryKind
from app.operating.memory import MemoryType

SNAPSHOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS period_marks (
    company_id TEXT NOT NULL,
    loop_id    TEXT NOT NULL,
    last_seq   INTEGER NOT NULL,
    marked_at  TEXT NOT NULL,
    PRIMARY KEY (company_id, loop_id)
);

CREATE TABLE IF NOT EXISTS findings (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  TEXT NOT NULL,
    loop_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    severity    TEXT NOT NULL,
    department  TEXT NOT NULL,
    anchor      TEXT NOT NULL,
    anchor_delta REAL NOT NULL,
    message     TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    escalated   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_findings_lookup
    ON findings(company_id, severity, seq);
"""


def init_monitoring() -> None:
    with connection() as conn:
        conn.executescript(SNAPSHOT_SCHEMA)


def _max_seq(company_id: str) -> int:
    with connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS s FROM ledger WHERE company_id = ?",
            (company_id,)).fetchone()
    return int(row["s"])


def _mark(company_id: str, loop_id: str, seq: int, at: str) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO period_marks (company_id, loop_id, last_seq, marked_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(company_id, loop_id) DO UPDATE SET "
            "last_seq = excluded.last_seq, marked_at = excluded.marked_at",
            (company_id, loop_id, seq, at))


def _last_mark(company_id: str, loop_id: str) -> int | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT last_seq FROM period_marks WHERE company_id = ? AND loop_id = ?",
            (company_id, loop_id)).fetchone()
    return int(row["last_seq"]) if row else None


def anchors_at(company_id: str, seq: int) -> AnchorSet:
    # Recompute anchors from the ledger up to a sequence number. Nothing stored.
    entries = [e for e in ledger_module.read(company_id) if (e.seq or 0) <= seq]
    return AnchorSet.compute(company_id, entries)


def record_findings(company_id: str, loop_id: str,
                    findings: list[mon.Finding]) -> int:
    escalated = {id(f) for f in mon.escalations(findings)}
    with connection() as conn:
        for f in findings:
            conn.execute(
                "INSERT INTO findings (company_id, loop_id, kind, severity, "
                "department, anchor, anchor_delta, message, detected_at, escalated) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (company_id, loop_id, str(f.kind), str(f.severity), f.department,
                 f.anchor, f.anchor_delta, f.message, f.detected_at,
                 1 if id(f) in escalated else 0))
    return len(findings)


def open_findings(company_id: str, limit: int = 100) -> list[dict]:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM findings WHERE company_id = ? ORDER BY seq DESC LIMIT ?",
            (company_id, limit)).fetchall()
    return sorted((dict(r) for r in rows), key=lambda r: order.get(r["severity"], 9))


# ------------------------------------------------------------------ claims ----

def _proxy_delta(before: AnchorSet, after: AnchorSet, metric: str):
    # Movement in a proxy across the period.
    #
    # AnchorSet.delta only reports anchors computable in BOTH readings, which is
    # correct for it: an anchor that did not exist before has no measured change.
    # A proxy is different. A department going from no acquisitions to forty has
    # very clearly claimed progress, and that first active period is exactly when
    # capture is most likely - so treating an absent baseline as zero is the
    # honest reading here, not an imputation.
    now = after.value(metric)
    if now is None:
        return None
    was = before.value(metric)
    return now - (was if was is not None else 0.0)


def claims_from_ledger(company_id: str, before: AnchorSet,
                       after: AnchorSet) -> list[mon.Claim]:
    # Reconstruct each department's implicit claim from what it actually did.
    #
    # A department that completed work is treated as claiming progress on its own
    # proxy. It nominates the anchor its profile says it serves. This is the step
    # that makes capture checkable without asking the department to self-report:
    # the claim is derived from the ledger, and the anchor comes from the profile.
    claims: list[mon.Claim] = []
    for name, profile in PROFILES.items():
        proxy_delta = _proxy_delta(before, after, profile.proxy_metric)
        if proxy_delta is None or abs(proxy_delta) < mon.CLAIM_NOISE_FLOOR:
            continue
        claims.append(mon.Claim(
            department=name, proxy_name=profile.proxy_metric,
            proxy_delta=proxy_delta, expected_anchor=profile.serves_anchor))
    return claims


def reports_from_ledger(company_id: str, before: AnchorSet,
                        after: AnchorSet) -> list[mon.DepartmentReport]:
    out = []
    for name, profile in PROFILES.items():
        delta = _proxy_delta(before, after, profile.proxy_metric)
        if delta is None:
            continue
        out.append(mon.DepartmentReport(name, profile.proxy_metric, delta))
    return out


# ---------------------------------------------------------------- handlers ----

@dataclass
class MonitorRun:
    loop_id: str
    findings: int = 0
    escalated: int = 0
    period_entries: int = 0
    note: str = ""

    def as_dict(self) -> dict:
        return {"loop_id": self.loop_id, "findings": self.findings,
                "escalated": self.escalated,
                "period_entries": self.period_entries, "note": self.note}


def _period(company_id: str, loop_id: str, now: datetime):
    # Returns (before, after, current_seq) or None when there is no prior mark.
    current = _max_seq(company_id)
    previous = _last_mark(company_id, loop_id)
    _mark(company_id, loop_id, current, now.isoformat())
    if previous is None:
        return None
    if current == previous:
        return None
    return anchors_at(company_id, previous), anchors_at(company_id, current), current


def goodhart_handler(company_id: str, now: datetime) -> dict:
    run = MonitorRun("goodhart_detector")
    period = _period(company_id, run.loop_id, now)
    if period is None:
        run.note = "baseline recorded; no prior period to compare"
        return run.as_dict()
    before, after, seq = period
    run.period_entries = after.entry_count - before.entry_count
    findings = mon.claim_vs_ledger(
        claims_from_ledger(company_id, before, after), before, after)
    run.findings = record_findings(company_id, run.loop_id, findings)
    run.escalated = len(mon.escalations(findings))
    return run.as_dict()


def conflict_handler(company_id: str, now: datetime) -> dict:
    run = MonitorRun("conflict_detector")
    period = _period(company_id, run.loop_id, now)
    if period is None:
        run.note = "baseline recorded"
        return run.as_dict()
    before, after, seq = period
    run.period_entries = after.entry_count - before.entry_count
    findings = mon.detect_conflict(
        reports_from_ledger(company_id, before, after), before, after)
    run.findings = record_findings(company_id, run.loop_id, findings)
    run.escalated = len(mon.escalations(findings))
    return run.as_dict()


def drift_handler(thresholds: list[mon.Threshold] | None = None):
    def handler(company_id: str, now: datetime) -> dict:
        run = MonitorRun("drift_monitor")
        current = AnchorSet.compute(company_id)
        findings = mon.detect_drift(thresholds or [], current, now=now.isoformat())
        run.findings = record_findings(company_id, run.loop_id, findings)
        run.escalated = len(mon.escalations(findings))
        if not thresholds:
            run.note = "no calibrated thresholds registered"
        return run.as_dict()
    return handler


def objective_review_handler(objectives: list[mon.Objective] | None = None):
    def handler(company_id: str, now: datetime) -> dict:
        run = MonitorRun("objective_review")
        period = _period(company_id, run.loop_id, now)
        if period is None:
            run.note = "baseline recorded"
            return run.as_dict()
        before, after, seq = period
        findings = mon.review_objectives(objectives or [], before, after,
                                         now=now.isoformat())
        run.findings = record_findings(company_id, run.loop_id, findings)
        run.escalated = len(mon.escalations(findings))
        if not objectives:
            run.note = "no objectives registered"
        return run.as_dict()
    return handler


def reflection_handler(company_id_departments=None):
    # Reflection runs for every department, grounded in measured anchor deltas.
    def handler(company_id: str, now: datetime) -> dict:
        period = _period(company_id, "reflection", now)
        if period is None:
            return {"loop_id": "reflection", "note": "baseline recorded",
                    "reflections": 0}
        before, after, seq = period
        written = 0
        verdicts = {}
        for name in (company_id_departments or PROFILES):
            r = refl.reflect(company_id, name, before, after,
                             period_end=now.isoformat())
            written += len(refl.persist(r))
            verdicts[name] = str(r.verdict)
        return {"loop_id": "reflection", "reflections": len(verdicts),
                "memories_written": written, "verdicts": verdicts}
    return handler


def register_all(scheduler, *, thresholds=None, objectives=None) -> list[str]:
    # Wire every monitor and the reflection loop into a scheduler.
    handlers = {
        "goodhart_detector": goodhart_handler,
        "conflict_detector": conflict_handler,
        "drift_monitor": drift_handler(thresholds),
        "objective_review": objective_review_handler(objectives),
        "reflection": reflection_handler(),
    }
    wired = []
    for loop_id, handler in handlers.items():
        if loop_id in scheduler.graph.loops:
            scheduler.register_handler(loop_id, handler)
            wired.append(loop_id)
    return wired
