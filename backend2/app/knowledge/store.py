"""Knowledge document ingestion — chunk + embed uploaded files into ChromaDB.

A document uploaded in the Command Center lands here. We extract its text,
split it into overlapping chunks, and add them to the user's Chroma collection
(`documents_<user_id>`) — the exact collection the `document_rag` tool searches.
So the moment a doc is attached, agents in the mission can retrieve from it.

Text extraction is best-effort and dependency-light:
  • .txt / .md / .csv  → decoded directly
  • .pdf               → pypdf if installed
  • .docx              → python-docx if installed
Unsupported/!extractable types raise IngestError with a clear message.
"""

from __future__ import annotations

import io
import re
import uuid

from app.config import settings


class IngestError(Exception):
    """Raised when a document cannot be read or embedded."""


_client = None
_client_path = None


def _get_client():
    global _client, _client_path
    from app.config import settings as _settings
    path = str(_settings.chroma_dir)
    if _client is None or _client_path != path:
        import chromadb

        _client = chromadb.PersistentClient(path=path)
        _client_path = path
    return _client


def _collection_name(user_id: str) -> str:
    return f"documents_{user_id}"


def extract_text(filename: str, data: bytes, content_type: str = "") -> str:
    name = (filename or "").lower()

    if name.endswith((".txt", ".md", ".csv")) or content_type.startswith("text/"):
        return data.decode("utf-8", errors="replace")

    if name.endswith(".pdf") or content_type == "application/pdf":
        try:
            from pypdf import PdfReader
        except Exception as e:  # noqa: BLE001
            raise IngestError("PDF support needs 'pypdf' (pip install pypdf).") from e
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if name.endswith(".docx") or content_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        try:
            import docx  # python-docx
        except Exception as e:  # noqa: BLE001
            raise IngestError("DOCX support needs 'python-docx' (pip install python-docx).") from e
        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)

    # Last resort: try UTF-8; if it's binary this yields garbage, so guard it.
    text = data.decode("utf-8", errors="ignore")
    if not text.strip():
        raise IngestError(f"Cannot extract text from '{filename}'. Supported: TXT, MD, CSV, PDF, DOCX.")
    return text


def _chunk(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+\n", "\n", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
        if start <= 0:
            break
    return [c for c in chunks if c.strip()]


def _ext_to_type(filename: str) -> str:
    name = (filename or "").lower()
    for ext in ("pdf", "docx", "csv", "md", "txt", "xlsx"):
        if name.endswith("." + ext):
            return ext
    return "txt"


def _embed_chunks(user_id: str, document_id: str, filename: str, chunks: list[str]) -> str:
    """Store chunks in Chroma if available, else the keyword fallback. Returns the
    collection id used (empty for fallback)."""
    try:
        import chromadb  # noqa: F401

        client = _get_client()
        coll = client.get_or_create_collection(_collection_name(user_id))
        ids = [f"{document_id}:{i}" for i in range(len(chunks))]
        metadatas = [{"document_id": document_id, "filename": filename, "chunk": i}
                     for i in range(len(chunks))]
        coll.add(ids=ids, documents=chunks, metadatas=metadatas)
        return _collection_name(user_id)
    except ImportError:
        from app.knowledge import fallback

        fallback.add_chunks(user_id, filename, chunks, document_id=document_id)
        return ""


def ingest_document(
    user_id: str, filename: str, data: bytes, content_type: str = "",
    *, department_id: str | None = None, persist: bool = True, index: bool = True
) -> dict:
    """Extract + persist a document. Chunks/embeds ONLY when index=True.

    When index=False the document is stored (status='uploaded') without being
    chunked/embedded — chunking happens on-demand via index_document(). Returns
    {document_id, chunks, filename, indexed}.
    """
    from app.knowledge import documents as docstore

    doc_type = _ext_to_type(filename)
    doc_id = docstore.create_document(
        name=filename, type=doc_type, uploaded_by=user_id, size_bytes=len(data),
        department_id=department_id,
    ) if persist else None

    try:
        text = extract_text(filename, data, content_type)
        if not (text or "").strip():
            raise IngestError(f"'{filename}' had no extractable text.")
        # Persist the raw text so it can be indexed later without re-upload.
        if doc_id:
            _save_raw_text(user_id, doc_id, text)
        if not index:
            # Store only — no chunking/embedding.
            if doc_id:
                docstore.mark_uploaded(doc_id, len(text))
            return {"document_id": doc_id, "chunks": 0, "filename": filename, "indexed": False}
        chunks = _chunk(text)
        if not chunks:
            raise IngestError(f"'{filename}' had no extractable text.")
        coll = _embed_chunks(user_id, doc_id or "", filename, chunks)
        if doc_id:
            docstore.mark_active(doc_id, len(chunks), coll)
        return {"document_id": doc_id, "chunks": len(chunks), "filename": filename, "indexed": True}
    except IngestError as e:
        if doc_id:
            docstore.mark_error(doc_id, str(e))
        raise
    except Exception as e:  # noqa: BLE001
        if doc_id:
            docstore.mark_error(doc_id, str(e))
        raise IngestError(f"Could not embed document: {e}") from e


def ingest_url(user_id: str, url: str, *, name: str | None = None,
               department_id: str | None = None) -> dict:
    """Fetch a URL, extract main text, chunk + embed, persist a documents row."""
    import httpx
    from app.knowledge import documents as docstore

    try:
        from bs4 import BeautifulSoup
    except Exception as e:  # noqa: BLE001
        raise IngestError("URL ingest needs beautifulsoup4.") from e

    title = name or url
    doc_id = docstore.create_document(
        name=title, type="url", uploaded_by=user_id, source_url=url, department_id=department_id,
    )
    try:
        resp = httpx.get(url, timeout=20.0, follow_redirects=True,
                         headers={"User-Agent": "OrionAgent/1.0"})
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["nav", "footer", "script", "style", "header", "noscript"]):
            tag.decompose()
        if not name and soup.title and soup.title.string:
            title = soup.title.string.strip()
            with _title_update(doc_id, title):
                pass
        text = soup.get_text(separator="\n", strip=True)
        chunks = _chunk(text)
        if not chunks:
            raise IngestError("No extractable text at URL.")
        coll = _embed_chunks(user_id, doc_id, title, chunks)
        docstore.mark_active(doc_id, len(chunks), coll)
        return {"document_id": doc_id, "chunks": len(chunks), "name": title}
    except IngestError as e:
        docstore.mark_error(doc_id, str(e))
        raise
    except Exception as e:  # noqa: BLE001
        docstore.mark_error(doc_id, str(e))
        raise IngestError(f"Could not ingest URL: {e}") from e


from contextlib import contextmanager  # noqa: E402


@contextmanager
def _title_update(doc_id: str, title: str):
    from app.db.sqlite import connection

    with connection() as conn:
        conn.execute("UPDATE documents SET name=? WHERE id=?", (title, doc_id))
    yield


def list_chunks(user_id: str, document_id: str) -> list[dict]:
    """Return the stored chunks for a document (for the Chunk Inspector)."""
    try:
        import chromadb  # noqa: F401

        client = _get_client()
        try:
            coll = client.get_collection(_collection_name(user_id))
        except Exception:  # noqa: BLE001
            return []
        res = coll.get(where={"document_id": document_id})
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        out = [{"chunk": (metas[i] or {}).get("chunk", i), "text": d} for i, d in enumerate(docs)]
        return sorted(out, key=lambda c: c["chunk"])
    except ImportError:
        from app.knowledge import fallback

        return fallback.list_chunks(user_id, document_id)


def delete_chunks(user_id: str, document_id: str) -> int:
    """Remove a document's chunks from the vector/keyword store."""
    try:
        import chromadb  # noqa: F401

        client = _get_client()
        try:
            coll = client.get_collection(_collection_name(user_id))
        except Exception:  # noqa: BLE001
            return 0
        coll.delete(where={"document_id": document_id})
        return 1
    except ImportError:
        from app.knowledge import fallback

        return fallback.delete_document(user_id, document_id)



# ---- Raw text storage (so an uploaded-but-unindexed doc can be indexed later) ----

def _raw_dir():
    from pathlib import Path
    from app.config import settings as _settings
    p = Path(_settings.chroma_dir) / "rawdocs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _save_raw_text(user_id: str, doc_id: str, text: str) -> None:
    try:
        (_raw_dir() / f"{user_id}__{doc_id}.txt").write_text(text, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _load_raw_text(user_id: str, doc_id: str) -> str:
    try:
        p = _raw_dir() / f"{user_id}__{doc_id}.txt"
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:  # noqa: BLE001
        return ""


def index_document(user_id: str, doc_id: str) -> dict:
    """Chunk + embed a previously-uploaded (unindexed) document on demand."""
    from app.knowledge import documents as docstore
    doc = docstore.get_document(doc_id)
    if doc is None:
        raise IngestError("Document not found.")
    text = _load_raw_text(user_id, doc_id)
    if not text.strip():
        raise IngestError("No stored text to index (re-upload the document).")
    chunks = _chunk(text)
    if not chunks:
        raise IngestError("No extractable text to index.")
    coll = _embed_chunks(user_id, doc_id, doc.get("name", ""), chunks)
    docstore.mark_active(doc_id, len(chunks), coll)
    return {"document_id": doc_id, "chunks": len(chunks), "indexed": True}



# ============================================================================
# Lazy, type-aware document querying — the agent-facing retrieval primitive.
#   • No chunking happens at upload. The FIRST time a document is queried it is
#     chunked + cached (lazy); later queries reuse the cache.
#   • Retrieval is content-type-aware: CSV/structured → relevant ROWS;
#     large text → top-k semantic/keyword PASSAGES; small text → returned whole.
# ============================================================================

import csv as _csv
import io as _io
import re as _re


def _is_chunked(doc: dict) -> bool:
    return (doc.get("status") == "active") and (doc.get("chunks_count") or 0) > 0


def _ensure_chunked(user_id: str, doc: dict) -> None:
    """Lazy-chunk a document on first use (idempotent). Safe no-op if already done."""
    if _is_chunked(doc):
        return
    try:
        index_document(user_id, doc["id"])
    except Exception:  # noqa: BLE001 — querying must not hard-fail on chunking
        pass


def _query_csv(text: str, query: str, limit: int) -> dict:
    """Return relevant ROWS from CSV text (not semantic chunks). Supports
    'first N' and simple keyword row-matching; defaults to the first `limit` rows."""
    try:
        rows = list(_csv.DictReader(_io.StringIO(text)))
    except Exception:  # noqa: BLE001
        rows = []
    if not rows:
        # Not clean CSV → fall back to line slices.
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return {"rows": [], "lines": lines[:limit], "total_rows": len(lines), "kind": "csv_raw"}

    q = (query or "").lower()
    n = limit
    m = _re.search(r"\b(?:first|top)\s+(\d+)\b", q)
    if m:
        n = min(int(m.group(1)), 200)

    # Keyword row filter if the query names a column value; else first N.
    terms = [t for t in _re.findall(r"[a-z0-9@._-]+", q)
             if t not in ("first", "top", "rows", "row", "the", "get", "list", "users", "user", "all")]
    selected = rows
    if terms and not m:
        def match(r):
            blob = " ".join(str(v) for v in r.values()).lower()
            return any(t in blob for t in terms)
        filtered = [r for r in rows if match(r)]
        selected = filtered or rows  # if nothing matched, don't return empty

    out = selected[:n]
    return {"rows": out, "columns": list(rows[0].keys()), "returned": len(out),
            "total_rows": len(rows), "kind": "csv"}


def query_document(user_id: str, doc_id: str, query: str = "", limit: int = 10) -> dict:
    """Agent-facing: return ONLY the relevant part of a document for `query`.

    Lazy-chunks on first use. CSV/structured → relevant rows; large text → top-k
    passages; small text → returned whole. Never returns the entire large file.
    """
    from app.knowledge import documents as docstore
    doc = docstore.get_document(doc_id)
    if doc is None:
        return {"error": f"Document '{doc_id}' not found."}
    dtype = (doc.get("type") or "").lower()
    name = doc.get("name", doc_id)

    # Structured data (CSV/xlsx exported as text) → row selection, NOT chunking.
    if dtype in ("csv", "xls", "xlsx"):
        text = _load_raw_text(user_id, doc_id)
        if not text.strip():
            return {"error": "No stored content for this document (re-upload)."}
        res = _query_csv(text, query, limit)
        res["document"] = name
        return res

    # Unstructured text → lazy chunk on first use, then top-k relevant passages.
    text = _load_raw_text(user_id, doc_id)
    SMALL = 2500
    if text and len(text) <= SMALL:
        # Small doc → return it whole (no need to chunk/retrieve a part).
        return {"document": name, "kind": "small", "content": text}

    _ensure_chunked(user_id, doc)  # lazy: chunk now if not already
    # Retrieve only the relevant chunks for the query.
    try:
        import chromadb  # noqa: F401
        from app.config import settings
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        coll = client.get_collection(_collection_name(user_id))
        res = coll.query(query_texts=[query or name], n_results=limit,
                         where={"document_id": doc_id})
        docs = (res.get("documents") or [[]])[0]
        return {"document": name, "kind": "passages", "passages": docs, "count": len(docs)}
    except Exception:  # noqa: BLE001 — keyword fallback scoped to this doc
        from app.knowledge import fallback
        chunks = fallback.list_chunks(user_id, doc_id)
        if not chunks:
            return {"document": name, "kind": "passages", "passages": [], "count": 0,
                    "note": "No content retrieved."}
        q = (query or "").lower()
        terms = set(_re.findall(r"[a-z0-9]+", q))
        scored = sorted(chunks, key=lambda c: len(terms & set(_re.findall(r"[a-z0-9]+", c["text"].lower()))),
                        reverse=True)
        top = [c["text"] for c in scored[:limit] if (not terms or (terms & set(_re.findall(r"[a-z0-9]+", c["text"].lower()))))]
        return {"document": name, "kind": "passages", "passages": top or [c["text"] for c in chunks[:limit]],
                "count": min(limit, len(chunks))}
