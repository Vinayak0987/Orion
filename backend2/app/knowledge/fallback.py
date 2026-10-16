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
    base = Path(settings.chroma_dir)
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


def add_chunks(user_id: str, filename: str, chunks: list[str]) -> str:
    rows = _load(user_id)
    document_id = str(uuid.uuid4())
    for i, text in enumerate(chunks):
        rows.append({"document_id": document_id, "filename": filename, "chunk": i, "text": text})
    _save(user_id, rows)
    return document_id


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall((s or "").lower()))


def search(user_id: str, query: str, n: int = 5) -> list[dict]:
    rows = _load(user_id)
    if not rows:
        return []
    q = _tokens(query)
    if not q:
        return []
    scored = []
    for r in rows:
        overlap = len(q & _tokens(r["text"]))
        if overlap:
            scored.append((overlap, r["text"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": t} for _, t in scored[:n]]
