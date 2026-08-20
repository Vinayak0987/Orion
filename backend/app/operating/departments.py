# Department operating loops - the thing the scheduler drives.
#
# One tick of a department:
#
#     read anchors -> retrieve own memory -> plan -> submit decisions
#                  -> execute what governance approved -> record outcomes
#                  -> write episodic memory
#
# That sequence is the operating layer assembled. Everything it touches already
# exists and is tested in isolation; this module is what makes a department act
# without being asked.
#
# The planner is deliberately rule-based
# --------------------------------------
# `plan` maps an objective and the department's memory onto candidate tasks using
# declared rules, not an LLM call. Three reasons:
#
#   * The suite stays offline and deterministic, so a department tick can be
#     tested at the same density as everything else.
#   * The ablation for RQ4 to RQ7 varies control topology. If planning were
#     non-deterministic, run-to-run variance in the planner would confound the
#     comparison - which is precisely the effect PAPER.md section 7.2 measured.
#   * A rule-based planner makes governance and monitor behaviour observable
#     without inference cost on every tick.
#
# LLM-backed planning is a later substitution behind the same Planner protocol.
# It is NOT wired, and docs/OPERATING_LAYER.md says so. What is claimed here is
# that the loop runs, gates correctly and records honestly - not that the
# planning is intelligent.
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.operating import governance as G
from app.operating import ledger as ledger_module
from app.operating import memory as memory_module
from app.operating.anchors import AnchorSet
from app.operating.constitution import (
    ActionKind,
    ConstitutionContext,
    ProposedAction,
    context_from_ledger,
)
from app.operating.governance import DecisionState
from app.operating.ledger import EntryKind, LedgerEntry
from app.operating.memory import Memory, MemoryType


@dataclass(frozen=True, slots=True)
class Task:
    # One unit of proposed work.
    #
    # `effects` declares the ledger entries the task produces if it executes.
    # Declaring the effect up front is what lets the outcome be checked against
    # the intent rather than inferred afterwards.
    task_id: str
    department: str
    description: str
    action_kind: ActionKind
    amount_minor: int = 0
    effects: tuple[tuple[EntryKind, int, int], ...] = ()
    serves_anchor: str = "net_margin_pct"


@dataclass(frozen=True, slots=True)
class DepartmentProfile:
    # A department's standing remit.
    #
    # `proxy_metric` is what the department watches day to day; `serves_anchor`
    # is the real quantity it is accountable for. Naming both is what makes proxy
    # capture detectable - the monitor compares one against the other. A profile
    # that named only a proxy would make capture invisible.
    name: str
    objective: str
    proxy_metric: str
    serves_anchor: str
    task_budget_minor: int = 20_000_00


PROFILES: dict[str, DepartmentProfile] = {
    "strategy": DepartmentProfile(
        "strategy", "keep positioning matched to the market",
        proxy_metric="competitor_set_size", serves_anchor="gross_margin_pct",
        task_budget_minor=5_000_00),
    "finance": DepartmentProfile(
        "finance", "protect margin and runway",
        proxy_metric="cost_reduction_pct", serves_anchor="net_margin_pct",
        task_budget_minor=10_000_00),
    "branding": DepartmentProfile(
        "branding", "keep the brand recognisable and consistent",
        proxy_metric="asset_count", serves_anchor="arpc",
        task_budget_minor=5_000_00),
    "marketing": DepartmentProfile(
        "marketing", "acquire customers who stay",
        proxy_metric="customers_acquired", serves_anchor="net_margin_pct",
        task_budget_minor=20_000_00),
    "operations": DepartmentProfile(
        "operations", "deliver reliably at planned cost",
        proxy_metric="tasks_completed", serves_anchor="sla_breaches",
        task_budget_minor=15_000_00),
}

# Phrases in a reflective memory that argue against further discretionary spend.
# Kept explicit rather than inferred, so the branch is inspectable and testable.
SPEND_WARNINGS: tuple[str, ...] = (
    "cut margin", "does not retain", "margin fell", "churn rose",
    "acquisition cost rose",
)


class Planner(Protocol):
    def __call__(self, profile: DepartmentProfile, anchors: AnchorSet,
                 memories: list[dict], tick: datetime) -> list[Task]: ...


def retrieval_query(profile: DepartmentProfile) -> str:
    # What a department asks its own memory for at the start of a tick.
    #
    # Includes `serves_anchor` deliberately. Retrieval is lexical token overlap:
    # memory.py `_score` returns 0.0 when overlap is 0 and `retrieve` drops
    # anything scoring 0. Reflection phrases its lessons in ANCHOR vocabulary
    # ("net margin fell over the period..."), so a query built only from the
    # objective and the proxy shares no tokens with them and the lesson is
    # discarded before the planner sees it.
    #
    # That was a real defect: the spend-suppression branch below is unit-tested by
    # passing a memory dict in directly, but was unreachable end to end. It was
    # found by running the ablation sweep, in which all four arms produced
    # byte-identical outcomes because no arm's memory could alter behaviour.
    # `tests/test_departments.py::test_memory_alone_changes_the_plan_while_the_
    # anchor_stays_healthy` pins it.
    #
    # Extracted as a function so tests exercise the production query rather than
    # a query they construct themselves.
    return " ".join((profile.objective, profile.proxy_metric,
                     profile.serves_anchor))


def _warned_against_spend(memories: list[dict]) -> bool:
    for m in memories:
        if m.get("memory_type") != str(MemoryType.REFLECTIVE):
            continue
        content = (m.get("content") or "").lower()
        if any(w in content for w in SPEND_WARNINGS):
            return True
    return False


def _anchor_unhealthy(profile: DepartmentProfile, anchors: AnchorSet) -> bool:
    value = anchors.value(profile.serves_anchor)
    if value is None:
        return False
    if profile.serves_anchor in ("sla_breaches", "churn_pct", "cac"):
        return value > 0
    return value < 10.0


def rule_based_planner(profile: DepartmentProfile, anchors: AnchorSet,
                       memories: list[dict], tick: datetime) -> list[Task]:
    # Propose work from the anchor state and what the department remembers.
    #
    # Two behaviours matter, because they are the ones the monitors observe:
    #
    #   * When the anchor a department serves is unhealthy it proposes corrective
    #     work rather than more of the same.
    #   * A reflective memory warning against spend suppresses the spend task.
    #     This is the only place memory changes behaviour, and it is what makes
    #     "the department learned something" a checkable claim rather than a
    #     narrative.
    stamp = tick.strftime("%Y%m%d")
    warned = _warned_against_spend(memories)
    unhealthy = _anchor_unhealthy(profile, anchors)
    tasks: list[Task] = []

    if profile.name == "marketing":
        if warned or unhealthy:
            tasks.append(Task(
                task_id="marketing-" + stamp + "-retain",
                department="marketing",
                description="retention work: contact lapsed customers, no discount",
                action_kind=ActionKind.UPDATE_PLAYBOOK,
                serves_anchor=profile.serves_anchor,
                effects=((EntryKind.TASK_COMPLETED, 0, 1),)))
        else:
            spend = min(4_000_00, profile.task_budget_minor)
            tasks.append(Task(
                task_id="marketing-" + stamp + "-acquire",
                department="marketing",
                description="run an acquisition campaign",
                action_kind=ActionKind.SPEND,
                amount_minor=spend,
                serves_anchor=profile.serves_anchor,
                effects=((EntryKind.MARKETING_SPEND, spend, 0),
                         (EntryKind.CUSTOMER_ACQUIRED, 0, 8),
                         (EntryKind.TASK_COMPLETED, 0, 1))))

    elif profile.name == "operations":
        spend = min(2_000_00, profile.task_budget_minor)
        tasks.append(Task(
            task_id="operations-" + stamp + "-fulfil",
            department="operations",
            description="fulfil the period's orders",
            action_kind=ActionKind.SPEND,
            amount_minor=spend,
            serves_anchor=profile.serves_anchor,
            effects=((EntryKind.OPEX, spend, 0),
                     (EntryKind.TASK_COMPLETED, 0, 1))))

    elif profile.name == "finance":
        tasks.append(Task(
            task_id="finance-" + stamp + "-reconcile",
            department="finance",
            description="reconcile the cost base against the ledger",
            action_kind=ActionKind.UPDATE_PLAYBOOK,
            serves_anchor=profile.serves_anchor,
            effects=((EntryKind.TASK_COMPLETED, 0, 1),)))

    else:  # strategy, branding
        tasks.append(Task(
            task_id=profile.name + "-" + stamp + "-review",
            department=profile.name,
            description="review " + profile.objective,
            action_kind=ActionKind.UPDATE_PLAYBOOK,
            serves_anchor=profile.serves_anchor,
            effects=((EntryKind.TASK_COMPLETED, 0, 1),)))

    return tasks


@dataclass
class TickResult:
    # What one department tick did. Returned to the scheduler run log.
    department: str
    anchors_read: int = 0
    memories_retrieved: int = 0
    tasks_planned: int = 0
    submitted: int = 0
    executed: int = 0
    blocked: int = 0
    awaiting_review: int = 0
    ledger_entries: int = 0
    memories_written: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "department": self.department,
            "anchors_read": self.anchors_read,
            "memories_retrieved": self.memories_retrieved,
            "tasks_planned": self.tasks_planned,
            "submitted": self.submitted,
            "executed": self.executed,
            "blocked": self.blocked,
            "awaiting_review": self.awaiting_review,
            "ledger_entries": self.ledger_entries,
            "memories_written": self.memories_written,
            "notes": self.notes,
        }


def run_tick(company_id: str, department: str, tick: datetime, *,
             planner: Planner = rule_based_planner,
             context: ConstitutionContext | None = None) -> TickResult:
    # One department tick, end to end.
    #
    # A governance refusal is a normal recorded outcome, not an exception: a
    # blocked or queued task is counted and the tick continues. Only genuine
    # exceptions reach the scheduler's isolation, so one gated task never looks
    # like a crashed department.
    profile = PROFILES.get(department)
    if profile is None:
        raise ValueError("unknown department " + repr(department))

    result = TickResult(department=department)

    anchors = AnchorSet.compute(company_id)
    result.anchors_read = len(anchors.computable())

    # The retrieval query must include the anchor the department is accountable
    # for; see `retrieval_query` for why, and for the defect it fixes.
    query = retrieval_query(profile)
    memories = memory_module.retrieve(
        company_id, department, query, limit=5, now=tick)
    result.memories_retrieved = len(memories)

    tasks = planner(profile, anchors, memories, tick)
    result.tasks_planned = len(tasks)

    ctx = context or context_from_ledger(company_id, day=tick.date().isoformat())

    for task in tasks:
        action = ProposedAction(
            kind=task.action_kind,
            department=department,
            actor=department + "_planner",
            company_id=company_id,
            amount_minor=task.amount_minor,
            description=task.description,
            payload={"task_id": task.task_id,
                     "serves_anchor": task.serves_anchor})
        decision = G.submit(task.task_id, action)
        result.submitted += 1

        if decision.state is DecisionState.PENDING_REVIEW:
            result.awaiting_review += 1
            result.notes.append(task.task_id + ": queued for review")
            continue

        try:
            G.execute(decision, ctx)
        except Exception as exc:
            result.blocked += 1
            result.notes.append(task.task_id + ": " + type(exc).__name__)
            continue

        result.executed += 1
        for kind, amount, quantity in task.effects:
            ledger_module.append(LedgerEntry(
                company_id=company_id, kind=kind, department=department,
                actor=department + "_worker", amount_minor=amount,
                quantity=quantity, occurred_at=tick.isoformat(),
                memo=task.description, ref={"task_id": task.task_id}))
            result.ledger_entries += 1

        memory_module.write(Memory(
            company_id=company_id, department=department,
            memory_type=MemoryType.EPISODIC,
            content=task.description + " (task " + task.task_id + ")",
            confidence=0.6,
            meta={"task_id": task.task_id, "tick": tick.isoformat()}))
        result.memories_written += 1

    return result


def make_handler(department: str, *, planner: Planner = rule_based_planner):
    # Adapt a department tick into a scheduler handler.
    def handler(company_id: str, now: datetime) -> dict:
        return run_tick(company_id, department, now, planner=planner).as_dict()
    return handler


def register_all(scheduler, *, planner: Planner = rule_based_planner) -> list[str]:
    # Register every implemented department with a scheduler.
    #
    # A department in PROFILES with no corresponding loop in the graph is skipped
    # rather than raising, so a partial topology stays usable.
    wired = []
    for name in PROFILES:
        if name in scheduler.graph.loops:
            scheduler.register_handler(name, make_handler(name, planner=planner))
            wired.append(name)
    return wired
