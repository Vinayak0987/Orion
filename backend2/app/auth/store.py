"""MongoDB access layer for the user/website data layer.

The Mongo client is created lazily and can be swapped — real pymongo against
Atlas at runtime, or in-process mongomock in tests. Nothing else talks to Mongo
directly; go through this module.

Collections
-----------
users           { _id, email (unique, lowercased), full_name, password_hash,
                  created_at, ... }
refresh_tokens  { _id=jti, user_id, expires_at, revoked, created_at }
sessions        { _id, user_id, raw_prompt, intent_json, status, plan_json,
                  metadata_json, active_departments, skipped_departments,
                  total_tokens, total_duration_ms, completeness_score,
                  created_at, completed_at }
                  Business plan sessions with user isolation - data persists
                  across devices when MongoDB is configured.
missions        { _id, user_id, prompt, title, status, department_id,
                  conversation_id, mode, result_json, created_at, completed_at }
                  Mission execution records with user isolation - data persists
                  across devices when MongoDB is configured.
mission_tasks   { _id, mission_id, title, agent_type, agent_id, tools_needed,
                  depends_on, status, result, created_at, completed_at }
execution_traces { _id, mission_id, task_id, agent_id, trace_type, provider,
                  model, input_tokens, output_tokens, cost_usd, tool_name,
                  tool_input, tool_output, latency_ms, success, error_message,
                  created_at }
agents          { _id, name, purpose, system_prompt, agent_type, tools,
                  sub_agents, department_id, model, temperature, memory_enabled,
                  permissions, status, created_by, created_at, updated_at,
                  origin, source_mission_id, role_title }
departments     { _id, name, slug, description, purpose, responsibilities,
                  dept_type, instructions, status, config, is_default,
                  created_by, created_at, updated_at }
department_members { _id, department_id, agent_id, role, status, instructions,
                    permissions, created_at, updated_at }
conversations   { _id, title, created_by, created_at, updated_at }
messages        { _id, conversation_id, role, content, mission_id, attachments,
                  outputs, charts, status, created_at }
global_context  { _id, user_id, key, value, created_at, updated_at }
tools           { _id, name, display_name, description, type, category,
                  input_schema, config, enabled, requires_key, degraded,
                  created_at, updated_at }
mcp_servers     { _id, name, description, server_url, status, tool_count,
                  last_active, auth_token, auth_scheme, created_at }
integrations    { _id, name, description, category, auth_kind, status,
                  account_label, credential, connected_at, connect_method,
                  oauth_provider, mcp_url, docs_url, logo_key, created_at,
                  updated_at }
agent_templates { _id, name, description, category, base_config, tags,
                  is_featured, created_at }
agent_versions  { _id, agent_id, version, config, note, created_by, created_at }
documents       { _id, name, type, file_path, source_url, size_bytes,
                  chunks_count, status, department_id, processing_error,
                  uploaded_by, uploaded_at }
memory_entries  { _id, agent_id, department_id, content, source_mission_id,
                  created_at, expires_at }
oauth_connections { _id, user_id, provider, account_id, account_label,
                    access_token, refresh_token, expires_at, scopes, status,
                    created_at, updated_at }
oauth_states    { _id, user_id, provider, code_verifier, redirect_uri,
                  created_at, expires_at }
user_settings   { _id=user_id, api_keys, updated_at }
document_embeddings { _id, document_id, chunk_id, text, embedding, metadata,
                      user_id, created_at }
                    Vector search index for document chunks (replaces ChromaDB)
memory_embeddings { _id, memory_id, content, embedding, agent_id,
                     department_id, source_mission_id, user_id, created_at,
                     expires_at }
                    Vector search index for memory entries (replaces ChromaDB)
"""

from __future__ import annotations

import datetime as dt
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from app.config import settings

_client: Any = None
_db: Any = None


def _now() -> datetime:
    return datetime.now(UTC)


def configure(client: Any, db_name: str | None = None) -> None:
    """Inject a Mongo client (real or mongomock). Tests use mongomock."""
    global _client, _db
    _client = client
    _db = client[db_name or settings.mongo_db_name]
    _ensure_indexes()


def _create_real_client() -> Any:
    from pymongo import MongoClient

    if not settings.mongodb_uri.strip():
        raise RuntimeError(
            "MONGODB_URI is not set — the user/auth data layer is unavailable. "
            "Add it to .env."
        )
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
        maxPoolSize=50,
        minPoolSize=5,
    )


def get_db() -> Any:
    global _client, _db
    if _db is None:
        _client = _create_real_client()
        _db = _client[settings.mongo_db_name]
        _ensure_indexes()
    return _db


def _ensure_indexes() -> None:
    if _db is None:
        return
    _db.users.create_index("email", unique=True)
    _db.refresh_tokens.create_index("user_id")
    # Session indexes for user isolation and efficient queries
    _db.sessions.create_index([("user_id", 1), ("created_at", -1)])
    _db.sessions.create_index("status")
    # Mission indexes for user isolation and efficient queries
    _db.missions.create_index([("user_id", 1), ("created_at", -1)])
    _db.missions.create_index("status")
    # Mission tasks
    _db.mission_tasks.create_index([("mission_id", 1)])
    # Execution traces
    _db.execution_traces.create_index([("mission_id", 1)])
    _db.execution_traces.create_index([("agent_id", 1)])
    _db.execution_traces.create_index([("trace_type", 1)])  # For tool usage stats
    _db.execution_traces.create_index([("trace_type", 1), ("created_at", -1)])  # For tool stats with date
    # Agents
    _db.agents.create_index([("agent_type", 1), ("created_by", 1)])
    # Departments
    _db.departments.create_index([("created_by", 1), ("status", 1)])
    # Department members
    _db.department_members.create_index([("department_id", 1), ("status", 1)])
    _db.department_members.create_index([("agent_id", 1)])
    # Conversations
    _db.conversations.create_index([("created_by", 1), ("updated_at", -1)])
    # Messages
    _db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    # Global context
    _db.global_context.create_index([("user_id", 1)])
    _db.global_context.create_index([("user_id", 1), ("key", 1)], unique=True)
    # Tools
    _db.tools.create_index([("type", 1)])
    _db.tools.create_index([("enabled", 1)])
    _db.tools.create_index([("category", 1)])
    _db.tools.create_index([("name", 1)], unique=True)  # For fast lookups by name
    _db.tools.create_index([("category", 1), ("name", 1)])  # For sorted listing
    # Agent versions
    _db.agent_versions.create_index([("agent_id", 1), ("created_at", -1)])
    # Documents
    _db.documents.create_index([("status", 1)])
    _db.documents.create_index([("uploaded_by", 1)])
    # Memory entries
    _db.memory_entries.create_index([("agent_id", 1)])
    _db.memory_entries.create_index([("expires_at", 1)])
    # OAuth connections
    _db.oauth_connections.create_index([("user_id", 1)])
    _db.oauth_connections.create_index([("user_id", 1), ("provider", 1)], unique=True)
    # OAuth states
    _db.oauth_states.create_index([("expires_at", 1)])
    # KV store for agent tools
    _db.kv_store.create_index([("namespace", 1), ("key", 1)], unique=True)
    _db.kv_store.create_index([("expires_at", 1)])
    # Integrations
    _db.integrations.create_index([("connect_method", 1)])
    # MCP servers
    _db.mcp_servers.create_index([("server_url", 1)], unique=True)
    # Scheduled missions
    _db.scheduled_missions.create_index([("enabled", 1), ("next_run", 1)])
    _db.scheduled_missions.create_index([("created_by", 1)])
    # Document embeddings - vector search index
    try:
        _db.document_embeddings.create_search_index(
            {
                "mappings": {
                    "dynamic": True,
                    "fields": {
                        "embedding": {
                            "type": "knnVector",
                            "dimensions": 1536,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
    except Exception:
        # Index may already exist
        pass
    _db.document_embeddings.create_index([("user_id", 1)])
    _db.document_embeddings.create_index([("document_id", 1)])
    # Memory embeddings - vector search index
    try:
        _db.memory_embeddings.create_search_index(
            {
                "mappings": {
                    "dynamic": True,
                    "fields": {
                        "embedding": {
                            "type": "knnVector",
                            "dimensions": 1536,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
    except Exception:
        # Index may already exist
        pass
    _db.memory_embeddings.create_index([("agent_id", 1)])
    _db.memory_embeddings.create_index([("expires_at", 1)])


def reset_for_tests() -> None:
    global _client, _db
    _client = None
    _db = None


def is_configured() -> bool:
    """True if a client has been injected (tests) — lifespan should not override."""
    return _db is not None


# --- Users -------------------------------------------------------------------
def _normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[dict]:
    return get_db().users.find_one({"email": _normalise_email(email)})


def get_user_by_id(user_id: str) -> Optional[dict]:
    return get_db().users.find_one({"_id": user_id})


def create_user(email: str, full_name: str, password_hash: str) -> dict:
    db = get_db()
    normalised = _normalise_email(email)
    if db.users.find_one({"email": normalised}):
        raise ValueError("Email already registered")

    doc = {
        "_id": uuid.uuid4().hex,
        "email": normalised,
        "full_name": full_name.strip(),
        "password_hash": password_hash,
        "created_at": _now(),
    }
    try:
        db.users.insert_one(doc)
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "E11000" in str(exc):
            raise ValueError("Email already registered") from exc
        raise
    return doc


def update_user_password(user_id: str, password_hash: str) -> None:
    get_db().users.update_one(
        {"_id": user_id}, {"$set": {"password_hash": password_hash}}
    )


def update_user(user_id: str, **fields) -> None:
    """Update profile fields. Used by PUT /auth/me and the avatar endpoint."""
    allowed = {
        k: v
        for k, v in fields.items()
        if k in {"full_name", "email", "avatar_url", "job_title", "bio"}
    }
    if not allowed:
        return
    if "email" in allowed:
        allowed["email"] = _normalise_email(allowed["email"])
    allowed["updated_at"] = _now()
    get_db().users.update_one({"_id": user_id}, {"$set": allowed})


# --- Refresh tokens (revocable) ---------------------------------------------
def store_refresh_token(jti: str, user_id: str, expires_at: datetime) -> None:
    get_db().refresh_tokens.insert_one(
        {
            "_id": jti,
            "user_id": user_id,
            "expires_at": expires_at,
            "revoked": False,
            "created_at": _now(),
        }
    )


def is_refresh_token_active(jti: str) -> bool:
    doc = get_db().refresh_tokens.find_one({"_id": jti})
    if not doc or doc.get("revoked"):
        return False
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < _now():
            return False
    return True


def revoke_refresh_token(jti: str) -> None:
    get_db().refresh_tokens.update_one({"_id": jti}, {"$set": {"revoked": True}})


def revoke_all_user_tokens(user_id: str) -> None:
    get_db().refresh_tokens.update_many(
        {"user_id": user_id}, {"$set": {"revoked": True}}
    )


# --- Sessions (Business Plans with User Isolation) -------------------------
def create_session(
    session_id: str,
    user_id: str,
    raw_prompt: str,
    intent_json: dict | None = None,
) -> dict:
    """Create a new business plan session for a specific user."""
    db = get_db()
    doc = {
        "_id": session_id,
        "user_id": user_id,
        "raw_prompt": raw_prompt,
        "intent_json": intent_json,
        "status": "pending",
        "plan_json": None,
        "metadata_json": None,
        "active_departments": [],
        "skipped_departments": [],
        "total_tokens": 0,
        "total_duration_ms": None,
        "completeness_score": None,
        "created_at": _now(),
        "completed_at": None,
    }
    db.sessions.insert_one(doc)
    return doc


def update_session(session_id: str, **fields: Any) -> None:
    """Update session fields. Only allows updating existing sessions."""
    allowed = {
        "intent_json",
        "status",
        "plan_json",
        "metadata_json",
        "active_departments",
        "skipped_departments",
        "total_tokens",
        "total_duration_ms",
        "completeness_score",
        "completed_at",
    }
    unknown = fields.keys() - allowed
    if unknown:
        raise ValueError(f"Unknown session field(s): {sorted(unknown)}")

    update_data = {k: v for k, v in fields.items() if v is not None}
    if not update_data:
        return

    get_db().sessions.update_one({"_id": session_id}, {"$set": update_data})


def get_session(session_id: str, user_id: str) -> dict | None:
    """Get a session, but only if it belongs to the requesting user."""
    return get_db().sessions.find_one({"_id": session_id, "user_id": user_id})


def list_sessions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """List sessions for a specific user only (user isolation)."""
    cursor = (
        get_db()
        .sessions.find({"user_id": user_id})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return list(cursor)


def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a session, but only if it belongs to the requesting user."""
    result = get_db().sessions.delete_one({"_id": session_id, "user_id": user_id})
    return result.deleted_count > 0


# --- Missions (Mission Engine with User Isolation) ------------------------
def create_mission(
    mission_id: str,
    user_id: str,
    prompt: str,
    title: str | None = None,
    department_id: str | None = None,
    conversation_id: str | None = None,
    mode: str = "action",
) -> dict:
    """Create a new mission for a specific user."""
    db = get_db()
    doc = {
        "_id": mission_id,
        "user_id": user_id,
        "prompt": prompt,
        "title": title,
        "status": "planning",
        "department_id": department_id,
        "conversation_id": conversation_id,
        "mode": mode,
        "result_json": None,
        "created_at": _now(),
        "completed_at": None,
    }
    db.missions.insert_one(doc)
    return doc


def update_mission(mission_id: str, **fields: Any) -> None:
    """Update mission fields."""
    allowed = {
        "title",
        "status",
        "department_id",
        "conversation_id",
        "mode",
        "result_json",
        "completed_at",
        "progress",
        "total_tasks",
        "completed_tasks",
    }
    unknown = fields.keys() - allowed
    if unknown:
        raise ValueError(f"Unknown mission field(s): {sorted(unknown)}")

    update_data = {k: v for k, v in fields.items() if v is not None}
    if not update_data:
        return

    get_db().missions.update_one({"_id": mission_id}, {"$set": update_data})


def get_mission(mission_id: str, user_id: str) -> dict | None:
    """Get a mission, but only if it belongs to the requesting user."""
    return get_db().missions.find_one({"_id": mission_id, "user_id": user_id})


def list_missions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """List missions for a specific user only (user isolation)."""
    cursor = (
        get_db()
        .missions.find({"user_id": user_id})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return list(cursor)


def delete_mission(mission_id: str, user_id: str) -> bool:
    """Delete a mission, but only if it belongs to the requesting user."""
    result = get_db().missions.delete_one({"_id": mission_id, "user_id": user_id})
    return result.deleted_count > 0


# --- Mission Tasks ---------------------------------------------------------
def create_mission_task(task_id: str, mission_id: str, title: str, agent_type: str,
                       agent_id: str | None = None, tools_needed: list = [],
                       depends_on: list = [], status: str = "pending") -> dict:
    """Create a mission task."""
    db = get_db()
    doc = {
        "_id": task_id,
        "mission_id": mission_id,
        "title": title,
        "agent_type": agent_type,
        "agent_id": agent_id,
        "tools_needed": tools_needed,
        "depends_on": depends_on,
        "status": status,
        "result": None,
        "created_at": _now(),
        "completed_at": None,
    }
    db.mission_tasks.insert_one(doc)
    return doc


def update_mission_task(task_id: str, **fields: Any) -> None:
    """Update mission task fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        get_db().mission_tasks.update_one({"_id": task_id}, {"$set": update_data})


def get_mission_tasks(mission_id: str) -> list[dict]:
    """Get all tasks for a mission."""
    return list(get_db().mission_tasks.find({"mission_id": mission_id}))


def delete_mission_tasks(mission_id: str) -> int:
    """Delete all tasks for a mission."""
    result = get_db().mission_tasks.delete_many({"mission_id": mission_id})
    return result.deleted_count


# --- Execution Traces ------------------------------------------------------
def create_execution_trace(trace_id: str, mission_id: str, task_id: str, agent_id: str,
                          trace_type: str, provider: str | None = None, model: str | None = None,
                          input_tokens: int | None = None, output_tokens: int | None = None,
                          cost_usd: float | None = None, tool_name: str | None = None,
                          tool_input: dict | None = None, tool_output: dict | None = None,
                          latency_ms: int | None = None, success: bool = True,
                          error_message: str | None = None) -> dict:
    """Create an execution trace."""
    db = get_db()
    doc = {
        "_id": trace_id,
        "mission_id": mission_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "trace_type": trace_type,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "latency_ms": latency_ms,
        "success": 1 if success else 0,
        "error_message": error_message,
        "created_at": _now(),
    }
    db.execution_traces.insert_one(doc)
    return doc


def get_execution_traces(mission_id: str) -> list[dict]:
    """Get all traces for a mission."""
    return list(get_db().execution_traces.find({"mission_id": mission_id}).sort("created_at", 1))


def delete_execution_traces(mission_id: str) -> int:
    """Delete all traces for a mission."""
    result = get_db().execution_traces.delete_many({"mission_id": mission_id})
    return result.deleted_count


# --- Agents ----------------------------------------------------------------
def create_agent(agent_id: str, name: str, system_prompt: str, agent_type: str,
                model: str = "groq:llama-3.1-8b-instant", temperature: float = 0.7,
                tools: list = [], sub_agents: list = [], department_id: str | None = None, 
                created_by: str = "system", origin: str = "reusable", role_title: str | None = None) -> dict:
    """Create an agent."""
    db = get_db()
    doc = {
        "_id": agent_id,
        "name": name,
        "purpose": None,
        "system_prompt": system_prompt,
        "agent_type": agent_type,
        "tools": tools,
        "sub_agents": sub_agents,
        "department_id": department_id,
        "model": model,
        "temperature": temperature,
        "memory_enabled": 0,
        "permissions": {},
        "status": "active",
        "created_by": created_by,
        "created_at": _now(),
        "updated_at": _now(),
        "origin": origin,
        "source_mission_id": None,
        "role_title": role_title,
    }
    db.agents.insert_one(doc)
    return doc


def get_agent(agent_id: str) -> dict | None:
    """Get an agent by ID."""
    return get_db().agents.find_one({"_id": agent_id})


def list_agents(agent_type: str | None = None, created_by: str | None = None,
               status: str = "active") -> list[dict]:
    """List agents with optional filters."""
    query = {"status": status}
    if agent_type:
        query["agent_type"] = agent_type
    if created_by:
        query["created_by"] = created_by
    return list(get_db().agents.find(query))


def update_agent(agent_id: str, **fields: Any) -> None:
    """Update agent fields."""
    fields["updated_at"] = _now()
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        get_db().agents.update_one({"_id": agent_id}, {"$set": update_data})


def delete_agent(agent_id: str) -> bool:
    """Delete an agent."""
    result = get_db().agents.delete_one({"_id": agent_id})
    return result.deleted_count > 0


# --- Documents -------------------------------------------------------------
def create_document(doc_id: str, name: str, doc_type: str, size_bytes: int = 0,
                  chunks_count: int = 0, status: str = "processing",
                  uploaded_by: str = "default-user", file_path: str | None = None,
                  source_url: str | None = None, department_id: str | None = None) -> dict:
    """Create a document record."""
    db = get_db()
    doc = {
        "_id": doc_id,
        "name": name,
        "type": doc_type,
        "file_path": file_path,
        "source_url": source_url,
        "size_bytes": size_bytes,
        "chunks_count": chunks_count,
        "status": status,
        "department_id": department_id,
        "processing_error": None,
        "uploaded_by": uploaded_by,
        "uploaded_at": _now(),
    }
    db.documents.insert_one(doc)
    return doc


def get_document(doc_id: str) -> dict | None:
    """Get a document by ID."""
    return get_db().documents.find_one({"_id": doc_id})


def list_documents(user_id: str, status: str | None = None) -> list[dict]:
    """List documents for a user."""
    query = {"uploaded_by": user_id}
    if status:
        query["status"] = status
    return list(get_db().documents.find(query).sort("uploaded_at", -1))


def update_document(doc_id: str, **fields: Any) -> None:
    """Update document fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        get_db().documents.update_one({"_id": doc_id}, {"$set": update_data})


def delete_document(doc_id: str) -> bool:
    """Delete a document."""
    result = get_db().documents.delete_one({"_id": doc_id})
    return result.deleted_count > 0


# --- Document Embeddings (Vector Search) -----------------------------------
def add_document_embedding(embedding_id: str, document_id: str, chunk_id: str,
                         text: str, embedding: list[float], metadata: dict,
                         user_id: str) -> dict:
    """Add a document embedding for vector search."""
    db = get_db()
    doc = {
        "_id": embedding_id,
        "document_id": document_id,
        "chunk_id": chunk_id,
        "text": text,
        "embedding": embedding,
        "metadata": metadata,
        "user_id": user_id,
        "created_at": _now(),
    }
    db.document_embeddings.insert_one(doc)
    return doc


def search_document_embeddings(query_embedding: list[float], user_id: str,
                              limit: int = 5, document_id: str | None = None) -> list[dict]:
    """Search document embeddings using vector similarity."""
    db = get_db()
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": limit,
            }
        },
        {"$match": {"user_id": user_id}},
        {"$project": {"embedding": 0, "_id": 0}},
    ]
    if document_id:
        pipeline[1]["$match"]["document_id"] = document_id
    return list(db.document_embeddings.aggregate(pipeline))


def delete_document_embeddings(document_id: str) -> int:
    """Delete all embeddings for a document."""
    result = get_db().document_embeddings.delete_many({"document_id": document_id})
    return result.deleted_count


def list_document_embeddings(document_id: str) -> list[dict]:
    """List all embeddings for a document."""
    return list(get_db().document_embeddings.find({"document_id": document_id}))

def list_all_memory_entries(limit: int = 200) -> list[dict]:
    """List all memory entries."""
    return list(get_db().memory_entries.find().sort("created_at", -1).limit(limit))


# --- Memory Embeddings (Vector Search) ------------------------------------
def add_memory_embedding(embedding_id: str, memory_id: str, content: str,
                       embedding: list[float], agent_id: str, user_id: str,
                       department_id: str | None = None, source_mission_id: str | None = None,
                       expires_at: datetime | None = None) -> dict:
    """Add a memory embedding for vector search."""
    db = get_db()
    doc = {
        "_id": embedding_id,
        "memory_id": memory_id,
        "content": content,
        "embedding": embedding,
        "agent_id": agent_id,
        "department_id": department_id,
        "source_mission_id": source_mission_id,
        "user_id": user_id,
        "created_at": _now(),
        "expires_at": expires_at,
    }
    db.memory_embeddings.insert_one(doc)
    return doc


def search_memory_embeddings(query_embedding: list[float], agent_id: str,
                            limit: int = 5) -> list[dict]:
    """Search memory embeddings using vector similarity."""
    db = get_db()
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": limit,
            }
        },
        {"$match": {"agent_id": agent_id}},
        {"$project": {"embedding": 0, "_id": 0}},
    ]
    return list(db.memory_embeddings.aggregate(pipeline))


def delete_memory_embeddings(agent_id: str) -> int:
    """Delete all embeddings for an agent."""
    result = get_db().memory_embeddings.delete_many({"agent_id": agent_id})
    return result.deleted_count


def cleanup_expired_memories() -> int:
    """Delete expired memory embeddings."""
    result = get_db().memory_embeddings.delete_many({"expires_at": {"$lt": _now()}})
    return result.deleted_count


# --- Departments ------------------------------------------------------------
def create_department(dept_id: str, name: str, created_by: str = "default-user",
                      description: str = "", purpose: str = "", responsibilities: list = [],
                      slug: str = "", dept_type: str = "custom", instructions: str = "",
                      config: dict = {}, status: str = "active", is_default: bool = False) -> dict:
    """Create a department."""
    db = get_db()
    doc = {
        "_id": dept_id,
        "name": name,
        "slug": slug or name.lower().replace(" ", "-"),
        "description": description,
        "purpose": purpose,
        "responsibilities": responsibilities,
        "dept_type": dept_type,
        "instructions": instructions,
        "status": status,
        "config": config,
        "is_default": bool(is_default),
        "created_by": created_by,
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.departments.insert_one(doc)
    return doc


def get_department(dept_id: str) -> dict | None:
    """Get a department by ID."""
    return get_db().departments.find_one({"_id": dept_id})


def list_departments(created_by: str = "default-user", status: str | None = None) -> list[dict]:
    """List departments for a user."""
    query = {"$or": [{"created_by": created_by}, {"is_default": True}]}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$ne": "archived"}
    return list(get_db().departments.find(query).sort("is_default", -1).sort("created_at", 1))


def update_department(dept_id: str, **fields: Any) -> None:
    """Update department fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        update_data["updated_at"] = _now()
        get_db().departments.update_one({"_id": dept_id}, {"$set": update_data})


def delete_department(dept_id: str) -> bool:
    """Delete a department."""
    result = get_db().departments.delete_one({"_id": dept_id})
    return result.deleted_count > 0


# --- Department Members ------------------------------------------------------
def create_department_member(member_id: str, department_id: str, agent_id: str,
                           role: str = "specialist", status: str = "active",
                           instructions: str = "", permissions: dict = {}) -> dict:
    """Create a department member."""
    db = get_db()
    doc = {
        "_id": member_id,
        "department_id": department_id,
        "agent_id": agent_id,
        "role": role,
        "status": status,
        "instructions": instructions,
        "permissions": permissions,
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.department_members.insert_one(doc)
    return doc


def get_department_member(member_id: str) -> dict | None:
    """Get a department member by ID."""
    return get_db().department_members.find_one({"_id": member_id})


def list_department_members(department_id: str, status: str = "active") -> list[dict]:
    """List members of a department."""
    query = {"department_id": department_id}
    if status:
        query["status"] = status
    return list(get_db().department_members.find(query))

def list_department_members_by_agent(agent_id: str) -> list[dict]:
    """List all department memberships for an agent."""
    return list(get_db().department_members.find({"agent_id": agent_id}))


def update_department_member(member_id: str, **fields: Any) -> None:
    """Update department member fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        update_data["updated_at"] = _now()
        get_db().department_members.update_one({"_id": member_id}, {"$set": update_data})


def delete_department_member(department_id: str, agent_id: str) -> bool:
    """Delete a department member."""
    result = get_db().department_members.delete_one({"department_id": department_id, "agent_id": agent_id})
    return result.deleted_count > 0


# --- Agent Versions ---------------------------------------------------------
def create_agent_version(version_id: str, agent_id: str, version: str,
                        config: dict, note: str = "", created_by: str = "default-user") -> dict:
    """Create an agent version."""
    db = get_db()
    doc = {
        "_id": version_id,
        "agent_id": agent_id,
        "version": version,
        "config": config,
        "note": note,
        "created_by": created_by,
        "created_at": _now(),
    }
    db.agent_versions.insert_one(doc)
    return doc


def get_agent_version(version_id: str) -> dict | None:
    """Get an agent version by ID."""
    return get_db().agent_versions.find_one({"_id": version_id})


def list_agent_versions(agent_id: str) -> list[dict]:
    """List versions of an agent."""
    return list(get_db().agent_versions.find({"agent_id": agent_id}).sort("created_at", -1))


# --- Agent Templates --------------------------------------------------------
def create_agent_template(template_id: str, name: str, description: str = "",
                         category: str = "", base_config: dict = {}, tags: list = [],
                         is_featured: bool = False) -> dict:
    """Create an agent template."""
    db = get_db()
    doc = {
        "_id": template_id,
        "name": name,
        "description": description,
        "category": category,
        "base_config": base_config,
        "tags": tags,
        "is_featured": is_featured,
        "created_at": _now(),
    }
    db.agent_templates.insert_one(doc)
    return doc


def get_agent_template(template_id: str) -> dict | None:
    """Get an agent template by ID."""
    return get_db().agent_templates.find_one({"_id": template_id})


def list_agent_templates() -> list[dict]:
    """List all agent templates."""
    return list(get_db().agent_templates.find().sort("is_featured", -1).sort("name", 1))


# --- Conversations ----------------------------------------------------------
def create_conversation(conversation_id: str, title: str, created_by: str = "default-user") -> dict:
    """Create a conversation."""
    db = get_db()
    doc = {
        "_id": conversation_id,
        "title": title,
        "created_by": created_by,
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.conversations.insert_one(doc)
    return doc


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation by ID."""
    return get_db().conversations.find_one({"_id": conversation_id})


def list_conversations(created_by: str = "default-user", limit: int = 100) -> list[dict]:
    """List conversations for a user."""
    return list(get_db().conversations.find({"created_by": created_by}).sort("updated_at", -1).limit(limit))


def update_conversation(conversation_id: str, **fields: Any) -> None:
    """Update conversation fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        update_data["updated_at"] = _now()
        get_db().conversations.update_one({"_id": conversation_id}, {"$set": update_data})


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation."""
    get_db().messages.delete_many({"conversation_id": conversation_id})
    result = get_db().conversations.delete_one({"_id": conversation_id})
    return result.deleted_count > 0


# --- Messages ---------------------------------------------------------------
def create_message(message_id: str, conversation_id: str, role: str, content: str = "",
                  mission_id: str | None = None, attachments: list = [], outputs: list = [],
                  status: str = "done") -> dict:
    """Create a message."""
    db = get_db()
    doc = {
        "_id": message_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "mission_id": mission_id,
        "attachments": attachments,
        "outputs": outputs,
        "charts": [],
        "status": status,
        "created_at": _now(),
    }
    db.messages.insert_one(doc)
    # Update conversation timestamp
    update_conversation(conversation_id)
    return doc


def get_message(message_id: str) -> dict | None:
    """Get a message by ID."""
    return get_db().messages.find_one({"_id": message_id})


def list_messages(conversation_id: str) -> list[dict]:
    """List messages for a conversation."""
    return list(get_db().messages.find({"conversation_id": conversation_id}).sort("created_at", 1))


def update_message(message_id: str, **fields: Any) -> None:
    """Update message fields."""
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        get_db().messages.update_one({"_id": message_id}, {"$set": update_data})


def delete_messages(conversation_id: str) -> int:
    """Delete all messages for a conversation."""
    result = get_db().messages.delete_many({"conversation_id": conversation_id})
    return result.deleted_count


# --- Global Context ---------------------------------------------------------
def set_global_context(context_id: str, user_id: str, key: str, value: str) -> dict:
    """Set a global context value (upsert)."""
    db = get_db()
    update_doc = {
        "user_id": user_id,
        "key": key.strip()[:80],
        "value": value.strip()[:500],
        "updated_at": _now(),
    }
    result = db.global_context.update_one({"user_id": user_id, "key": key.strip()[:80]}, {"$set": update_doc}, upsert=True)
    if result.upserted_id:
        update_doc["_id"] = result.upserted_id
        update_doc["created_at"] = _now()
    return update_doc


def get_global_context(user_id: str, key: str) -> dict | None:
    """Get a global context value."""
    return get_db().global_context.find_one({"user_id": user_id, "key": key})


def list_global_context(user_id: str = "default-user") -> list[dict]:
    """List all global context for a user."""
    return list(get_db().global_context.find({"user_id": user_id}).sort("updated_at", -1))


def delete_global_context(user_id: str, key: str) -> bool:
    """Delete a global context value."""
    result = get_db().global_context.delete_one({"user_id": user_id, "key": key})
    return result.deleted_count > 0


# --- Memory Entries ---------------------------------------------------------
def create_memory_entry(entry_id: str, agent_id: str, content: str,
                      department_id: str | None = None, source_mission_id: str | None = None,
                      expires_at: datetime | None = None) -> dict:
    """Create a memory entry."""
    db = get_db()
    doc = {
        "_id": entry_id,
        "agent_id": agent_id,
        "department_id": department_id,
        "content": content,
        "source_mission_id": source_mission_id,
        "created_at": _now(),
        "expires_at": expires_at,
    }
    db.memory_entries.insert_one(doc)
    return doc


def get_memory_entry(entry_id: str) -> dict | None:
    """Get a memory entry by ID."""
    return get_db().memory_entries.find_one({"_id": entry_id})


def list_memory_entries(agent_id: str, limit: int = 50) -> list[dict]:
    """List memory entries for an agent."""
    return list(get_db().memory_entries.find({"agent_id": agent_id}).sort("created_at", -1).limit(limit))


def delete_memory_entry(entry_id: str) -> bool:
    """Delete a memory entry."""
    result = get_db().memory_entries.delete_one({"_id": entry_id})
    return result.deleted_count > 0


def count_memory_entries_by_agent() -> dict:
    """Count memory entries grouped by agent_id from MongoDB."""
    db = get_db()
    # Simple aggregation without expiration filter first
    pipeline = [
        {"$group": {"_id": "$agent_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    results = list(db.memory_entries.aggregate(pipeline))
    return {r["_id"]: r["count"] for r in results}


# --- OAuth States (one-time CSRF + PKCE) ------------------------------------
def create_oauth_state(state: str, user_id: str, provider: str, code_verifier: str | None,
                       redirect_uri: str, ttl_minutes: int = 10) -> None:
    """Create an OAuth state record."""
    now = _now()
    expires = (now + dt.timedelta(minutes=ttl_minutes)).isoformat() if isinstance(now, datetime) else now
    db = get_db()
    doc = {
        "_id": state,
        "user_id": user_id,
        "provider": provider,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "created_at": now,
        "expires_at": expires,
    }
    db.oauth_states.insert_one(doc)


def consume_oauth_state(state: str) -> dict | None:
    """Fetch AND delete an OAuth state (one-time use). Returns None if missing/expired."""
    db = get_db()
    doc = db.oauth_states.find_one({"_id": state})
    if doc is None:
        return None
    db.oauth_states.delete_one({"_id": state})
    # Check expiration
    expires_at = doc.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < _now():
            return None
    return doc


def purge_expired_oauth_states() -> int:
    """Delete expired OAuth states."""
    db = get_db()
    result = db.oauth_states.delete_many({"expires_at": {"$lt": _now()}})
    return result.deleted_count


# --- OAuth Connections -------------------------------------------------------
def upsert_oauth_connection(*, user_id: str, provider: str, access_token: str,
                           refresh_token: str | None, expires_at: str | None,
                           scopes: list[str], account_id: str = "", account_label: str = "") -> str:
    """Create or update an OAuth connection."""
    from app.core.crypto import decrypt, encrypt

    db = get_db()
    now = _now()
    existing = db.oauth_connections.find_one({"user_id": user_id, "provider": provider})
    conn_id = existing["_id"] if existing else uuid.uuid4().hex

    doc = {
        "_id": conn_id,
        "user_id": user_id,
        "provider": provider,
        "account_id": account_id,
        "account_label": account_label,
        "access_token": encrypt(access_token),
        "refresh_token": encrypt(refresh_token) if refresh_token else None,
        "expires_at": expires_at,
        "scopes": scopes,
        "status": "connected",
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
    }

    if existing:
        db.oauth_connections.update_one({"_id": conn_id}, {"$set": doc})
    else:
        db.oauth_connections.insert_one(doc)

    return conn_id


def update_oauth_tokens(*, user_id: str, provider: str, access_token: str,
                        refresh_token: str | None, expires_at: str | None) -> None:
    """Update OAuth tokens after refresh."""
    from app.core.crypto import decrypt, encrypt

    db = get_db()
    existing = db.oauth_connections.find_one({"user_id": user_id, "provider": provider})
    if existing:
        keep_refresh = existing.get("refresh_token")
        new_refresh = encrypt(refresh_token) if refresh_token else keep_refresh
        db.oauth_connections.update_one(
            {"user_id": user_id, "provider": provider},
            {
                "$set": {
                    "access_token": encrypt(access_token),
                    "refresh_token": new_refresh,
                    "expires_at": expires_at,
                    "status": "connected",
                    "updated_at": _now(),
                }
            },
        )


def set_oauth_connection_status(user_id: str, provider: str, status: str) -> None:
    """Set OAuth connection status."""
    db = get_db()
    db.oauth_connections.update_one(
        {"user_id": user_id, "provider": provider},
        {"$set": {"status": status, "updated_at": _now()}},
    )


def get_oauth_connection(user_id: str, provider: str) -> dict | None:
    """Get OAuth connection WITH decrypted tokens (for token service only)."""
    from app.core.crypto import decrypt

    db = get_db()
    doc = db.oauth_connections.find_one({"user_id": user_id, "provider": provider})
    if doc is None:
        return None
    # Decrypt tokens
    if doc.get("access_token"):
        doc["access_token"] = decrypt(doc["access_token"])
    if doc.get("refresh_token"):
        doc["refresh_token"] = decrypt(doc["refresh_token"])
    return doc


def get_oauth_connection_public(user_id: str, provider: str) -> dict | None:
    """Get OAuth connection WITHOUT tokens (safe for API responses)."""
    db = get_db()
    doc = db.oauth_connections.find_one({"user_id": user_id, "provider": provider})
    if doc is None:
        return None
    # Strip sensitive fields
    return {
        "id": doc["_id"],
        "provider": doc["provider"],
        "account_id": doc.get("account_id"),
        "account_label": doc.get("account_label"),
        "status": doc["status"],
        "expires_at": doc.get("expires_at"),
        "scopes": doc.get("scopes", []),
        "connected": doc["status"] == "connected",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def list_oauth_connections_public(user_id: str) -> list[dict]:
    """List all OAuth connections for a user WITHOUT tokens."""
    db = get_db()
    docs = db.oauth_connections.find({"user_id": user_id}).sort("provider", 1)
    return [
        {
            "id": d["_id"],
            "provider": d["provider"],
            "account_id": d.get("account_id"),
            "account_label": d.get("account_label"),
            "status": d["status"],
            "expires_at": d.get("expires_at"),
            "scopes": d.get("scopes", []),
            "connected": d["status"] == "connected",
            "created_at": d.get("created_at"),
            "updated_at": d.get("updated_at"),
        }
        for d in docs
    ]


def delete_oauth_connection(user_id: str, provider: str) -> bool:
    """Delete an OAuth connection."""
    db = get_db()
    result = db.oauth_connections.delete_one({"user_id": user_id, "provider": provider})
    return result.deleted_count > 0


def get_oauth_user_id_for_provider(provider: str) -> str | None:
    """Get the user_id for a connected OAuth provider (single-tenant helper)."""
    db = get_db()
    doc = db.oauth_connections.find_one({"provider": provider, "status": "connected"})
    return doc["user_id"] if doc else None


# --- Integrations -----------------------------------------------------------
def seed_integrations(catalog: list[dict]) -> int:
    """Seed integrations catalog from a list of dicts."""
    db = get_db()
    now = _now()
    count = 0
    for it in catalog:
        auth_kind = {"oauth": "oauth", "mcp": "token", "api_key": "api_key"}.get(it.get("connect_method", "api_key"), "api_key")
        doc = {
            "_id": it["id"],
            "name": it["name"],
            "description": it.get("description", ""),
            "category": it.get("category", ""),
            "auth_kind": auth_kind,
            "status": "available",
            "connect_method": it.get("connect_method", "api_key"),
            "oauth_provider": it.get("oauth_provider"),
            "mcp_url": it.get("mcp_url"),
            "docs_url": it.get("docs_url"),
            "logo_key": it.get("logo_key"),
            "credential": None,
            "account_label": None,
            "connected_at": None,
            "created_at": now,
            "updated_at": now,
        }
        db.integrations.update_one({"_id": it["id"]}, {"$set": doc}, upsert=True)
        count += 1
    return count


def list_integrations() -> list[dict]:
    """List all integrations."""
    db = get_db()
    rows = db.integrations.find().sort("name", 1)
    out = []
    mcp_servers = list(db.mcp_servers.find({}, {"server_url": 1, "status": 1}))
    mcp_status = {r["server_url"]: r["status"] for r in mcp_servers}
    for r in rows:
        doc = dict(r)
        doc.pop("credential", None)  # never expose credential
        doc["has_credential"] = bool(doc.get("credential"))
        if doc.get("connect_method") == "mcp" and doc.get("mcp_url") in mcp_status:
            st = mcp_status[doc["mcp_url"]]
            doc["status"] = "connected" if st == "connected" else "available"
            doc["via_mcp"] = True
        out.append(doc)
    return out


def get_integration(integration_id: str) -> dict | None:
    """Get an integration by ID."""
    db = get_db()
    doc = db.integrations.find_one({"_id": integration_id})
    if doc:
        doc = dict(doc)
        doc.pop("credential", None)
    return doc


def update_integration(integration_id: str, **fields: Any) -> None:
    """Update integration fields."""
    from app.core.crypto import encrypt

    db = get_db()
    update_data = {}
    for k, v in fields.items():
        if v is not None:
            # Encrypt credential field if present
            if k == "credential":
                update_data[k] = encrypt(v)
            else:
                update_data[k] = v
    if update_data:
        update_data["updated_at"] = _now()
        db.integrations.update_one({"_id": integration_id}, {"$set": update_data})


# --- MCP Servers -------------------------------------------------------------
def create_mcp_server(*, name: str, server_url: str, description: str = "", tool_count: int = 0,
                      auth_token: str | None = None, auth_scheme: str = "bearer",
                      refresh_token: str | None = None, oauth_config: str | None = None) -> str:
    """Create or update an MCP server."""
    from app.core.crypto import encrypt

    db = get_db()
    sid = uuid.uuid4().hex
    now = _now()
    enc = encrypt(auth_token) if auth_token else None
    enc_refresh = encrypt(refresh_token) if refresh_token else None

    doc = {
        "_id": sid,
        "name": name,
        "description": description,
        "server_url": server_url,
        "status": "connected",
        "tool_count": tool_count,
        "last_active": now,
        "auth_token": enc,
        "auth_scheme": auth_scheme,
        "refresh_token": enc_refresh,
        "oauth_config": oauth_config,
        "created_at": now,
    }

    existing = db.mcp_servers.find_one({"server_url": server_url})
    if existing:
        db.mcp_servers.update_one({"server_url": server_url}, {"$set": doc})
        return existing["_id"]
    else:
        db.mcp_servers.insert_one(doc)
        return sid


def update_mcp_server_tokens(server_url: str, access_token: str, refresh_token: str | None) -> None:
    """Rotate MCP server tokens after refresh."""
    from app.core.crypto import encrypt

    db = get_db()
    existing = db.mcp_servers.find_one({"server_url": server_url})
    if existing:
        keep = existing.get("refresh_token")
        new_refresh = encrypt(refresh_token) if refresh_token else keep
        db.mcp_servers.update_one(
            {"server_url": server_url},
            {
                "$set": {
                    "auth_token": encrypt(access_token),
                    "refresh_token": new_refresh,
                    "last_active": _now(),
                }
            },
        )


def list_mcp_servers() -> list[dict]:
    """List all MCP servers."""
    db = get_db()
    rows = db.mcp_servers.find().sort("created_at", -1)
    out = []
    for r in rows:
        doc = dict(r)
        doc.pop("auth_token", None)  # never expose token
        doc.pop("refresh_token", None)
        doc["has_auth"] = bool(doc.get("auth_token"))
        out.append(doc)
    return out


def get_mcp_server(server_url: str) -> dict | None:
    """Get an MCP server by URL (WITH decrypted tokens for internal use)."""
    from app.core.crypto import decrypt

    db = get_db()
    doc = db.mcp_servers.find_one({"server_url": server_url})
    if doc:
        doc = dict(doc)
        if doc.get("auth_token"):
            doc["auth_token"] = decrypt(doc["auth_token"])
        if doc.get("refresh_token"):
            doc["refresh_token"] = decrypt(doc["refresh_token"])
    return doc


def delete_mcp_server(server_url: str) -> bool:
    """Delete an MCP server."""
    db = get_db()
    result = db.mcp_servers.delete_one({"server_url": server_url})
    return result.deleted_count > 0


# --- Scheduled Missions ------------------------------------------------------
def create_scheduled_mission(schedule_id: str, prompt: str, department_id: str | None = None,
                             mode: str = "planning", cadence: str = "daily",
                             interval_minutes: int = 1440, enabled: bool = True,
                             next_run: str | None = None, created_by: str = "default-user") -> dict:
    """Create a scheduled mission."""
    db = get_db()
    now = _now()
    if next_run is None:
        next_run = now.isoformat()
    doc = {
        "_id": schedule_id,
        "prompt": prompt,
        "department_id": department_id,
        "mode": mode,
        "cadence": cadence,
        "interval_minutes": interval_minutes,
        "enabled": enabled,
        "next_run": next_run,
        "last_run": None,
        "last_mission_id": None,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    db.scheduled_missions.insert_one(doc)
    return doc


def list_scheduled_missions(enabled_only: bool = False) -> list[dict]:
    """List scheduled missions."""
    db = get_db()
    query = {"enabled": True} if enabled_only else {}
    return list(db.scheduled_missions.find(query).sort("next_run", 1))


def update_scheduled_mission(schedule_id: str, **fields: Any) -> None:
    """Update scheduled mission fields."""
    db = get_db()
    update_data = {k: v for k, v in fields.items() if v is not None}
    if update_data:
        update_data["updated_at"] = _now()
        db.scheduled_missions.update_one({"_id": schedule_id}, {"$set": update_data})


def delete_scheduled_mission(schedule_id: str) -> bool:
    """Delete a scheduled mission."""
    db = get_db()
    result = db.scheduled_missions.delete_one({"_id": schedule_id})
    return result.deleted_count > 0
