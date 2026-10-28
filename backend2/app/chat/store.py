"""Chat store — conversations, messages, and global context.

Backs the multi-conversation Command Center. Everything is persisted in SQLite
so chats survive reloads. A conversation groups messages; a user message can
spawn a mission whose id is stored on the following assistant message.

global_context holds a small set of durable facts (NOT full history) that are
injected into every chat for a user — e.g. "company: Acme", "tone: concise".
"""

from __future__ import annotations

import json
import uuid

from app.db.sqlite import _now, connection

DEFAULT_USER = "default-user"


def _nid() -> str:
    return uuid.uuid4().hex[:12]


# --- conversations -----------------------------------------------------------

def create_conversation(created_by: str = DEFAULT_USER, title: str = "New chat") -> dict:
    cid = _nid()
    now = _now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, title, created_by, now, now),
        )
    return {"id": cid, "title": title, "created_by": created_by, "created_at": now, "updated_at": now}


def list_conversations(created_by: str = DEFAULT_USER, limit: int = 100) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT c.*, "
            "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
            "FROM conversations c WHERE c.created_by = ? ORDER BY c.updated_at DESC LIMIT ?",
            (created_by, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    return dict(row) if row else None


def rename_conversation(conversation_id: str, title: str) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title[:120], _now(), conversation_id),
        )
    return cur.rowcount > 0


def touch_conversation(conversation_id: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conversation_id)
        )


def delete_conversation(conversation_id: str) -> bool:
    with connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return cur.rowcount > 0


# --- messages ----------------------------------------------------------------

def _decode_message(row) -> dict:
    rec = dict(row)
    rec["attachments"] = json.loads(rec.get("attachments") or "[]")
    rec["outputs"] = json.loads(rec.get("outputs") or "[]")
    rec["charts"] = json.loads(rec.get("charts") or "[]")
    return rec


def add_message(
    conversation_id: str,
    role: str,
    content: str = "",
    mission_id: str | None = None,
    attachments: list | None = None,
    outputs: list | None = None,
    status: str = "done",
) -> dict:
    mid = _nid()
    now = _now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, mission_id, "
            "attachments, outputs, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                mid, conversation_id, role, content, mission_id,
                json.dumps(attachments or []), json.dumps(outputs or []), status, now,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
        )
    return {
        "id": mid, "conversation_id": conversation_id, "role": role, "content": content,
        "mission_id": mission_id, "attachments": attachments or [], "outputs": outputs or [],
        "status": status, "created_at": now,
    }


def update_message(message_id: str, **fields) -> None:
    allowed = {"content", "mission_id", "outputs", "status", "charts"}
    bad = fields.keys() - allowed
    if bad:
        raise ValueError(f"Unknown message column(s): {bad}")
    enc = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in fields.items()}
    assignments = ", ".join(f"{k} = ?" for k in enc)
    with connection() as conn:
        conn.execute(
            f"UPDATE messages SET {assignments} WHERE id = ?",  # noqa: S608 - whitelisted
            (*enc.values(), message_id),
        )


def list_messages(conversation_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,)
        ).fetchall()
    return [_decode_message(r) for r in rows]


# --- global context ----------------------------------------------------------

def set_context(user_id: str, key: str, value: str) -> dict:
    now = _now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO global_context (id, user_id, key, value, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (_nid(), user_id, key.strip()[:80], value.strip()[:500], now, now),
        )
    return {"key": key, "value": value}


def list_context(user_id: str = DEFAULT_USER) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT key, value, updated_at FROM global_context WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_context(user_id: str, key: str) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "DELETE FROM global_context WHERE user_id = ? AND key = ?", (user_id, key)
        )
    return cur.rowcount > 0


def context_block(user_id: str = DEFAULT_USER) -> str:
    """Render global context as a short text block for prompt injection."""
    facts = list_context(user_id)
    if not facts:
        return ""
    lines = "\n".join(f"- {f['key']}: {f['value']}" for f in facts)
    return f"Known context about the user/company (apply when relevant):\n{lines}"
