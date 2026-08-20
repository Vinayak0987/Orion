"""Append-only ledger — the operating layer's record of what actually happened.

Every anchor metric is derived from this table and from nothing else. The table
therefore has to be trustworthy in a way the rest of the state is not, so two
properties are enforced by the database rather than by convention:

1. **Append-only.** SQLite triggers abort any UPDATE or DELETE. An entry, once
   written, cannot be revised or removed by anything — not by an agent, not by a
   service, not by a stray query.
2. **Attributed.** Every entry records which department and which actor produced
   it, so a claimed outcome can always be traced to the work that caused it.

Why this exists
---------------
PAPER.md §4.4 records that where two agents asserted the same quantity, the
derived figure had to win over the asserted one, and that prompt-level
constraints were insufficient to achieve this. §7.2 records that estimates
travelling through a chain of agents compound variance. The conclusion drawn from
both is that a number an agent asserts about its own performance cannot be relied
upon.

The ledger is the alternative: agents record *events*, and the numbers that
matter are computed from those events by code. See `app.operating.anchors`.

Money
-----
Amounts are integer **minor units** (paise), never floats. A paper reporting on
numerical reliability should not accumulate binary floating-point error in its
own accounting.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.sqlite import connection

# --------------------------------------------------------------------- schema --

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   TEXT NOT NULL,
    kind         TEXT NOT NULL,
    occurred_at  TEXT NOT NULL,
    recorded_at  TEXT NOT NULL,
    amount_minor INTEGER NOT NULL DEFAULT 0,
    currency     TEXT NOT NULL DEFAULT 'INR',
    quantity     INTEGER NOT NULL DEFAULT 0,
    department   TEXT NOT NULL,
    actor        TEXT NOT NULL,
    memo         TEXT NOT NULL DEFAULT '',
    ref_json     TEXT
);

CREATE INDEX IF NOT EXISTS idx_ledger_company ON ledger(company_id, seq);
CREATE INDEX IF NOT EXISTS idx_ledger_kind    ON ledger(company_id, kind);

-- The append-only guarantee. Enforced here rather than in application code so
-- that it holds for every possible caller, including a future one that has not
-- read this docstring.
CREATE TRIGGER IF NOT EXISTS ledger_is_append_only_no_update
BEFORE UPDATE ON ledger
BEGIN
    SELECT RAISE(ABORT, 'ledger is append-only: UPDATE is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS ledger_is_append_only_no_delete
BEFORE DELETE ON ledger
BEGIN
    SELECT RAISE(ABORT, 'ledger is append-only: DELETE is not permitted');
END;
"""


def init_ledger() -> None:
    """Idempotent. Safe to call alongside app.db.sqlite.init_db()."""
    with connection() as conn:
        conn.executescript(LEDGER_SCHEMA)


# ---------------------------------------------------------------------- kinds --


class EntryKind(StrEnum):
    """What an entry records.

    Monetary kinds carry `amount_minor`; count kinds carry `quantity`. Mixing
    them is rejected at validation, because an anchor that silently summed a
    customer count into a revenue figure would be worse than no anchor at all.
    """

    REVENUE = "revenue"
    COGS = "cogs"
    OPEX = "opex"
    MARKETING_SPEND = "marketing_spend"
    CAPEX = "capex"
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    CUSTOMER_ACQUIRED = "customer_acquired"
    CUSTOMER_CHURNED = "customer_churned"
    SLA_BREACH = "sla_breach"
    TASK_COMPLETED = "task_completed"


MONETARY_KINDS: frozenset[EntryKind] = frozenset(
    {
        EntryKind.REVENUE,
        EntryKind.COGS,
        EntryKind.OPEX,
        EntryKind.MARKETING_SPEND,
        EntryKind.CAPEX,
        EntryKind.CASH_IN,
        EntryKind.CASH_OUT,
    }
)

COUNT_KINDS: frozenset[EntryKind] = frozenset(
    {
        EntryKind.CUSTOMER_ACQUIRED,
        EntryKind.CUSTOMER_CHURNED,
        EntryKind.SLA_BREACH,
        EntryKind.TASK_COMPLETED,
    }
)

assert MONETARY_KINDS | COUNT_KINDS == set(EntryKind), (
    "every EntryKind must be classified as monetary or count"
)


class LedgerAppendError(RuntimeError):
    """An entry was rejected before it reached the database."""


# ---------------------------------------------------------------------- model --


def _now() -> str:
    return datetime.now(UTC).isoformat()


class LedgerEntry(BaseModel):
    """One immutable fact. Frozen, because an entry is a record, not a variable."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    kind: EntryKind
    department: str
    actor: str
    occurred_at: str = Field(default_factory=_now)
    amount_minor: int = 0
    currency: str = "INR"
    quantity: int = 0
    memo: str = ""
    ref: dict[str, Any] = Field(default_factory=dict)
    seq: int | None = None
    recorded_at: str | None = None

    @field_validator("company_id", "department", "actor")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company_id, department and actor are required")
        return v.strip()

    @field_validator("amount_minor")
    @classmethod
    def _amount_is_non_negative(cls, v: int) -> int:
        # Direction is carried by `kind`, not by the sign. A negative revenue
        # entry would be a refund, which must be recorded as its own kind rather
        # than by flipping a sign and hoping every consumer notices.
        if v < 0:
            raise ValueError(
                "amount_minor must be non-negative; direction is carried by kind"
            )
        return v

    @field_validator("quantity")
    @classmethod
    def _quantity_is_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("quantity must be non-negative")
        return v

    def model_post_init(self, __context: object) -> None:
        if self.kind in MONETARY_KINDS and self.quantity:
            raise ValueError(
                f"{self.kind} is a monetary kind and must not carry a quantity"
            )
        if self.kind in COUNT_KINDS and self.amount_minor:
            raise ValueError(
                f"{self.kind} is a count kind and must not carry an amount"
            )

    @property
    def amount(self) -> float:
        """Major units, for display only. Never use this for arithmetic."""
        return self.amount_minor / 100


# ------------------------------------------------------------------ operations --


def append(entry: LedgerEntry) -> int:
    """Write one entry. Returns its sequence number.

    There is deliberately no `update` or `delete` counterpart.
    """
    if entry.seq is not None:
        raise LedgerAppendError(
            "seq is assigned by the database; do not supply it when appending"
        )
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO ledger (company_id, kind, occurred_at, recorded_at, "
            "amount_minor, currency, quantity, department, actor, memo, ref_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.company_id,
                str(entry.kind),
                entry.occurred_at,
                _now(),
                entry.amount_minor,
                entry.currency,
                entry.quantity,
                entry.department,
                entry.actor,
                entry.memo,
                json.dumps(entry.ref, default=str) if entry.ref else None,
            ),
        )
        return int(cursor.lastrowid)


def append_many(entries: Iterable[LedgerEntry]) -> list[int]:
    return [append(e) for e in entries]


def _row_to_entry(row: sqlite3.Row) -> LedgerEntry:
    return LedgerEntry(
        seq=row["seq"],
        company_id=row["company_id"],
        kind=EntryKind(row["kind"]),
        occurred_at=row["occurred_at"],
        recorded_at=row["recorded_at"],
        amount_minor=row["amount_minor"],
        currency=row["currency"],
        quantity=row["quantity"],
        department=row["department"],
        actor=row["actor"],
        memo=row["memo"],
        ref=json.loads(row["ref_json"]) if row["ref_json"] else {},
    )


def read(
    company_id: str,
    *,
    kinds: Iterable[EntryKind] | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[LedgerEntry]:
    """Entries for one company in sequence order."""
    sql = ["SELECT * FROM ledger WHERE company_id = ?"]
    params: list[Any] = [company_id]

    kind_list = [str(k) for k in (kinds or [])]
    if kind_list:
        sql.append(f"AND kind IN ({','.join('?' * len(kind_list))})")
        params.extend(kind_list)
    if since:
        sql.append("AND occurred_at >= ?")
        params.append(since)
    if until:
        sql.append("AND occurred_at < ?")
        params.append(until)
    sql.append("ORDER BY seq")

    with connection() as conn:
        rows = conn.execute(" ".join(sql), params).fetchall()
    return [_row_to_entry(r) for r in rows]


def total_minor(entries: Iterable[LedgerEntry], kind: EntryKind) -> int:
    """Integer sum of one monetary kind. No floats anywhere in the path."""
    if kind not in MONETARY_KINDS:
        raise ValueError(f"{kind} is not a monetary kind")
    return sum(e.amount_minor for e in entries if e.kind == kind)


def total_count(entries: Iterable[LedgerEntry], kind: EntryKind) -> int:
    if kind not in COUNT_KINDS:
        raise ValueError(f"{kind} is not a count kind")
    return sum(e.quantity for e in entries if e.kind == kind)


def entry_count(company_id: str) -> int:
    with connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM ledger WHERE company_id = ?", (company_id,)
        ).fetchone()
    return int(row["n"])
