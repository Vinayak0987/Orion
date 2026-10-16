"""User settings store — API keys (encrypted at rest) + preferences.

Single home for reading/writing the user_settings table. Both the Settings API
and the mission key-loader go through here. Keys are encrypted with Fernet
(app.core.crypto) before storage and decrypted only when loaded for a run.

Phase: single 'default-user' row until auth user_id is threaded into missions.
"""

from __future__ import annotations

import json

from app.core.crypto import decrypt, encrypt
from app.db.sqlite import _now, connection

DEFAULT_USER = "default-user"

PROVIDERS = (
    "groq_api_key",
    "gemini_api_key",
    "openai_api_key",
    "serper_api_key",
    "google_places_api_key",
)


def _load_raw(user_id: str) -> dict:
    with connection() as conn:
        row = conn.execute(
            "SELECT api_keys FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
    return json.loads(row["api_keys"]) if row else {}


def _save_raw(user_id: str, keys: dict) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO user_settings (user_id, api_keys, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET api_keys = excluded.api_keys, "
            "updated_at = excluded.updated_at",
            (user_id, json.dumps(keys), _now()),
        )


def set_keys(updates: dict, user_id: str = DEFAULT_USER) -> None:
    """Store the given provider keys (encrypted). Only non-None values are set."""
    keys = _load_raw(user_id)
    for provider, value in updates.items():
        if provider in PROVIDERS and value is not None:
            keys[provider] = encrypt(value.strip())
    _save_raw(user_id, keys)


def delete_key(provider: str, user_id: str = DEFAULT_USER) -> bool:
    """Remove one provider key. `provider` may be short ('groq') or full
    ('groq_api_key'). Returns True if a key was removed."""
    full = provider if provider.endswith("_api_key") else f"{provider}_api_key"
    keys = _load_raw(user_id)
    if full in keys:
        keys.pop(full)
        _save_raw(user_id, keys)
        return True
    return False


def masked_keys(user_id: str = DEFAULT_USER) -> dict:
    """Return keys masked to last 4 chars (null if unset). For the UI."""
    keys = _load_raw(user_id)
    out = {}
    for provider in PROVIDERS:
        stored = keys.get(provider)
        plain = decrypt(stored) if stored else ""
        out[provider.replace("_api_key", "")] = (
            f"...{plain[-4:]}" if len(plain) > 4 else ("..." if plain else None)
        )
    return out


def decrypted_keys(user_id: str = DEFAULT_USER) -> dict:
    """Return the plaintext keys for a mission run. Never exposed over the API.

    Keys are returned under their full names (groq_api_key, serper_api_key, …)
    so the LLM chain and tools can read them directly.
    """
    keys = _load_raw(user_id)
    return {p: decrypt(keys[p]) for p in PROVIDERS if keys.get(p)}
