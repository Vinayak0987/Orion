"""Reflection — how a department learns, and what it is not allowed to learn from.

The mechanism is unremarkable: periodically ask what worked, what did not, and
what should change. The constraint on it is the contribution.

    Reflection is grounded in measured anchor deltas, not in the department's
    account of its own performance.

A department that believes it had an excellent month, in a month where margin and
retention fell, produces a **negative** reflection. It is not permitted to be the
source of evidence about itself.

Why this constraint rather than the usual one
---------------------------------------------
Reflexion [Shinn et al. 2023] establishes that an agent can improve by writing
natural-language reflections on failure and retrieving them later. In that design
the reflection is grounded in the agent's own record of the episode. PAPER.md §7.2
gives a reason to be cautious about that here: estimates travelling through a
chain of agents compounded variance badly enough that the pipeline was
*unreliably better* rather than reliably worse. An agent's own account of a period
is exactly such an estimate.

So the verdict is decided by arithmetic on the ledger before any text is written.
`Reflection.verdict` is not a judgement the department makes; it is a
classification of anchor movement. The department's narrative is recorded
alongside as `claimed`, and where the two disagree the disagreement is the lesson.

Nothing here calls an LLM. A reflection is a structured record; producing prose
from it is a separate concern, and keeping the grounding free of inference is what
makes it testable and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.operating import memory as memory_module
from app.operating.anchors import AnchorSet
from app.operating.memory import Memory, MemoryType

#: Anchor movement smaller than this is treated as flat rather than as progress.
MATERIAL_MOVEMENT = 0.5

#: Anchors where a *lower* number is the better outcome.
LOWER_IS_BETTER: frozenset[str] = frozenset({
    "churn_pct", "cac", "sla_breaches", "cogs", "opex",
})


class Verdict(StrEnum):
    IMPROVED = "improved"
    DECLINED = "declined"
    FLAT = "flat"
    UNKNOWN = "unknown"      # no anchor was computable in both readings


@dataclass(frozen=True, slots=True)
class AnchorMovement:
    """One anchor's change over the period, with its direction interpreted."""

    anchor: str
    delta: float
    favourable: bool
    material: bool

    @property
    def summary(self) -> str:
        arrow = "improved" if self.favourable else "worsened"
        if not self.material:
            arrow = "held"
        return f"{self.anchor} {arrow} ({self.delta:+g})"


@dataclass(frozen=True, slots=True)
class Reflection:
    """A department's period review, decided by measurement.

    `claimed` is whatever the department said about itself. It is recorded but
    carries no weight in `verdict`.
    """

    company_id: str
    department: str
    verdict: Verdict
    movements: tuple[AnchorMovement, ...]
    lessons: tuple[str, ...]
    claimed: str = ""
    contradicted: bool = False
    period_start: str = ""
    period_end: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    @property
    def favourable(self) -> tuple[AnchorMovement, ...]:
        return tuple(m for m in self.movements if m.material and m.favourable)

    @property
    def adverse(self) -> tuple[AnchorMovement, ...]:
        return tuple(m for m in self.movements if m.material and not m.favourable)

    def as_text(self) -> str:
        """A flat record. Reads like a review, contains no unmeasured claim."""
        lines = [
            f"{self.department}: {self.verdict.upper()}",
        ]
        if self.contradicted:
            lines.append(
                "  NOTE: the department's own account did not match the measured "
                "outcome; the measurement stands."
            )
        for movement in self.movements:
            if movement.material:
                lines.append(f"  {movement.summary}")
        for lesson in self.lessons:
            lines.append(f"  lesson: {lesson}")
        return "\n".join(lines)


# ------------------------------------------------------------------ grounding --


def _favourable(anchor: str, delta: float) -> bool:
    return delta < 0 if anchor in LOWER_IS_BETTER else delta > 0


def movements_between(
    before: AnchorSet, after: AnchorSet, *,
    anchors: tuple[str, ...] | None = None,
) -> tuple[AnchorMovement, ...]:
    """Interpret every measured delta, applying each anchor's own direction."""
    deltas = after.delta(before)
    wanted = anchors or tuple(deltas)
    out = []
    for anchor in wanted:
        if anchor not in deltas:
            continue
        delta = deltas[anchor]
        out.append(AnchorMovement(
            anchor=anchor,
            delta=delta,
            favourable=_favourable(anchor, delta),
            material=abs(delta) >= MATERIAL_MOVEMENT,
        ))
    return tuple(out)


def decide_verdict(movements: tuple[AnchorMovement, ...]) -> Verdict:
    """The verdict is arithmetic, not opinion."""
    material = [m for m in movements if m.material]
    if not material:
        return Verdict.FLAT if movements else Verdict.UNKNOWN
    good = sum(1 for m in material if m.favourable)
    bad = len(material) - good
    if good > bad:
        return Verdict.IMPROVED
    if bad > good:
        return Verdict.DECLINED
    return Verdict.FLAT


#: Anchors that indicate a specific, nameable problem when they move adversely.
_LESSON_TEMPLATES: dict[str, str] = {
    "net_margin_pct": (
        "net margin fell over the period; volume gained without margin is not "
        "progress"
    ),
    "gross_margin_pct": (
        "gross margin fell; unit economics moved against us before any overhead"
    ),
    "churn_pct": (
        "churn rose; acquisition that does not retain is spend, not growth"
    ),
    "retention_pct": "retention fell; examine what changed for existing customers",
    "cac": "acquisition cost rose; the channel mix is getting more expensive",
    "cash_balance": "cash fell; check the spend cadence against the runway",
    "sla_breaches": "service level breaches rose; capacity is behind demand",
}


def derive_lessons(movements: tuple[AnchorMovement, ...]) -> tuple[str, ...]:
    """Lessons that name a measured movement. No generic advice.

    A lesson with no anchor behind it would be an opinion recorded as knowledge,
    which is the failure mode this whole module is arranged to avoid.
    """
    lessons = []
    for movement in movements:
        if not movement.material or movement.favourable:
            continue
        template = _LESSON_TEMPLATES.get(movement.anchor)
        if template:
            lessons.append(f"{template} ({movement.anchor} {movement.delta:+g})")
    return tuple(lessons)


# ------------------------------------------------------------------- reflect --


def reflect(
    company_id: str,
    department: str,
    before: AnchorSet,
    after: AnchorSet,
    *,
    claimed: str = "",
    claimed_verdict: Verdict | None = None,
    anchors: tuple[str, ...] | None = None,
    period_start: str = "",
    period_end: str = "",
) -> Reflection:
    """Produce a reflection from measured movement.

    `claimed_verdict` is the department's own assessment, if it offered one. When
    it disagrees with the measurement, `contradicted` is set — and the measured
    verdict is the one recorded.
    """
    movements = movements_between(before, after, anchors=anchors)
    verdict = decide_verdict(movements)
    contradicted = (
        claimed_verdict is not None
        and verdict is not Verdict.UNKNOWN
        and claimed_verdict != verdict
    )
    return Reflection(
        company_id=company_id,
        department=department,
        verdict=verdict,
        movements=movements,
        lessons=derive_lessons(movements),
        claimed=claimed,
        contradicted=contradicted,
        period_start=period_start,
        period_end=period_end,
    )


def persist(reflection: Reflection) -> list[str]:
    """Write the reflection into the department's own reflective memory.

    Returns the memory ids written. Only lessons grounded in a movement are
    stored, so the reflective store cannot fill with unfalsifiable sentiment.
    """
    written: list[str] = []
    for lesson in reflection.lessons:
        written.append(memory_module.write(Memory(
            company_id=reflection.company_id,
            department=reflection.department,
            memory_type=MemoryType.REFLECTIVE,
            content=lesson,
            confidence=0.7,
            meta={
                "verdict": str(reflection.verdict),
                "period_start": reflection.period_start,
                "period_end": reflection.period_end,
                "contradicted_claim": reflection.contradicted,
            },
        )))

    if reflection.contradicted:
        written.append(memory_module.write(Memory(
            company_id=reflection.company_id,
            department=reflection.department,
            memory_type=MemoryType.REFLECTIVE,
            content=(
                f"our own assessment of this period did not match the measured "
                f"outcome; measurement said {reflection.verdict}"
            ),
            confidence=0.9,
            meta={"verdict": str(reflection.verdict), "contradicted_claim": True},
        )))
    return written


def make_handler(
    before_provider,
    after_provider,
    *,
    department: str,
    claim_provider=None,
):
    """Adapt `reflect` into a scheduler handler.

    Kept as a factory rather than a fixed function so the scheduler stays
    unaware of how a period's boundaries are chosen.
    """

    def handler(company_id: str, now: datetime) -> dict:
        before = before_provider(company_id, now)
        after = after_provider(company_id, now)
        claimed, claimed_verdict = ("", None)
        if claim_provider is not None:
            claimed, claimed_verdict = claim_provider(company_id, now)
        reflection = reflect(
            company_id, department, before, after,
            claimed=claimed, claimed_verdict=claimed_verdict,
            period_end=now.isoformat(),
        )
        written = persist(reflection)
        return {
            "verdict": str(reflection.verdict),
            "lessons": len(reflection.lessons),
            "contradicted": reflection.contradicted,
            "memories_written": len(written),
        }

    return handler
