"""Encryption at rest for secrets (user API keys).

Fernet symmetric encryption. The key comes from settings.encryption_key when
set; otherwise a deterministic key is derived from jwt_secret so the app boots
in development without extra config. Set a real ENCRYPTION_KEY outside dev.

Stored ciphertext is prefixed with 'enc:' so a value can be detected as
encrypted vs legacy plaintext and migrated transparently.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_PREFIX = "enc:"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.encryption_key.strip()
    if key:
        # Expect a urlsafe base64 32-byte key. If a raw string was provided,
        # derive a valid Fernet key from it.
        try:
            Fernet(key.encode())
            return Fernet(key.encode())
        except Exception:
            derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
            return Fernet(derived)
    # Dev fallback: derive deterministically from jwt_secret.
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(derived)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    token = _fernet().encrypt(plaintext.encode()).decode()
    return _PREFIX + token


def decrypt(stored: str) -> str:
    if not stored:
        return ""
    if not stored.startswith(_PREFIX):
        # Legacy plaintext (pre-encryption). Return as-is for transparent migration.
        return stored
    token = stored[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""  # key rotated or corrupt — treat as unset rather than crash
