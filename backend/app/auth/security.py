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

_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or the wrong type."""


# --- Password hashing --------------------------------------------------------
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except Exception:
        return False


# --- JWT tokens --------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(UTC)


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
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
