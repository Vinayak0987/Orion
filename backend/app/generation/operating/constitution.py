"""The Constitution — hard constraints enforced in the call path.

PAPER.md §4.4 records a finding this module exists to act on:

    The market-sizing prompt included an explicit numeric sanity range and the
    revenue prompt stated that year-1 revenue must not exceed the obtainable
    market. Both were ignored repeatedly. In a multi-agent system, cross-agent
    constraints must be enforced in code, not requested in prose.

That finding was about arithmetic inside one generation run. Under continuous
operation the same problem appears with consequences: a spend cap stated in a
prompt is a request that a sufficiently confident model will occasionally reason
past, and the result is money.

So the Constitution is not described to the departments. It is a set of
predicates evaluated at the execution gate, and an action that fails one does not
run. There is no prompt phrasing, no confidence score and no justification that
changes the outcome.

Two properties distinguish it from ordinary policy
--------------------------------------------------
* **Rules are code, not data.** They are defined in this module, not loaded from
  the database, so an agent that can write to the database still cannot add,
  remove or weaken one.
* **Amendment requires a human.** `amend()` demands an explicit signature and
  records the change. Nothing in the agent runtime calls it, and a test asserts
  that.

Policy rules that *should* be configurable — which spend threshold requires
review, who signs off — belong in the governance layer, not here. The
distinction is deliberate: policy changes with the business, the Constitution
does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable

from app.generation.operating.ledger import EntryKind

# --------------------------------------------------------------------- actions --


class ActionKind(StrEnum):
    """What a department is proposing to do."""

    SPEND = "spend"
    PUBLISH_CLAIM = "publish_claim"
    DELETE_CUSTOMER_DATA = "delete_customer_data"
    ISSUE_PAYMENT = "issue_payment"
    CHANGE_PRICE = "change_price"
    HIRE = "hire"
    SIGN_CONTRACT = "sign_contract"
    APPEND_LEDGER = "append_ledger"
    UPDATE_PLAYBOOK = "update_playbook"


#: Actions that cannot be undone once executed. These require approval by rule,
#: independent of amount.
IRREVERSIBLE: frozenset[ActionKind] = frozenset(
    {
        ActionKind.DELETE_CUSTOMER_DATA,
        ActionKind.ISSUE_PAYMENT,
        ActionKind.SIGN_CONTRACT,
        ActionKind.PUBLISH_CLAIM,
    }
)


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """An action awaiting the execution gate.

    Frozen: the gate must judge exactly what was proposed. A mutable action
    could be altered between evaluation and execution, which would make the
    verdict meaningless.
    """

    kind: ActionKind
    department: str
    actor: str
    company_id: str
    amount_minor: int = 0
    currency: str = "INR"
    description: str = ""
    approved_by: str | None = None
    verified: bool = False
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def irreversible(self) -> bool:
        return self.kind in IRREVERSIBLE

    @property
    def amount(self) -> float:
        return self.amount_minor / 100


# ----------------------------------------------------------------------- rules --


class Severity(StrEnum):
    BLOCK = "block"        # the action does not run
    REQUIRE_HUMAN = "require_human"  # it runs only with a recorded approval


@dataclass(frozen=True, slots=True)
class Verdict:
    """Why an action was permitted or refused."""

    allowed: bool
    rule_id: str | None = None
    severity: Severity | None = None
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return not self.allowed


@dataclass(frozen=True, slots=True)
class Rule:
    """One constraint.

    `applies` selects the actions a rule judges; `violated` decides. Both are
    plain functions, so a rule is testable in isolation and cannot be influenced
    by anything a model emits.
    """

    id: str
    description: str
    severity: Severity
    applies: Callable[[ProposedAction, "ConstitutionContext"], bool]
    violated: Callable[[ProposedAction, "ConstitutionContext"], bool]
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class ConstitutionContext:
    """Facts the rules need, all measured rather than asserted.

    `spent_today_minor` comes from the ledger, not from a department's report of
    what it has spent — which is the whole point.
    """

    daily_spend_cap_minor: int = 10_000_00      # ₹10,000/day
    single_spend_cap_minor: int = 50_000_00     # ₹50,000 in one action
    spent_today_minor: int = 0
    cash_balance_minor: int | None = None

    def remaining_today_minor(self) -> int:
        return max(0, self.daily_spend_cap_minor - self.spent_today_minor)


class ConstitutionViolation(RuntimeError):
    """An action was refused by a hard constraint."""

    def __init__(self, verdict: Verdict) -> None:
        super().__init__(f"[{verdict.rule_id}] {verdict.reason}")
        self.verdict = verdict


# ------------------------------------------------------------------ the rules --

def _is_spend(action: ProposedAction, _ctx: ConstitutionContext) -> bool:
    return action.kind in (ActionKind.SPEND, ActionKind.ISSUE_PAYMENT)


RULES: tuple[Rule, ...] = (
    Rule(
        id="C1_DAILY_SPEND_CAP",
        description="Cumulative spend in a day may not exceed the daily cap.",
        severity=Severity.BLOCK,
        applies=_is_spend,
        violated=lambda a, c: (
            c.spent_today_minor + a.amount_minor > c.daily_spend_cap_minor
        ),
        rationale=(
            "An unbounded spend loop can exhaust a budget faster than a human "
            "reviews it. The cap is arithmetic on figures from the ledger."
        ),
    ),
    Rule(
        id="C2_SINGLE_SPEND_CAP",
        description="No single action may exceed the per-action spend cap.",
        severity=Severity.BLOCK,
        applies=_is_spend,
        violated=lambda a, c: a.amount_minor > c.single_spend_cap_minor,
        rationale="Bounds the worst single mistake independently of the daily total.",
    ),
    Rule(
        id="C3_NO_OVERDRAFT",
        description="Spend may not exceed the measured cash balance.",
        severity=Severity.BLOCK,
        applies=lambda a, c: _is_spend(a, c) and c.cash_balance_minor is not None,
        violated=lambda a, c: a.amount_minor > (c.cash_balance_minor or 0),
        rationale=(
            "Cash is derived from the ledger, so this cannot be satisfied by a "
            "department asserting it has funds."
        ),
    ),
    Rule(
        id="C4_NO_CUSTOMER_DATA_DELETION",
        description="Customer data is never deleted by an autonomous action.",
        severity=Severity.BLOCK,
        applies=lambda a, _c: a.kind is ActionKind.DELETE_CUSTOMER_DATA,
        violated=lambda _a, _c: True,
        rationale=(
            "Unconditional. There is no amount, approval or justification that "
            "permits it, because the loss is not recoverable."
        ),
    ),
    Rule(
        id="C5_PAYMENT_REQUIRES_VERIFICATION",
        description="A payment must carry verification before it is issued.",
        severity=Severity.BLOCK,
        applies=lambda a, _c: a.kind is ActionKind.ISSUE_PAYMENT,
        violated=lambda a, _c: not a.verified,
        rationale="Verification is a precondition, not a step an agent may skip.",
    ),
    Rule(
        id="C6_IRREVERSIBLE_REQUIRES_APPROVAL",
        description="An irreversible action requires a recorded human approval.",
        severity=Severity.REQUIRE_HUMAN,
        applies=lambda a, _c: a.irreversible,
        violated=lambda a, _c: not a.approved_by,
        rationale=(
            "The approval is recorded as an identity, so the audit trail names "
            "who accepted the consequence."
        ),
    ),
    Rule(
        id="C7_LEDGER_APPEND_MUST_BE_ATTRIBUTED",
        description="A ledger append must name its department and actor.",
        severity=Severity.BLOCK,
        applies=lambda a, _c: a.kind is ActionKind.APPEND_LEDGER,
        violated=lambda a, _c: not (a.department.strip() and a.actor.strip()),
        rationale=(
            "Anchors are only as traceable as the entries beneath them. An "
            "unattributed entry cannot be checked against the work that caused it."
        ),
    ),
)

#: Rule ids, exported so governance can reference one without inventing a name.
RULE_IDS: tuple[str, ...] = tuple(r.id for r in RULES)


# ------------------------------------------------------------------ evaluation --


def evaluate(
    action: ProposedAction, context: ConstitutionContext | None = None
) -> list[Verdict]:
    """Every verdict for one action, in rule order. Pure; no I/O."""
    ctx = context or ConstitutionContext()
    verdicts: list[Verdict] = []
    for rule in RULES:
        if not rule.applies(action, ctx):
            continue
        if rule.violated(action, ctx):
            verdicts.append(
                Verdict(
                    allowed=False,
                    rule_id=rule.id,
                    severity=rule.severity,
                    reason=rule.description,
                )
            )
    return verdicts


def check(
    action: ProposedAction, context: ConstitutionContext | None = None
) -> Verdict:
    """The single verdict the execution gate acts on.

    Returns the first refusal, preferring BLOCK over REQUIRE_HUMAN so the most
    serious reason is the one reported.
    """
    verdicts = evaluate(action, context)
    if not verdicts:
        return Verdict(allowed=True, reason="no constraint applies")
    blocking = [v for v in verdicts if v.severity is Severity.BLOCK]
    return (blocking or verdicts)[0]


def enforce(
    action: ProposedAction, context: ConstitutionContext | None = None
) -> None:
    """Raise unless the action is permitted. The execution gate calls this.

    Deliberately returns nothing: there is no truthy value a caller could
    mistakenly ignore.
    """
    verdict = check(action, context)
    if verdict.blocked:
        raise ConstitutionViolation(verdict)


def context_from_ledger(
    company_id: str, *, day: str | None = None, **overrides: Any
) -> ConstitutionContext:
    """Build a context from measured facts.

    Spend-to-date and cash come from the ledger. A department cannot influence
    them except by actually spending, which is recorded.
    """
    from app.generation.operating import ledger as ledger_module

    today = day or datetime.now(UTC).date().isoformat()
    entries = ledger_module.read(company_id)

    spent = sum(
        e.amount_minor
        for e in entries
        if e.kind in (EntryKind.OPEX, EntryKind.MARKETING_SPEND, EntryKind.CAPEX)
        and e.occurred_at.startswith(today)
    )
    cash_in = ledger_module.total_minor(entries, EntryKind.CASH_IN)
    cash_out = ledger_module.total_minor(entries, EntryKind.CASH_OUT)
    has_cash_entries = any(
        e.kind in (EntryKind.CASH_IN, EntryKind.CASH_OUT) for e in entries
    )

    defaults: dict[str, Any] = {
        "spent_today_minor": spent,
        "cash_balance_minor": (cash_in - cash_out) if has_cash_entries else None,
    }
    defaults.update(overrides)
    return ConstitutionContext(**defaults)


# ------------------------------------------------------------------ amendment --


class UnsignedAmendment(RuntimeError):
    """An attempt to change the Constitution without a human signature."""


def amend(*, signed_by: str, rationale: str) -> None:
    """Placeholder for the only sanctioned amendment path.

    The Constitution is code, so a real amendment is a reviewed change to this
    module. This function exists to make that explicit and to give the
    architecture a test: nothing in the agent runtime may call it.
    """
    if not signed_by or not signed_by.strip():
        raise UnsignedAmendment(
            "Amending the Constitution requires a named human signatory. "
            "Rules are code: edit app/operating/constitution.py under review."
        )
    if not rationale or not rationale.strip():
        raise UnsignedAmendment("An amendment requires a recorded rationale.")
    raise UnsignedAmendment(
        "The Constitution cannot be amended at runtime. Change the module, have "
        f"the change reviewed, and record that {signed_by.strip()} signed it."
    )


def describe() -> list[dict[str, str]]:
    """Human-readable rule list, for the interface and the audit trail."""
    return [
        {
            "id": r.id,
            "severity": str(r.severity),
            "description": r.description,
            "rationale": r.rationale,
        }
        for r in RULES
    ]
