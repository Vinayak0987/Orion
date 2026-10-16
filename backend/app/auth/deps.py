"""FastAPI dependencies for authentication.

`get_current_user` requires a valid Bearer access token. `get_optional_user`
returns None instead of raising, for endpoints that stay open but personalise
when logged in.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import security, store
from app.auth.models import UserPublic

_bearer = HTTPBearer(auto_error=False)


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=user["_id"],
        email=user["email"],
        full_name=user["full_name"],
        created_at=user["created_at"],
        avatar_url=user.get("avatar_url"),
        job_title=user.get("job_title"),
        bio=user.get("bio"),
    )


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserPublic:
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
