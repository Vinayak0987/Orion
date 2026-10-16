"""Tests for anchor metrics.

The first group is the important one: it asserts the invariant that the whole
operating layer depends on — that no caller can write an anchor. If those tests
ever pass vacuously, the architecture's central claim is unsupported.
"""

from __future__ import annotations

import inspect

import pytest

from app.generation.operating import anchors, ledger
from app.generation.operating.anchors import (
    ANCHOR_NAMES,
    THIN_EVIDENCE_THRESHOLD,
    AnchorSet,
    AnchorWriteAttempted,
)
from app.generation.operating.ledger import EntryKind, LedgerEntry


@pytest.fixture(autouse=True)
def ledger_db(tmp_path, monkeypatch):
    from app.generation.db import sqlite as sqlite_module

    db_file = tmp_path / "anchor-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    yield


def add(kind: EntryKind, *, amount=0, quantity=0, department="finance",
        actor="agent", company="c1", occurred_at=None) -> None:
    kwargs = dict(company_id=company, kind=kind, department=department, actor=actor)
    if amount:
        kwargs["amount_minor"] = amount
    if quantity:
        kwargs["quantity"] = quantity
    if occurred_at:
        kwargs["occurred_at"] = occurred_at
    ledger.append(LedgerEntry(**kwargs))


# =========================================================== THE INVARIANT ====


def test_anchor_set_cannot_be_mutated():
    add(EntryKind.REVENUE, amount=100_00)
    a = AnchorSet.compute("c1")
    with pytest.raises(AnchorWriteAttempted):
        a.entry_count = 999


def test_anchor_dict_assignment_does_not_persist():
    """Even if a caller mutates the returned dict, the next read is unaffected."""
    add(EntryKind.REVENUE, amount=100_00)
    a = AnchorSet.compute("c1")
    a.anchors.pop("revenue", None)  # local vandalism
    fresh = AnchorSet.compute("c1")
    assert fresh.value("revenue") == 100.0


def test_module_exposes_no_anchor_writer():
    """There must be no function that sets, records or overrides an anchor."""
    forbidden_verbs = ("set_", "write_", "record_", "store_", "save_",
                       "update_", "override_", "put_")
    public = [n for n in dir(anchors) if not n.startswith("_")]
    offenders = [n for n in public if n.startswith(forbidden_verbs)]
    assert offenders == [], f"anchors must have no writer, found {offenders}"


def test_no_anchor_table_exists():
    """Anchors are derived, so there is nothing to write to.

    A stored anchor would be a value an agent could eventually reach.
    """
    from app.generation.db.sqlite import connection

    with connection() as conn:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert not any("anchor" in t.lower() for t in tables)


def test_the_only_constructor_reads_the_ledger():
    """compute() must derive from entries, not accept caller-supplied values."""
    signature = inspect.signature(AnchorSet.compute)
    assert list(signature.parameters) == ["company_id", "entries"]
    # `entries` accepts LedgerEntry objects only; there is no way to pass a
    # pre-computed anchor value in.
    with pytest.raises(Exception):
        AnchorSet.compute("c1", entries=[{"revenue": 999.0}])


def test_recomputation_is_the_only_way_to_change_an_anchor():
    add(EntryKind.REVENUE, amount=100_00)
    before = AnchorSet.compute("c1")
    assert before.value("revenue") == 100.0
    add(EntryKind.REVENUE, amount=50_00)
    after = AnchorSet.compute("c1")
    assert after.value("revenue") == 150.0


def test_computation_is_deterministic():
    for _ in range(3):
        add(EntryKind.REVENUE, amount=333_33)
    first = AnchorSet.compute("c1")
    second = AnchorSet.compute("c1")
    assert first.anchors == second.anchors


# ========================================================== DERIVATION ========


def test_margins_match_hand_calculation():
    add(EntryKind.REVENUE, amount=1_000_00)         # 1000.00
    add(EntryKind.COGS, amount=400_00)              #  400.00
    add(EntryKind.OPEX, amount=200_00)              #  200.00
    add(EntryKind.MARKETING_SPEND, amount=100_00)   #  100.00
    a = AnchorSet.compute("c1")
    assert a.value("gross_profit") == 600.0
    assert a.value("gross_margin_pct") == 60.0
    assert a.value("net_profit") == 300.0
    assert a.value("net_margin_pct") == 30.0


def test_negative_margin_is_reported_not_clamped():
    add(EntryKind.REVENUE, amount=100_00)
    add(EntryKind.COGS, amount=90_00)
    add(EntryKind.OPEX, amount=50_00)
    a = AnchorSet.compute("c1")
    assert a.value("net_margin_pct") == -40.0


def test_cash_balance_nets_in_against_out():
    add(EntryKind.CASH_IN, amount=500_00)
    add(EntryKind.CASH_OUT, amount=120_00)
    assert AnchorSet.compute("c1").value("cash_balance") == 380.0


def test_customer_counts_and_retention():
    for _ in range(10):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    for _ in range(2):
        add(EntryKind.CUSTOMER_CHURNED, quantity=1, department="sales")
    a = AnchorSet.compute("c1")
    assert a.value("customers_acquired") == 10.0
    assert a.value("customers_churned") == 2.0
    assert a.value("customers_active") == 8.0
    assert a.value("churn_pct") == 20.0
    assert a.value("retention_pct") == 80.0


def test_cac_is_marketing_spend_per_acquisition():
    add(EntryKind.MARKETING_SPEND, amount=1_000_00, department="marketing")
    for _ in range(4):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    assert AnchorSet.compute("c1").value("cac") == 250.0


def test_division_by_zero_yields_none_not_an_exception():
    add(EntryKind.MARKETING_SPEND, amount=1_000_00)
    a = AnchorSet.compute("c1")
    assert a.value("cac") is None          # no acquisitions
    assert a.value("net_margin_pct") is None  # no revenue


def test_absent_evidence_yields_none_rather_than_zero():
    """Mirrors the evaluation harness's refusal to impute.

    Zero revenue and unknown revenue are different claims. Reporting the second
    as the first would make an empty ledger look like a failing business.
    """
    a = AnchorSet.compute("c1")
    assert a.entry_count == 0
    assert all(anchor.value is None for anchor in a.anchors.values())
    assert a.value("revenue") is None
    assert a.value("net_margin_pct") is None


def test_anchor_names_are_stable():
    a = AnchorSet.compute("c1")
    assert set(a.anchors) == set(ANCHOR_NAMES)
    assert "net_margin_pct" in ANCHOR_NAMES
    assert "cac" in ANCHOR_NAMES


def test_anchors_are_company_scoped():
    add(EntryKind.REVENUE, amount=100_00, company="c1")
    add(EntryKind.REVENUE, amount=900_00, company="c2")
    assert AnchorSet.compute("c1").value("revenue") == 100.0
    assert AnchorSet.compute("c2").value("revenue") == 900.0


# ========================================================== PROVENANCE ========


def test_thin_evidence_is_flagged():
    add(EntryKind.REVENUE, amount=100_00)
    a = AnchorSet.compute("c1")
    assert a.get("revenue").thin is True
    assert a.is_thin is True


def test_sufficient_evidence_is_not_flagged_thin():
    for _ in range(THIN_EVIDENCE_THRESHOLD + 1):
        add(EntryKind.REVENUE, amount=10_00)
    assert AnchorSet.compute("c1").get("revenue").thin is False


def test_entry_counts_are_carried_per_anchor():
    add(EntryKind.REVENUE, amount=100_00)
    add(EntryKind.REVENUE, amount=100_00)
    add(EntryKind.COGS, amount=50_00)
    a = AnchorSet.compute("c1")
    assert a.get("revenue").entries == 2
    # gross margin depends on both revenue and cogs entries
    assert a.get("gross_margin_pct").entries == 3


# ============================================================== DELTAS ========


def test_delta_reports_measured_movement():
    add(EntryKind.REVENUE, amount=1_000_00)
    add(EntryKind.COGS, amount=500_00)
    before = AnchorSet.compute("c1")
    assert before.value("gross_margin_pct") == 50.0

    add(EntryKind.COGS, amount=300_00)  # costs rise, margin falls
    after = AnchorSet.compute("c1")

    delta = after.delta(before)
    assert delta["gross_margin_pct"] == pytest.approx(-30.0)
    assert delta["cogs"] == pytest.approx(300.0)


def test_delta_skips_anchors_that_were_not_computable_before():
    add(EntryKind.REVENUE, amount=100_00)
    before = AnchorSet.compute("c1")
    for _ in range(2):
        add(EntryKind.CUSTOMER_ACQUIRED, quantity=1, department="sales")
    after = AnchorSet.compute("c1")
    assert "customers_acquired" not in after.delta(before)


def test_read_only_view_returns_an_anchor_set():
    add(EntryKind.REVENUE, amount=250_00)
    view = anchors.read_only_view("c1")
    assert isinstance(view, AnchorSet)
    assert view.value("revenue") == 250.0
    with pytest.raises(AnchorWriteAttempted):
        view.company_id = "c2"
