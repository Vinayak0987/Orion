"""Governance — the gate chain every consequential action passes.

    Decision -> Review Queue -> Approval Gate -> Execution Gate -> Audit Trail

Three of those five can halt an action. The audit trail records the passage
regardless of outcome, including the halts, because a governance layer that only
records successes cannot be audited.

Two kinds of rule, deliberately separated
-----------------------------------------
**Policy** is evaluated at the approval gate and is configurable: which spend
threshold needs review, which categories are subjective, who may sign off. These
are business decisions and they change.

**Hard constraints** are evaluated at the execution gate by
`app.operating.constitution`, which is code. They do not change at runtime and no
approval unlocks them.

The distinction matters because collapsing the two would make the Constitution
configurable, and a configurable hard constraint is a policy.

Subjective questions
--------------------
Whether a payment exceeds a threshold is arithmetic. Whether a brand voice is
right, whether a strategy is ethical, whether copy is any good — these are
matters of judgement, and `POLICY.subjective_kinds` routes them to a human by
rule rather than at an agent's discretion. Departments draft; they do not ratify.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.db.sqlite import connection
from app.operating import constitution as C
from app.operating.constitution import (
    ActionKind,
    ConstitutionContext,
    ProposedAction,
    Severity,
)

# --------------------------------------------------------------------- schema --

GOVERNANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id            TEXT PRIMARY KEY,
    company_id    TEXT NOT NULL,
    department    TEXT NOT NULL,
    actor         TEXT NOT NULL,
    action_kind   TEXT NOT NULL,
    amount_minor  INTEGER NOT NULL DEFAULT 0,
    description   TEXT NOT NULL DEFAULT '',
    state         TEXT NOT NULL,
    risk          TEXT NOT NULL,
    reason        TEXT NOT NULL DEFAULT '',
    decided_by    TEXT,
    payload_json  TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_state
    ON decisions(company_id, state, created_at);

CREATE TABLE IF NOT EXISTS audit_trail (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    company_id  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    rule_id     TEXT,
    detail      TEXT NOT NULL DEFAULT '',
    actor       TEXT NOT NULL,
    at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_trail(decision_id, seq);

-- The audit trail is append-only for the same reason the ledger is: a record
-- that can be revised is not a record.
CREATE TRIGGER IF NOT EXISTS audit_is_append_only_no_update
BEFORE UPDATE ON audit_trail
BEGIN
    SELECT RAISE(ABORT, 'audit_trail is append-only: UPDATE is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS audit_is_append_only_no_delete
BEFORE DELETE ON audit_trail
BEGIN
    SELECT RAISE(ABORT, 'audit_trail is append-only: DELETE is not permitted');
END;
"""


def init_governance() -> None:
    """Idempotent."""
    with connection() as conn:
        conn.executescript(GOVERNANCE_SCHEMA)


# ---------------------------------------------------------------------- states --


class DecisionState(StrEnum):
    PROPOSED = "proposed"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"       # refused by a hard constraint
    EXECUTED = "executed"
    RETURNED = "returned"     # sent back for revision


class Risk(StrEnum):
    ROUTINE = "routine"
    ELEVATED = "elevated"
    SUBJECTIVE = "subjective"
    IRREVERSIBLE = "irreversible"


class Stage(StrEnum):
    DECISION = "decision"
    REVIEW_QUEUE = "review_queue"
    APPROVAL_GATE = "approval_gate"
    EXECUTION_GATE = "execution_gate"
    AUDIT = "audit"


#: Legal transitions. Anything else raises, so a decision cannot be executed
#: without having passed through the gates that precede execution.
LEGAL_TRANSITIONS: dict[DecisionState, frozenset[DecisionState]] = {
    DecisionState.PROPOSED: frozenset(
        {DecisionState.PENDING_REVIEW, DecisionState.APPROVED,
         DecisionState.BLOCKED, DecisionState.RETURNED}
    ),
    DecisionState.PENDING_REVIEW: frozenset(
        {DecisionState.APPROVED, DecisionState.REJECTED,
         DecisionState.RETURNED, DecisionState.BLOCKED}
    ),
    DecisionState.APPROVED: frozenset(
        {DecisionState.EXECUTED, DecisionState.BLOCKED}
    ),
    DecisionState.RETURNED: frozenset({DecisionState.PROPOSED}),
    DecisionState.REJECTED: frozenset(),
    DecisionState.BLOCKED: frozenset(),
    DecisionState.EXECUTED: frozenset(),
}


class IllegalTransition(RuntimeError):
    """A decision was moved between states by an unsanctioned path."""


class NotApproved(RuntimeError):
    """Execution was attempted on a decision that had not been approved."""


# ---------------------------------------------------------------------- policy --


@dataclass(frozen=True, slots=True)
class Policy:
    """Configurable review rules. Distinct from the Constitution.

    Changing these changes *what a human is asked about*. It never changes what
    is permitted — that is the Constitution's job and it is not configurable.
    """

    review_above_minor: int = 5_000_00
    subjective_kinds: frozenset[ActionKind] = frozenset(
        {ActionKind.PUBLISH_CLAIM, ActionKind.CHANGE_PRICE, ActionKind.HIRE}
    )
    auto_approve_routine: bool = True

    def classify(self, action: ProposedAction) -> tuple[Risk, str]:
        if action.irreversible:
            return Risk.IRREVERSIBLE, "action cannot be undone once executed"
        if action.kind in self.subjective_kinds:
            return Risk.SUBJECTIVE, (
                "outcome is a matter of judgement, not arithmetic"
            )
        if action.amount_minor > self.review_above_minor:
            return Risk.ELEVATED, (
                f"amount {action.amount:,.2f} exceeds the review threshold of "
                f"{self.review_above_minor / 100:,.2f}"
            )
        return Risk.ROUTINE, "below all review thresholds"


POLICY = Policy()


# -------------------------------------------------------------------- records --


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Decision:
    """One proposal moving through the chain."""

    id: str
    action: ProposedAction
    state: DecisionState
    risk: Risk
    reason: str = ""
    decided_by: str | None = None
    history: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ audit trail --


def record_audit(
    decision_id: str,
    company_id: str,
    stage: Stage,
    outcome: str,
    *,
    actor: str,
    rule_id: str | None = None,
    detail: str = "",
) -> None:
    """Append one immutable audit line. Called on every transition, including halts."""
    with connection() as conn:
        conn.execute(
            "INSERT INTO audit_trail (decision_id, company_id, stage, outcome, "
            "rule_id, detail, actor, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (decision_id, company_id, str(stage), outcome, rule_id, detail,
             actor, _now()),
        )


def audit_for(decision_id: str) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_trail WHERE decision_id = ? ORDER BY seq",
            (decision_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ persistence --


def _persist(decision: Decision) -> None:
    a = decision.action
    with connection() as conn:
        conn.execute(
            "INSERT INTO decisions (id, company_id, department, actor, "
            "action_kind, amount_minor, description, state, risk, reason, "
            "decided_by, payload_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET state=excluded.state, "
            "risk=excluded.risk, reason=excluded.reason, "
            "decided_by=excluded.decided_by, updated_at=excluded.updated_at",
            (
                decision.id, a.company_id, a.department, a.actor,
                str(a.kind), a.amount_minor, a.description,
                str(decision.state), str(decision.risk), decision.reason,
                decision.decided_by,
                json.dumps(a.payload, default=str) if a.payload else None,
                _now(), _now(),
            ),
        )


def get_decision_row(decision_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
    return dict(row) if row else None


def review_queue(company_id: str) -> list[dict]:
    """What a human is being asked to decide, worst risk first."""
    order = {
        str(Risk.IRREVERSIBLE): 0, str(Risk.SUBJECTIVE): 1,
        str(Risk.ELEVATED): 2, str(Risk.ROUTINE): 3,
    }
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE company_id = ? AND state = ? "
            "ORDER BY created_at",
            (company_id, str(DecisionState.PENDING_REVIEW)),
        ).fetchall()
    return sorted((dict(r) for r in rows), key=lambda r: order.get(r["risk"], 9))


# ---------------------------------------------------------------- the gate chain --


def _transition(decision: Decision, new_state: DecisionState) -> None:
    allowed = LEGAL_TRANSITIONS[decision.state]
    if new_state not in allowed:
        raise IllegalTransition(
            f"decision {decision.id} cannot move {decision.state} -> {new_state}. "
            f"Legal next states: {sorted(str(s) for s in allowed) or 'none'}."
        )
    decision.history.append(f"{decision.state}->{new_state}")
    decision.state = new_state


def submit(decision_id: str, action: ProposedAction,
           policy: Policy | None = None) -> Decision:
    """Stage 1-2: create the decision and classify it into the review queue."""
    pol = policy or POLICY
    risk, reason = pol.classify(action)
    decision = Decision(id=decision_id, action=action,
                        state=DecisionState.PROPOSED, risk=risk, reason=reason)
    _persist(decision)
    record_audit(decision_id, action.company_id, Stage.DECISION, "proposed",
                 actor=action.actor, detail=action.description)

    needs_human = risk is not Risk.ROUTINE or not pol.auto_approve_routine
    if needs_human:
        _transition(decision, DecisionState.PENDING_REVIEW)
        record_audit(decision_id, action.company_id, Stage.REVIEW_QUEUE,
                     "queued", actor="governance", detail=f"{risk}: {reason}")
    else:
        _transition(decision, DecisionState.APPROVED)
        decision.decided_by = "policy:auto"
        record_audit(decision_id, action.company_id, Stage.APPROVAL_GATE,
                     "auto-approved", actor="governance", detail=reason)
    _persist(decision)
    return decision


def approve(decision: Decision, *, by: str) -> Decision:
    """Stage 3: a human accepts the decision.

    `by` is required and recorded, so the audit trail names who accepted the
    consequence rather than reporting an anonymous approval.
    """
    if not by or not by.strip():
        raise ValueError("an approval must name the human who gave it")
    _transition(decision, DecisionState.APPROVED)
    decision.decided_by = by.strip()
    _persist(decision)
    record_audit(decision.id, decision.action.company_id, Stage.APPROVAL_GATE,
                 "approved", actor=by.strip())
    return decision


def reject(decision: Decision, *, by: str, reason: str = "") -> Decision:
    if not by or not by.strip():
        raise ValueError("a rejection must name the human who gave it")
    _transition(decision, DecisionState.REJECTED)
    decision.decided_by = by.strip()
    decision.reason = reason or decision.reason
    _persist(decision)
    record_audit(decision.id, decision.action.company_id, Stage.APPROVAL_GATE,
                 "rejected", actor=by.strip(), detail=reason)
    return decision


def return_for_revision(decision: Decision, *, by: str, reason: str) -> Decision:
    _transition(decision, DecisionState.RETURNED)
    decision.reason = reason
    _persist(decision)
    record_audit(decision.id, decision.action.company_id, Stage.REVIEW_QUEUE,
                 "returned", actor=by, detail=reason)
    return decision


def execute(decision: Decision,
            context: ConstitutionContext | None = None) -> Decision:
    """Stage 4-5: the execution gate.

    Two conditions, in order. The decision must be APPROVED, and the action must
    satisfy every hard constraint. The second check happens here rather than at
    proposal time because the facts it depends on — spend to date, cash — move
    while a decision waits in the queue.
    """
    if decision.state is not DecisionState.APPROVED:
        record_audit(decision.id, decision.action.company_id,
                     Stage.EXECUTION_GATE, "refused", actor="governance",
                     detail=f"state was {decision.state}, not approved")
        raise NotApproved(
            f"decision {decision.id} is {decision.state}; only an APPROVED "
            f"decision may execute"
        )

    verdict = C.check(decision.action, context)
    if verdict.blocked:
        _transition(decision, DecisionState.BLOCKED)
        decision.reason = verdict.reason
        _persist(decision)
        record_audit(decision.id, decision.action.company_id,
                     Stage.EXECUTION_GATE, "blocked", actor="constitution",
                     rule_id=verdict.rule_id, detail=verdict.reason)
        raise C.ConstitutionViolation(verdict)

    _transition(decision, DecisionState.EXECUTED)
    _persist(decision)
    record_audit(decision.id, decision.action.company_id, Stage.EXECUTION_GATE,
                 "executed", actor=decision.action.actor)
    record_audit(decision.id, decision.action.company_id, Stage.AUDIT,
                 "recorded", actor="governance")
    return decision


# ------------------------------------------------------------------- reporting --


def load_size() -> dict[str, int]:
    """Human decision load, for the RQ that asks whether governance is tractable."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT state, risk, COUNT(*) AS n FROM decisions GROUP BY state, risk"
        ).fetchall()
    out: dict[str, int] = {}
    for row in rows:
        out[f"{row['state']}:{row['risk']}"] = int(row["n"])
    return out


def describe_chain() -> list[dict[str, str]]:
    return [
        {"stage": str(Stage.DECISION), "can_halt": "no",
         "note": "a department proposes an action"},
        {"stage": str(Stage.REVIEW_QUEUE), "can_halt": "yes",
         "note": "classified by risk; may be returned for revision"},
        {"stage": str(Stage.APPROVAL_GATE), "can_halt": "yes",
         "note": "configurable policy; a human may reject"},
        {"stage": str(Stage.EXECUTION_GATE), "can_halt": "yes",
         "note": "hard constraints in code; no approval unlocks them"},
        {"stage": str(Stage.AUDIT), "can_halt": "no",
         "note": "append-only record of the passage, including halts"},
    ]
