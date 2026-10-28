"""Documents table store — metadata rows for uploaded knowledge documents.

The chunk vectors live in ChromaDB (or the keyword fallback); this table is the
UI-facing record: name, type, size, chunk count, status, source. One row per
uploaded file/URL.
"""

from __future__ import annotations

import uuid

from app.db.sqlite import _now, connection


def create_document(*, name: str, type: str, uploaded_by: str = "default-user",
                    file_path: str | None = None, source_url: str | None = None,
                    size_bytes: int = 0, department_id: str | None = None,
                    chroma_collection_id: str = "", status: str = "processing") -> str:
    doc_id = uuid.uuid4().hex
    with connection() as conn:
        conn.execute(
            """INSERT INTO documents
               (id, name, type, file_path, source_url, size_bytes, chunks_count, status,
                department_id, chroma_collection_id, processing_error, uploaded_by, uploaded_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, name, type, file_path, source_url, size_bytes, 0, status,
             department_id, chroma_collection_id, None, uploaded_by, _now()),
        )
    return doc_id


def mark_active(doc_id: str, chunks_count: int, chroma_collection_id: str = "") -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE documents SET status='active', chunks_count=?, chroma_collection_id=? WHERE id=?",
            (chunks_count, chroma_collection_id, doc_id),
        )


def mark_error(doc_id: str, error: str) -> None:
    with connection() as conn:
        conn.execute("UPDATE documents SET status='error', processing_error=? WHERE id=?", (error, doc_id))


def mark_uploaded(doc_id: str, size_bytes: int = 0) -> None:
    """Document stored but NOT yet chunked/indexed (status='uploaded')."""
    with connection() as conn:
        conn.execute("UPDATE documents SET status='uploaded', chunks_count=0 WHERE id=?", (doc_id,))


def get_document(doc_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    return dict(row) if row else None


def list_documents(*, uploaded_by: str = "default-user", type: str | None = None,
                   status: str | None = None, search: str | None = None) -> list[dict]:
    q = "SELECT * FROM documents WHERE uploaded_by=?"
    params: list = [uploaded_by]
    if type:
        q += " AND type=?"; params.append(type)
    if status:
        q += " AND status=?"; params.append(status)
    if search:
        q += " AND name LIKE ?"; params.append(f"%{search}%")
    q += " ORDER BY uploaded_at DESC"
    with connection() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    return cur.rowcount > 0


def summary(uploaded_by: str = "default-user") -> dict:
    with connection() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS docs, COALESCE(SUM(chunks_count),0) AS chunks,
                      MAX(uploaded_at) AS last_updated
               FROM documents WHERE uploaded_by=?""",
            (uploaded_by,),
        ).fetchone()
    return {"documents": row["docs"], "chunks": row["chunks"], "last_updated": row["last_updated"]}



def allowed_document_ids(agent_id: str | None) -> list[str] | None:
    """Documents an acting agent may retrieve from:
      • org-wide docs (department_id IS NULL), PLUS
      • docs in any department the agent belongs to.
    Returns a list of allowed doc ids, or None meaning 'no scoping' (agent not
    in any department → sees org-wide only, handled by returning that set).
    """
    from app.departments.store import agent_department_ids
    with connection() as conn:
        org = [r["id"] for r in conn.execute(
            "SELECT id FROM documents WHERE department_id IS NULL OR department_id=''").fetchall()]
        dept_ids = agent_department_ids(agent_id) if agent_id else []
        scoped = []
        if dept_ids:
            qs = ",".join("?" * len(dept_ids))
            scoped = [r["id"] for r in conn.execute(
                f"SELECT id FROM documents WHERE department_id IN ({qs})", dept_ids).fetchall()]
    return list(dict.fromkeys(org + scoped))
