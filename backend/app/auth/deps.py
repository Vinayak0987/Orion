"""FastAPI dependencies for authentication.

`get_current_user` extracts + verifies the Bearer access token and loads the
user. `get_optional_user` does the same but returns None instead of raising —
useful for endpoints that stay open but personalise when logged in (the existing
routes remain open per project decision).
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import security, store
from app.auth.models import UserPublic

# auto_error=False so we can return 401 with our own message / support optional.
_bearer = HTTPBearer(auto_error=False)


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["_id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"],
    )


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserPublic:
    """Require a valid access token; return the authenticated user or 401."""
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = security.decode_token(
            creds.credentials, expected_type=security.ACCESS_TOKEN_TYPE
        )
    except security.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = store.get_user_by_id(payload.get("sub", ""))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _to_public(user)


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UserPublic]:
    """Return the user if a valid token is present, else None (never raises)."""
    if creds is None or not creds.credentials:
        return None
    try:
        payload = security.decode_token(
            creds.credentials, expected_type=security.ACCESS_TOKEN_TYPE
        )
    except security.TokenError:
        return None
    user = store.get_user_by_id(payload.get("sub", ""))
    return _to_public(user) if user else None
