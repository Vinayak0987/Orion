"""Password hashing (Argon2id) and JWT token handling.

Pure, dependency-light functions with no I/O — trivially unit-testable offline.
Secrets and TTLs come from `app.config.settings`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import settings

# Argon2id is the default type for PasswordHasher(). One shared instance is fine
# (it is stateless beyond its parameters).
_hasher = PasswordHasher()

# Token "type" claim values, so an access token can never be used where a
# refresh token is expected and vice-versa.
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or the wrong type."""


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Return an Argon2id hash of `password` (includes salt + parameters)."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """True if `password` matches `hashed`. Never raises for a wrong password."""
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the stored hash should be upgraded (parameters changed)."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# JWT tokens
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(UTC)


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Short-lived access token. `subject` is the user id."""
    issued = _now()
    claims: dict[str, Any] = {
        "sub": subject,
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued,
        "exp": issued + timedelta(minutes=settings.access_token_ttl_minutes),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        claims.update(extra)
    return _encode(claims)


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    """Long-lived refresh token.

    Returns (token, jti, expiry). The jti is stored server-side so the token can
    be revoked (logout / rotation), giving stateful control over refresh.
    """
    issued = _now()
    jti = uuid.uuid4().hex
    expiry = issued + timedelta(days=settings.refresh_token_ttl_days)
    token = _encode(
        {
            "sub": subject,
            "type": REFRESH_TOKEN_TYPE,
            "iat": issued,
            "exp": expiry,
            "jti": jti,
        }
    )
    return token, jti, expiry


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode + verify a token. Raises TokenError on any problem.

    If `expected_type` is given, the token's "type" claim must match.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenError(
            f"Expected a {expected_type} token, got {payload.get('type')!r}"
        )
    return payload
