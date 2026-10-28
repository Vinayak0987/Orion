"""Episodic agent memory store.

Mirrors the knowledge document store: facts an agent learns are embedded into a
per-agent ChromaDB collection when available, and ALWAYS recorded in the SQLite
`memory_entries` table (for the Memory UI + a keyword fallback search). When
ChromaDB is unavailable the keyword fallback over SQLite is used so memory still
works end-to-end.

Public API:
  write(agent_id, content, mission_id=None, ttl_days=30) -> entry_id
  search(agent_id, query, top_k=5) -> [ {content, score, id, created_at} ]
  read(agent_id, limit=50) -> [ entries ]      (most recent, non-expired)
  delete(entry_id) / clear_agent(agent_id)
"""

from __future__ import annotations

import datetime as dt
import re
import uuid

from app.config import settings
from app.db.sqlite import _now, connection

_WORD = re.compile(r"[a-z0-9]+")
_client = None


def _chroma():
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client


def _coll_name(agent_id: str) -> str:
    return f"memory_{agent_id}"


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall((s or "").lower()))


def write(agent_id: str, content: str, *, mission_id: str | None = None,
          department_id: str | None = None, ttl_days: int = 30) -> str:
    content = (content or "").strip()
    if not content:
        return ""
    entry_id = uuid.uuid4().hex
    now = dt.datetime.now(dt.UTC)
    expires = (now + dt.timedelta(days=max(1, ttl_days))).isoformat()
    # Best-effort vector store.
    try:
        import chromadb  # noqa: F401

        coll = _chroma().get_or_create_collection(_coll_name(agent_id))
        coll.add(ids=[entry_id], documents=[content],
                 metadatas=[{"agent_id": agent_id, "mission_id": mission_id or "",
                             "expires_at": expires}])
    except Exception:  # noqa: BLE001 — SQLite row below is the source of truth for the UI
        pass
    with connection() as conn:
        conn.execute(
            """INSERT INTO memory_entries
               (id, agent_id, department_id, content, chroma_id, source_mission_id, created_at, expires_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (entry_id, agent_id, department_id, content, entry_id, mission_id, now.isoformat(), expires),
        )
    return entry_id


def search(agent_id: str, query: str, top_k: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    now_iso = _now()
    # Try vector search first.
    try:
        import chromadb  # noqa: F401

        coll = _chroma().get_collection(_coll_name(agent_id))
        res = coll.query(query_texts=[query], n_results=top_k,
                         where={"expires_at": {"$gt": now_iso}})
        docs = (res.get("documents") or [[]])[0]
        ids = (res.get("ids") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        if docs:
            return [{"id": ids[i] if i < len(ids) else None, "content": d,
                     "score": round(1 - dists[i], 4) if i < len(dists) else None}
                    for i, d in enumerate(docs)]
    except Exception:  # noqa: BLE001 — fall through to keyword
        pass
    # Keyword fallback over SQLite.
    q = _tokens(query)
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, content, created_at FROM memory_entries WHERE agent_id = ? AND expires_at > ?",
            (agent_id, now_iso),
        ).fetchall()
    scored = []
    for r in rows:
        overlap = len(q & _tokens(r["content"]))
        if overlap:
            scored.append((overlap, dict(r)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"id": r["id"], "content": r["content"], "score": s, "created_at": r["created_at"]}
            for s, r in scored[:top_k]]


def read(agent_id: str, limit: int = 50) -> list[dict]:
    now_iso = _now()
    with connection() as conn:
        rows = conn.execute(
            """SELECT * FROM memory_entries WHERE agent_id = ? AND expires_at > ?
               ORDER BY created_at DESC LIMIT ?""",
            (agent_id, now_iso, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_all(limit: int = 200) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_entries ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete(entry_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
        agent = None
    try:
        import chromadb  # noqa: F401

        # We don't know the agent here cheaply; deletion by id across collections is
        # best-effort. The SQLite delete above is authoritative for the UI.
    except Exception:  # noqa: BLE001
        pass
    return cur.rowcount > 0


def clear_agent(agent_id: str) -> int:
    with connection() as conn:
        cur = conn.execute("DELETE FROM memory_entries WHERE agent_id = ?", (agent_id,))
        removed = cur.rowcount
    try:
        import chromadb  # noqa: F401

        try:
            _chroma().delete_collection(_coll_name(agent_id))
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
    return removed


def purge_expired() -> int:
    with connection() as conn:
        cur = conn.execute("DELETE FROM memory_entries WHERE expires_at <= ?", (_now(),))
        return cur.rowcount



# ---- Memory settings (global + per-agent) ----------------------------------
_SETTINGS_NS = "memory_settings"
_SETTINGS_KEY = "default-user"
_DEFAULT_SETTINGS = {
    "global_enabled": True,
    "default_ttl_days": 90,
    "max_global_entries": 10000,
    "per_agent": {},
}


def get_settings() -> dict:
    import json

    with connection() as conn:
        row = conn.execute(
            "SELECT value FROM kv_store WHERE namespace=? AND key=?", (_SETTINGS_NS, _SETTINGS_KEY)
        ).fetchone()
    if not row:
        return dict(_DEFAULT_SETTINGS)
    try:
        data = json.loads(row["value"])
        return {**_DEFAULT_SETTINGS, **data}
    except Exception:  # noqa: BLE001
        return dict(_DEFAULT_SETTINGS)


def update_settings(changes: dict) -> dict:
    import json

    current = get_settings()
    current.update({k: v for k, v in changes.items() if k in _DEFAULT_SETTINGS})
    with connection() as conn:
        conn.execute(
            """INSERT INTO kv_store (namespace, key, value, expires_at, updated_at) VALUES (?,?,?,?,?)
               ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (_SETTINGS_NS, _SETTINGS_KEY, json.dumps(current), None, _now()),
        )
    return current


def count_by_agent() -> dict:
    with connection() as conn:
        rows = conn.execute(
            "SELECT agent_id, COUNT(*) AS n FROM memory_entries GROUP BY agent_id"
        ).fetchall()
    return {r["agent_id"]: r["n"] for r in rows}



# ---- Executor hooks (pre-task retrieve + post-task extract/store) -----------

async def retrieve_memory(agent: dict, task_description: str, top_k: int = 5) -> str:
    """Pre-task: return a prompt block of relevant remembered facts, or "" if
    memory is disabled globally/for-agent or nothing relevant is found."""
    settings_ = get_settings()
    if not settings_.get("global_enabled", True):
        return ""
    agent_id = agent.get("id")
    if not agent_id or not agent.get("memory_enabled"):
        return ""
    per = settings_.get("per_agent", {}).get(agent_id, {})
    if per.get("enabled") is False:
        return ""
    hits = search(agent_id, task_description, top_k=top_k)
    if not hits:
        return ""
    lines = "\n".join(f"- {h['content']}" for h in hits)
    return f"What you remember from past work:\n{lines}"


async def extract_and_store_memory(agent: dict, mission_id: str, task_result: str,
                                   llm=None) -> list[str]:
    """Post-task: ask the LLM to extract durable facts from the result and store
    them. Returns the stored facts. No-op if memory disabled or result empty."""
    settings_ = get_settings()
    if not settings_.get("global_enabled", True):
        return []
    agent_id = agent.get("id")
    if not agent_id or not agent.get("memory_enabled") or not (task_result or "").strip():
        return []
    per = settings_.get("per_agent", {}).get(agent_id, {})
    if per.get("enabled") is False:
        return []
    ttl = per.get("ttl_days") or agent.get("memory_ttl_days") or settings_.get("default_ttl_days", 90)

    facts: list[str] = []
    try:
        if llm is None:
            from app.llm.client import LLMClient

            llm = LLMClient()
        prompt = (
            "Review this completed task result and extract up to 5 concise, durable facts worth "
            "remembering for future tasks (specific data points, what worked, decisions). Ignore "
            'generic advice. Return ONLY a JSON array of strings.\n\n' + (task_result or "")[:3000]
        )
        res = await llm.call([{"role": "user", "content": prompt}], tier="fast")
        from app.llm.repair import extract_json

        data = extract_json(res.text or "[]")
        if isinstance(data, list):
            facts = [str(f).strip() for f in data if str(f).strip()][:5]
    except Exception:  # noqa: BLE001 — memory extraction must never break a task
        facts = []

    for fact in facts:
        write(agent_id, fact, mission_id=mission_id, department_id=agent.get("department_id"),
              ttl_days=int(ttl))
    return facts
