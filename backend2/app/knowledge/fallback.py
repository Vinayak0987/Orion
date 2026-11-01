"""Local fallback document store — used when ChromaDB is unavailable.

ChromaDB needs native wheels (chroma-hnswlib → MS C++ Build Tools on Windows).
When it can't be installed, document ingestion and `document_rag` degrade to
this dependency-free store: chunks are persisted to a JSON file per user and
retrieved with a simple TF-style keyword overlap score.

Same shape as the Chroma path: ingest writes chunks, search returns
[{"text": ...}] passages. Good enough for Phase 1 so attaching a doc in the
Command Center actually feeds the agents.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from app.config import settings

_WORD = re.compile(r"[a-z0-9]+")


def _store_path(user_id: str) -> Path:
    from app.config import settings as _settings
    base = Path(_settings.chroma_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"fallback_docs_{user_id}.json"


def _load(user_id: str) -> list[dict]:
    p = _store_path(user_id)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return []


def _save(user_id: str, rows: list[dict]) -> None:
    _store_path(user_id).write_text(json.dumps(rows), "utf-8")


def add_chunks(user_id: str, filename: str, chunks: list[str], document_id: str | None = None) -> str:
    rows = _load(user_id)
    document_id = document_id or str(uuid.uuid4())
    for i, text in enumerate(chunks):
        rows.append({"document_id": document_id, "filename": filename, "chunk": i, "text": text})
    _save(user_id, rows)
    return document_id


def delete_document(user_id: str, document_id: str) -> int:
    rows = _load(user_id)
    kept = [r for r in rows if r.get("document_id") != document_id]
    removed = len(rows) - len(kept)
    _save(user_id, kept)
    return removed


def list_chunks(user_id: str, document_id: str) -> list[dict]:
    return [r for r in _load(user_id) if r.get("document_id") == document_id]


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall((s or "").lower()))


async def search(user_id: str, query: str, n: int = 5, allowed_document_ids: list[str] | None = None) -> list[dict]:
    """Search MongoDB document embeddings with vector similarity, keyword fallback."""
    # Primary: Try vector search using MongoDB's $vectorSearch
    try:
        from app.auth import store as auth_store
        from app.llm.embeddings import get_embedding_client

        # Generate query embedding
        embedding_client = get_embedding_client()
        query_embedding = await embedding_client.embed_text(query)

        if query_embedding and any(query_embedding):  # Non-zero vector
            # Use vector search
            results = auth_store.search_document_embeddings(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=n,
            )

            if results:
                # Filter by allowed document IDs if specified
                if allowed_document_ids is not None:
                    allow = set(allowed_document_ids)
                    results = [r for r in results if r.get("document_id") in allow]

                if results:
                    # Return results with text content
                    return [{"text": r.get("text", ""), "document_id": r.get("document_id")} for r in results]
    except Exception:
        # Vector search failed, fall through to keyword search
        pass

    # Fallback: Keyword matching on MongoDB embeddings
    try:
        from app.auth import store as auth_store
        embeddings = auth_store.get_db().document_embeddings.find({"user_id": user_id})

        if allowed_document_ids is not None:
            allow = set(allowed_document_ids)
            embeddings = [e for e in embeddings if e.get("document_id") in allow]

        if not embeddings:
            # Final fallback: local JSON file
            return _search_local(user_id, query, n, allowed_document_ids)

        q = _tokens(query)
        if not q:
            return []

        scored = []
        for emb in embeddings:
            text = emb.get("text", "")
            overlap = len(q & _tokens(text))
            if overlap:
                scored.append((overlap, text, emb.get("document_id")))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"text": t, "document_id": doc_id} for _, t, doc_id in scored[:n]]
    except Exception:
        # Final fallback: local JSON file on any error
        return _search_local(user_id, query, n, allowed_document_ids)


def _search_local(user_id: str, query: str, n: int = 5, allowed_document_ids: list[str] | None = None) -> list[dict]:
    """Search local JSON fallback store."""
    rows = _load(user_id)
    if not rows:
        return []
    if allowed_document_ids is not None:
        allow = set(allowed_document_ids)
        rows = [r for r in rows if r.get("document_id") in allow]
        if not rows:
            return []
    q = _tokens(query)
    if not q:
        return []
    scored = []
    for r in rows:
        overlap = len(q & _tokens(r["text"]))
        if overlap:
            scored.append((overlap, r["text"], r.get("document_id")))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": t, "document_id": doc_id} for _, t, doc_id in scored[:n]]
