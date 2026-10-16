"""Startup/shutdown hooks for the v1 generation + operating engine.

Called from the v2 FastAPI app (``app.main``) so the generation layer boots
alongside the mission engine without duplicating lifecycle logic.
"""

from __future__ import annotations

from app.generation.config import settings as gen_settings
from app.generation.core.logging import configure_logging
from app.generation.db import sqlite


def init_generation() -> None:
    """Initialise the generation + operating + planning stores. Idempotent."""
    configure_logging()
    sqlite.init_db()

    from app.generation.operating import init_all
    from app.generation.planning import init_planning

    init_all()
    init_planning()

    for warning in gen_settings.warnings():
        # Surface config warnings through the generation logger.
        import structlog

        structlog.get_logger(__name__).warning("generation.config.warning", detail=warning)


async def shutdown_generation() -> None:
    """Close the generation LLM client."""
    from app.generation.llm.chain import llm_client

    await llm_client.aclose()
