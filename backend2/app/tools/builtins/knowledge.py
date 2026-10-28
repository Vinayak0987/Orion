"""Knowledge & Retrieval + Memory built-in tools (6).

These bind the agent to the document store (ChromaDB with keyword fallback) and
the episodic memory store. document_rag + keyword_search read uploaded docs;
memory_read/write/search operate on the acting agent's episodic memory.
"""

from __future__ import annotations

from app.knowledge import fallback, memory
from app.tools.base import ToolContext, err, need, ok, tool


# --- query_document ----------------------------------------------------------
@tool(
    "query_document",
    display_name="Query Document",
    description="Get ONLY the relevant part of a specific uploaded document. For CSV/table data "
    "it returns matching ROWS (supports 'first N' or keyword filters); for long documents it "
    "returns the most relevant passages; small docs are returned whole. Chunking happens "
    "automatically on first use. IMPORTANT: You must have a document_id to use this tool. "
    "Call list_documents first to discover available files and get their document_id. "
    "Input: {document_id: str, query: str, limit?: int=10}.",
    category="knowledge",
    input_schema={
        "properties": {
            "document_id": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer"}
        },
        "required": ["document_id"]
    },
)
def query_document(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "document_id")):
        return err(m)
    from app.knowledge.store import query_document as _qd
    res = _qd(ctx.user_id or "default-user", ti["document_id"].strip(),
              ti.get("query", ""), int(ti.get("limit") or 10))
    if res.get("error"):
        return err(res["error"])
    return ok(**res)


def _doc_search(user_id: str, query: str, top_k: int = 5, agent_id: str | None = None) -> dict:
    """Shared doc retrieval: Chroma if present, else keyword fallback.
    When agent_id is given, results are scoped to documents the agent may see
    (its departments + org-wide docs)."""
    # Resolve the allowed-document scope for this acting agent.
    allowed = None
    if agent_id:
        try:
            from app.knowledge import documents as _docs
            allowed = _docs.allowed_document_ids(agent_id)
        except Exception:  # noqa: BLE001 — scoping must never break retrieval
            allowed = None
    try:
        import chromadb  # noqa: F401

        from app.config import settings

        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        try:
            coll = client.get_collection(f"documents_{user_id}")
        except Exception:  # noqa: BLE001 — nothing uploaded yet
            return ok(passages=[], note="No documents uploaded yet.")
        where = None
        if allowed is not None:
            if not allowed:
                return ok(passages=[], count=0, note="No documents in your scope.")
            where = {"document_id": {"$in": allowed}}
        res = coll.query(query_texts=[query], n_results=top_k, where=where)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        passages = [{"text": d, "source": (metas[i] or {}).get("filename") if i < len(metas) else None}
                    for i, d in enumerate(docs)]
        return ok(passages=passages, count=len(passages), source="chroma")
    except ImportError:
        passages = fallback.search(user_id, query, n=top_k, allowed_document_ids=allowed)
        if not passages:
            return ok(passages=[], note="No documents uploaded yet.")
        return ok(passages=passages, count=len(passages), source="keyword")


# --- 95. document_rag --------------------------------------------------------
@tool(
    "document_rag",
    description="Search the uploaded knowledge base (documents) for passages relevant to a query. "
    "Input: {query: str, top_k?: int=5}.",
    category="knowledge",
    input_schema={"properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
)
def document_rag(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, passages=[])
    return _doc_search(ctx.user_id or "default-user", ti["query"].strip(), int(ti.get("top_k") or 5),
                       agent_id=ctx.agent_id)


# --- 97. keyword_search ------------------------------------------------------
@tool(
    "keyword_search",
    description="Keyword (non-semantic) search over the uploaded knowledge base. Input: "
    "{query: str, top_k?: int=5}.",
    category="knowledge",
    input_schema={"properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
)
def keyword_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, passages=[])
    passages = fallback.search(ctx.user_id or "default-user", ti["query"].strip(), n=int(ti.get("top_k") or 5))
    return ok(passages=passages, count=len(passages))


# --- 100. chunk_retriever ----------------------------------------------------
@tool(
    "chunk_retriever",
    description="Retrieve the top-k most relevant document chunks for a query (same store as "
    "document_rag, returns raw chunk text). Input: {query: str, top_k?: int=8}.",
    category="knowledge",
    input_schema={"properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
)
def chunk_retriever(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, chunks=[])
    res = _doc_search(ctx.user_id or "default-user", ti["query"].strip(), int(ti.get("top_k") or 8),
                      agent_id=ctx.agent_id)
    passages = res.get("passages", [])
    return ok(chunks=[p.get("text") for p in passages], count=len(passages))


# --- list_documents ---------------------------------------------------------
@tool(
    "list_documents",
    display_name="List Documents",
    description="List all uploaded documents in the knowledge base. Returns document_id, name, "
    "type (csv, pdf, txt, etc.), status (uploaded/active), and chunk count. Use this to discover "
    "available files before calling query_document. Input: {type?: str} (optional filter by file type, "
    "e.g. 'csv' to list only CSV files).",
    category="knowledge",
    input_schema={"properties": {"type": {"type": "string"}}, "required": []},
)
def list_documents(ti: dict, ctx: ToolContext) -> dict:
    from app.knowledge import documents as _docs
    user_id = ctx.user_id or "default-user"
    file_type = ti.get("type", "").strip().lower() if ti.get("type") else None
    docs = _docs.list_documents(uploaded_by=user_id, type=file_type)
    # Return only the fields agents need: id, name, type, status, chunks
    return ok(
        documents=[
            {
                "document_id": d["id"],
                "name": d["name"],
                "type": d["type"],
                "status": d["status"],
                "chunks_count": d["chunks_count"],
            }
            for d in docs
        ],
        count=len(docs),
    )


# --- 103. memory_write -------------------------------------------------------
@tool(
    "memory_write",
    description="Store a fact in the acting agent's long-term memory for future tasks. Input: "
    "{content: str, ttl_days?: int=30}.",
    category="knowledge",
    input_schema={"properties": {"content": {"type": "string"}, "ttl_days": {"type": "integer"}}, "required": ["content"]},
)
def memory_write(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "content")):
        return err(m)
    if not ctx.agent_id:
        return err("no acting agent in context")
    eid = memory.write(ctx.agent_id, ti["content"].strip(), mission_id=ctx.mission_id,
                       ttl_days=int(ti.get("ttl_days") or 30))
    return ok(stored=bool(eid), entry_id=eid)


# --- 102. memory_read --------------------------------------------------------
@tool(
    "memory_read",
    description="Read the acting agent's most recent remembered facts. Input: {limit?: int=20}.",
    category="knowledge",
    input_schema={"properties": {"limit": {"type": "integer"}}, "required": []},
)
def memory_read(ti: dict, ctx: ToolContext) -> dict:
    if not ctx.agent_id:
        return err("no acting agent in context", entries=[])
    entries = memory.read(ctx.agent_id, limit=int(ti.get("limit") or 20))
    return ok(entries=[{"content": e["content"], "created_at": e["created_at"]} for e in entries],
              count=len(entries))


# --- 105. memory_search ------------------------------------------------------
@tool(
    "memory_search",
    description="Semantically search the acting agent's memory for facts relevant to a query. Input: "
    "{query: str, top_k?: int=5}.",
    category="knowledge",
    input_schema={"properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
)
def memory_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, results=[])
    if not ctx.agent_id:
        return err("no acting agent in context", results=[])
    results = memory.search(ctx.agent_id, ti["query"].strip(), top_k=int(ti.get("top_k") or 5))
    return ok(results=results, count=len(results))
