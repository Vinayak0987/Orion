"""Mission event pub/sub — in-memory, per-mission.

The engine emits events; the WebSocket handler drains them. Events are also
BUFFERED per mission, so a client that connects a moment after the mission
starts still receives the full history (avoids a race between POST /missions
returning and the WS connecting). The buffer is cleared when the mission stream
finishes and no subscribers remain.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

_subscribers: dict[str, list[asyncio.Queue]] = {}
_buffers: dict[str, list[dict]] = {}
_finished: set[str] = set()

_DONE = object()


def make_emitter(mission_id: str):
    _buffers.setdefault(mission_id, [])

    async def emit(event: str, **data) -> None:
        payload = {"event": event, **data}
        _buffers[mission_id].append(payload)
        for q in _subscribers.get(mission_id, []):
            await q.put(payload)
    return emit


async def finish(mission_id: str) -> None:
    _finished.add(mission_id)
    for q in _subscribers.get(mission_id, []):
        await q.put(_DONE)


async def emit_to(mission_id: str, event: str, **data) -> None:
    """Emit a one-off event to a mission's subscribers (e.g. mission_stopped)."""
    payload = {"event": event, **data}
    _buffers.setdefault(mission_id, []).append(payload)
    for q in _subscribers.get(mission_id, []):
        await q.put(payload)


async def subscribe(mission_id: str) -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue()

    # Replay buffered events first (history for a late-connecting client).
    for payload in list(_buffers.get(mission_id, [])):
        yield payload

    # If the mission already finished, nothing more will come.
    if mission_id in _finished:
        _cleanup_if_idle(mission_id)
        return

    _subscribers.setdefault(mission_id, []).append(q)
    try:
        while True:
            item = await q.get()
            if item is _DONE:
                return
            yield item
    finally:
        subs = _subscribers.get(mission_id, [])
        if q in subs:
            subs.remove(q)
        _cleanup_if_idle(mission_id)


def _cleanup_if_idle(mission_id: str) -> None:
    if mission_id in _finished and not _subscribers.get(mission_id):
        _subscribers.pop(mission_id, None)
        _buffers.pop(mission_id, None)
        _finished.discard(mission_id)
