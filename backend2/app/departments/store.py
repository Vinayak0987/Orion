"""Departments store — the organizational layer the Master routes into.

CRUD over departments + department_members. A "department head" is an agent
with a role='head' membership. Specialists/subagents are added dynamically by
the Head as missions run. Seeded defaults give the system a working org out of
the box; users may also create custom departments.
"""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection

_JSON = ("responsibilities", "config")
_VALID_STATUS = {"active", "inactive", "archived"}
_VALID_ROLES = {"head", "specialist", "member"}


def _decode(row) -> dict:
    r = dict(row)
    for f in _JSON:
        r[f] = json.loads(r[f]) if r.get(f) else ([] if f == "responsibilities" else {})
    r["is_default"] = bool(r.get("is_default"))
    return r


def _decode_member(row) -> dict:
    r = dict(row)
    r["permissions"] = json.loads(r["permissions"]) if r.get("permissions") else {}
    return r


# ---------------------------------------------------------------- departments
def create_department(*, name: str, created_by: str = "default-user", description: str = "",
                      purpose: str = "", responsibilities: list | None = None, slug: str = "",
                      dept_type: str = "custom", instructions: str = "", config: dict | None = None,
                      status: str = "active", is_default: bool = False, id: str | None = None) -> str:
    did = id or uuid.uuid4().hex[:12]
    now = _now()
    with connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO departments
               (id, name, slug, description, purpose, responsibilities, dept_type, instructions,
                status, config, is_default, created_by, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (did, name, slug or name.lower().replace(" ", "-"), description, purpose,
             json.dumps(responsibilities or []), dept_type, instructions,
             status if status in _VALID_STATUS else "active", json.dumps(config or {}),
             1 if is_default else 0, created_by, now, now),
        )
    return did


def get_department(dept_id: str, *, created_by: str | None = None) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (dept_id,)).fetchone()
    if row is None:
        return None
    d = _decode(row)
    # Default (system) departments are visible to everyone; custom ones are
    # scoped to their owner.
    if created_by is not None and not d["is_default"] and d["created_by"] != created_by:
        return None
    return d


def list_departments(*, created_by: str = "default-user", status: str | None = None,
                     search: str | None = None) -> list[dict]:
    q = "SELECT * FROM departments WHERE (created_by = ? OR is_default = 1)"
    params: list = [created_by]
    if status:
        q += " AND status = ?"; params.append(status)
    else:
        q += " AND status != 'archived'"
    if search:
        q += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)"
        like = f"%{search.lower()}%"; params += [like, like]
    q += " ORDER BY is_default DESC, created_at"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_decode(r) for r in rows]


_UPD = {"name", "description", "purpose", "responsibilities", "dept_type", "instructions",
        "status", "config", "slug"}
_UPD_JSON = {"responsibilities", "config"}


def update_department(dept_id: str, changes: dict, *, created_by: str | None = None) -> dict | None:
    cur = get_department(dept_id, created_by=created_by)
    if cur is None:
        return None
    sets, params = [], []
    for k, v in changes.items():
        if k not in _UPD:
            continue
        if k == "status" and v not in _VALID_STATUS:
            continue
        sets.append(f"{k} = ?")
        params.append(json.dumps(v) if k in _UPD_JSON else v)
    if not sets:
        return cur
    sets.append("updated_at = ?"); params.append(_now()); params.append(dept_id)
    with connection() as conn:
        conn.execute(f"UPDATE departments SET {', '.join(sets)} WHERE id = ?", params)  # noqa: S608
    return get_department(dept_id, created_by=created_by)


def archive_department(dept_id: str, *, created_by: str | None = None) -> bool:
    d = get_department(dept_id, created_by=created_by)
    if d is None or d["is_default"]:
        return False  # don't archive default departments
    with connection() as conn:
        conn.execute("UPDATE departments SET status='archived', updated_at=? WHERE id=?", (_now(), dept_id))
    return True


# ------------------------------------------------------------------- members
def list_members(dept_id: str, *, status: str = "active") -> list[dict]:
    q = ("SELECT dm.*, a.name AS agent_name, a.agent_type, a.purpose AS agent_purpose, "
         "a.tools AS agent_tools, a.origin AS agent_origin, a.role_title AS agent_role_title, "
         "a.status AS agent_status FROM department_members dm JOIN agents a ON a.id = dm.agent_id "
         "WHERE dm.department_id = ?")
    params: list = [dept_id]
    if status:
        q += " AND dm.status = ?"; params.append(status)
    q += " ORDER BY CASE dm.role WHEN 'head' THEN 0 WHEN 'specialist' THEN 1 ELSE 2 END, dm.created_at"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        m = _decode_member(r)
        try:
            m["agent_tools"] = json.loads(r["agent_tools"]) if r["agent_tools"] else []
        except Exception:  # noqa: BLE001
            m["agent_tools"] = []
        out.append(m)
    return out


def get_head(dept_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT dm.*, a.name AS agent_name, a.agent_type FROM department_members dm "
            "JOIN agents a ON a.id = dm.agent_id "
            "WHERE dm.department_id = ? AND dm.role = 'head' AND dm.status = 'active' LIMIT 1",
            (dept_id,),
        ).fetchone()
    return _decode_member(row) if row else None


def agent_department_ids(agent_id: str) -> list[str]:
    """Department ids an agent belongs to (active memberships)."""
    if not agent_id:
        return []
    with connection() as conn:
        rows = conn.execute(
            "SELECT department_id FROM department_members WHERE agent_id=? AND status='active'",
            (agent_id,),
        ).fetchall()
    return [r["department_id"] for r in rows]


def add_member(dept_id: str, agent_id: str, *, role: str = "specialist",
               instructions: str = "", permissions: dict | None = None) -> dict | None:
    role = role if role in _VALID_ROLES else "specialist"
    now = _now()
    with connection() as conn:
        if role == "head":
            conn.execute("UPDATE department_members SET role='specialist', updated_at=? "
                         "WHERE department_id=? AND role='head'", (now, dept_id))
        existing = conn.execute("SELECT id FROM department_members WHERE department_id=? AND agent_id=?",
                                (dept_id, agent_id)).fetchone()
        if existing:
            conn.execute("UPDATE department_members SET role=?, status='active', instructions=?, "
                         "permissions=?, updated_at=? WHERE id=?",
                         (role, instructions, json.dumps(permissions or {}), now, existing["id"]))
            mid = existing["id"]
        else:
            mid = uuid.uuid4().hex[:12]
            conn.execute("""INSERT INTO department_members
                   (id, department_id, agent_id, role, status, instructions, permissions, created_at, updated_at)
                   VALUES (?,?,?,?,'active',?,?,?,?)""",
                   (mid, dept_id, agent_id, role, instructions, json.dumps(permissions or {}), now, now))
        conn.execute("UPDATE agents SET department_id = COALESCE(NULLIF(department_id,''), ?), updated_at=? WHERE id=?",
                     (dept_id, now, agent_id))
    return get_member(mid)


def get_member(member_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM department_members WHERE id=?", (member_id,)).fetchone()
    return _decode_member(row) if row else None


def remove_member(dept_id: str, agent_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM department_members WHERE department_id=? AND agent_id=?",
                           (dept_id, agent_id))
    return cur.rowcount > 0


def assign_head(dept_id: str, agent_id: str, *, instructions: str = "") -> dict | None:
    return add_member(dept_id, agent_id, role="head", instructions=instructions)


def member_departments(agent_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT d.*, dm.role AS member_role FROM department_members dm "
            "JOIN departments d ON d.id = dm.department_id "
            "WHERE dm.agent_id=? AND dm.status='active' AND d.status != 'archived'", (agent_id,)
        ).fetchall()
    out = []
    for r in rows:
        d = _decode(r); d["member_role"] = r["member_role"]; out.append(d)
    return out


# --------------------------------------------------------------------- stats
def department_stats(dept_id: str) -> dict:
    with connection() as conn:
        members = conn.execute("SELECT COUNT(*) AS n FROM department_members WHERE department_id=? AND status='active'",
                               (dept_id,)).fetchone()["n"]
        head = conn.execute("SELECT a.name FROM department_members dm JOIN agents a ON a.id=dm.agent_id "
                            "WHERE dm.department_id=? AND dm.role='head' AND dm.status='active' LIMIT 1",
                            (dept_id,)).fetchone()
        missions = conn.execute("SELECT COUNT(*) AS n FROM missions WHERE department_id=?", (dept_id,)).fetchone()["n"]
        active = conn.execute("SELECT COUNT(*) AS n FROM missions WHERE department_id=? AND status IN "
                              "('planning','running','awaiting_input')", (dept_id,)).fetchone()["n"]
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents WHERE department_id=?", (dept_id,)).fetchone()["n"]
        last = conn.execute("SELECT MAX(created_at) AS t FROM missions WHERE department_id=?", (dept_id,)).fetchone()["t"]
    return {"members": members, "head": head["name"] if head else None, "missions": missions,
            "active_missions": active, "knowledge_documents": docs, "last_activity": last}


def list_departments_with_stats(*, created_by: str = "default-user", status: str | None = None,
                                search: str | None = None) -> list[dict]:
    depts = list_departments(created_by=created_by, status=status, search=search)
    for d in depts:
        d["stats"] = department_stats(d["id"])
    return depts


def find_by_slug_or_name(query: str, *, created_by: str = "default-user") -> dict | None:
    q = (query or "").strip().lower()
    for d in list_departments(created_by=created_by):
        if d["slug"] == q or d["name"].lower() == q or d["dept_type"] == q:
            return d
    return None
