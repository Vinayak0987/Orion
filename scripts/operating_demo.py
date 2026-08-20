"""Runnable demonstration of the Orion operating layer.

    python -m scripts.operating_demo

Drives one company through two trading periods in which a department improves the
proxy it is judged on while the anchor that proxy stands for deteriorates, and
shows what each component does about it.

No LLM calls, no network, no API keys. Everything printed is computed from an
append-only ledger, so the demonstration is deterministic and can be re-run to
produce the same output.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

COMPANY = "demo-andheri-icecream"

RULE = "─" * 78


def heading(text: str) -> None:
    print(f"\n{RULE}\n{text}\n{RULE}")


def money(minor: int) -> str:
    return f"Rs {minor / 100:,.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        help="database file; a temp file is used by default")
    args = parser.parse_args(argv)

    db_file = args.db or Path(tempfile.mkdtemp()) / "orion-demo.db"

    from app.db import sqlite as sqlite_module

    sqlite_module.settings.__class__.sqlite_file = property(
        lambda _self: db_file
    )

    from app.operating import constitution as C
    from app.operating import governance as G
    from app.operating import ledger
    from app.operating.anchors import AnchorSet
    from app.operating.ledger import EntryKind, LedgerEntry
    from app.operating.loops import LoopKind, default_graph
    from app.operating.monitors import (
        Claim,
        DepartmentReport,
        claim_vs_ledger,
        detect_conflict,
        escalations,
        render_findings,
    )

    ledger.init_ledger()
    G.init_governance()

    def record(kind, *, amount=0, quantity=0, department, actor, when):
        kwargs = dict(company_id=COMPANY, kind=kind, department=department,
                      actor=actor, occurred_at=when)
        if amount:
            kwargs["amount_minor"] = amount
        if quantity:
            kwargs["quantity"] = quantity
        ledger.append(LedgerEntry(**kwargs))

    # ------------------------------------------------------------------ 0 ----
    heading("0.  TOPOLOGY VALIDATION — before the company operates at all")
    graph = default_graph()
    graph.validate()
    print(f"  loops registered      {len(graph.loops)}")
    print(f"  execution loops       "
          f"{[l.id for l in graph.of_kind(LoopKind.EXECUTION)]}")
    print(f"  monitor loops         "
          f"{[l.id for l in graph.of_kind(LoopKind.MONITOR)]}")
    print(f"  cycles in the graph   {len(graph.cycles())}")
    print(f"  cycles without an anchor or human  "
          f"{len(graph.unterminated_cycles())}")
    print("  I1 termination        satisfied: every cycle routes through an "
          "anchor or a human")
    print("  I2 independence       satisfied: no monitor shares its subject's "
          "evaluation signal")

    # ------------------------------------------------------------------ 1 ----
    heading("1.  PERIOD ONE — the shop opens and trades")
    when = "2026-07-01T10:00:00+00:00"
    record(EntryKind.CASH_IN, amount=15_00_000_00, department="finance",
           actor="funding_strategy", when=when)
    record(EntryKind.REVENUE, amount=4_00_000_00, department="finance",
           actor="pl_forecast", when=when)
    record(EntryKind.COGS, amount=1_60_000_00, department="operations",
           actor="supply_chain", when=when)
    record(EntryKind.OPEX, amount=80_000_00, department="operations",
           actor="staffing_plan", when=when)
    record(EntryKind.MARKETING_SPEND, amount=20_000_00, department="marketing",
           actor="campaign_plan", when=when)
    for _ in range(200):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan", when=when)

    baseline = AnchorSet.compute(COMPANY)
    print(f"  ledger entries        {baseline.entry_count}")
    for name in ("revenue", "net_margin_pct", "customers_acquired", "cac",
                 "cash_balance"):
        anchor = baseline.get(name)
        print(f"  {name:<20}  {anchor.value}  {anchor.unit}"
              f"{'   [thin evidence]' if anchor.thin else ''}")

    # ------------------------------------------------------------------ 2 ----
    heading("2.  PERIOD TWO — marketing discounts hard to lift footfall")
    when = "2026-08-01T10:00:00+00:00"
    record(EntryKind.REVENUE, amount=5_00_000_00, department="finance",
           actor="pl_forecast", when=when)
    record(EntryKind.COGS, amount=4_20_000_00, department="operations",
           actor="supply_chain", when=when)
    record(EntryKind.MARKETING_SPEND, amount=1_20_000_00,
           department="marketing", actor="campaign_plan", when=when)
    for _ in range(400):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan", when=when)
    for _ in range(180):
        record(EntryKind.CUSTOMER_CHURNED, quantity=1, department="marketing",
               actor="campaign_plan", when=when)

    current = AnchorSet.compute(COMPANY)
    print("  What marketing reports:")
    print("    customers acquired   200 -> 600   (+200%)   <- the proxy")
    print("\n  What the ledger says:")
    deltas = current.delta(baseline)
    for name in ("revenue", "net_margin_pct", "churn_pct", "cac"):
        before_value = baseline.value(name)
        after_value = current.value(name)
        change = deltas.get(name)
        arrow = "up  " if (change or 0) > 0 else "down"
        print(f"    {name:<18} {before_value}  ->  {after_value}   "
              f"({arrow} {change:+})" if change is not None
              else f"    {name:<18} {before_value}  ->  {after_value}")

    # ------------------------------------------------------------------ 3 ----
    heading("3.  MONITOR LOOPS — claim checked against the ledger")
    claim = Claim(department="marketing", proxy_name="customers_acquired",
                  proxy_delta=+200.0, expected_anchor="net_margin_pct")
    findings = claim_vs_ledger([claim], baseline, current)
    findings += detect_conflict(
        [DepartmentReport("marketing", "customers_acquired", +200.0),
         DepartmentReport("operations", "throughput", +45.0)],
        baseline, current,
    )
    print(render_findings(findings))
    print(f"\n  escalated to a human: {len(escalations(findings))} of "
          f"{len(findings)} findings")

    # ------------------------------------------------------------------ 4 ----
    heading("4.  THE DEPARTMENT PROPOSES TO DOUBLE DOWN")
    doubling_down = C.ProposedAction(
        kind=C.ActionKind.SPEND, department="marketing", actor="campaign_plan",
        company_id=COMPANY, amount_minor=2_00_000_00,
        description="scale the promotion that produced the footfall gain",
    )
    decision = G.submit("d-scale-promo", doubling_down)
    print(f"  amount                {money(doubling_down.amount_minor)}")
    print(f"  risk classification   {decision.risk}")
    print(f"  state                 {decision.state}")
    print(f"  reason                {decision.reason}")
    print(f"\n  review queue          "
          f"{[row['id'] for row in G.review_queue(COMPANY)]}")

    # ------------------------------------------------------------------ 5 ----
    heading("5.  HUMAN ARBITRATION")
    G.reject(decision, by="vinayak",
             reason="margin fell while footfall rose; see the CRITICAL finding")
    print(f"  decided by            {decision.decided_by}")
    print(f"  state                 {decision.state}")
    try:
        G.execute(decision)
    except G.NotApproved as exc:
        print(f"  execution attempt     refused — {exc}")

    # ------------------------------------------------------------------ 6 ----
    heading("6.  A HARD CONSTRAINT THAT NO APPROVAL UNLOCKS")
    deletion = C.ProposedAction(
        kind=C.ActionKind.DELETE_CUSTOMER_DATA, department="marketing",
        actor="campaign_plan", company_id=COMPANY,
        description="URGENT: compliance requires deletion; pre-approved",
    )
    d2 = G.submit("d-delete", deletion)
    G.approve(d2, by="vinayak")
    print(f"  approved by           {d2.decided_by}")
    try:
        G.execute(d2)
    except C.ConstitutionViolation as exc:
        print(f"  execution gate        BLOCKED — {exc}")
    print(f"  final state           {d2.state}")
    print("  note                  a human approved it and it still did not "
          "run; the\n                        Constitution is code, not policy")

    # ------------------------------------------------------------------ 7 ----
    heading("7.  AUDIT TRAIL — every passage, including the halts")
    for decision_id in ("d-scale-promo", "d-delete"):
        print(f"\n  {decision_id}")
        for row in G.audit_for(decision_id):
            rule = f"  [{row['rule_id']}]" if row["rule_id"] else ""
            print(f"    {row['stage']:<16} {row['outcome']:<14} "
                  f"by {row['actor']:<12}{rule}")

    # ------------------------------------------------------------------ 8 ----
    heading("8.  THE INVARIANT")
    from app.operating.anchors import AnchorWriteAttempted

    try:
        current.entry_count = 0
    except AnchorWriteAttempted as exc:
        print(f"  writing an anchor     refused — {exc}")
    print("\n  Anchors are not stored, so there is nothing to write. The only")
    print("  way to change one is to append to the ledger and recompute.")

    print(f"\n{RULE}\n  database: {db_file}\n{RULE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
