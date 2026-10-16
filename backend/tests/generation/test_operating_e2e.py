"""End-to-end test of the operating layer.

One scenario, driven through every component: a department pursues a proxy, the
ledger records what actually happened, anchors are recomputed, a monitor finds the
divergence, the finding escalates, a human arbitrates, and the Constitution
refuses the action that would have made it worse.

This is the test that would fail if the operating layer were decorative.
"""

from __future__ import annotations

import pytest

from app.generation.operating import governance as G
from app.generation.operating import ledger, monitors
from app.generation.operating.anchors import AnchorSet
from app.generation.operating.constitution import (
    ActionKind,
    ConstitutionContext,
    ConstitutionViolation,
    ProposedAction,
)
from app.generation.operating.governance import DecisionState, Risk
from app.generation.operating.ledger import EntryKind, LedgerEntry
from app.generation.operating.loops import LoopKind, default_graph
from app.generation.operating.monitors import (
    Claim,
    DepartmentReport,
    FindingKind,
    Severity,
    claim_vs_ledger,
    detect_conflict,
    escalations,
    render_findings,
)

COMPANY = "p01-andheri-icecream"


@pytest.fixture(autouse=True)
def operating_db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module

    db_file = tmp_path / "e2e-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    G.init_governance()
    yield


def record(kind: EntryKind, *, amount=0, quantity=0, department, actor,
           occurred_at="2026-07-01T10:00:00+00:00"):
    kwargs = dict(company_id=COMPANY, kind=kind, department=department,
                  actor=actor, occurred_at=occurred_at)
    if amount:
        kwargs["amount_minor"] = amount
    if quantity:
        kwargs["quantity"] = quantity
    ledger.append(LedgerEntry(**kwargs))


def test_topology_is_valid_before_anything_runs():
    """A company does not begin operating on an unvalidated control graph."""
    graph = default_graph()
    graph.validate()
    assert graph.unterminated_cycles() == []
    assert len(graph.of_kind(LoopKind.EXECUTION)) == 5


def test_goodhart_scenario_end_to_end():
    graph = default_graph()
    graph.validate()

    # --- period 1: the business opens and trades healthily ------------------
    record(EntryKind.CASH_IN, amount=15_00_000_00, department="finance",
           actor="funding_strategy")                       # ₹15L opening
    record(EntryKind.REVENUE, amount=4_00_000_00, department="finance",
           actor="pl_forecast")
    record(EntryKind.COGS, amount=1_60_000_00, department="operations",
           actor="supply_chain")
    record(EntryKind.OPEX, amount=80_000_00, department="operations",
           actor="staffing_plan")
    record(EntryKind.MARKETING_SPEND, amount=20_000_00, department="marketing",
           actor="campaign_plan")
    for _ in range(200):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan")

    baseline = AnchorSet.compute(COMPANY)
    assert baseline.value("net_margin_pct") == pytest.approx(35.0)
    opening_margin = baseline.value("net_margin_pct")

    # --- period 2: deep discounting lifts footfall and destroys margin ------
    record(EntryKind.REVENUE, amount=5_00_000_00, department="finance",
           actor="pl_forecast", occurred_at="2026-08-01T10:00:00+00:00")
    record(EntryKind.COGS, amount=4_20_000_00, department="operations",
           actor="supply_chain", occurred_at="2026-08-01T10:00:00+00:00")
    record(EntryKind.MARKETING_SPEND, amount=1_20_000_00, department="marketing",
           actor="campaign_plan", occurred_at="2026-08-01T10:00:00+00:00")
    for _ in range(400):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan", occurred_at="2026-08-01T10:00:00+00:00")
    for _ in range(180):
        record(EntryKind.CUSTOMER_CHURNED, quantity=1, department="marketing",
               actor="campaign_plan", occurred_at="2026-08-01T10:00:00+00:00")

    current = AnchorSet.compute(COMPANY)

    # the proxy the department is judged on has improved dramatically
    footfall_gain = +100.0  # customers acquired doubled and then some
    # the anchor it nominated has not
    assert current.value("net_margin_pct") < opening_margin
    assert current.value("churn_pct") > 0

    # --- the Goodhart detector -------------------------------------------
    claim = Claim(
        department="marketing",
        proxy_name="customers_acquired",
        proxy_delta=footfall_gain,
        expected_anchor="net_margin_pct",
    )
    findings = claim_vs_ledger([claim], baseline, current)
    assert len(findings) == 1
    assert findings[0].kind is FindingKind.PROXY_DIVERGENCE
    assert findings[0].severity is Severity.CRITICAL

    # --- the conflict detector -------------------------------------------
    findings += detect_conflict(
        [
            DepartmentReport("marketing", "customers_acquired", +100.0),
            DepartmentReport("operations", "throughput", +45.0),
        ],
        baseline, current,
    )
    assert any(f.kind is FindingKind.DEPARTMENT_CONFLICT for f in findings)

    # every finding cites a real anchor movement
    for finding in findings:
        assert finding.anchor
        assert finding.anchor_delta != 0

    # --- escalation -------------------------------------------------------
    to_human = escalations(findings)
    assert len(to_human) >= 2
    assert to_human[0].severity is Severity.CRITICAL
    report = render_findings(findings)
    assert report.splitlines()[0].startswith("[CRITICAL]")

    # --- the department proposes to double down --------------------------
    doubling_down = ProposedAction(
        kind=ActionKind.SPEND,
        department="marketing",
        actor="campaign_plan",
        company_id=COMPANY,
        amount_minor=2_00_000_00,     # ₹2L more discounting
        description="scale the promotion that produced the footfall gain",
    )
    decision = G.submit("d-scale-promo", doubling_down)
    assert decision.risk is Risk.ELEVATED
    assert decision.state is DecisionState.PENDING_REVIEW

    # a human sees the queue, and sees the finding alongside it
    queue = G.review_queue(COMPANY)
    assert [row["id"] for row in queue] == ["d-scale-promo"]

    # --- the human rejects it on the monitor's evidence -----------------
    G.reject(decision, by="vinayak",
             reason="margin fell while footfall rose; see CRITICAL finding")
    assert decision.state is DecisionState.REJECTED

    with pytest.raises(G.NotApproved):
        G.execute(decision)

    trail = G.audit_for("d-scale-promo")
    outcomes = [row["outcome"] for row in trail]
    assert "proposed" in outcomes
    assert "queued" in outcomes
    assert "rejected" in outcomes
    assert "refused" in outcomes
    assert any(row["actor"] == "vinayak" for row in trail)


def test_constitution_blocks_the_action_even_if_a_human_approves_it():
    """The two-layer separation, end to end."""
    record(EntryKind.CASH_IN, amount=1_00_000_00, department="finance",
           actor="funding_strategy")

    reckless = ProposedAction(
        kind=ActionKind.SPEND, department="marketing", actor="campaign_plan",
        company_id=COMPANY, amount_minor=5_00_000_00,
        description="spend five times the cash balance",
    )
    decision = G.submit("d-reckless", reckless)
    G.approve(decision, by="vinayak")

    context = __import__(
        "app.generation.operating.constitution", fromlist=["context_from_ledger"]
    ).context_from_ledger(COMPANY, day="2026-07-01")

    with pytest.raises(ConstitutionViolation):
        G.execute(decision, context)

    assert decision.state is DecisionState.BLOCKED
    blocked = [r for r in G.audit_for("d-reckless") if r["outcome"] == "blocked"]
    assert len(blocked) == 1
    assert blocked[0]["rule_id"] in ("C1_DAILY_SPEND_CAP", "C2_SINGLE_SPEND_CAP",
                                     "C3_NO_OVERDRAFT")


def test_anchors_cannot_be_written_anywhere_in_the_pipeline():
    """The invariant, asserted against the assembled system."""
    record(EntryKind.REVENUE, amount=1_00_000_00, department="finance",
           actor="pl_forecast")
    snapshot = AnchorSet.compute(COMPANY)

    from app.generation.operating.anchors import AnchorWriteAttempted

    with pytest.raises(AnchorWriteAttempted):
        snapshot.entry_count = 0

    # and no module in the operating layer offers a writer
    from app.generation.operating import anchors as anchors_module

    writers = [
        name for name in dir(anchors_module)
        if name.startswith(("set_", "write_", "record_", "save_", "update_"))
    ]
    assert writers == []


def test_a_supported_claim_passes_without_a_finding():
    """The monitors must not cry wolf, or the review queue becomes noise."""
    record(EntryKind.REVENUE, amount=4_00_000_00, department="finance",
           actor="pl_forecast")
    record(EntryKind.COGS, amount=2_00_000_00, department="operations",
           actor="supply_chain")
    for _ in range(100):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan")
    before = AnchorSet.compute(COMPANY)

    # a genuinely good period: revenue up, costs proportionally lower
    record(EntryKind.REVENUE, amount=4_00_000_00, department="finance",
           actor="pl_forecast", occurred_at="2026-08-01T10:00:00+00:00")
    record(EntryKind.COGS, amount=1_00_000_00, department="operations",
           actor="supply_chain", occurred_at="2026-08-01T10:00:00+00:00")
    for _ in range(100):
        record(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="marketing",
               actor="campaign_plan", occurred_at="2026-08-01T10:00:00+00:00")
    after = AnchorSet.compute(COMPANY)

    claim = Claim("marketing", "customers_acquired", +100.0, "gross_margin_pct")
    assert claim_vs_ledger([claim], before, after) == []
    assert render_findings([]).startswith("No findings")


def test_routine_work_is_not_escalated():
    """Governance load has to stay tractable, so routine work auto-approves."""
    for i in range(20):
        small = ProposedAction(
            kind=ActionKind.UPDATE_PLAYBOOK, department="marketing",
            actor="campaign_plan", company_id=COMPANY,
            description=f"routine update {i}",
        )
        decision = G.submit(f"d-routine-{i}", small)
        G.execute(decision)
        assert decision.state is DecisionState.EXECUTED

    assert G.review_queue(COMPANY) == []
