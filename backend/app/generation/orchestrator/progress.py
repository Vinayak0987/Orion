"""F12 - Progress events.

Emitted as each department starts and finishes so the frontend (F48) can show
live agent activity. The emitter is transport-agnostic: it takes an async
callback, which Phase 8 will wire to a WebSocket and the evaluation harness
leaves unset.

Failures in the callback are swallowed. A dropped browser connection must never
abort a generation run that is already consuming free-tier quota.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum

import structlog
from pydantic import BaseModel, Field

from app.generation.models.state import Department

log = structlog.get_logger(__name__)


class ProgressEventType(StrEnum):
    SESSION_STARTED = "session_started"
    INTENT_RESOLVED = "intent_resolved"
    ROUTING_RESOLVED = "routing_resolved"
    DEPARTMENT_STARTED = "department_started"
    DEPARTMENT_COMPLETED = "department_completed"
    DEPARTMENT_FAILED = "department_failed"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


class ProgressEvent(BaseModel):
    session_id: str
    event: ProgressEventType
    department: str | None = None
    completed: int = 0
    total: int = 0
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def percent(self) -> float:
        return round(100.0 * self.completed / self.total, 1) if self.total else 0.0


ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]


class ProgressEmitter:
    """Tracks department completion and forwards events to an optional sink."""

    def __init__(
        self,
        session_id: str,
        total_departments: int,
        callback: ProgressCallback | None = None,
    ) -> None:
        self.session_id = session_id
        self.total = total_departments
        self._callback = callback
        self._completed = 0
        self.events: list[ProgressEvent] = []

    @property
    def completed(self) -> int:
        return self._completed

    async def _emit(
        self,
        event: ProgressEventType,
        department: Department | None = None,
        detail: str = "",
    ) -> ProgressEvent:
        payload = ProgressEvent(
            session_id=self.session_id,
            event=event,
            department=department.value if department else None,
            completed=self._completed,
            total=self.total,
            detail=detail,
        )
        self.events.append(payload)
        # NOTE: structlog reserves `event` for the log message itself, so the
        # event type is logged as `event_type`.
        log.info(
            "progress",
            event_type=event.value,
            department=payload.department,
            completed=payload.completed,
            total=payload.total,
            detail=detail,
        )
        if self._callback is not None:
            try:
                await self._callback(payload)
            except Exception as exc:  # noqa: BLE001 - a dead socket must not abort the run
                log.warning("progress.callback_failed", error=str(exc)[:200])
        return payload

    async def session_started(self, prompt: str) -> None:
        await self._emit(ProgressEventType.SESSION_STARTED, detail=prompt[:120])

    async def intent_resolved(self, detail: str) -> None:
        await self._emit(ProgressEventType.INTENT_RESOLVED, detail=detail)

    async def routing_resolved(self, detail: str) -> None:
        await self._emit(ProgressEventType.ROUTING_RESOLVED, detail=detail)

    async def department_started(self, department: Department) -> None:
        await self._emit(ProgressEventType.DEPARTMENT_STARTED, department)

    async def department_completed(self, department: Department) -> None:
        self._completed += 1
        await self._emit(ProgressEventType.DEPARTMENT_COMPLETED, department)

    async def department_failed(self, department: Department, error: str) -> None:
        self._completed += 1
        await self._emit(ProgressEventType.DEPARTMENT_FAILED, department, detail=error[:200])

    async def session_completed(self, detail: str) -> None:
        await self._emit(ProgressEventType.SESSION_COMPLETED, detail=detail)

    async def session_failed(self, detail: str) -> None:
        await self._emit(ProgressEventType.SESSION_FAILED, detail=detail)
