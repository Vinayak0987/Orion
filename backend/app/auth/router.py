"""Auth endpoints.

Token model:
  • access token  — short-lived, returned in the JSON body; the client holds it
    in memory and sends it as `Authorization: Bearer`.
  • refresh token — long-lived, delivered ONLY as an httpOnly cookie so JS can't
    read it (XSS-resistant). Stored server-side (revocable) and rotated on each
    refresh.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.auth import security, store
from app.auth.deps import _to_public, get_current_user
from app.auth.models import (
    LoginRequest,
    MessageResponse,
    SignupRequest,
    TokenResponse,
    UserPublic,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _access_ttl_seconds() -> int:
    return settings.access_token_ttl_minutes * 60


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.refresh_cookie_name, path="/auth")


def _issue_tokens(response: Response, user: dict) -> TokenResponse:
    """Mint an access token + a rotated refresh token, set the cookie, return
    the body payload."""
    access = security.create_access_token(user["_id"])
    refresh, jti, expiry = security.create_refresh_token(user["_id"])
    store.store_refresh_token(jti, user["_id"], expiry)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access,
        expires_in=_access_ttl_seconds(),
        user=_to_public(user),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response) -> TokenResponse:
    try:
        user = store.create_user(
            email=body.email,
            full_name=body.full_name,
            password_hash=security.hash_password(body.password),
        )
    except ValueError:
        # Do not reveal which emails exist beyond this direct signup collision.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return _issue_tokens(response, user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response) -> TokenResponse:
    user = store.get_user_by_email(body.email)
    # Same generic message whether the email is unknown or the password is wrong,
    # so the endpoint doesn't leak which emails are registered.
    if user is None or not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    # Opportunistically upgrade the hash if Argon2 parameters have changed.
    if security.needs_rehash(user["password_hash"]):
        store.update_user_password(
            user["_id"], security.hash_password(body.password)
        )
    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, orion_refresh: str | None = Cookie(default=None)) -> TokenResponse:
    # The cookie parameter name must match settings.refresh_cookie_name; keep in
    # sync if that changes.
    token = orion_refresh
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token."
        )
    try:
        payload = security.decode_token(token, expected_type=security.REFRESH_TOKEN_TYPE)
    except security.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    jti = payload.get("jti", "")
    if not store.is_refresh_token_active(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is no longer valid.",
        )

    user = store.get_user_by_id(payload.get("sub", ""))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists."
        )

    # Rotate: revoke the used refresh token, issue a fresh pair.
    store.revoke_refresh_token(jti)
    return _issue_tokens(response, user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, orion_refresh: str | None = Cookie(default=None)) -> MessageResponse:
    # Best-effort revoke of the presented refresh token, then clear the cookie.
    if orion_refresh:
        try:
            payload = security.decode_token(
                orion_refresh, expected_type=security.REFRESH_TOKEN_TYPE
            )
            store.revoke_refresh_token(payload.get("jti", ""))
        except security.TokenError:
            pass
    _clear_refresh_cookie(response)
    return MessageResponse(detail="Logged out.")


@router.get("/me", response_model=UserPublic)
def me(current: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current
