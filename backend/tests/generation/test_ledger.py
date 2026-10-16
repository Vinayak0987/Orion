"""Tests for the append-only ledger.

The append-only property is the foundation the anchor invariant rests on, so it
is tested at the database level — not merely by checking that no Python function
happens to offer an update.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.generation.db.sqlite import connection
from app.generation.operating import ledger
from app.generation.operating.ledger import (
    COUNT_KINDS,
    MONETARY_KINDS,
    EntryKind,
    LedgerAppendError,
    LedgerEntry,
)


@pytest.fixture(autouse=True)
def ledger_db(tmp_path, monkeypatch):
    """Point the ledger at a throwaway database for every test.

    `Settings.sqlite_file` is a computed property with no setter, so the class
    attribute is replaced — the same approach tests/test_db.py uses.
    """
    from app.generation.db import sqlite as sqlite_module

    db_file = tmp_path / "ledger-test.db"
    monkeypatch.setattr(
        sqlite_module.settings.__class__, "sqlite_file",
        property(lambda _self: db_file),
    )
    ledger.init_ledger()
    yield


def entry(**kwargs) -> LedgerEntry:
    defaults = dict(
        company_id="c1",
        kind=EntryKind.REVENUE,
        department="finance",
        actor="pl_forecast",
        amount_minor=100_00,
    )
    defaults.update(kwargs)
    return LedgerEntry(**defaults)


# ------------------------------------------------------------------ basic I/O --


def test_init_is_idempotent():
    ledger.init_ledger()
    ledger.init_ledger()
    assert ledger.entry_count("c1") == 0


def test_append_returns_increasing_sequence_numbers():
    a = ledger.append(entry())
    b = ledger.append(entry())
    assert b > a


def test_read_returns_entries_in_sequence_order():
    for i in range(1, 4):
        ledger.append(entry(amount_minor=i * 100))
    rows = ledger.read("c1")
    assert [r.amount_minor for r in rows] == [100, 200, 300]
    assert [r.seq for r in rows] == sorted(r.seq for r in rows)


def test_entries_are_scoped_by_company():
    ledger.append(entry(company_id="c1"))
    ledger.append(entry(company_id="c2"))
    assert len(ledger.read("c1")) == 1
    assert len(ledger.read("c2")) == 1


def test_read_filters_by_kind():
    ledger.append(entry(kind=EntryKind.REVENUE, amount_minor=500))
    ledger.append(entry(kind=EntryKind.OPEX, amount_minor=200))
    only_opex = ledger.read("c1", kinds=[EntryKind.OPEX])
    assert [r.kind for r in only_opex] == [EntryKind.OPEX]


def test_read_filters_by_time_window():
    ledger.append(entry(occurred_at="2026-01-01T00:00:00+00:00"))
    ledger.append(entry(occurred_at="2026-06-01T00:00:00+00:00"))
    window = ledger.read("c1", since="2026-03-01T00:00:00+00:00")
    assert len(window) == 1
    assert window[0].occurred_at.startswith("2026-06")


def test_ref_payload_round_trips():
    ledger.append(entry(ref={"task_id": "t7", "campaign": "diwali"}))
    assert ledger.read("c1")[0].ref == {"task_id": "t7", "campaign": "diwali"}


def test_attribution_is_preserved():
    ledger.append(entry(department="marketing", actor="campaign_plan"))
    row = ledger.read("c1")[0]
    assert row.department == "marketing"
    assert row.actor == "campaign_plan"


# ------------------------------------------------- the append-only guarantee ---


def test_update_is_rejected_by_the_database():
    ledger.append(entry(amount_minor=100))
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        with connection() as conn:
            conn.execute("UPDATE ledger SET amount_minor = 999999")
    assert "append-only" in str(excinfo.value)


def test_delete_is_rejected_by_the_database():
    ledger.append(entry())
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        with connection() as conn:
            conn.execute("DELETE FROM ledger")
    assert "append-only" in str(excinfo.value)


def test_a_rejected_update_leaves_the_entry_intact():
    """The trigger must abort the write, not merely report it."""
    ledger.append(entry(amount_minor=4242))
    with pytest.raises(sqlite3.IntegrityError):
        with connection() as conn:
            conn.execute("UPDATE ledger SET amount_minor = 1")
    assert ledger.read("c1")[0].amount_minor == 4242


def test_module_exposes_no_mutation_functions():
    """A future contributor should not find an update() to reach for."""
    forbidden = {"update", "delete", "edit", "amend", "set_amount", "overwrite"}
    exposed = {name for name in dir(ledger) if not name.startswith("_")}
    assert not (forbidden & exposed)


def test_entry_model_is_frozen():
    e = entry()
    with pytest.raises(Exception):
        e.amount_minor = 1


def test_supplying_seq_on_append_is_rejected():
    with pytest.raises(LedgerAppendError):
        ledger.append(entry(seq=5))


# ------------------------------------------------------------- validation ------


def test_monetary_kind_may_not_carry_a_quantity():
    with pytest.raises(Exception):
        LedgerEntry(company_id="c1", kind=EntryKind.REVENUE, department="finance",
                    actor="a", amount_minor=100, quantity=3)


def test_count_kind_may_not_carry_an_amount():
    with pytest.raises(Exception):
        LedgerEntry(company_id="c1", kind=EntryKind.CUSTOMER_ACQUIRED,
                    department="sales", actor="a", amount_minor=100, quantity=1)


def test_negative_amount_is_rejected():
    with pytest.raises(Exception):
        entry(amount_minor=-1)


def test_negative_quantity_is_rejected():
    with pytest.raises(Exception):
        LedgerEntry(company_id="c1", kind=EntryKind.SLA_BREACH,
                    department="operations", actor="a", quantity=-1)


def test_blank_attribution_is_rejected():
    with pytest.raises(Exception):
        entry(actor="   ")


def test_every_kind_is_classified():
    assert MONETARY_KINDS | COUNT_KINDS == set(EntryKind)
    assert not (MONETARY_KINDS & COUNT_KINDS)


# --------------------------------------------------------------- aggregation ---


def test_total_minor_sums_only_the_named_kind():
    ledger.append(entry(kind=EntryKind.REVENUE, amount_minor=1000))
    ledger.append(entry(kind=EntryKind.REVENUE, amount_minor=2000))
    ledger.append(entry(kind=EntryKind.OPEX, amount_minor=500))
    rows = ledger.read("c1")
    assert ledger.total_minor(rows, EntryKind.REVENUE) == 3000
    assert ledger.total_minor(rows, EntryKind.OPEX) == 500


def test_total_minor_rejects_a_count_kind():
    with pytest.raises(ValueError):
        ledger.total_minor([], EntryKind.CUSTOMER_ACQUIRED)


def test_total_count_rejects_a_monetary_kind():
    with pytest.raises(ValueError):
        ledger.total_count([], EntryKind.REVENUE)


def test_integer_arithmetic_avoids_float_drift():
    """Ten entries of 10.10 must total exactly 101.00, not 100.99999999999999."""
    for _ in range(10):
        ledger.append(entry(amount_minor=1010))
    rows = ledger.read("c1")
    assert ledger.total_minor(rows, EntryKind.REVENUE) == 10_100
    assert ledger.total_minor(rows, EntryKind.REVENUE) / 100 == 101.0


def test_amount_property_is_display_only():
    assert entry(amount_minor=12345).amount == 123.45
