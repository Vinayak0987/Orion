"""Unified mission storage - MongoDB (cloud) only.

This module provides a single interface for mission storage that:
- Uses MongoDB Atlas for cloud persistence and multi-device access
- Maintains user isolation across the application
- Ensures data consistency across the application

Usage:
    from app.db.unified import create_mission, get_mission, list_missions, delete_mission
"""

from __future__ import annotations

from typing import Any

from app.auth import store as auth_store


def create_mission(
    mission_id: str,
    user_id: str,
    prompt: str,
    title: str | None = None,
    department_id: str | None = None,
    conversation_id: str | None = None,
    mode: str = "action",
) -> str:
    """Create a mission in MongoDB. Returns mission_id."""
    auth_store.create_mission(
        mission_id, user_id, prompt, title, department_id, conversation_id, mode
    )
    return mission_id


def update_mission(mission_id: str, **fields: Any) -> None:
    """Update mission fields in MongoDB."""
    auth_store.update_mission(mission_id, **fields)


def get_mission(mission_id: str, user_id: str) -> dict | None:
    """Get a mission from MongoDB."""
    return auth_store.get_mission(mission_id, user_id)


def list_missions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """List missions for a user from MongoDB."""
    return auth_store.list_missions(user_id, limit, offset)


def list_missions_by_department(department_id: str, user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """List missions for a specific department from MongoDB (optimized query)."""
    db = auth_store.get_db()
    query = {"department_id": department_id}
    cursor = (
        db.missions.find(query)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    missions = list(cursor)
    # Convert _id to id for frontend compatibility
    for m in missions:
        if "_id" in m and "id" not in m:
            m["id"] = m.pop("_id")
    return missions


def delete_mission(mission_id: str, user_id: str) -> bool:
    """Delete a mission from MongoDB."""
    return auth_store.delete_mission(mission_id, user_id)
