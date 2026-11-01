"""Episodic agent memory store.

Mirrors the knowledge document store: facts an agent learns are embedded into
MongoDB Vector Search, and ALWAYS recorded in the `memory_entries` collection
(for the Memory UI + a keyword fallback search).

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

from app.auth import store as auth_store

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall((s or "").lower()))


async def write(agent_id: str, content: str, *, mission_id: str | None = None,
          department_id: str | None = None, ttl_days: int = 30) -> str:
    """Write a memory entry to MongoDB with vector embedding."""
    content = (content or "").strip()
    if not content:
        return ""
    entry_id = uuid.uuid4().hex
    now = dt.datetime.now(dt.UTC)
    expires = (now + dt.timedelta(days=max(1, ttl_days)))

    # Store in MongoDB memory_entries collection
    auth_store.create_memory_entry(
        entry_id=entry_id,
        agent_id=agent_id,
        content=content,
        department_id=department_id,
        source_mission_id=mission_id,
        expires_at=expires
    )

    # Generate and store embedding for vector search
    try:
        from app.llm.embeddings import get_embedding_client

        embedding_client = get_embedding_client()
        embedding = await embedding_client.embed_text(content)

        if embedding and any(embedding):
            embedding_id = f"{entry_id}:emb"
            auth_store.add_memory_embedding(
                embedding_id=embedding_id,
                memory_id=entry_id,
                content=content,
                embedding=embedding,
                agent_id=agent_id,
                user_id="default-user",  # Memory is per-agent, not per-user
                department_id=department_id,
                source_mission_id=mission_id,
                expires_at=expires,
            )
    except Exception:  # noqa: BLE001 — embedding failure should not break memory write
        pass

    return entry_id


async def search(agent_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Search memory entries using vector similarity, keyword fallback."""
    query = (query or "").strip()
    if not query:
        return []

    # Primary: Try vector search using MongoDB's $vectorSearch
    try:
        from app.llm.embeddings import get_embedding_client

        embedding_client = get_embedding_client()
        query_embedding = await embedding_client.embed_text(query)

        if query_embedding and any(query_embedding):  # Non-zero vector
            results = auth_store.search_memory_embeddings(
                query_embedding=query_embedding,
                agent_id=agent_id,
                limit=top_k,
            )

            if results:
                return [{"id": r.get("memory_id"), "content": r.get("content"), "score": 1.0,
                        "created_at": r.get("created_at")} for r in results]
    except Exception:
        # Vector search failed, fall through to keyword search
        pass

    # Fallback: Keyword matching
    q = _tokens(query)
    entries = auth_store.list_memory_entries(agent_id, limit=100)

    scored = []
    for entry in entries:
        entry_dict = dict(entry)
        entry_dict["id"] = entry_dict.pop("_id")
        overlap = len(q & _tokens(entry_dict.get("content", "")))
        if overlap:
            scored.append((overlap, entry_dict))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"id": r["id"], "content": r["content"], "score": s, "created_at": r["created_at"]}
            for s, r in scored[:top_k]]


def read(agent_id: str, limit: int = 50) -> list[dict]:
    """Read memory entries for an agent from MongoDB."""
    entries = auth_store.list_memory_entries(agent_id, limit=limit)
    out = []
    for entry in entries:
        e = dict(entry)
        e["id"] = e.pop("_id")
        out.append(e)
    return out


def list_all(limit: int = 200) -> list[dict]:
    """List all memory entries from MongoDB."""
    entries = auth_store.list_all_memory_entries(limit)
    out = []
    for entry in entries:
        e = dict(entry)
        e["id"] = e.pop("_id")
        out.append(e)
    return out


def delete(entry_id: str) -> bool:
    """Delete a memory entry from MongoDB."""
    return auth_store.delete_memory_entry(entry_id)


def clear_agent(agent_id: str) -> int:
    """Clear all memory entries for an agent from MongoDB."""
    # Delete from memory_entries collection
    db = auth_store.get_db()
    result = db.memory_entries.delete_many({"agent_id": agent_id})
    # Also delete embeddings
    auth_store.delete_memory_embeddings(agent_id)
    return result.deleted_count


def purge_expired() -> int:
    """Purge expired memory entries from MongoDB."""
    return auth_store.cleanup_expired_memories()


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
    """Get memory settings from MongoDB."""
    # Note: Need to implement kv_store methods in auth_store
    # For now, return default settings
    return dict(_DEFAULT_SETTINGS)


def update_settings(changes: dict) -> dict:
    """Update memory settings in MongoDB."""
    # Note: Need to implement kv_store methods in auth_store
    current = get_settings()
    current.update({k: v for k, v in changes.items() if k in _DEFAULT_SETTINGS})
    return current


def count_by_agent() -> dict:
    """Count memory entries by agent from MongoDB."""
    return auth_store.count_memory_entries_by_agent()


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
        await write(agent_id, fact, mission_id=mission_id, department_id=agent.get("department_id"),
                    ttl_days=int(ttl))
    return facts
