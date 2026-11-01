"""document_rag built-in tool — MongoDB-backed semantic search.

Searches document embeddings stored in MongoDB Atlas Vector Search using
actual embeddings. Falls back to keyword matching if vector search fails.
Never crashes — returns empty results on error.
"""

from __future__ import annotations

import re

from app.auth import store as auth_store
from app.config import settings
from app.llm.embeddings import get_embedding_client


async def document_rag(tool_input: dict, user_keys: dict | None = None,
                       collection: str = "documents_default-user") -> dict:
    query = (tool_input or {}).get("query", "").strip()
    if not query:
        return {"error": "document_rag requires a 'query'", "passages": []}

    # Extract user_id from collection name (format: documents_<user_id>)
    user_id = collection.replace("documents_", "", 1) or "default-user"

    try:
        db = auth_store.get_db()

        # Try vector search first
        try:
            embedding_client = get_embedding_client(user_keys)
            query_embedding = await embedding_client.embed_text(query)

            # Use MongoDB's vector search if we have a valid embedding
            if query_embedding and any(v != 0 for v in query_embedding):
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "vector_index",
                            "path": "embedding",
                            "queryVector": query_embedding,
                            "numCandidates": 50,
                            "limit": 5,
                        }
                    },
                    {"$match": {"user_id": user_id}},
                    {"$project": {"embedding": 0, "_id": 0}},
                ]
                results = list(db.document_embeddings.aggregate(pipeline))

                if results:
                    passages = [{"text": r.get("text", "")} for r in results]
                    return {"passages": passages, "count": len(passages), "method": "vector_search"}
        except Exception as e:  # noqa: BLE001 - fall back to keyword search
            pass

        # Fallback: keyword-based search
        query_lower = query.lower()
        terms = set(re.findall(r"[a-z0-9]+", query_lower))

        if not terms:
            return {"passages": [], "note": "Query contains no searchable terms."}

        # Search document embeddings by keyword matching
        embeddings = list(db.document_embeddings.find({"user_id": user_id}).limit(100))

        # Score each chunk by term overlap
        scored = []
        for emb in embeddings:
            text = emb.get("text", "").lower()
            overlap = len(terms & set(re.findall(r"[a-z0-9]+", text)))
            if overlap > 0:
                scored.append({"text": emb.get("text", ""), "score": overlap, "chunk_id": emb.get("chunk_id")})

        # Sort by score and return top 5
        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:5]

        if not top:
            return {"passages": [], "note": "No matching documents found."}

        passages = [{"text": item["text"]} for item in top]
        return {"passages": passages, "count": len(passages), "method": "keyword_search"}

    except Exception as e:  # noqa: BLE001 - degrade, never crash the mission
        return {"error": f"document_rag unavailable: {e}", "passages": []}
