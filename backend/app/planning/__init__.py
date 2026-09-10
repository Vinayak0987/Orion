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

from app.planning.store import init_planning

__all__ = ["init_planning"]