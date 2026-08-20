"""Anchor metrics — the numbers the business is judged by.

The invariant this module exists to hold:

    No department, planner, worker or reflection process may write an anchor
    metric, and no learning process may optimise directly against one. Anchors
    are computed, never reported.

How it is enforced, rather than merely stated
---------------------------------------------
Anchors are **not stored**. There is no anchor table, no anchor column and no
setter. `AnchorSet` is a frozen model whose only constructor is `compute()`,
which reads the append-only ledger and derives every field arithmetically. A
caller cannot write an anchor because there is nowhere to write one, and cannot
mutate a returned `AnchorSet` because Pydantic rejects assignment.

This is the same reasoning production ML applies to a held-out evaluation set: it
keeps its meaning because the training loop cannot reach it. PAPER.md §4.4 arrived
at a local version of the same conclusion — derived figures had to override
asserted ones, because prompts asking agents to respect numeric bounds were
ignored.

Provenance
----------
Every anchor carries the number of ledger entries it was derived from. A metric
computed from three events and one computed from three thousand should not look
alike on a dashboard, and `AnchorSet.is_thin` makes the difference explicit
rather than leaving it to the reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.operating import ledger
from app.operating.ledger import EntryKind, LedgerEntry

#: Below this many contributing entries an anchor is reported but marked thin.
THIN_EVIDENCE_THRESHOLD = 5


class AnchorWriteAttempted(RuntimeError):
    """Raised if any caller tries to set an anchor value.

    Nothing in the codebase should ever be able to trigger this. It exists so
    that an attempt fails loudly rather than silently succeeding, and so the
    invariant has a test that can fail.
    """


@dataclass(frozen=True, slots=True)
class Anchor:
    """One derived value, with the evidence it rests on."""

    name: str
    value: float | None
    unit: str
    entries: int
    note: str = ""

    @property
    def thin(self) -> bool:
        return self.entries < THIN_EVIDENCE_THRESHOLD

    @property
    def computable(self) -> bool:
        return self.value is not None


class AnchorSet(BaseModel):
    """A complete anchor reading for one company at one moment.

    Frozen: an anchor set is an observation, not a mutable view. Construct it
    with `AnchorSet.compute(...)`.
    """

    model_config = ConfigDict(frozen=True)

    company_id: str
    entry_count: int
    anchors: dict[str, Anchor] = Field(default_factory=dict)

    # -------------------------------------------------------------- construction

    @classmethod
    def compute(
        cls, company_id: str, entries: Iterable[LedgerEntry] | None = None
    ) -> "AnchorSet":
        """Derive every anchor from the ledger.

        Deterministic: the same entries always produce the same anchors, which
        is what allows a monitor's finding to be reproduced from stored records.
        """
        rows = list(entries) if entries is not None else ledger.read(company_id)
        return cls(
            company_id=company_id,
            entry_count=len(rows),
            anchors=_derive(rows),
        )

    # ------------------------------------------------------------------ read API

    def get(self, name: str) -> Anchor | None:
        return self.anchors.get(name)

    def value(self, name: str) -> float | None:
        anchor = self.anchors.get(name)
        return anchor.value if anchor else None

    def computable(self) -> dict[str, Anchor]:
        return {k: a for k, a in self.anchors.items() if a.computable}

    def thin(self) -> dict[str, Anchor]:
        return {k: a for k, a in self.computable().items() if a.thin}

    @property
    def is_thin(self) -> bool:
        """True when most computable anchors rest on little evidence."""
        computable = self.computable()
        if not computable:
            return True
        return len(self.thin()) > len(computable) / 2

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise AnchorWriteAttempted(
            f"Anchors are computed, never written. Attempted to set '{name}'. "
            f"To change an anchor, append ledger entries and recompute."
        )

    def delta(self, earlier: "AnchorSet") -> dict[str, float]:
        """Change in each anchor against an earlier reading.

        This is what reflection and the monitor loops consume: a department's
        performance is judged on measured movement, not on its own account.
        """
        out: dict[str, float] = {}
        for name, anchor in self.computable().items():
            previous = earlier.value(name)
            if previous is None or anchor.value is None:
                continue
            out[name] = round(anchor.value - previous, 4)
        return out


# ------------------------------------------------------------------ derivation --


def _pct(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 2)


def _derive(rows: list[LedgerEntry]) -> dict[str, Anchor]:
    """All arithmetic on integer minor units; division only at the last step."""
    n = len

    revenue = ledger.total_minor(rows, EntryKind.REVENUE)
    cogs = ledger.total_minor(rows, EntryKind.COGS)
    opex = ledger.total_minor(rows, EntryKind.OPEX)
    marketing = ledger.total_minor(rows, EntryKind.MARKETING_SPEND)
    capex = ledger.total_minor(rows, EntryKind.CAPEX)
    cash_in = ledger.total_minor(rows, EntryKind.CASH_IN)
    cash_out = ledger.total_minor(rows, EntryKind.CASH_OUT)

    acquired = ledger.total_count(rows, EntryKind.CUSTOMER_ACQUIRED)
    churned = ledger.total_count(rows, EntryKind.CUSTOMER_CHURNED)
    breaches = ledger.total_count(rows, EntryKind.SLA_BREACH)
    completed = ledger.total_count(rows, EntryKind.TASK_COMPLETED)

    def count_of(*kinds: EntryKind) -> int:
        wanted = set(kinds)
        return n([e for e in rows if e.kind in wanted])

    gross_profit = revenue - cogs
    net_profit = revenue - cogs - opex - marketing
    cash = cash_in - cash_out

    anchors: dict[str, Anchor] = {
        "revenue": Anchor(
            "revenue", revenue / 100 if count_of(EntryKind.REVENUE) else None,
            "INR", count_of(EntryKind.REVENUE),
        ),
        "cogs": Anchor(
            "cogs", cogs / 100 if count_of(EntryKind.COGS) else None,
            "INR", count_of(EntryKind.COGS),
        ),
        "opex": Anchor(
            "opex", opex / 100 if count_of(EntryKind.OPEX) else None,
            "INR", count_of(EntryKind.OPEX),
        ),
        "marketing_spend": Anchor(
            "marketing_spend",
            marketing / 100 if count_of(EntryKind.MARKETING_SPEND) else None,
            "INR", count_of(EntryKind.MARKETING_SPEND),
        ),
        "capex": Anchor(
            "capex", capex / 100 if count_of(EntryKind.CAPEX) else None,
            "INR", count_of(EntryKind.CAPEX),
        ),
        "cash_balance": Anchor(
            "cash_balance",
            cash / 100 if count_of(EntryKind.CASH_IN, EntryKind.CASH_OUT) else None,
            "INR", count_of(EntryKind.CASH_IN, EntryKind.CASH_OUT),
        ),
        "gross_profit": Anchor(
            "gross_profit",
            gross_profit / 100 if count_of(EntryKind.REVENUE) else None,
            "INR", count_of(EntryKind.REVENUE, EntryKind.COGS),
        ),
        "net_profit": Anchor(
            "net_profit",
            net_profit / 100 if count_of(EntryKind.REVENUE) else None,
            "INR",
            count_of(EntryKind.REVENUE, EntryKind.COGS, EntryKind.OPEX,
                     EntryKind.MARKETING_SPEND),
        ),
        "gross_margin_pct": Anchor(
            "gross_margin_pct", _pct(gross_profit, revenue), "%",
            count_of(EntryKind.REVENUE, EntryKind.COGS),
            note="gross profit over revenue",
        ),
        "net_margin_pct": Anchor(
            "net_margin_pct", _pct(net_profit, revenue), "%",
            count_of(EntryKind.REVENUE, EntryKind.COGS, EntryKind.OPEX,
                     EntryKind.MARKETING_SPEND),
            note="the anchor a marketing proxy is checked against",
        ),
        "customers_acquired": Anchor(
            "customers_acquired",
            float(acquired) if count_of(EntryKind.CUSTOMER_ACQUIRED) else None,
            "count", count_of(EntryKind.CUSTOMER_ACQUIRED),
        ),
        "customers_churned": Anchor(
            "customers_churned",
            float(churned) if count_of(EntryKind.CUSTOMER_CHURNED) else None,
            "count", count_of(EntryKind.CUSTOMER_CHURNED),
        ),
        "customers_active": Anchor(
            "customers_active",
            float(acquired - churned) if count_of(EntryKind.CUSTOMER_ACQUIRED) else None,
            "count",
            count_of(EntryKind.CUSTOMER_ACQUIRED, EntryKind.CUSTOMER_CHURNED),
        ),
        "churn_pct": Anchor(
            "churn_pct", _pct(churned, acquired), "%",
            count_of(EntryKind.CUSTOMER_ACQUIRED, EntryKind.CUSTOMER_CHURNED),
            note="churned over acquired",
        ),
        "retention_pct": Anchor(
            "retention_pct",
            None if acquired == 0 else round((acquired - churned) / acquired * 100, 2),
            "%",
            count_of(EntryKind.CUSTOMER_ACQUIRED, EntryKind.CUSTOMER_CHURNED),
        ),
        "cac": Anchor(
            "cac",
            None if acquired == 0 else round(marketing / acquired / 100, 2),
            "INR", count_of(EntryKind.MARKETING_SPEND, EntryKind.CUSTOMER_ACQUIRED),
            note="marketing spend per customer acquired",
        ),
        "arpc": Anchor(
            "arpc",
            None if acquired == 0 else round(revenue / acquired / 100, 2),
            "INR", count_of(EntryKind.REVENUE, EntryKind.CUSTOMER_ACQUIRED),
            note="average revenue per customer acquired",
        ),
        "sla_breaches": Anchor(
            "sla_breaches",
            float(breaches) if count_of(EntryKind.SLA_BREACH) else None,
            "count", count_of(EntryKind.SLA_BREACH),
        ),
        "tasks_completed": Anchor(
            "tasks_completed",
            float(completed) if count_of(EntryKind.TASK_COMPLETED) else None,
            "count", count_of(EntryKind.TASK_COMPLETED),
        ),
    }
    return anchors


#: The anchors a monitor loop may cite. Exported so a monitor cannot invent a
#: name and have its finding silently ignored.
ANCHOR_NAMES: tuple[str, ...] = tuple(_derive([]).keys())


def read_only_view(company_id: str) -> AnchorSet:
    """The only anchor accessor the agent runtime is given.

    Named for what it is. There is no corresponding writer anywhere in the
    package, and `tests/test_anchors.py` asserts that.
    """
    return AnchorSet.compute(company_id)
