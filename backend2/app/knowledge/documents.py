"""Documents table store — metadata rows for uploaded knowledge documents.

The chunk vectors live in MongoDB Vector Search; this table is the
UI-facing record: name, type, size, chunk count, status, source. One row per
uploaded file/URL.
"""

from __future__ import annotations

import uuid

from app.auth import store as auth_store


def create_document(*, name: str, type: str, uploaded_by: str = "default-user",
                    file_path: str | None = None, source_url: str | None = None,
                    size_bytes: int = 0, department_id: str | None = None,
                    chroma_collection_id: str = "", status: str = "processing") -> str:
    """Create a document in MongoDB."""
    doc_id = uuid.uuid4().hex
    auth_store.create_document(
        doc_id=doc_id,
        name=name,
        doc_type=type,
        size_bytes=size_bytes,
        chunks_count=0,
        status=status,
        uploaded_by=uploaded_by,
        file_path=file_path,
        source_url=source_url,
        department_id=department_id,
    )
    return doc_id


def mark_active(doc_id: str, chunks_count: int, chroma_collection_id: str = "") -> None:
    """Mark document as active in MongoDB."""
    auth_store.update_document(doc_id, status="active", chunks_count=chunks_count)


def mark_error(doc_id: str, error: str) -> None:
    """Mark document as having an error in MongoDB."""
    auth_store.update_document(doc_id, status="error", processing_error=error)


def mark_uploaded(doc_id: str, size_bytes: int = 0) -> None:
    """Document stored but NOT yet chunked/indexed (status='uploaded')."""
    auth_store.update_document(doc_id, status="uploaded", chunks_count=0)


def get_document(doc_id: str) -> dict | None:
    """Get a document from MongoDB."""
    doc = auth_store.get_document(doc_id)
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


def list_documents(*, uploaded_by: str = "default-user", type: str | None = None,
                   status: str | None = None, search: str | None = None) -> list[dict]:
    """List documents from MongoDB."""
    docs = auth_store.list_documents(uploaded_by, status=status)
    
    if type:
        docs = [d for d in docs if d.get("type") == type]
    if search:
        search_lower = search.lower()
        docs = [d for d in docs if search_lower in d.get("name", "").lower()]
    
    out = []
    for d in docs:
        doc = dict(d)
        doc["id"] = doc.pop("_id")
        out.append(doc)
    return out


def delete_document(doc_id: str) -> bool:
    """Delete a document from MongoDB."""
    return auth_store.delete_document(doc_id)


def summary(uploaded_by: str = "default-user") -> dict:
    """Get document summary from MongoDB."""
    docs = auth_store.list_documents(uploaded_by)
    total_chunks = sum(d.get("chunks_count", 0) for d in docs)
    # Handle both datetime and string timestamps
    timestamps = [d.get("uploaded_at") for d in docs if d.get("uploaded_at")]
    if timestamps:
        # Convert all to datetime if needed, normalizing timezone awareness
        from datetime import datetime
        normalized = []
        for ts in timestamps:
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts)
                    # Make all datetimes offset-naive for comparison
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    normalized.append(dt)
                except:
                    pass
            elif isinstance(ts, datetime):
                # Make all datetimes offset-naive for comparison
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                normalized.append(ts)
        last_updated = max(normalized) if normalized else None
    else:
        last_updated = None
    return {"documents": len(docs), "chunks": total_chunks, "last_updated": last_updated}


def allowed_document_ids(agent_id: str | None) -> list[str] | None:
    """Documents an acting agent may retrieve from:
      • org-wide docs (department_id IS NULL), PLUS
      • docs in any department the agent belongs to.
    Returns a list of allowed doc ids, or None meaning 'no scoping' (agent not
    in any department → sees org-wide only, handled by returning that set).
    """
    from app.departments.store import agent_department_ids
    
    # Get all documents for the user
    docs = auth_store.list_documents("default-user")  # Note: need to pass actual user_id
    
    # Get org-wide docs (no department_id)
    org = [d["_id"] for d in docs if not d.get("department_id")]
    
    # Get docs in agent's departments
    dept_ids = agent_department_ids(agent_id) if agent_id else []
    scoped = []
    if dept_ids:
        scoped = [d["_id"] for d in docs if d.get("department_id") in dept_ids]
    
    return list(dict.fromkeys(org + scoped))
