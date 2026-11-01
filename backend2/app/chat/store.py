"""Chat store — conversations, messages, and global context.

Backs the multi-conversation Command Center. Everything is persisted in MongoDB
so chats survive reloads. A conversation groups messages; a user message can
spawn a mission whose id is stored on the following assistant message.

global_context holds a small set of durable facts (NOT full history) that are
injected into every chat for a user — e.g. "company: Acme", "tone: concise".
"""

from __future__ import annotations

import json
import uuid

from app.auth import store as auth_store

DEFAULT_USER = "default-user"


def _nid() -> str:
    return uuid.uuid4().hex[:12]


# --- conversations -----------------------------------------------------------

def create_conversation(created_by: str = DEFAULT_USER, title: str = "New chat") -> dict:
    """Create a conversation in MongoDB."""
    cid = _nid()
    doc = auth_store.create_conversation(cid, title, created_by)
    return {"id": doc["_id"], "title": doc["title"], "created_by": doc["created_by"],
            "created_at": doc["created_at"], "updated_at": doc["updated_at"]}


def list_conversations(created_by: str = DEFAULT_USER, limit: int = 100) -> list[dict]:
    """List conversations from MongoDB with batch-optimized message counts."""
    convs = auth_store.list_conversations(created_by, limit)
    
    # Collect all conversation IDs
    conv_ids = [c.get("_id") for c in convs]
    
    # Batch count messages for all conversations in a single aggregation query
    db = auth_store.get_db()
    pipeline = [
        {"$match": {"conversation_id": {"$in": conv_ids}}},
        {"$group": {"_id": "$conversation_id", "count": {"$sum": 1}}}
    ]
    message_counts = {doc["_id"]: doc["count"] for doc in db.messages.aggregate(pipeline)}
    
    out = []
    for c in convs:
        doc = dict(c)
        doc["id"] = doc.pop("_id")
        # Get message count from pre-fetched batch
        doc["message_count"] = message_counts.get(doc["id"], 0)
        # Normalize timestamp format
        if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        if "updated_at" in doc and hasattr(doc["updated_at"], "isoformat"):
            doc["updated_at"] = doc["updated_at"].isoformat()
        out.append(doc)
    return out


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation from MongoDB."""
    doc = auth_store.get_conversation(conversation_id)
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


def rename_conversation(conversation_id: str, title: str) -> bool:
    """Rename a conversation in MongoDB."""
    auth_store.update_conversation(conversation_id, title=title[:120])
    return True


def touch_conversation(conversation_id: str) -> None:
    """Update conversation timestamp in MongoDB."""
    auth_store.update_conversation(conversation_id)


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation from MongoDB."""
    return auth_store.delete_conversation(conversation_id)


# --- messages ----------------------------------------------------------------

def _decode_message(doc: dict) -> dict:
    """Convert MongoDB doc to message dict."""
    rec = dict(doc)
    rec["id"] = rec.pop("_id")
    rec["attachments"] = rec.get("attachments") or []
    rec["outputs"] = rec.get("outputs") or []
    rec["charts"] = rec.get("charts") or []
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
    """Add a message to MongoDB."""
    mid = _nid()
    doc = auth_store.create_message(
        message_id=mid,
        conversation_id=conversation_id,
        role=role,
        content=content,
        mission_id=mission_id,
        attachments=attachments or [],
        outputs=outputs or [],
        status=status
    )
    return {
        "id": doc["_id"], "conversation_id": doc["conversation_id"], "role": doc["role"],
        "content": doc["content"], "mission_id": doc["mission_id"],
        "attachments": doc["attachments"], "outputs": doc["outputs"],
        "status": doc["status"], "created_at": doc["created_at"],
    }


def update_message(message_id: str, **fields) -> None:
    """Update a message in MongoDB."""
    allowed = {"content", "mission_id", "outputs", "status", "charts"}
    bad = fields.keys() - allowed
    if bad:
        raise ValueError(f"Unknown message column(s): {bad}")
    auth_store.update_message(message_id, **fields)


def list_messages(conversation_id: str) -> list[dict]:
    """List messages from MongoDB."""
    messages = auth_store.list_messages(conversation_id)
    return [_decode_message(m) for m in messages]


# --- global context ----------------------------------------------------------

def set_context(user_id: str, key: str, value: str) -> dict:
    """Set global context in MongoDB."""
    context_id = _nid()
    auth_store.set_global_context(context_id, user_id, key, value)
    return {"key": key, "value": value}


def list_context(user_id: str = DEFAULT_USER) -> list[dict]:
    """List global context from MongoDB."""
    contexts = auth_store.list_global_context(user_id)
    return [{"key": c["key"], "value": c["value"], "updated_at": c["updated_at"]} for c in contexts]


def delete_context(user_id: str, key: str) -> bool:
    """Delete global context from MongoDB."""
    return auth_store.delete_global_context(user_id, key)


def context_block(user_id: str = DEFAULT_USER) -> str:
    """Render global context as a short text block for prompt injection."""
    facts = list_context(user_id)
    if not facts:
        return ""
    lines = "\n".join(f"- {f['key']}: {f['value']}" for f in facts)
    return f"Known context about the user/company (apply when relevant):\n{lines}"
