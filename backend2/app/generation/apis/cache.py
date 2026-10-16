"""F40/F61 - ChromaDB knowledge cache.

Three collections:

    competitors       place results keyed by business type + locality
    market_research   search findings keyed by query
    plans             finished plan embeddings, for retrieval across runs

The cache is what makes the evaluation harness affordable and repeatable. The
30+ prompts in `evaluation/prompts.json` are run across several arms (multi-agent,
baseline, dynamic vs all-departments, with and without grounding). Re-issuing the
same Serper query for every arm would burn 4x the credits and, worse, could
return different results between arms - so a measured difference would no longer
be attributable to the manipulation.

Cached entries carry their original retrieval timestamp, so a cache hit is still
correctly tagged by F41 and goes stale on schedule instead of looking permanently
fresh.

Degradation: every operation is wrapped. If the ChromaDB server is unreachable or
the package is missing, caching turns itself off and the pipeline continues
uncached rather than failing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from app.generation.apis.freshness import Freshness, age_days, is_stale, now_iso
from app.generation.config import settings

log = structlog.get_logger(__name__)

COLLECTION_COMPETITORS = "mabgp_competitors"
COLLECTION_MARKET_RESEARCH = "mabgp_market_research"
COLLECTION_PLANS = "mabgp_plans"

# ChromaDB requires 3-63 chars, alphanumeric plus underscore/hyphen.
_ID_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")


def cache_key(*parts: str) -> str:
    """Stable, ChromaDB-safe id from arbitrary text parts."""
    joined = "_".join(p.strip().lower() for p in parts if p and p.strip())
    safe = _ID_SAFE.sub("_", joined).strip("_") or "empty"
    return safe[:200]


def _older_than(retrieved_at: str, max_age_days: int) -> bool:
    age = age_days(retrieved_at)
    return age is None or age > max_age_days


class KnowledgeCache:
    """Thin wrapper over ChromaDB with graceful degradation."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self._enabled = settings.enable_chroma_cache
        self._attempted = client is not None
        self._collections: dict[str, Any] = {}

    # --- lifecycle -------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    def connect(self) -> bool:
        """Lazily connect. Returns False and disables the cache on any failure.

        Two modes, both free:

            local   chromadb.PersistentClient writes to a directory. No server,
                    no Docker, no ports. This is the default, because the
                    evaluation sweep needs a working cache and requiring Docker
                    for it would make the experiment harder to reproduce.
            server  chromadb.HttpClient against the docker-compose service, for
                    when the stack is run containerised.
        """
        if not self._enabled:
            return False
        if self._client is not None:
            return True
        if self._attempted:
            return False
        self._attempted = True

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            chroma_settings = ChromaSettings(anonymized_telemetry=False)

            if settings.chroma_mode == "server":
                self._client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    settings=chroma_settings,
                )
                self._client.heartbeat()
                log.info(
                    "cache.connected",
                    mode="server",
                    host=f"{settings.chroma_host}:{settings.chroma_port}",
                )
            else:
                path = Path(settings.chroma_path).expanduser().resolve()
                path.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(path), settings=chroma_settings
                )
                log.info("cache.connected", mode="local", path=str(path))
            return True
        except Exception as exc:  # noqa: BLE001 - cache is optional infrastructure
            log.warning("cache.unavailable", mode=settings.chroma_mode, error=str(exc)[:200])
            self._client = None
            self._enabled = False
            return False

    def _collection(self, name: str) -> Any | None:
        if not self.connect():
            return None
        if name in self._collections:
            return self._collections[name]
        try:
            collection = self._client.get_or_create_collection(name)
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.collection_failed", collection=name, error=str(exc)[:200])
            self._enabled = False
            return None
        self._collections[name] = collection
        return collection

    # --- generic document cache -----------------------------------------
    #
    # ChromaDB embeds whatever is passed as `documents`, so the document slot
    # holds human-readable text for semantic lookup and the structured payload
    # travels in metadata as a JSON string. Putting the JSON in the document slot
    # instead would mean embedding punctuation and field names, which makes
    # `similar()` useless for F61 plan retrieval.

    _PAYLOAD_FIELD = "payload_json"

    def get(
        self, collection_name: str, key: str, *, max_age_days: int | None = None
    ) -> tuple[dict | None, Freshness | None]:
        """Exact-id lookup. Returns (payload, freshness), or (None, None) on a
        miss or when the entry has gone stale (F41)."""
        collection = self._collection(collection_name)
        if collection is None:
            return None, None

        try:
            result = collection.get(ids=[key], include=["metadatas"])
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.get_failed", key=key, error=str(exc)[:150])
            return None, None

        metadatas = result.get("metadatas") or []
        if not metadatas or not metadatas[0]:
            return None, None

        metadata = metadatas[0]
        retrieved_at = str(metadata.get("retrieved_at") or "")
        source = str(metadata.get("source") or collection_name)

        expired = (
            is_stale(retrieved_at)
            if max_age_days is None
            else _older_than(retrieved_at, max_age_days)
        )
        if expired:
            log.info("cache.stale", collection=collection_name, key=key)
            return None, None

        raw = metadata.get(self._PAYLOAD_FIELD)
        if not isinstance(raw, str):
            return None, None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None, None

        log.info("cache.hit", collection=collection_name, key=key, source=source)
        return payload, Freshness.from_cache(source, retrieved_at)

    def put(
        self,
        collection_name: str,
        key: str,
        payload: dict,
        *,
        source: str,
        searchable_text: str = "",
        retrieved_at: str | None = None,
        extra_metadata: dict | None = None,
    ) -> bool:
        """Upsert a payload. Returns False if the cache is unavailable."""
        collection = self._collection(collection_name)
        if collection is None:
            return False

        metadata: dict[str, Any] = {
            "source": source,
            "retrieved_at": retrieved_at or now_iso(),
            self._PAYLOAD_FIELD: json.dumps(payload, default=str),
        }
        for name, value in (extra_metadata or {}).items():
            if isinstance(value, (str, int, float, bool)):
                metadata[name] = value

        document = searchable_text.strip() or key.replace("_", " ")

        try:
            collection.upsert(ids=[key], documents=[document], metadatas=[metadata])
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.put_failed", key=key, error=str(exc)[:150])
            return False

        log.info("cache.stored", collection=collection_name, key=key)
        return True

    def similar(
        self, collection_name: str, text: str, limit: int = 3
    ) -> list[tuple[dict, float]]:
        """Semantic neighbours, nearest first. Used for cross-run plan retrieval (F61)."""
        collection = self._collection(collection_name)
        if collection is None or not text.strip():
            return []

        try:
            result = collection.query(
                query_texts=[text], n_results=limit, include=["metadatas", "distances"]
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.query_failed", error=str(exc)[:150])
            return []

        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        matches: list[tuple[dict, float]] = []
        for metadata, distance in zip(metadatas, distances, strict=False):
            raw = (metadata or {}).get(self._PAYLOAD_FIELD)
            if not isinstance(raw, str):
                continue
            try:
                matches.append((json.loads(raw), float(distance)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return matches

    def count(self, collection_name: str) -> int:
        collection = self._collection(collection_name)
        if collection is None:
            return 0
        try:
            return int(collection.count())
        except Exception:  # noqa: BLE001
            return 0

    def health(self) -> dict:
        """Surfaced on /health (F64)."""
        if not settings.enable_chroma_cache:
            return {"enabled": False, "reason": "ENABLE_CHROMA_CACHE=false"}
        if not self.connect():
            return {"enabled": False, "reason": "chromadb unreachable"}
        location = (
            f"{settings.chroma_host}:{settings.chroma_port}"
            if settings.chroma_mode == "server"
            else settings.chroma_path
        )
        return {
            "enabled": True,
            "mode": settings.chroma_mode,
            "location": location,
            "collections": {
                COLLECTION_COMPETITORS: self.count(COLLECTION_COMPETITORS),
                COLLECTION_MARKET_RESEARCH: self.count(COLLECTION_MARKET_RESEARCH),
                COLLECTION_PLANS: self.count(COLLECTION_PLANS),
            },
        }


# Module-level cache used by the API wrappers.
knowledge_cache = KnowledgeCache()
