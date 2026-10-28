"""Idempotent seeding of all built-in tools into the `tools` table.

Called at startup. Re-seeding updates descriptions/schemas but preserves a
user's enable/disable choice (handled in store.upsert_tool).
"""

from __future__ import annotations

from app.tools import store
from app.tools.base import load_all


def seed_builtin_tools() -> int:
    registry = load_all()
    for bt in registry.values():
        store.upsert_tool(
            name=bt.name,
            display_name=bt.display_name,
            description=bt.description,
            type="builtin",
            category=bt.category,
            input_schema=bt.input_schema,
            enabled=bt.enabled_by_default,
            requires_key=bt.requires_key,
            degraded=bt.degraded,
        )
    return len(registry)
