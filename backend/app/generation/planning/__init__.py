"""Planning Report layer - the pre-execution inspect-and-confirm flow.

Reads intent classification, routing and agent topology from the generation
layer; writes only its own `planning_reports` table and the report lifecycle:

    ready --confirm--> confirmed --run completed--> executed
    ready --24 h TTL--> expired   (derived lazily at read time; no reaper)
    blocked                      (terminal)

Modules:
    store   the `planning_reports` table and its status machine
    service report builder: intent, routing, agent roster, readiness, estimates
    api     thin HTTP routes under /planning
"""

from app.generation.planning.plan_store import init_plans
from app.generation.planning.store import init_planning as _init_reports


def init_planning() -> None:
    """Initialise all planning tables (reports + execution plans/events).

    Idempotent. Called on FastAPI startup next to the operating `init_all()`.
    """
    _init_reports()
    init_plans()


__all__ = ["init_planning"]