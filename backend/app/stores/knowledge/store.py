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


def _get_client():
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
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


def ingest_document(
    user_id: str, filename: str, data: bytes, content_type: str = ""
) -> dict:
    """Extract, chunk, and embed a document. Returns {document_id, chunks, filename}."""
    text = extract_text(filename, data, content_type)
    chunks = _chunk(text)
    if not chunks:
        raise IngestError(f"'{filename}' had no extractable text.")

    try:
        import chromadb  # noqa: F401

        client = _get_client()
        coll = client.get_or_create_collection(_collection_name(user_id))
        document_id = str(uuid.uuid4())
        ids = [f"{document_id}:{i}" for i in range(len(chunks))]
        metadatas = [{"document_id": document_id, "filename": filename, "chunk": i} for i in range(len(chunks))]
        # Chroma's default embedding function embeds the documents on add.
        coll.add(ids=ids, documents=chunks, metadatas=metadatas)
    except ImportError:
        # ChromaDB not installed (native wheel unavailable) — use the local
        # keyword fallback so ingestion still works end-to-end.
        from app.stores.knowledge import fallback

        document_id = fallback.add_chunks(user_id, filename, chunks)
    except IngestError:
        raise
    except Exception as e:  # noqa: BLE001
        raise IngestError(f"Could not embed document: {e}") from e

    return {"document_id": document_id, "chunks": len(chunks), "filename": filename}
