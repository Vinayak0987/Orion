"""Auth endpoints.

Token model:
  • access token  — short-lived, in the JSON body; client holds it in memory,
    sends it as `Authorization: Bearer`.
  • refresh token — long-lived, httpOnly cookie (XSS-resistant), stored
    server-side (revocable), rotated on each refresh.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.auth import security, store
from app.auth.deps import _to_public, get_current_user
from app.auth.models import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
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
    access = security.create_access_token(user["_id"])
    refresh, jti, expiry = security.create_refresh_token(user["_id"])
    store.store_refresh_token(jti, user["_id"], expiry)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access, expires_in=_access_ttl_seconds(), user=_to_public(user)
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    return _issue_tokens(response, user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response) -> TokenResponse:
    user = store.get_user_by_email(body.email)
    if user is None or not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    if security.needs_rehash(user["password_hash"]):
        store.update_user_password(user["_id"], security.hash_password(body.password))
    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, orion_refresh: str | None = Cookie(default=None)) -> TokenResponse:
    token = orion_refresh
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token.")
    try:
        payload = security.decode_token(token, expected_type=security.REFRESH_TOKEN_TYPE)
    except security.TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    jti = payload.get("jti", "")
    if not store.is_refresh_token_active(jti):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is no longer valid.")

    user = store.get_user_by_id(payload.get("sub", ""))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")

    store.revoke_refresh_token(jti)  # rotate
    return _issue_tokens(response, user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, orion_refresh: str | None = Cookie(default=None)) -> MessageResponse:
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


@router.put("/me", response_model=UserPublic)
def update_me(
    body: UpdateProfileRequest, current: UserPublic = Depends(get_current_user)
) -> UserPublic:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        try:
            store.update_user(current.id, **fields)
        except Exception as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, "Could not update profile.") from exc
    user = store.get_user_by_id(current.id)
    return _to_public(user)


@router.put("/password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest, current: UserPublic = Depends(get_current_user)
) -> MessageResponse:
    user = store.get_user_by_id(current.id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")
    if not security.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect.")
    store.update_user_password(current.id, security.hash_password(body.new_password))
    # Revoke all refresh tokens so other sessions must re-authenticate.
    store.revoke_all_user_tokens(current.id)
    return MessageResponse(detail="Password changed.")
