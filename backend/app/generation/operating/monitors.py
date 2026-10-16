"""Monitor loops — the parts that check the work.

Four monitors, each addressing one documented failure mode of a single
goal-measure-act loop:

    Goodhart detector    a claimed improvement with no matching anchor movement
    Conflict detector    two departments improving while a shared anchor falls
    Drift monitor        a threshold or lesson still in use after it expired
    Objective review     an objective still in force while its anchor declines

Discipline borrowed from convergent auditing
--------------------------------------------
The `production-audit` methodology requires every finding to be pinned to a
`file:line` or be dropped, on the grounds that an unlocatable finding cannot be
acted on and inflates the report. The equivalent here is an **anchor citation**:
a finding must name the anchor it rests on and the measured delta, or it is not
emitted. `Finding` cannot be constructed without one.

Its claim-versus-code lens — verifying a public promise against the
implementation that delivers it — is the direct ancestor of `claim_vs_ledger`
below. The substitution is: a department's claimed success stands in for the
public promise, and the append-only ledger stands in for the code.

Independence
------------
These monitors are judged on detection quality, never on the departmental
metrics they audit. That separation is enforced structurally by
`app.generation.operating.loops` invariant I2, not by convention here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.generation.operating.anchors import ANCHOR_NAMES, AnchorSet

# --------------------------------------------------------------------- claims --


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class Claim:
    """A department's assertion that something improved.

    A claim must name the anchor it expects to have moved, and in which
    direction. A department that cannot say which real quantity its work should
    have shifted has not made a checkable claim, and `validate()` rejects it.

    This is the mechanism that makes proxy capture visible: the department is
    free to choose its proxy, but not to avoid nominating an anchor.
    """

    department: str
    proxy_name: str
    proxy_delta: float
    expected_anchor: str
    expected_direction: Direction = Direction.UP
    period_start: str = ""
    period_end: str = ""
    note: str = ""

    def validate(self) -> None:
        if self.expected_anchor not in ANCHOR_NAMES:
            raise ValueError(
                f"claim from '{self.department}' cites unknown anchor "
                f"'{self.expected_anchor}'. A claim must name an anchor that is "
                f"actually derived from the ledger; see ANCHOR_NAMES."
            )
        if not self.proxy_name.strip():
            raise ValueError("a claim must name the proxy it improved")


# -------------------------------------------------------------------- findings --


class Severity(StrEnum):
    """Ordered worst-first, matching the audit rubric this borrows from."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


class FindingKind(StrEnum):
    PROXY_DIVERGENCE = "proxy_divergence"        # F1: proxy up, anchor down
    PROXY_UNSUPPORTED = "proxy_unsupported"      # F1: proxy up, anchor flat
    DEPARTMENT_CONFLICT = "department_conflict"   # F3
    METRIC_STALE = "metric_stale"                # F4
    OBJECTIVE_STALE = "objective_stale"          # F2


class UncitedFinding(RuntimeError):
    """A finding was constructed without an anchor citation."""


@dataclass(frozen=True, slots=True)
class Finding:
    """One monitor observation, pinned to measured evidence.

    `anchor` and `anchor_delta` are mandatory. A monitor that wants to report a
    suspicion it cannot ground in a movement must stay silent — the same
    trade-off convergent auditing makes when it drops findings that cannot be
    located.
    """

    kind: FindingKind
    severity: Severity
    department: str
    anchor: str
    anchor_delta: float
    message: str
    proxy_name: str = ""
    proxy_delta: float | None = None
    detected_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    escalate: bool = True

    def __post_init__(self) -> None:
        if not self.anchor:
            raise UncitedFinding(
                "a finding must cite the anchor it rests on, or not be emitted"
            )
        if self.anchor not in ANCHOR_NAMES:
            raise UncitedFinding(f"unknown anchor '{self.anchor}'")

    def as_row(self) -> str:
        """One flat, pinned line. No summary, no hedging."""
        proxy = (
            f" proxy {self.proxy_name} {self.proxy_delta:+g}"
            if self.proxy_delta is not None
            else ""
        )
        return (
            f"[{self.severity.upper()}] [{self.kind}] {self.department} — "
            f"{self.message} — anchor {self.anchor} {self.anchor_delta:+g}{proxy}"
        )


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (SEVERITY_ORDER[f.severity], f.department, f.anchor),
    )


# ------------------------------------------------ 1. Goodhart / claim-vs-ledger --

#: A proxy must move by at least this much before a claim is worth checking.
CLAIM_NOISE_FLOOR = 1.0

#: An anchor movement smaller than this is treated as flat rather than as
#: confirmation. Without a floor, a +0.01 drift would "support" any claim.
ANCHOR_FLAT_BAND = 0.5


def claim_vs_ledger(
    claims: list[Claim],
    before: AnchorSet,
    after: AnchorSet,
) -> list[Finding]:
    """Check each claimed improvement against what the ledger records.

    Three outcomes per claim:

    * the anchor moved as expected — no finding, the claim is supported;
    * the anchor moved against the claim — PROXY_DIVERGENCE, the signature of
      proxy capture;
    * the anchor did not move — PROXY_UNSUPPORTED, weaker, because absence of
      movement may only mean the effect has not landed yet.

    A claim whose anchor is not computable produces no finding. Reporting one
    would be reporting on the absence of evidence, which the evaluation harness's
    refusal-to-impute policy already establishes as the wrong move.
    """
    deltas = after.delta(before)
    findings: list[Finding] = []

    for claim in claims:
        claim.validate()
        if abs(claim.proxy_delta) < CLAIM_NOISE_FLOOR:
            continue  # nothing claimed

        if claim.expected_anchor not in deltas:
            continue  # not computable in both readings; stay silent

        anchor_delta = deltas[claim.expected_anchor]
        wanted_up = claim.expected_direction is Direction.UP
        moved_favourably = anchor_delta > 0 if wanted_up else anchor_delta < 0
        moved_adversely = anchor_delta < 0 if wanted_up else anchor_delta > 0
        flat = abs(anchor_delta) < ANCHOR_FLAT_BAND

        if flat:
            findings.append(Finding(
                kind=FindingKind.PROXY_UNSUPPORTED,
                severity=Severity.MEDIUM,
                department=claim.department,
                anchor=claim.expected_anchor,
                anchor_delta=anchor_delta,
                proxy_name=claim.proxy_name,
                proxy_delta=claim.proxy_delta,
                message=(
                    f"claimed {claim.proxy_name} {claim.proxy_delta:+g} but "
                    f"{claim.expected_anchor} did not move"
                ),
            ))
        elif moved_adversely and claim.proxy_delta > 0:
            findings.append(Finding(
                kind=FindingKind.PROXY_DIVERGENCE,
                severity=Severity.CRITICAL,
                department=claim.department,
                anchor=claim.expected_anchor,
                anchor_delta=anchor_delta,
                proxy_name=claim.proxy_name,
                proxy_delta=claim.proxy_delta,
                message=(
                    f"claimed {claim.proxy_name} {claim.proxy_delta:+g} while "
                    f"{claim.expected_anchor} moved {anchor_delta:+g} — the proxy "
                    f"has decoupled from the objective it stands for"
                ),
            ))
        elif moved_favourably:
            continue

    return sort_findings(findings)


# ----------------------------------------------------------- 2. Conflict -------


@dataclass(frozen=True, slots=True)
class DepartmentReport:
    """What one department says about its own period."""

    department: str
    own_metric: str
    own_delta: float


def detect_conflict(
    reports: list[DepartmentReport],
    before: AnchorSet,
    after: AnchorSet,
    shared_anchors: tuple[str, ...] = ("net_margin_pct", "retention_pct",
                                       "cash_balance"),
) -> list[Finding]:
    """Two or more departments improving while a shared anchor declines.

    No single department's report reveals this; it is only visible to something
    accountable for the interaction between them, which is why it needs its own
    loop rather than a check inside each department.
    """
    deltas = after.delta(before)
    improving = [r for r in reports if r.own_delta > 0]
    if len(improving) < 2:
        return []

    findings: list[Finding] = []
    for anchor in shared_anchors:
        movement = deltas.get(anchor)
        if movement is None or movement >= -ANCHOR_FLAT_BAND:
            continue
        names = ", ".join(sorted(r.department for r in improving))
        findings.append(Finding(
            kind=FindingKind.DEPARTMENT_CONFLICT,
            severity=Severity.HIGH,
            department=names,
            anchor=anchor,
            anchor_delta=movement,
            message=(
                f"{len(improving)} departments report improvement ({names}) "
                f"while the shared anchor {anchor} moved {movement:+g}"
            ),
        ))
    return sort_findings(findings)


# -------------------------------------------------------------- 3. Drift ------


@dataclass(frozen=True, slots=True)
class Threshold:
    """A calibrated value with the date it was calibrated."""

    name: str
    anchor: str
    value: float
    calibrated_at: str
    max_age_days: int = 90


def detect_drift(
    thresholds: list[Threshold],
    current: AnchorSet,
    *,
    now: str | None = None,
) -> list[Finding]:
    """Flag thresholds older than their stated shelf life.

    Staleness produces no error on its own — a stale threshold still returns a
    number — so it has to be looked for deliberately. The finding says the
    threshold is no longer *known* to be right, not that it is wrong.
    """
    reference = datetime.fromisoformat(now) if now else datetime.now(UTC)
    findings: list[Finding] = []

    for threshold in thresholds:
        anchor = current.get(threshold.anchor)
        if anchor is None or not anchor.computable:
            continue  # cannot cite a delta, so no finding
        calibrated = datetime.fromisoformat(threshold.calibrated_at)
        age = (reference - calibrated).days
        if age <= threshold.max_age_days:
            continue
        gap = round((anchor.value or 0.0) - threshold.value, 4)
        findings.append(Finding(
            kind=FindingKind.METRIC_STALE,
            severity=Severity.MEDIUM if age < threshold.max_age_days * 2
            else Severity.HIGH,
            department="finance",
            anchor=threshold.anchor,
            anchor_delta=gap,
            message=(
                f"threshold '{threshold.name}' was calibrated {age} days ago "
                f"(shelf life {threshold.max_age_days}); it is no longer known "
                f"to describe current conditions"
            ),
        ))
    return sort_findings(findings)


# --------------------------------------------------- 4. Objective review ------


@dataclass(frozen=True, slots=True)
class Objective:
    """A goal in force, with the anchor it is meant to serve."""

    objective_id: str
    department: str
    description: str
    serves_anchor: str
    in_force_since: str
    review_after_days: int = 30


def review_objectives(
    objectives: list[Objective],
    before: AnchorSet,
    after: AnchorSet,
    *,
    now: str | None = None,
) -> list[Finding]:
    """Ask whether an objective should still exist.

    Escalation goes outside the owning department by construction: a department
    asked to judge its own objective has an obvious conflict, which is the
    failure this monitor exists to catch.
    """
    reference = datetime.fromisoformat(now) if now else datetime.now(UTC)
    deltas = after.delta(before)
    findings: list[Finding] = []

    for objective in objectives:
        movement = deltas.get(objective.serves_anchor)
        if movement is None:
            continue
        since = datetime.fromisoformat(objective.in_force_since)
        in_force_days = (reference - since).days
        if in_force_days < objective.review_after_days:
            continue
        if movement >= -ANCHOR_FLAT_BAND:
            continue  # the anchor is not deteriorating
        findings.append(Finding(
            kind=FindingKind.OBJECTIVE_STALE,
            severity=Severity.HIGH,
            department=objective.department,
            anchor=objective.serves_anchor,
            anchor_delta=movement,
            message=(
                f"objective '{objective.description}' has been in force for "
                f"{in_force_days} days while {objective.serves_anchor} moved "
                f"{movement:+g}. Should this objective still exist?"
            ),
        ))
    return sort_findings(findings)


# ------------------------------------------------------------------ reporting --


def render_findings(findings: list[Finding]) -> str:
    """A flat severity-ordered list. Deliberately no executive summary.

    A summary is where an audit softens; every row here stands alone.
    """
    if not findings:
        return "No findings. Every claim in this period is supported by a "\
               "matching anchor movement."
    return "\n".join(f.as_row() for f in sort_findings(findings))


def escalations(findings: list[Finding]) -> list[Finding]:
    """Findings that go to a human. CRITICAL and HIGH by default."""
    return [
        f for f in sort_findings(findings)
        if f.escalate and f.severity in (Severity.CRITICAL, Severity.HIGH)
    ]


def stale_after(days: int, *, now: str | None = None) -> str:
    """Helper for tests and seeds: an ISO timestamp `days` in the past."""
    reference = datetime.fromisoformat(now) if now else datetime.now(UTC)
    return (reference - timedelta(days=days)).isoformat()
