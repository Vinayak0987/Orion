"""Knowledge Base + Memory API (Plan 07).

Documents: upload (file/URL) → chunk + embed (Chroma or keyword fallback) and a
persisted documents row. List/detail(+chunks)/delete/reindex/search.
Memory: list/delete/clear episodic entries + global/per-agent settings.

Phase 1: single-user placeholder ('default-user').
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.knowledge import documents as docstore
from app.knowledge import memory
from app.knowledge.store import (
    IngestError,
    delete_chunks,
    ingest_document,
    ingest_url,
    list_chunks,
)

router = APIRouter(tags=["knowledge"])

DEFAULT_USER = "default-user"
MAX_DOC_BYTES = 25 * 1024 * 1024


# ============================================================================
# Documents
# ============================================================================

@router.post("/knowledge/documents", status_code=201)
async def upload_document(file: UploadFile = File(...),
                          department_id: str | None = Form(default=None),
                          index: bool = Form(default=False)) -> dict:
    data = await file.read()
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "Document exceeds 25 MB.")
    if not data:
        raise HTTPException(422, "Empty file.")
    try:
        result = ingest_document(DEFAULT_USER, file.filename or "document", data,
                                 file.content_type or "", department_id=department_id, index=index)
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    indexed = result.get("indexed")
    return {
        "document_id": result["document_id"], "filename": result["filename"],
        "chunks": result["chunks"], "status": "active" if indexed else "uploaded",
        "indexed": indexed,
        "message": (f"Indexed '{result['filename']}' ({result['chunks']} chunks)." if indexed
                    else f"Uploaded '{result['filename']}' (not indexed — index it when an agent needs search)."),
    }


@router.post("/knowledge/documents/{doc_id}/index")
async def index_document_endpoint(doc_id: str) -> dict:
    """Chunk + embed a previously-uploaded document on demand."""
    from app.knowledge.store import index_document
    try:
        r = index_document(DEFAULT_USER, doc_id)
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    return {"document_id": doc_id, "chunks": r["chunks"], "status": "active", "indexed": True}


# ============================================================================
# External sources — Google Drive (OAuth-based import into the knowledge store)
# ============================================================================

def _google_user() -> str | None:
    """The user_id that owns the Google OAuth connection (single-tenant)."""
    from app.db.sqlite import connection
    with connection() as c:
        row = c.execute("SELECT user_id FROM oauth_connections WHERE provider='google' "
                        "AND status='connected' LIMIT 1").fetchone()
    return row["user_id"] if row else None


@router.get("/knowledge/sources/drive/status")
async def drive_status() -> dict:
    return {"connected": _google_user() is not None}


@router.get("/knowledge/sources/drive/picker-config")
async def drive_picker_config() -> dict:
    """Config the frontend needs to launch the REAL Google Picker.
    Returns the OAuth access token + browser API key + client id. When the
    api_key is missing the frontend falls back to the built-in list modal."""
    from app.config import settings
    from app.oauth.service import get_valid_access_token
    uid = _google_user()
    token = await get_valid_access_token(uid, "google") if uid else None
    cid = settings.oauth_google_client_id or ""
    app_id = cid.split("-")[0] if "-" in cid else ""  # project number prefix
    return {
        "connected": bool(token),
        "access_token": token or "",
        "api_key": settings.google_picker_api_key or "",
        "client_id": cid,
        "app_id": app_id,
        "has_picker_key": bool((settings.google_picker_api_key or "").strip()),
    }


@router.get("/knowledge/sources/drive/files")
async def drive_files(q: str | None = None, page_size: int = 25) -> dict:
    """List the user's Google Drive files (name + id + type)."""
    import httpx
    from app.oauth.service import get_valid_access_token
    uid = _google_user()
    if not uid:
        raise HTTPException(400, "Google Drive not connected. Connect Google first.")
    token = await get_valid_access_token(uid, "google")
    if not token:
        raise HTTPException(400, "Google token unavailable — reconnect Google.")
    # Exclude folders; prefer docs/sheets/pdf/text. Simple name search when q given.
    query = "trashed=false and mimeType != 'application/vnd.google-apps.folder'"
    if q:
        safe = q.replace("'", "\\'")
        query += f" and name contains '{safe}'"
    params = {"q": query, "pageSize": min(page_size, 100),
              "fields": "files(id,name,mimeType,modifiedTime,size)", "orderBy": "modifiedTime desc"}
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get("https://www.googleapis.com/drive/v3/files",
                        headers={"Authorization": f"Bearer {token}"}, params=params)
    if r.status_code >= 400:
        raise HTTPException(502, f"Drive list failed ({r.status_code}): {r.text[:200]}")
    files = r.json().get("files", [])
    return {"files": files, "count": len(files)}


class DriveImportRequest(BaseModel):
    file_id: str
    name: str | None = None
    mime_type: str | None = None


# Google Docs/Sheets/Slides need export; binary files are downloaded directly.
_EXPORT = {
    "application/vnd.google-apps.document": ("text/plain", "txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
    "application/vnd.google-apps.presentation": ("text/plain", "txt"),
}


@router.post("/knowledge/sources/drive/import", status_code=201)
async def drive_import(req: DriveImportRequest) -> dict:
    """Download a Drive file and STORE it in the knowledge base (no chunking —
    lazy, same as upload). Google-native docs are exported to text/csv."""
    import httpx
    from app.oauth.service import get_valid_access_token
    uid = _google_user()
    if not uid:
        raise HTTPException(400, "Google Drive not connected.")
    token = await get_valid_access_token(uid, "google")
    if not token:
        raise HTTPException(400, "Google token unavailable — reconnect Google.")
    hdr = {"Authorization": f"Bearer {token}"}
    mime = req.mime_type or ""
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as c:
        if mime in _EXPORT:
            export_mime, ext = _EXPORT[mime]
            r = await c.get(f"https://www.googleapis.com/drive/v3/files/{req.file_id}/export",
                            headers=hdr, params={"mimeType": export_mime})
            fname = f"{req.name or req.file_id}.{ext}"
            ctype = export_mime
        else:
            r = await c.get(f"https://www.googleapis.com/drive/v3/files/{req.file_id}",
                            headers=hdr, params={"alt": "media"})
            fname = req.name or req.file_id
            ctype = mime or "application/octet-stream"
    if r.status_code >= 400:
        raise HTTPException(502, f"Drive download failed ({r.status_code}): {r.text[:200]}")
    data = r.content
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "File exceeds 25 MB.")
    try:
        # Store-only (index=False) — chunked lazily when an agent queries it.
        result = ingest_document(DEFAULT_USER, fname, data, ctype, index=False)
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    return {"document_id": result["document_id"], "filename": result["filename"],
            "status": "uploaded", "source": "google_drive"}


# ============================================================================
# Generic connector helpers + Microsoft / GitHub / Slack import endpoints
# ============================================================================

def _provider_user(provider: str) -> str | None:
    """The user_id owning a connected OAuth provider (single-tenant)."""
    from app.db.sqlite import connection
    with connection() as c:
        row = c.execute("SELECT user_id FROM oauth_connections WHERE provider=? "
                        "AND status='connected' LIMIT 1", (provider,)).fetchone()
    return row["user_id"] if row else None


async def _provider_token(provider: str) -> str | None:
    from app.oauth.service import get_valid_access_token
    uid = _provider_user(provider)
    return await get_valid_access_token(uid, provider) if uid else None


def _store_bytes(filename: str, data: bytes, ctype: str, source: str) -> dict:
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "File exceeds 25 MB.")
    try:
        result = ingest_document(DEFAULT_USER, filename, data, ctype, index=False)
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    return {"document_id": result["document_id"], "filename": result["filename"],
            "status": "uploaded", "source": source}


# ---- Microsoft OneDrive / SharePoint (Graph, Files.ReadWrite) --------------
@router.get("/knowledge/sources/ms/status")
async def ms_status() -> dict:
    return {"connected": _provider_user("microsoft") is not None}


@router.get("/knowledge/sources/ms/files")
async def ms_files(q: str | None = None) -> dict:
    import httpx
    token = await _provider_token("microsoft")
    if not token:
        raise HTTPException(400, "Microsoft not connected.")
    hdr = {"Authorization": f"Bearer {token}"}
    if q:
        url = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{q}')"
    else:
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(url, headers=hdr, params={"$top": 50})
    if r.status_code >= 400:
        raise HTTPException(502, f"OneDrive list failed ({r.status_code}): {r.text[:200]}")
    files = [{"id": f["id"], "name": f["name"],
              "mimeType": (f.get("file") or {}).get("mimeType", ""),
              "is_folder": "folder" in f}
             for f in r.json().get("value", [])
             if "folder" not in f and (f.get("file") or {}).get("mimeType")]
    return {"files": files, "count": len(files)}


class MsImportRequest(BaseModel):
    file_id: str
    name: str | None = None


@router.post("/knowledge/sources/ms/import", status_code=201)
async def ms_import(req: MsImportRequest) -> dict:
    import httpx
    token = await _provider_token("microsoft")
    if not token:
        raise HTTPException(400, "Microsoft not connected.")
    hdr = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as c:
        r = await c.get(f"https://graph.microsoft.com/v1.0/me/drive/items/{req.file_id}/content", headers=hdr)
    if r.status_code >= 400:
        raise HTTPException(502, f"OneDrive download failed ({r.status_code}): {r.text[:200]}")
    return _store_bytes(req.name or req.file_id, r.content,
                        r.headers.get("content-type", "application/octet-stream"), "microsoft")


# ---- GitHub repo files (repo scope) ----------------------------------------
@router.get("/knowledge/sources/github/status")
async def github_status() -> dict:
    return {"connected": _provider_user("github") is not None}


@router.get("/knowledge/sources/github/repos")
async def github_repos() -> dict:
    import httpx
    token = await _provider_token("github")
    if not token:
        raise HTTPException(400, "GitHub not connected.")
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get("https://api.github.com/user/repos",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                        params={"per_page": 50, "sort": "updated"})
    if r.status_code >= 400:
        raise HTTPException(502, f"GitHub repos failed ({r.status_code}): {r.text[:200]}")
    repos = [{"full_name": x["full_name"], "default_branch": x.get("default_branch", "main")}
             for x in r.json()]
    return {"repos": repos, "count": len(repos)}


@router.get("/knowledge/sources/github/files")
async def github_files(repo: str, path: str = "") -> dict:
    """List files/dirs at a path in a repo (GitHub contents API)."""
    import httpx
    token = await _provider_token("github")
    if not token:
        raise HTTPException(400, "GitHub not connected.")
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(f"https://api.github.com/repos/{repo}/contents/{path}",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    if r.status_code >= 400:
        raise HTTPException(502, f"GitHub files failed ({r.status_code}): {r.text[:200]}")
    data = r.json()
    items = data if isinstance(data, list) else [data]
    files = [{"name": x["name"], "path": x["path"], "type": x["type"]} for x in items]
    return {"files": files, "count": len(files), "repo": repo, "path": path}


class GithubImportRequest(BaseModel):
    repo: str
    path: str


@router.post("/knowledge/sources/github/import", status_code=201)
async def github_import(req: GithubImportRequest) -> dict:
    import base64
    import httpx
    token = await _provider_token("github")
    if not token:
        raise HTTPException(400, "GitHub not connected.")
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.get(f"https://api.github.com/repos/{req.repo}/contents/{req.path}",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    if r.status_code >= 400:
        raise HTTPException(502, f"GitHub download failed ({r.status_code}): {r.text[:200]}")
    j = r.json()
    content = base64.b64decode(j.get("content", "")) if j.get("encoding") == "base64" else (j.get("content", "") or "").encode()
    name = req.path.split("/")[-1] or req.repo.replace("/", "_")
    return _store_bytes(name, content, "text/plain", "github")


# ---- Slack files (needs files:read scope) ----------------------------------
@router.get("/knowledge/sources/slack/status")
async def slack_status() -> dict:
    return {"connected": _provider_user("slack") is not None}


@router.get("/knowledge/sources/slack/files")
async def slack_files() -> dict:
    import httpx
    token = await _provider_token("slack")
    if not token:
        raise HTTPException(400, "Slack not connected.")
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get("https://slack.com/api/files.list",
                        headers={"Authorization": f"Bearer {token}"}, params={"count": 50})
    j = r.json()
    if not j.get("ok"):
        err = j.get("error", "unknown")
        if err in ("missing_scope", "not_allowed_token_type"):
            raise HTTPException(403, "Slack needs the files:read permission — reconnect Slack to grant it.")
        raise HTTPException(502, f"Slack files failed: {err}")
    files = [{"id": f["id"], "name": f.get("name") or f.get("title") or f["id"],
              "url": f.get("url_private", ""), "mimetype": f.get("mimetype", "")}
             for f in j.get("files", [])]
    return {"files": files, "count": len(files)}


class SlackImportRequest(BaseModel):
    url: str
    name: str | None = None


@router.post("/knowledge/sources/slack/import", status_code=201)
async def slack_import(req: SlackImportRequest) -> dict:
    import httpx
    token = await _provider_token("slack")
    if not token:
        raise HTTPException(400, "Slack not connected.")
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as c:
        r = await c.get(req.url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code >= 400:
        raise HTTPException(502, f"Slack download failed ({r.status_code}).")
    return _store_bytes(req.name or "slack-file", r.content,
                        r.headers.get("content-type", "application/octet-stream"), "slack")


class UrlIngestRequest(BaseModel):
    url: str
    name: str | None = None
    department_id: str | None = None


@router.post("/knowledge/documents/url", status_code=201)
async def upload_url(req: UrlIngestRequest) -> dict:
    if not req.url.lower().startswith(("http://", "https://")):
        raise HTTPException(422, "Provide a valid http(s) URL.")
    try:
        result = ingest_url(DEFAULT_USER, req.url, name=req.name, department_id=req.department_id)
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    return {"document_id": result["document_id"], "name": result["name"],
            "chunks": result["chunks"], "status": "active"}


@router.get("/knowledge/documents")
async def list_documents(type: str | None = None, status: str | None = None,
                         search: str | None = None) -> dict:
    docs = docstore.list_documents(uploaded_by=DEFAULT_USER, type=type, status=status, search=search)
    return {"documents": docs, "count": len(docs), "summary": docstore.summary(DEFAULT_USER)}


@router.get("/knowledge/documents/{doc_id}")
async def get_document(doc_id: str, include_chunks: bool = True) -> dict:
    doc = docstore.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, f"Document '{doc_id}' not found")
    out = {"document": doc}
    if include_chunks:
        out["chunks"] = list_chunks(DEFAULT_USER, doc_id)
    # Always include the RAW stored text so the viewer can show the actual
    # document even when it hasn't been chunked yet (store-only / lazy model).
    from app.knowledge.store import _load_raw_text
    raw = _load_raw_text(DEFAULT_USER, doc_id)
    out["raw"] = raw
    out["raw_truncated"] = len(raw) > 200_000
    if out["raw_truncated"]:
        out["raw"] = raw[:200_000]
    return out


@router.delete("/knowledge/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    doc = docstore.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, f"Document '{doc_id}' not found")
    removed = delete_chunks(DEFAULT_USER, doc_id)
    docstore.delete_document(doc_id)
    return {"deleted": True, "chunks_removed": removed}


@router.post("/knowledge/documents/{doc_id}/reindex")
async def reindex_document(doc_id: str) -> dict:
    """Re-chunk/re-embed a URL document (file re-upload would be needed for files)."""
    doc = docstore.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, f"Document '{doc_id}' not found")
    if doc["type"] != "url" or not doc.get("source_url"):
        raise HTTPException(422, "Only URL documents can be reindexed in-place; re-upload files.")
    delete_chunks(DEFAULT_USER, doc_id)
    try:
        result = ingest_url(DEFAULT_USER, doc["source_url"], name=doc["name"],
                            department_id=doc.get("department_id"))
    except IngestError as e:
        raise HTTPException(422, str(e)) from e
    return {"status": "reindexed", "chunks": result["chunks"]}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = 5


@router.post("/knowledge/search")
async def search_knowledge(req: SearchRequest) -> dict:
    """Direct search over the knowledge base (same path document_rag uses)."""
    from app.tools import registry
    from app.tools.base import ToolContext

    out = await registry.dispatch("document_rag", {"query": req.query, "top_k": req.limit},
                                  ctx=ToolContext(user_id=DEFAULT_USER))
    return {"passages": out.get("passages", []), "count": out.get("count", 0)}


# ============================================================================
# Memory
# ============================================================================

@router.get("/knowledge/memory")
async def list_memory(agent_id: str | None = None, limit: int = 200) -> dict:
    if agent_id:
        entries = memory.read(agent_id, limit=limit)
    else:
        entries = memory.list_all(limit=limit)
    return {"entries": entries, "count": len(entries), "by_agent": memory.count_by_agent()}


@router.delete("/knowledge/memory/{entry_id}")
async def delete_memory(entry_id: str) -> dict:
    return {"deleted": memory.delete(entry_id)}


class ClearRequest(BaseModel):
    confirm: str = ""


@router.delete("/knowledge/memory/agent/{agent_id}")
async def clear_agent_memory(agent_id: str, confirm: str = "") -> dict:
    if confirm != "CLEAR":
        raise HTTPException(422, "Pass confirm=CLEAR to clear an agent's memory.")
    removed = memory.clear_agent(agent_id)
    return {"deleted": True, "entries_removed": removed}


@router.get("/knowledge/memory/settings")
async def get_memory_settings() -> dict:
    return memory.get_settings()


class MemorySettingsRequest(BaseModel):
    global_enabled: bool | None = None
    default_ttl_days: int | None = None
    max_global_entries: int | None = None
    per_agent: dict | None = None


@router.put("/knowledge/memory/settings")
async def update_memory_settings(req: MemorySettingsRequest) -> dict:
    changes = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    return memory.update_settings(changes)
