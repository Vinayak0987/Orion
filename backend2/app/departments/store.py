"""Departments store — the organizational layer the Master routes into.

CRUD over departments + department_members in MongoDB. A "department head" is an agent
with a role='head' membership. Specialists/subagents are added dynamically by
the Head as missions run. Seeded defaults give the system a working org out of
the box; users may also create custom departments.
"""

from __future__ import annotations

import json
import uuid

from app.auth import store as auth_store

_JSON = ("responsibilities", "config")
_VALID_STATUS = {"active", "inactive", "archived"}
_VALID_ROLES = {"head", "specialist", "member"}


def _decode(doc: dict) -> dict:
    """Convert MongoDB doc to department dict."""
    r = dict(doc)
    r["id"] = r.pop("_id")
    for f in _JSON:
        r[f] = r.get(f) or ([] if f == "responsibilities" else {})
    r["is_default"] = bool(r.get("is_default"))
    return r


def _decode_member(doc: dict) -> dict:
    """Convert MongoDB doc to department member dict."""
    r = dict(doc)
    r["id"] = r.pop("_id")
    r["permissions"] = r.get("permissions") or {}
    return r


# ---------------------------------------------------------------- departments
def create_department(*, name: str, created_by: str = "default-user", description: str = "",
                      purpose: str = "", responsibilities: list | None = None, slug: str = "",
                      dept_type: str = "custom", instructions: str = "", config: dict | None = None,
                      status: str = "active", is_default: bool = False, id: str | None = None) -> str:
    """Create a department in MongoDB."""
    did = id or uuid.uuid4().hex[:12]
    auth_store.create_department(
        dept_id=did, name=name, created_by=created_by, description=description,
        purpose=purpose, responsibilities=responsibilities or [], slug=slug,
        dept_type=dept_type, instructions=instructions, config=config or {},
        status=status if status in _VALID_STATUS else "active", is_default=is_default
    )
    return did


def get_department(dept_id: str, *, created_by: str | None = None) -> dict | None:
    """Get a department from MongoDB."""
    doc = auth_store.get_department(dept_id)
    if doc is None:
        return None
    d = _decode(doc)
    # Default (system) departments are visible to everyone; custom ones are
    # scoped to their owner.
    if created_by is not None and not d["is_default"] and d["created_by"] != created_by:
        return None
    return d


def list_departments(*, created_by: str = "default-user", status: str | None = None,
                     search: str | None = None) -> list[dict]:
    """List departments from MongoDB."""
    depts = auth_store.list_departments(created_by=created_by, status=status)
    
    if search:
        search_lower = search.lower()
        depts = [d for d in depts if search_lower in d.get("name", "").lower() or search_lower in d.get("description", "").lower()]
    
    return [_decode(d) for d in depts]


_UPD = {"name", "description", "purpose", "responsibilities", "dept_type", "instructions",
        "status", "config", "slug"}
_UPD_JSON = {"responsibilities", "config"}


def update_department(dept_id: str, changes: dict, *, created_by: str | None = None) -> dict | None:
    """Update a department in MongoDB."""
    cur = get_department(dept_id, created_by=created_by)
    if cur is None:
        return None
    sets, params = [], []
    for k, v in changes.items():
        if k not in _UPD:
            continue
        if k == "status" and v not in _VALID_STATUS:
            continue
        params.append(v)
    if params:
        update_data = {k: v for k, v in changes.items() if k in _UPD}
        auth_store.update_department(dept_id, **update_data)
    return get_department(dept_id, created_by=created_by)


def archive_department(dept_id: str, *, created_by: str | None = None) -> bool:
    """Archive a department in MongoDB."""
    d = get_department(dept_id, created_by=created_by)
    if d is None or d["is_default"]:
        return False  # don't archive default departments
    auth_store.update_department(dept_id, status="archived")
    return True


# ------------------------------------------------------------------- members
def list_members(dept_id: str, *, status: str = "active") -> list[dict]:
    """List department members from MongoDB with batch-optimized agent details."""
    members = auth_store.list_department_members(dept_id, status=status)
    
    # Collect all agent IDs
    agent_ids = [m.get("agent_id") for m in members if m.get("agent_id")]
    
    # Batch fetch all agents in a single query
    db = auth_store.get_db()
    agents = {a["_id"]: a for a in db.agents.find({"_id": {"$in": agent_ids}})}
    
    out = []
    for m in members:
        decoded = _decode_member(m)
        # Get agent details from pre-fetched batch
        agent = agents.get(m.get("agent_id"))
        if agent:
            decoded["agent_name"] = agent.get("name")
            decoded["agent_type"] = agent.get("agent_type")
            decoded["agent_purpose"] = agent.get("purpose")
            decoded["agent_tools"] = agent.get("tools", [])
            decoded["agent_origin"] = agent.get("origin")
            decoded["agent_role_title"] = agent.get("role_title")
            decoded["agent_status"] = agent.get("status")
        out.append(decoded)
    # Sort by role
    role_order = {"head": 0, "specialist": 1, "member": 2}
    out.sort(key=lambda x: role_order.get(x.get("role", "member"), 2))
    return out


def get_head(dept_id: str) -> dict | None:
    """Get department head from MongoDB with optimized query."""
    # Query directly for head role (single query instead of fetching all members)
    db = auth_store.get_db()
    head_member = db.department_members.find_one({"department_id": dept_id, "role": "head", "status": "active"})
    
    if not head_member:
        return None
    
    decoded = _decode_member(head_member)
    # Get agent details in a single query
    agent = db.agents.find_one({"_id": head_member.get("agent_id")})
    if agent:
        decoded["agent_name"] = agent.get("name")
        decoded["agent_type"] = agent.get("agent_type")
    return decoded


def agent_department_ids(agent_id: str) -> list[str]:
    """Department ids an agent belongs to (active memberships)."""
    if not agent_id:
        return []
    members = auth_store.list_department_members_by_agent(agent_id)
    return [m["department_id"] for m in members if m.get("status") == "active"]


def add_member(dept_id: str, agent_id: str, *, role: str = "specialist",
               instructions: str = "", permissions: dict | None = None) -> dict | None:
    """Add a member to a department in MongoDB."""
    role = role if role in _VALID_ROLES else "specialist"
    
    # If setting as head, demote existing head
    if role == "head":
        members = auth_store.list_department_members(dept_id, status="active")
        for m in members:
            if m.get("role") == "head":
                auth_store.update_department_member(m["_id"], role="specialist")
    
    # Check if member already exists
    members = auth_store.list_department_members(dept_id)
    existing = next((m for m in members if m.get("agent_id") == agent_id), None)
    
    if existing:
        auth_store.update_department_member(
            existing["_id"],
            role=role,
            status="active",
            instructions=instructions,
            permissions=permissions or {}
        )
        return get_member(existing["_id"])
    else:
        mid = uuid.uuid4().hex[:12]
        auth_store.create_department_member(
            member_id=mid,
            department_id=dept_id,
            agent_id=agent_id,
            role=role,
            status="active",
            instructions=instructions,
            permissions=permissions or {}
        )
        # Update agent's department_id
        auth_store.update_agent(agent_id, department_id=dept_id)
        return get_member(mid)


def get_member(member_id: str) -> dict | None:
    """Get a department member from MongoDB."""
    doc = auth_store.get_department_member(member_id)
    return _decode_member(doc) if doc else None


def remove_member(dept_id: str, agent_id: str) -> bool:
    """Remove a member from a department in MongoDB."""
    return auth_store.delete_department_member(dept_id, agent_id)


def assign_head(dept_id: str, agent_id: str, *, instructions: str = "") -> dict | None:
    """Assign a head to a department in MongoDB."""
    return add_member(dept_id, agent_id, role="head", instructions=instructions)


def member_departments(agent_id: str) -> list[dict]:
    """Get departments an agent belongs to from MongoDB."""
    members = auth_store.list_department_members_by_agent(agent_id)
    out = []
    for m in members:
        if m.get("status") != "active":
            continue
        dept = auth_store.get_department(m["department_id"])
        if dept:
            d = _decode(dept)
            d["member_role"] = m.get("role")
            out.append(d)
    return out


# --------------------------------------------------------------------- stats
def department_stats(dept_id: str) -> dict:
    """Get department stats from MongoDB."""
    members = auth_store.list_department_members(dept_id, status="active")
    head = get_head(dept_id)
    
    # Get missions and documents stats
    # Note: Need to implement these queries in auth_store
    missions = 0
    active = 0
    docs = 0
    last = None
    
    return {"members": len(members), "head": head.get("agent_name") if head else None,
            "missions": missions, "active_missions": active, "knowledge_documents": docs,
            "last_activity": last}


def list_departments_with_stats(*, created_by: str = "default-user", status: str | None = None,
                                search: str | None = None) -> list[dict]:
    """List departments with stats from MongoDB."""
    depts = list_departments(created_by=created_by, status=status, search=search)
    for d in depts:
        d["stats"] = department_stats(d["id"])
    return depts


def find_by_slug_or_name(query: str, *, created_by: str = "default-user") -> dict | None:
    """Find a department by slug or name from MongoDB."""
    q = (query or "").strip().lower()
    for d in list_departments(created_by=created_by):
        if d["slug"] == q or d["name"].lower() == q or d["dept_type"] == q:
            return d
    return None
