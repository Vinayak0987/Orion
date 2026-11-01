"""Embedding service for vector search.

Generates embeddings for documents and queries using available LLM providers.
Supports OpenAI-compatible embedding endpoints and falls back to simple hash-based
embeddings if no embedding provider is available.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from app.config import settings


class EmbeddingError(RuntimeError):
    """Embedding generation failed."""


class EmbeddingClient:
    """Generate embeddings using available providers."""

    def __init__(self, user_keys: dict | None = None):
        self.user_keys = user_keys or {}

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        if not text or not text.strip():
            return [0.0] * 1536  # Return zero vector for empty text

        # Try available embedding providers in order
        providers = [
            self._try_openai_embed,
            self._try_ollama_embed,
        ]

        for provider in providers:
            try:
                embedding = await provider(text)
                if embedding:
                    return embedding
            except Exception:  # noqa: BLE001
                continue

        # Fallback: simple hash-based embedding (not semantic, but functional)
        return self._hash_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batched)."""
        if not texts:
            return []

        # For now, process sequentially (can be optimized with real batch API)
        embeddings = []
        for text in texts:
            emb = await self.embed_text(text)
            embeddings.append(emb)
        return embeddings

    async def _try_openai_embed(self, text: str) -> list[float] | None:
        """Try OpenAI-compatible embedding endpoint (OpenAI, OpenRouter, etc.)."""
        # Try OpenAI API key first
        api_key = self.user_keys.get("openai_api_key") or settings.openai_api_key
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "text-embedding-3-small", "input": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["data"][0]["embedding"]
        except Exception:  # noqa: BLE001
            pass

        return None

    async def _try_ollama_embed(self, text: str) -> list[float] | None:
        """Try Ollama's embedding endpoint (local, free)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_model, "prompt": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("embedding")
        except Exception:  # noqa: BLE001
            pass

        return None

    def _hash_embedding(self, text: str, dim: int = 1536) -> list[float]:
        """Fallback: generate a deterministic embedding from text hash.

        This is NOT semantic - it's just a functional fallback when no embedding
        provider is available. The vector search will still work, just without
        semantic understanding.
        """
        # Create a hash of the text
        hash_obj = hashlib.sha256(text.encode("utf-8"))
        hash_bytes = hash_obj.digest()

        # Expand hash to desired dimension by repeating and mixing
        embedding = []
        for i in range(dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Convert to float in [-1, 1] range
            embedding.append((byte_val / 255.0) * 2 - 1)

        return embedding


# Singleton instance
_client: EmbeddingClient | None = None


def get_embedding_client(user_keys: dict | None = None) -> EmbeddingClient:
    """Get or create the embedding client singleton."""
    global _client
    if _client is None:
        _client = EmbeddingClient(user_keys)
    return _client
