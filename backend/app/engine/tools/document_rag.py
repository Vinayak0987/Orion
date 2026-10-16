"""document_rag built-in tool — ChromaDB-backed semantic search.

Phase 1: searches whatever has been embedded into the user's collection. An
empty or missing collection returns {"passages": []} — never crashes. The
upload pipeline that fills ChromaDB arrives in Phase 4; this tool is ready for
it now.
"""

from __future__ import annotations

from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client


async def document_rag(tool_input: dict, user_keys: dict | None = None,
                       collection: str = "documents_default-user") -> dict:
    query = (tool_input or {}).get("query", "").strip()
    if not query:
        return {"error": "document_rag requires a 'query'", "passages": []}

    try:
        try:
            import chromadb  # noqa: F401
        except ImportError:
            # No ChromaDB — use the local keyword fallback store.
            from app.stores.knowledge import fallback

            user_id = collection.replace("documents_", "", 1) or "default-user"
            passages = fallback.search(user_id, query)
            if not passages:
                return {"passages": [], "note": "No documents uploaded yet."}
            return {"passages": passages, "count": len(passages)}

        client = _get_client()
        try:
            coll = client.get_collection(collection)
        except Exception:
            # Collection does not exist yet (nothing uploaded) — not an error.
            return {"passages": [], "note": "No documents uploaded yet."}

        res = coll.query(query_texts=[query], n_results=5)
        docs = (res.get("documents") or [[]])[0]
        passages = [{"text": d} for d in docs]
        return {"passages": passages, "count": len(passages)}
    except Exception as e:  # noqa: BLE001 - degrade, never crash the mission
        return {"error": f"document_rag unavailable: {e}", "passages": []}
