"""Pydantic request/response schemas for the auth endpoints.

Kept minimal and permissive on the user document itself (Mongo lets the schema
evolve), but strict on the inputs we accept over the wire.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(value: str) -> str:
    """Server-side password policy for NEW passwords (signup).

    Mirrors the frontend rules in auth/validation.js so the two agree, but —
    critically — this runs on the server where it cannot be bypassed by calling
    the API directly (curl/Postman/a modified frontend). Client validation is
    UX; this is the actual control.

    Rules: 8-128 chars, at least one lowercase, one uppercase, one digit.
    """
    if not (8 <= len(value) <= 128):
        raise ValueError("Password must be between 8 and 128 characters.")
    if not any(c.islower() for c in value):
        raise ValueError("Password must contain a lowercase letter.")
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain an uppercase letter.")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain a number.")
    return value


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    # Length bounds here; composition rules enforced by the validator below.
    # The upper bound also guards against DoS via very long Argon2 inputs.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    """User fields safe to return to the client — never the password hash."""

    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Login/refresh response. The refresh token itself is delivered separately
    as an httpOnly cookie, not in this body."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token lifetime in seconds
    user: UserPublic


class MessageResponse(BaseModel):
    detail: str
