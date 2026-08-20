"""F64 - structured JSON logging.

Every LLM call and every external API call emits a machine-readable log line.
The evaluation harness parses these to compute routing efficiency (F58) without
needing to instrument the agents a second time.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    renderer: structlog.types.Processor
    if settings.app_env == "development":
        renderer = structlog.dev.ConsoleRenderer(colors=False)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_session(session_id: str) -> None:
    """Attach a session_id to every subsequent log line on this task."""
    structlog.contextvars.bind_contextvars(session_id=session_id)


def clear_session() -> None:
    structlog.contextvars.clear_contextvars()
