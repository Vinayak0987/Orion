# Runs a company unattended for a simulated quarter.
#
#     python -m scripts.autonomy_demo
#
# Nothing prompts anything. The scheduler wakes five department loops on their
# cadences and four monitor loops on theirs; work is planned, gated, executed and
# recorded; anchors are recomputed from the ledger; findings escalate to a human.
#
# No LLM calls, no network, no API keys. Time is injected, so the run is
# deterministic and reproducible.
from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile
from datetime import UTC, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))

RULE = "-" * 76


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--db", type=pathlib.Path)
    args = ap.parse_args(argv)

    db = args.db or (pathlib.Path(tempfile.mkdtemp()) / "orion-autonomy.db")
    from app.db import sqlite as sq
    sq.settings.__class__.sqlite_file = property(lambda _s: db)

    from app.operating import build_scheduler, init_all, monitoring as MO
    from app.operating import governance as G, ledger, memory as M, scheduler as S
    from app.operating.anchors import AnchorSet
    from app.operating.ledger import EntryKind, LedgerEntry
    from app.operating.memory import MemoryType
    from app.operating.scheduler import ManualClock

    init_all()
    COMPANY = "demo-icecream-andheri"
    T0 = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

    print(RULE)
    print("OPENING STATE - the generated plan becomes the company")
    print(RULE)
    for kind, amount in ((EntryKind.CASH_IN, 15_00_000_00),
                         (EntryKind.REVENUE, 4_00_000_00),
                         (EntryKind.COGS, 1_60_000_00)):
        ledger.append(LedgerEntry(company_id=COMPANY, kind=kind,
                                  department="finance", actor="pl_forecast",
                                  amount_minor=amount,
                                  occurred_at=T0.isoformat()))
    opening = AnchorSet.compute(COMPANY)
    for name in ("cash_balance", "revenue", "net_margin_pct"):
        print("  %-18s %s" % (name, opening.value(name)))

    clock = ManualClock(T0)
    sched = build_scheduler(clock)
    print("\n  loops wired: %d of %d schedulable have a handler"
          % (sum(1 for l in sched.schedulable() if l.id in sched.handlers),
             len(sched.schedulable())))

    print("\n" + RULE)
    print("RUNNING UNATTENDED FOR %d DAYS - nothing is prompted" % args.days)
    print(RULE)
    totals = {}
    for day in range(args.days):
        for run in sched.run_due(COMPANY, clock.now()):
            totals[run.loop_id] = totals.get(run.loop_id, 0) + 1
        clock.advance(days=1)
    for loop_id in sorted(totals):
        print("  %-20s ran %3d times" % (loop_id, totals[loop_id]))

    closing = AnchorSet.compute(COMPANY)
    print("\n" + RULE)
    print("CLOSING STATE - computed from the ledger, written by no agent")
    print(RULE)
    print("  ledger entries     %d" % ledger.entry_count(COMPANY))
    for name in ("cash_balance", "revenue", "net_margin_pct",
                 "customers_acquired", "cac", "tasks_completed"):
        was, now = opening.value(name), closing.value(name)
        print("  %-18s %-12s -> %s" % (name, was, now))

    print("\n" + RULE)
    print("WHAT THE MONITORS FOUND")
    print(RULE)
    findings = MO.open_findings(COMPANY, limit=8)
    if not findings:
        print("  no findings: every claim was matched by an anchor movement")
    for row in findings:
        print("  [%s] %s | %s | anchor %s %+g"
              % (row["severity"].upper(), row["kind"], row["department"],
                 row["anchor"], row["anchor_delta"]))

    print("\n" + RULE)
    print("GOVERNANCE")
    print(RULE)
    queue = G.review_queue(COMPANY)
    print("  awaiting human review   %d" % len(queue))
    for row in queue[:4]:
        print("    %-28s %-12s %s" % (row["id"], row["risk"], row["reason"][:44]))
    load = G.load_size()
    for key in sorted(load):
        print("  %-28s %d" % (key, load[key]))

    print("\n" + RULE)
    print("WHAT EACH DEPARTMENT LEARNED")
    print(RULE)
    stats = M.stats(COMPANY)
    for dept in sorted(stats):
        counts = stats[dept]
        print("  %-12s episodic %-4s reflective %-4s semantic %s"
              % (dept, counts.get(str(MemoryType.EPISODIC), 0),
                 counts.get(str(MemoryType.REFLECTIVE), 0),
                 counts.get(str(MemoryType.SEMANTIC), 0)))

    print("\n" + RULE)
    print("  scheduled runs recorded: %d" % len(S.run_history(COMPANY, limit=99999)))
    print("  database: %s" % db)
    print(RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
