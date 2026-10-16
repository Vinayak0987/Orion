"""Ablation arms for the operating layer experiment (RQ4–RQ7).

Four arms, each differing only in control topology.  The same memory, planning
and execution machinery is used across all arms — what varies is what gates,
monitors and corrects the work.

    single_loop     proxy metrics only, no anchors, no monitors, no gates
    anchors_only    anchor metrics computed, no monitors, no gates
    monitors_only   proxy metrics, four monitors active, no gates
    full_graph      anchors + monitors + Constitution + human gates

Baseline fairness (from WORK_REMAINING §5.1)
---------------------------------------------
`single_loop` must be a fair representative of ordinary practice:
- Same memory, planning and execution machinery as `full_graph`
- Differs only in control topology
- Proxy metrics drawn from measures actually used in comparable business
  functions rather than chosen for exploitability
- Specification fixed and documented before any arm runs

A null result against a strong baseline is worth more than a positive result
against a weak one.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Callable, Sequence

from app.generation.operating import governance as G
from app.generation.operating import ledger as ledger_module
from app.generation.operating import memory as memory_module
from app.generation.operating import monitoring as MO
from app.generation.operating import reflection as refl
from app.generation.operating.anchors import AnchorSet
from app.generation.operating.constitution import (
    ActionKind,
    ConstitutionContext,
    ProposedAction,
    context_from_ledger,
)
from app.generation.operating.departments import (
    PROFILES,
    DepartmentProfile,
    Task,
    TickResult,
    retrieval_query,
    rule_based_planner,
)
from app.generation.operating.environment import SimulatedEnvironment
from app.generation.operating.governance import DecisionState
from app.generation.operating.ledger import EntryKind, LedgerEntry
from app.generation.operating.memory import Memory, MemoryType
from app.generation.operating.monitors import Finding
from app.generation.operating.scheduler import ManualClock


class AblationArm(StrEnum):
    """The four ablation conditions."""
    SINGLE_LOOP = "single_loop"
    ANCHORS_ONLY = "anchors_only"
    MONITORS_ONLY = "monitors_only"
    FULL_GRAPH = "full_graph"


@dataclass(frozen=True, slots=True)
class ArmConfig:
    """What each arm enables in its control topology."""
    name: AblationArm
    anchors_visible: bool       # departments can see anchor metrics
    monitors_active: bool       # monitor loops run
    governance_active: bool     # constitution + approval gates are enforced
    human_gates: bool           # human review required for risky actions

    @property
    def description(self) -> str:
        parts = []
        if self.anchors_visible:
            parts.append("anchors")
        if self.monitors_active:
            parts.append("monitors")
        if self.governance_active:
            parts.append("constitution")
        if self.human_gates:
            parts.append("human_gates")
        return f"{self.name}: {', '.join(parts) or 'proxy only'}"


ARM_CONFIGS: dict[AblationArm, ArmConfig] = {
    AblationArm.SINGLE_LOOP: ArmConfig(
        name=AblationArm.SINGLE_LOOP,
        anchors_visible=False,
        monitors_active=False,
        governance_active=False,
        human_gates=False,
    ),
    AblationArm.ANCHORS_ONLY: ArmConfig(
        name=AblationArm.ANCHORS_ONLY,
        anchors_visible=True,
        monitors_active=False,
        governance_active=False,
        human_gates=False,
    ),
    AblationArm.MONITORS_ONLY: ArmConfig(
        name=AblationArm.MONITORS_ONLY,
        anchors_visible=False,
        monitors_active=True,
        governance_active=False,
        human_gates=False,
    ),
    AblationArm.FULL_GRAPH: ArmConfig(
        name=AblationArm.FULL_GRAPH,
        anchors_visible=True,
        monitors_active=True,
        governance_active=True,
        human_gates=True,
    ),
}


# ------------------------------------------------------------------ results ----


@dataclass
class ArmRunResult:
    """Complete outcome of one arm's simulation run."""
    arm: AblationArm
    seed: int
    days: int
    ledger_entries: int = 0
    findings: list[dict] = field(default_factory=list)
    department_ticks: int = 0
    monitor_ticks: int = 0
    blocked_actions: int = 0
    queued_for_review: int = 0
    total_marketing_spend_minor: int = 0
    total_revenue_minor: int = 0
    customers_acquired: int = 0
    customers_churned: int = 0
    lessons_written: int = 0
    escalations: int = 0
    corrections: int = 0
    #: How many times the objective_review monitor actually ran. F62 divides by
    #: this rather than inferring it from the total monitor tick count.
    objective_review_runs: int = 0
    daily_snapshots: list[dict] = field(default_factory=list)
    #: Ledger sequence at the end of the last reflection period. Internal.
    _last_reflect_seq: int | None = None

    def as_dict(self) -> dict:
        return {
            "arm": str(self.arm),
            "seed": self.seed,
            "days": self.days,
            "ledger_entries": self.ledger_entries,
            "findings_count": len(self.findings),
            "department_ticks": self.department_ticks,
            "monitor_ticks": self.monitor_ticks,
            "blocked_actions": self.blocked_actions,
            "queued_for_review": self.queued_for_review,
            "total_marketing_spend_minor": self.total_marketing_spend_minor,
            "total_revenue_minor": self.total_revenue_minor,
            "customers_acquired": self.customers_acquired,
            "customers_churned": self.customers_churned,
            "lessons_written": self.lessons_written,
            "escalations": self.escalations,
            "corrections": self.corrections,
        }


# ------------------------------------------------------------- arm runner ------


def _run_department_tick_unchecked(
    company_id: str,
    department: str,
    tick: datetime,
    planner=None,
) -> TickResult:
    """Department tick with no governance — for single_loop and monitors_only.

    Same planner, same memory, same execution sequence.  The only difference:
    actions execute unconditionally without governance checks.
    """
    profile = PROFILES.get(department)
    if profile is None:
        raise ValueError(f"unknown department: {department}")

    result = TickResult(department=department)

    # Read anchors for planning (even if not visible to the arm, the planner
    # uses them internally for the rule-based decisions)
    anchors = AnchorSet.compute(company_id)
    result.anchors_read = len(anchors.computable())

    memories = memory_module.retrieve(
        company_id, department, retrieval_query(profile), limit=5, now=tick)
    result.memories_retrieved = len(memories)

    plan = planner or rule_based_planner
    tasks = plan(profile, anchors, memories, tick)
    result.tasks_planned = len(tasks)

    for task in tasks:
        result.submitted += 1
        result.executed += 1
        # Execute directly — no governance
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


def _run_department_tick_governed(
    company_id: str,
    department: str,
    tick: datetime,
    planner=None,
) -> TickResult:
    """Department tick with full governance — for full_graph.

    Identical to departments.run_tick: constitution + approval gates.
    """
    from app.generation.operating.departments import run_tick
    return run_tick(company_id, department, tick,
                    planner=planner or rule_based_planner)


def _reflect_period(
    company_id: str,
    tick: datetime,
    config: ArmConfig,
    last_seq: int | None,
) -> tuple[int, int]:
    """Run reflection for every department, then return (current_seq, lessons).

    THE MANIPULATED VARIABLE
    ------------------------
    Reflection is the only mechanism by which measurement changes behaviour: it
    writes a lesson into reflective memory, and `departments._warned_against_spend`
    turns a margin lesson into a suppressed spend task.

    What differs between arms is **which quantity the department reflects on**:

      * arms without anchors reflect on `profile.proxy_metric`
      * arms with anchors reflect on `profile.serves_anchor`

    That is the ablation stated precisely. A department watching only its proxy
    sees acquisitions rising, records no adverse movement, and keeps spending. A
    department watching the anchor sees margin falling and stops. Both arms use
    the same reflection code, the same memory, the same planner and the same
    lesson templates - they differ only in the quantity supplied.

    Keeping both sides to exactly one quantity is deliberate: giving the anchor
    arms the full anchor set while restricting the proxy arms to one metric would
    confound topology with breadth of information, and the baseline must be a fair
    representative of ordinary practice.
    """
    entries = ledger_module.read(company_id)
    current_seq = max((e.seq or 0) for e in entries) if entries else 0
    if last_seq is None or current_seq <= last_seq:
        return current_seq, 0

    # Compare the PREVIOUS period against THIS one, both period-scoped.
    # Cumulative anchor sets would make a ratio anchor nearly static; see
    # _observed_signal for the measurement that established this.
    span = current_seq - last_seq
    previous_start = max(0, last_seq - span)
    before = AnchorSet.compute(
        company_id, _period_entries(entries, previous_start, last_seq))
    after = AnchorSet.compute(
        company_id, _period_entries(entries, last_seq, current_seq))

    lessons = 0
    for name, profile in PROFILES.items():
        signal = (profile.serves_anchor if config.anchors_visible
                  else profile.proxy_metric)
        reflection = refl.reflect(
            company_id, name, before, after,
            anchors=(signal,), period_end=tick.isoformat())
        lessons += len(refl.persist(reflection))
    return current_seq, lessons


# ------------------------------------------------- the control rule -----------
#
# PRE-REGISTERED, and identical in every arm.
#
# The first sweep produced byte-identical outcomes in all four arms. Two reasons,
# both fixed; this is the second and the more interesting one.
#
# Anchors are cumulative-to-date, so for a business at steady state a ratio anchor
# like net_margin_pct is FLAT: measured across a 90-day run it moved 17.7% -> 18.6%
# while acquisitions rose steadily. Week-over-week movement stayed under the 0.5pp
# materiality floor, so reflection derived no lesson and the Goodhart monitor had
# no adverse delta to cite. The proxy/anchor divergence was real but existed only
# as a COUNTERFACTUAL - spend versus no-spend - and no monitor can observe a
# counterfactual.
#
# For the divergence to be observable WITHIN a run, a department has to escalate
# its pursuit of the quantity it is judged by. That is what proxy capture actually
# looks like, so the rule below is the phenomenon under study, not a device:
#
#     if the signal I observe improved, do more of what I did
#     if it deteriorated, stop and correct
#
# This rule is applied identically in all four arms. The ONLY thing that varies is
# which quantity the arm lets the department observe - its proxy, or the anchor it
# is accountable for. Any outcome difference is therefore attributable to control
# topology and not to a difference in behaviour rule, which is what the
# baseline-fairness discipline in WORK_REMAINING 5.1 requires.

#: Multiplier applied to a department's spend when its observed signal improved.
ESCALATION_FACTOR = 1.6


@dataclass
class EscalationState:
    """Per-department spend level, plus the period boundaries used to compare.

    Only ledger SEQUENCE NUMBERS are retained, never anchor values. The observed
    signal is recomputed from the ledger on each evaluation.

    That is deliberate and follows the pattern `monitoring.py` already
    establishes for monitor baselines: storing an anchor value would create the
    writable copy the anchor invariant exists to prevent, and a stored number can
    drift from the ledger in a convenient direction. A sequence number cannot.
    """

    spend_minor: dict[str, int] = field(default_factory=dict)
    #: Ledger sequence at the end of each completed period, oldest first.
    boundaries: list[int] = field(default_factory=list)
    escalations: int = 0
    corrections: int = 0

    def current_spend(self, department: str, default: int) -> int:
        return self.spend_minor.get(department, default)


def _period_entries(
    entries: list[LedgerEntry], start_seq: int, end_seq: int
) -> list[LedgerEntry]:
    """Entries falling strictly inside one period."""
    return [e for e in entries if start_seq < (e.seq or 0) <= end_seq]


def _observed_signal(
    metric: str,
    entries: list[LedgerEntry],
    start_seq: int,
    end_seq: int,
) -> float | None:
    """The value a department observes for one period, recomputed from the ledger.

    PERIOD-SCOPED, not cumulative-to-date.
    -------------------------------------
    `AnchorSet.compute` derives from whatever entries it is given. Given the whole
    ledger it returns a cumulative figure, and a cumulative RATIO is dominated by
    history: measured that way net_margin_pct moved only 17.7% -> 18.6% across a
    90-day run in which the company was steadily destroying value on acquisition.
    Week-over-week movement stayed under the 0.5pp materiality floor, so nothing
    could detect it.

    Passing only this period's entries yields the period's own margin, which
    responds to this period's decisions. That is the correct basis for period
    control and for period-over-period comparison.

    No anchor is stored: the set is recomputed from the ledger on every call, and
    only sequence numbers are retained between periods.
    """
    window = _period_entries(entries, start_seq, end_seq)
    if not window:
        return None
    return AnchorSet.compute("period", window).value(metric)


def _signal_improved(metric: str, previous: float, current: float) -> bool | None:
    """Did the observed signal get better? None when the change is immaterial.

    Direction comes from reflection.LOWER_IS_BETTER so that rising churn is
    correctly read as a decline rather than as progress.
    """
    change = current - previous
    scale = max(abs(previous), 1.0)
    if abs(change) / scale < 0.02:  # under 2% relative movement is noise
        return None
    better_when_lower = metric in refl.LOWER_IS_BETTER
    return change < 0 if better_when_lower else change > 0


def make_escalating_planner(
    config: ArmConfig,
    state: EscalationState,
) -> "Planner":
    """The planner every arm uses. Wraps the shared rule-based planner.

    It defers entirely to `rule_based_planner` for WHAT to do, and only overrides
    the spend magnitude of a SPEND task using the escalation level that
    `evaluate_escalation` has already decided. Reusing the shared planner is what
    keeps the arms comparable: the task set, the anchor-health branch and the
    memory branch are all the production ones.
    """

    def planner(profile: DepartmentProfile, anchors: AnchorSet,
                memories: list[dict], tick: datetime) -> list[Task]:
        tasks = rule_based_planner(profile, anchors, memories, tick)
        out: list[Task] = []
        for task in tasks:
            if task.action_kind is not ActionKind.SPEND or not task.amount_minor:
                out.append(task)
                continue
            level = state.current_spend(profile.name, task.amount_minor)
            level = min(level, profile.task_budget_minor)
            if level == task.amount_minor:
                out.append(task)
                continue
            scaled_effects = tuple(
                (kind, level if kind in _SPEND_EFFECT_KINDS else amount, quantity)
                for kind, amount, quantity in task.effects
            )
            out.append(replace(task, amount_minor=level, effects=scaled_effects))
        return out

    return planner


#: Ledger kinds whose amount tracks the task's spend magnitude.
_SPEND_EFFECT_KINDS: frozenset[EntryKind] = frozenset({
    EntryKind.MARKETING_SPEND, EntryKind.OPEX, EntryKind.CAPEX,
})


def evaluate_escalation(
    company_id: str,
    config: ArmConfig,
    state: EscalationState,
) -> None:
    """Decide each department's next spend level from its observed signal.

    Called once per completed period. Applies the pre-registered rule above using
    whichever quantity this arm exposes.
    """
    entries = ledger_module.read(company_id)
    current_seq = max((e.seq or 0) for e in entries) if entries else 0
    state.boundaries.append(current_seq)
    if len(state.boundaries) < 3:
        return  # need two complete periods before a trend exists

    prev_start, prev_end, this_end = state.boundaries[-3:]

    for name, profile in PROFILES.items():
        metric = (profile.serves_anchor if config.anchors_visible
                  else profile.proxy_metric)
        previous = _observed_signal(metric, entries, prev_start, prev_end)
        current = _observed_signal(metric, entries, prev_end, this_end)
        if previous is None or current is None:
            continue
        verdict = _signal_improved(metric, previous, current)
        if verdict is None:
            continue

        base = state.current_spend(name, 4_000_00)
        if verdict:
            state.spend_minor[name] = min(
                int(base * ESCALATION_FACTOR), profile.task_budget_minor)
            state.escalations += 1
        else:
            state.spend_minor[name] = 0
            state.corrections += 1


def _ablation_objectives(start: datetime) -> list:
    """One standing objective per department, in force from the run's start.

    Registered so `review_objectives` has something to review. Passing an empty
    list - as the first version did - guaranteed zero findings, which made F62
    read 0.0 for every monitored arm and 1.0 for every unmonitored one. That was a
    restatement of the arm configuration, not a measurement.
    """
    from app.generation.operating import monitors as mon

    return [
        mon.Objective(
            objective_id=f"{name}-standing",
            department=name,
            description=profile.objective,
            serves_anchor=profile.serves_anchor,
            in_force_since=start.isoformat(),
            review_after_days=14,
        )
        for name, profile in PROFILES.items()
    ]


def _run_monitors(company_id: str, tick: datetime,
                  objectives: list | None = None) -> list[dict]:
    """Fire the four monitors for this period."""
    results = []
    for handler_name, handler_fn in [
        ("goodhart_detector", MO.goodhart_handler),
        ("conflict_detector", MO.conflict_handler),
    ]:
        result = handler_fn(company_id, tick)
        results.append(result)
    # No calibrated thresholds exist in the simulation, so the drift monitor has
    # nothing to check. Stated rather than silently passing an empty list.
    drift = MO.drift_handler([])(company_id, tick)
    results.append(drift)
    obj = MO.objective_review_handler(objectives or [])(company_id, tick)
    results.append(obj)
    return results


def run_arm(
    arm: AblationArm,
    *,
    seed: int = 42,
    days: int = 90,
    company_id: str | None = None,
    environment: SimulatedEnvironment | None = None,
) -> ArmRunResult:
    """Run one ablation arm for the given number of simulated days.

    The environment is stepped each day AFTER department ticks, simulating a
    market that reacts to what the departments did.

    Args:
        arm: which ablation condition to run
        seed: random seed for the environment
        days: number of simulated days
        company_id: optional company ID (default generated from arm+seed)
        environment: optional pre-configured environment

    Returns:
        ArmRunResult with full metrics for analysis
    """
    from datetime import timedelta, UTC

    config = ARM_CONFIGS[arm]
    cid = company_id or f"ablation-{arm}-seed{seed}"
    env = environment or SimulatedEnvironment(seed=seed)

    result = ArmRunResult(arm=arm, seed=seed, days=days)
    clock = ManualClock(datetime(2026, 1, 1, 9, 0, tzinfo=UTC))
    escalation = EscalationState()
    planner = make_escalating_planner(config, escalation)
    objectives = _ablation_objectives(clock.now())

    # Seed the company with opening capital
    ledger_module.append(LedgerEntry(
        company_id=cid, kind=EntryKind.CASH_IN,
        department="finance", actor="opening_capital",
        amount_minor=10_00_000_00,  # ₹10 lakh
        occurred_at=clock.now().isoformat(),
    ))

    # Department run schedule: daily for strategy/finance/marketing/operations,
    # weekly for branding (matching the default_graph cadences)
    daily_departments = ["strategy", "finance", "marketing", "operations"]
    weekly_departments = ["branding"]

    for day in range(days):
        now = clock.now()
        day_entries: list[LedgerEntry] = []

        # --- Department ticks ---
        departments_to_run = list(daily_departments)
        if day % 7 == 0:
            departments_to_run.extend(weekly_departments)

        for dept in departments_to_run:
            if config.governance_active:
                tick_result = _run_department_tick_governed(cid, dept, now, planner)
            else:
                tick_result = _run_department_tick_unchecked(cid, dept, now, planner)

            result.department_ticks += 1
            result.blocked_actions += tick_result.blocked
            result.queued_for_review += tick_result.awaiting_review

            # Collect entries produced this tick for the environment
            # (we read back recent entries from the ledger)

        # Read entries added today by departments
        today_str = now.isoformat()
        all_entries = ledger_module.read(cid, since=today_str)
        dept_entries_today = [
            e for e in all_entries if e.department != "environment"
        ]

        # Track marketing spend
        mkt_spend = sum(
            e.amount_minor for e in dept_entries_today
            if e.kind == EntryKind.MARKETING_SPEND
        )
        result.total_marketing_spend_minor += mkt_spend

        # --- Environment step ---
        outcome = env.step(cid, now, dept_entries_today)
        for entry in outcome.entries:
            ledger_module.append(entry)

        result.customers_acquired += outcome.organic_acquired + outcome.marketing_acquired
        result.customers_churned += outcome.churned
        result.total_revenue_minor += outcome.revenue_minor

        # --- Monitor ticks (weekly for Goodhart/conflict, matching default) ---
        if config.monitors_active and day % 7 == 6:
            monitor_results = _run_monitors(cid, now, objectives)
            result.monitor_ticks += len(monitor_results)
            for mr in monitor_results:
                if mr.get("loop_id") == "objective_review":
                    result.objective_review_runs += 1
                if mr.get("findings", 0) > 0:
                    mr = dict(mr)
                    mr["day"] = day
                    result.findings.append(mr)

        # --- Reflection: weekly, matching the default_graph cadence ---
        #
        # This is what makes measurement change behaviour. Which quantity is
        # reflected on is the manipulated variable; see _reflect_period.
        if day % 7 == 6:
            reflect_seq, lessons = _reflect_period(
                cid, now, config, result._last_reflect_seq)
            result._last_reflect_seq = reflect_seq
            result.lessons_written += lessons

            # The pre-registered control rule: pursue the signal this arm exposes.
            evaluate_escalation(cid, config, escalation)

        # --- Daily snapshot for time-series analysis ---
        if day % 7 == 6:  # weekly snapshots
            anchors = AnchorSet.compute(cid)
            result.daily_snapshots.append({
                "day": day,
                "net_margin_pct": anchors.value("net_margin_pct"),
                "customers_acquired": anchors.value("customers_acquired"),
                "customers_churned": anchors.value("customers_churned"),
                "churn_pct": anchors.value("churn_pct"),
                "cac": anchors.value("cac"),
                "marketing_spend": anchors.value("marketing_spend"),
            })

        clock.advance(days=1)

    result.ledger_entries = ledger_module.entry_count(cid)
    result.escalations = escalation.escalations
    result.corrections = escalation.corrections
    return result


def run_paired(
    seed: int,
    *,
    days: int = 90,
    arms: Sequence[AblationArm] | None = None,
) -> dict[AblationArm, ArmRunResult]:
    """Run all arms with the same seed for paired comparison.

    Each arm gets an independent environment instance with the same seed, so the
    stochastic market generates the same base demand.  Differences in outcome are
    attributable to the control topology.
    """
    arms_to_run = arms or list(AblationArm)
    results: dict[AblationArm, ArmRunResult] = {}

    for arm in arms_to_run:
        # Each arm gets its own environment with the same seed
        env = SimulatedEnvironment(seed=seed)
        results[arm] = run_arm(arm, seed=seed, days=days, environment=env)

    return results
