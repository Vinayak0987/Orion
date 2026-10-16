"""Tests for the monitor loops.

The central test is `test_goodhart_scenario_is_detected`: a department reports a
large proxy gain while the anchor it nominated moves against it. If that case
ever stops producing a CRITICAL finding, the operating layer's main claim is
unsupported.
"""

from __future__ import annotations

import pytest

from app.generation.operating import ledger, monitors
from app.generation.operating.anchors import AnchorSet
from app.generation.operating.ledger import EntryKind, LedgerEntry
from app.generation.operating.monitors import (
    Claim,
    DepartmentReport,
    Direction,
    Finding,
    FindingKind,
    Objective,
    Severity,
    Threshold,
    UncitedFinding,
    claim_vs_ledger,
    detect_conflict,
    detect_drift,
    escalations,
    render_findings,
    review_objectives,
    stale_after,
)


@pytest.fixture(autouse=True)
def ledger_db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module

    db_file = tmp_path / "monitors-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    yield


def add(kind: EntryKind, *, amount=0, quantity=0, department="finance"):
    kwargs = dict(company_id="c1", kind=kind, department=department, actor="agent")
    if amount:
        kwargs["amount_minor"] = amount
    if quantity:
        kwargs["quantity"] = quantity
    ledger.append(LedgerEntry(**kwargs))


def snapshot() -> AnchorSet:
    return AnchorSet.compute("c1")


# ===================== THE GOODHART CASE ======================================


def test_goodhart_scenario_is_detected():
    """Proxy rises steeply; the anchor it nominated falls. Must be CRITICAL."""
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=400_00)
    add(EntryKind.OPEX, amount=100_00)
    before = snapshot()
    assert before.value("net_margin_pct") == 50.0

    # discounting drives footfall but destroys margin
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=1_100_00)
    add(EntryKind.MARKETING_SPEND, amount=300_00, department="marketing")
    after = snapshot()
    assert after.value("net_margin_pct") < 50.0

    claim = Claim(
        department="marketing",
        proxy_name="footfall",
        proxy_delta=+38.0,
        expected_anchor="net_margin_pct",
        expected_direction=Direction.UP,
    )
    findings = claim_vs_ledger([claim], before, after)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind is FindingKind.PROXY_DIVERGENCE
    assert finding.severity is Severity.CRITICAL
    assert finding.department == "marketing"
    assert finding.anchor == "net_margin_pct"
    assert finding.anchor_delta < 0
    assert finding.proxy_delta == 38.0
    assert "decoupled" in finding.message


def test_supported_claim_produces_no_finding():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snapshot()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=200_00)  # margin improves
    after = snapshot()

    claim = Claim("marketing", "footfall", +20.0, "gross_margin_pct")
    assert claim_vs_ledger([claim], before, after) == []


def test_flat_anchor_yields_the_weaker_unsupported_finding():
    """Absence of movement may only mean the effect has not landed."""
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    before = snapshot()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)  # margin unchanged at 50%
    after = snapshot()

    findings = claim_vs_ledger(
        [Claim("marketing", "impressions", +52.0, "gross_margin_pct")],
        before, after,
    )
    assert len(findings) == 1
    assert findings[0].kind is FindingKind.PROXY_UNSUPPORTED
    assert findings[0].severity is Severity.MEDIUM


def test_a_claim_below_the_noise_floor_is_ignored():
    add(EntryKind.REVENUE, amount=1_000_00)
    before = snapshot()
    add(EntryKind.COGS, amount=900_00)
    after = snapshot()
    tiny = Claim("marketing", "footfall", +0.2, "gross_margin_pct")
    assert claim_vs_ledger([tiny], before, after) == []


def test_no_finding_when_the_anchor_is_not_computable():
    """Silence rather than a finding about missing evidence."""
    before = snapshot()
    add(EntryKind.MARKETING_SPEND, amount=100_00, department="marketing")
    after = snapshot()
    claim = Claim("marketing", "footfall", +30.0, "net_margin_pct")
    assert claim_vs_ledger([claim], before, after) == []


def test_downward_expectation_is_handled():
    """Some claims expect an anchor to fall — churn, for instance."""
    for _ in range(10):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    for _ in range(2):
        add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    before = snapshot()
    assert before.value("churn_pct") == 20.0

    for _ in range(6):
        add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    after = snapshot()  # churn worsens

    claim = Claim("marketing", "retention_campaigns", +5.0, "churn_pct",
                  expected_direction=Direction.DOWN)
    findings = claim_vs_ledger([claim], before, after)
    assert len(findings) == 1
    assert findings[0].kind is FindingKind.PROXY_DIVERGENCE


def test_claim_must_cite_a_real_anchor():
    with pytest.raises(ValueError) as excinfo:
        Claim("marketing", "footfall", 10.0, "vibes").validate()
    assert "unknown anchor" in str(excinfo.value)


def test_claim_must_name_a_proxy():
    with pytest.raises(ValueError):
        Claim("marketing", "   ", 10.0, "net_margin_pct").validate()


# ===================== FINDINGS MUST BE PINNED ================================


def test_a_finding_without_an_anchor_cannot_be_constructed():
    with pytest.raises(UncitedFinding):
        Finding(kind=FindingKind.PROXY_DIVERGENCE, severity=Severity.HIGH,
                department="marketing", anchor="", anchor_delta=-1.0,
                message="something felt wrong")


def test_a_finding_citing_an_unknown_anchor_is_rejected():
    with pytest.raises(UncitedFinding):
        Finding(kind=FindingKind.PROXY_DIVERGENCE, severity=Severity.HIGH,
                department="marketing", anchor="made_up", anchor_delta=-1.0,
                message="x")


def test_finding_row_is_flat_and_pinned():
    f = Finding(kind=FindingKind.PROXY_DIVERGENCE, severity=Severity.CRITICAL,
                department="marketing", anchor="net_margin_pct",
                anchor_delta=-11.0, proxy_name="footfall", proxy_delta=38.0,
                message="proxy decoupled")
    row = f.as_row()
    assert row.startswith("[CRITICAL]")
    assert "net_margin_pct" in row
    assert "-11" in row
    assert "footfall" in row


def test_findings_sort_worst_first():
    add(EntryKind.REVENUE, amount=100_00)
    low = Finding(kind=FindingKind.METRIC_STALE, severity=Severity.LOW,
                  department="a", anchor="revenue", anchor_delta=1.0, message="m")
    crit = Finding(kind=FindingKind.PROXY_DIVERGENCE, severity=Severity.CRITICAL,
                   department="b", anchor="revenue", anchor_delta=-1.0,
                   message="m")
    ordered = monitors.sort_findings([low, crit])
    assert ordered[0].severity is Severity.CRITICAL


def test_render_says_so_plainly_when_there_are_no_findings():
    assert "No findings" in render_findings([])


def test_escalations_include_critical_and_high_only():
    base = dict(department="a", anchor="revenue", anchor_delta=-1.0, message="m")
    findings = [
        Finding(kind=FindingKind.PROXY_DIVERGENCE, severity=Severity.CRITICAL, **base),
        Finding(kind=FindingKind.DEPARTMENT_CONFLICT, severity=Severity.HIGH, **base),
        Finding(kind=FindingKind.METRIC_STALE, severity=Severity.MEDIUM, **base),
        Finding(kind=FindingKind.METRIC_STALE, severity=Severity.LOW, **base),
    ]
    assert len(escalations(findings)) == 2


# ===================== CONFLICT ===============================================


def test_conflict_detected_when_two_departments_improve_and_margin_falls():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snapshot()
    add(EntryKind.REVENUE, amount=500_00)
    add(EntryKind.COGS, amount=800_00)  # margin collapses
    after = snapshot()

    reports = [
        DepartmentReport("marketing", "footfall", +38.0),
        DepartmentReport("finance", "cost_reduction", +12.0),
    ]
    findings = detect_conflict(reports, before, after)
    assert findings
    assert findings[0].kind is FindingKind.DEPARTMENT_CONFLICT
    assert findings[0].severity is Severity.HIGH
    assert "marketing" in findings[0].department
    assert "finance" in findings[0].department


def test_no_conflict_when_only_one_department_improves():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snapshot()
    add(EntryKind.COGS, amount=900_00)
    after = snapshot()
    reports = [
        DepartmentReport("marketing", "footfall", +38.0),
        DepartmentReport("finance", "cost_reduction", -4.0),
    ]
    assert detect_conflict(reports, before, after) == []


def test_no_conflict_when_the_shared_anchor_holds():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snapshot()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    after = snapshot()
    reports = [
        DepartmentReport("marketing", "footfall", +38.0),
        DepartmentReport("finance", "cost_reduction", +12.0),
    ]
    assert detect_conflict(reports, before, after) == []


# ===================== DRIFT ==================================================


def test_stale_threshold_is_flagged():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=400_00)
    current = snapshot()
    threshold = Threshold("sector_margin", "gross_margin_pct", 62.0,
                          calibrated_at=stale_after(200), max_age_days=90)
    findings = detect_drift([threshold], current)
    assert len(findings) == 1
    assert findings[0].kind is FindingKind.METRIC_STALE
    assert "no longer known" in findings[0].message


def test_fresh_threshold_is_not_flagged():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=400_00)
    current = snapshot()
    threshold = Threshold("sector_margin", "gross_margin_pct", 62.0,
                          calibrated_at=stale_after(10), max_age_days=90)
    assert detect_drift([threshold], current) == []


def test_very_stale_threshold_escalates_in_severity():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=400_00)
    current = snapshot()
    mild = detect_drift([Threshold("m", "gross_margin_pct", 62.0,
                                   stale_after(100), 90)], current)
    severe = detect_drift([Threshold("m", "gross_margin_pct", 62.0,
                                     stale_after(400), 90)], current)
    assert mild[0].severity is Severity.MEDIUM
    assert severe[0].severity is Severity.HIGH


def test_drift_stays_silent_when_the_anchor_is_not_computable():
    current = snapshot()  # empty ledger
    threshold = Threshold("m", "gross_margin_pct", 62.0, stale_after(400), 90)
    assert detect_drift([threshold], current) == []


# ===================== OBJECTIVE REVIEW =======================================


def test_long_running_objective_with_declining_anchor_is_questioned():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snapshot()
    add(EntryKind.COGS, amount=600_00)  # margin declines
    after = snapshot()

    objective = Objective(
        objective_id="o1", department="marketing",
        description="increase footfall", serves_anchor="gross_margin_pct",
        in_force_since=stale_after(120), review_after_days=30,
    )
    findings = review_objectives([objective], before, after)
    assert len(findings) == 1
    assert findings[0].kind is FindingKind.OBJECTIVE_STALE
    assert "Should this objective still exist?" in findings[0].message


def test_recent_objective_is_not_questioned():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    before = snapshot()
    add(EntryKind.COGS, amount=600_00)
    after = snapshot()
    objective = Objective("o1", "marketing", "increase footfall",
                          "gross_margin_pct", stale_after(5), 30)
    assert review_objectives([objective], before, after) == []


def test_objective_is_not_questioned_while_its_anchor_improves():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=600_00)
    before = snapshot()
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=100_00)  # margin improves
    after = snapshot()
    objective = Objective("o1", "marketing", "increase footfall",
                          "gross_margin_pct", stale_after(365), 30)
    assert review_objectives([objective], before, after) == []


# ===================== END TO END =============================================


def test_all_four_monitors_run_over_one_period():
    """The full monitor pass on a period that has gone wrong in several ways."""
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=300_00)
    for _ in range(10):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    before = snapshot()

    add(EntryKind.REVENUE, amount=500_00)
    add(EntryKind.COGS, amount=900_00)
    add(EntryKind.MARKETING_SPEND, amount=400_00, department="marketing")
    for _ in range(5):
        add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    after = snapshot()

    findings = []
    findings += claim_vs_ledger(
        [Claim("marketing", "footfall", +38.0, "net_margin_pct")], before, after)
    findings += detect_conflict(
        [DepartmentReport("marketing", "footfall", +38.0),
         DepartmentReport("finance", "cost_cut", +9.0)], before, after)
    findings += detect_drift(
        [Threshold("sector_margin", "gross_margin_pct", 62.0,
                   stale_after(400), 90)], after)
    findings += review_objectives(
        [Objective("o1", "marketing", "increase footfall", "net_margin_pct",
                   stale_after(120), 30)], before, after)

    kinds = {f.kind for f in findings}
    assert FindingKind.PROXY_DIVERGENCE in kinds
    assert FindingKind.DEPARTMENT_CONFLICT in kinds
    assert FindingKind.METRIC_STALE in kinds
    assert FindingKind.OBJECTIVE_STALE in kinds

    report = render_findings(findings)
    assert report.splitlines()[0].startswith("[CRITICAL]")
    assert len(escalations(findings)) >= 3
    # every row cites an anchor
    for line in report.splitlines():
        assert "anchor " in line
