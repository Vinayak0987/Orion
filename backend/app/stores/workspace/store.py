"""Workspace store (MongoDB).

Each user owns one workspace. The workspace holds settings (name, description,
logo, timezone, language) and a list of members. In the single-user system the
owner is the only "member" by default, but members can be added as invited
collaborators (stored as records, no login yet — a real invitation flow lands
with multi-user auth).

Collections
-----------
workspaces  { _id, owner_id, name, description, logo_url, timezone, language,
              created_at, updated_at }
members     { _id, workspace_id, name, email, role, status, invited_at }
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from app.auth.store import get_db

ROLES = ("Owner", "Admin", "Member", "Viewer")
DEFAULT_WORKSPACE = {
    "name": "My Workspace",
    "description": "",
    "logo_url": None,
    "timezone": "(GMT+05:30) Asia/Kolkata",
    "language": "English (US)",
}


def _now() -> datetime:
    return datetime.now(UTC)


def get_or_create_workspace(owner_id: str, owner_name: str = "", owner_email: str = "") -> dict:
    """Return the user's workspace, creating a default one (with the owner as the
    first member) on first access."""
    db = get_db()
    ws = db.workspaces.find_one({"owner_id": owner_id})
    if ws:
        return ws

    ws = {
        "_id": uuid.uuid4().hex,
        "owner_id": owner_id,
        **DEFAULT_WORKSPACE,
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.workspaces.insert_one(ws)
    # Seed the owner as the first member.
    db.members.insert_one({
        "_id": uuid.uuid4().hex,
        "workspace_id": ws["_id"],
        "name": owner_name or "Owner",
        "email": owner_email,
        "role": "Owner",
        "status": "active",
        "invited_at": _now(),
    })
    return ws


def update_workspace(owner_id: str, owner_name: str = "", owner_email: str = "", **fields) -> dict:
    allowed = {
        k: v
        for k, v in fields.items()
        if k in {"name", "description", "logo_url", "timezone", "language"} and v is not None
    }
    ws = get_or_create_workspace(owner_id, owner_name, owner_email)
    if allowed:
        allowed["updated_at"] = _now()
        get_db().workspaces.update_one({"_id": ws["_id"]}, {"$set": allowed})
    return get_db().workspaces.find_one({"_id": ws["_id"]})


# --- members -----------------------------------------------------------------

def list_members(owner_id: str, owner_name: str = "", owner_email: str = "") -> list[dict]:
    ws = get_or_create_workspace(owner_id, owner_name, owner_email)
    return list(get_db().members.find({"workspace_id": ws["_id"]}).sort("invited_at", 1))


def add_member(owner_id: str, name: str, email: str, role: str = "Member",
               owner_name: str = "", owner_email: str = "") -> dict:
    ws = get_or_create_workspace(owner_id, owner_name, owner_email)
    db = get_db()
    role = role if role in ROLES else "Member"
    # Prevent duplicate email within the same workspace.
    if db.members.find_one({"workspace_id": ws["_id"], "email": email.strip().lower()}):
        raise ValueError("A member with this email already exists.")
    member = {
        "_id": uuid.uuid4().hex,
        "workspace_id": ws["_id"],
        "name": name.strip(),
        "email": email.strip().lower(),
        "role": role,
        "status": "invited",
        "invited_at": _now(),
    }
    db.members.insert_one(member)
    return member


def update_member(owner_id: str, member_id: str, **fields) -> Optional[dict]:
    ws = get_or_create_workspace(owner_id)
    allowed = {k: v for k, v in fields.items() if k in {"name", "role", "status"} and v is not None}
    if "role" in allowed and allowed["role"] not in ROLES:
        allowed.pop("role")
    db = get_db()
    if allowed:
        db.members.update_one(
            {"_id": member_id, "workspace_id": ws["_id"]}, {"$set": allowed}
        )
    return db.members.find_one({"_id": member_id, "workspace_id": ws["_id"]})


def remove_member(owner_id: str, member_id: str) -> bool:
    ws = get_or_create_workspace(owner_id)
    db = get_db()
    member = db.members.find_one({"_id": member_id, "workspace_id": ws["_id"]})
    if not member:
        return False
    if member.get("role") == "Owner":
        raise ValueError("The workspace owner cannot be removed.")
    db.members.delete_one({"_id": member_id, "workspace_id": ws["_id"]})
    return True
