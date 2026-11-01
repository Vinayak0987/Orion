"""Unified session storage - MongoDB (cloud) with SQLite fallback (local).

This module provides a single interface for session storage that:
- Uses MongoDB Atlas when configured (cloud persistence, multi-device access)
- Falls back to SQLite when MongoDB is unavailable (local-only, single-device)
- Maintains user isolation in both backends
- Ensures data consistency across the application

Usage:
    from app.db.unified import create_session, get_session, list_sessions, delete_session
"""

from __future__ import annotations

from typing import Any

from app.auth import store as auth_store
from app.config import settings
from app.db import sqlite


def _use_mongodb() -> bool:
    """Check if MongoDB is configured and available."""
    return settings.mongo_available


def create_session(
    session_id: str,
    user_id: str,
    raw_prompt: str,
    intent_json: dict | None = None,
) -> None:
    """Create a session - uses MongoDB if available, otherwise SQLite."""
    if _use_mongodb():
        auth_store.create_session(session_id, user_id, raw_prompt, intent_json)
    else:
        sqlite.create_session(session_id, raw_prompt, user_id)


def update_session(session_id: str, **fields: Any) -> None:
    """Update session fields - uses MongoDB if available, otherwise SQLite."""
    if _use_mongodb():
        auth_store.update_session(session_id, **fields)
    else:
        sqlite.update_session(session_id, **fields)


def get_session(session_id: str, user_id: str) -> dict | None:
    """Get a session - uses MongoDB if available, otherwise SQLite."""
    if _use_mongodb():
        return auth_store.get_session(session_id, user_id)
    else:
        return sqlite.get_session(session_id, user_id)


def list_sessions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """List sessions for a user - uses MongoDB if available, otherwise SQLite."""
    if _use_mongodb():
        return auth_store.list_sessions(user_id, limit, offset)
    else:
        return sqlite.list_sessions(user_id, limit, offset)


def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a session - uses MongoDB if available, otherwise SQLite."""
    if _use_mongodb():
        return auth_store.delete_session(session_id, user_id)
    else:
        return sqlite.delete_session(session_id, user_id)
