"""Pydantic request/response schemas for the auth endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(value: str) -> str:
    """Server-side password policy for NEW passwords (signup).

    Rules: 8-128 chars, at least one lowercase, one uppercase, one digit.
    This is the actual control (cannot be bypassed by calling the API directly);
    frontend validation is UX only.
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
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=600)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime
    avatar_url: str | None = None
    job_title: str | None = None
    bio: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class MessageResponse(BaseModel):
    detail: str
