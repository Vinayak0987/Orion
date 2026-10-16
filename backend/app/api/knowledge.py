"""Knowledge API — upload documents into the mission knowledge base.

POST /knowledge/documents   multipart file → chunked + embedded into ChromaDB.
                            Agents can then retrieve it via the `document_rag` tool.

Phase 1: single-user placeholder (`default-user`), matching the missions API and
the `document_rag` collection name. Auth-scoped user_id is a later phase.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.stores.knowledge.store import IngestError, ingest_document

router = APIRouter(tags=["knowledge"])

DEFAULT_USER = "default-user"
MAX_DOC_BYTES = 25 * 1024 * 1024


@router.post("/knowledge/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "Document exceeds 25 MB.")
    if not data:
        raise HTTPException(422, "Empty file.")

    try:
        result = ingest_document(
            DEFAULT_USER, file.filename or "document", data, file.content_type or ""
        )
    except IngestError as e:
        raise HTTPException(422, str(e)) from e

    return {
        "document_id": result["document_id"],
        "filename": result["filename"],
        "chunks": result["chunks"],
        "message": f"Ingested '{result['filename']}' ({result['chunks']} chunks). "
        "Agents can now search it with document_rag.",
    }
