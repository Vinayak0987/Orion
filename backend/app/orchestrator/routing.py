"""F10 - Routing Rules Engine.

Decides which departments run for a given intent, and in which stages.

This module is the mechanism RQ2 is built on. `resolve_departments` has two
modes:

    dynamic  (settings.enable_dynamic_routing = True)   experimental arm
    force_all                                            control arm

Both arms consume the identical `BusinessIntent`, so the only difference between
them is the department set. That is what makes the measured token/time saving
attributable to routing rather than to prompt variation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.models.intent import BusinessIntent
from app.models.state import ALWAYS_ACTIVE, Department

# Stage layout. Strategy must complete first because Finance prices against its
# competitor set and Marketing targets its personas; Operations runs last because
# its staffing plan is costed against Finance's budget envelope.
STAGE_1: tuple[Department, ...] = (Department.STRATEGY,)
STAGE_2: tuple[Department, ...] = (
    Department.FINANCE,
    Department.BRANDING,
    Department.MARKETING,
)
STAGE_3: tuple[Department, ...] = (Department.OPERATIONS,)

ALL_STAGES: tuple[tuple[Department, ...], ...] = (STAGE_1, STAGE_2, STAGE_3)

ALL_DEPARTMENTS: tuple[Department, ...] = STAGE_1 + STAGE_2 + STAGE_3


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Immutable routing outcome. Recorded in RunMetadata for the paper."""

    active: tuple[Department, ...]
    skipped: tuple[Department, ...]
    reason: str
    dynamic: bool

    @property
    def stages(self) -> tuple[tuple[Department, ...], ...]:
        """Non-empty execution stages, filtered to active departments."""
        filtered = tuple(
            tuple(d for d in stage if d in self.active) for stage in ALL_STAGES
        )
        return tuple(stage for stage in filtered if stage)


def resolve_departments(
    intent: BusinessIntent,
    *,
    force_all: bool = False,
) -> RoutingDecision:
    """Apply routing rules to an intent.

    Args:
        intent: classified intent (F2).
        force_all: run every department regardless of intent. This is the RQ2
            control arm; also set implicitly when ENABLE_DYNAMIC_ROUTING=false.

    Returns:
        RoutingDecision listing active and skipped departments.
    """
    if force_all or not settings.enable_dynamic_routing:
        return RoutingDecision(
            active=ALL_DEPARTMENTS,
            skipped=(),
            reason=(
                "all departments forced (RQ2 control arm)"
                if force_all
                else "dynamic routing disabled via ENABLE_DYNAMIC_ROUTING"
            ),
            dynamic=False,
        )

    active: list[Department] = list(ALWAYS_ACTIVE)
    skipped: list[Department] = []

    if intent.requires_operations:
        active.append(Department.OPERATIONS)
        reason = (
            f"operations active: {intent.business_type} is "
            f"{'physical' if intent.is_physical else 'product-based'}"
        )
    else:
        skipped.append(Department.OPERATIONS)
        reason = (
            f"operations skipped: {intent.business_type} has no premises or "
            f"physical fulfilment"
        )

    # Preserve canonical stage order regardless of append order.
    ordered = tuple(d for d in ALL_DEPARTMENTS if d in set(active))

    return RoutingDecision(
        active=ordered,
        skipped=tuple(skipped),
        reason=reason,
        dynamic=True,
    )
