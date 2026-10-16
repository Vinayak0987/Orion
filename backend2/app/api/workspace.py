"""Workspace API — workspace settings + members. Requires auth."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.deps import get_current_user
from app.auth.models import UserPublic
from app.workspace import store

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    logo_url: str | None = None
    timezone: str | None = None
    language: str | None = None


class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: str = "Member"


class MemberUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: str | None = None
    status: str | None = None


def _ws_public(ws: dict) -> dict:
    return {
        "id": ws["_id"],
        "name": ws.get("name"),
        "description": ws.get("description"),
        "logo_url": ws.get("logo_url"),
        "timezone": ws.get("timezone"),
        "language": ws.get("language"),
        "created_at": ws.get("created_at"),
    }


def _member_public(m: dict) -> dict:
    return {
        "id": m["_id"],
        "name": m.get("name"),
        "email": m.get("email"),
        "role": m.get("role"),
        "status": m.get("status"),
        "invited_at": m.get("invited_at"),
    }


@router.get("")
async def get_workspace(current: UserPublic = Depends(get_current_user)) -> dict:
    ws = store.get_or_create_workspace(current.id, current.full_name, current.email)
    return _ws_public(ws)


@router.put("")
async def put_workspace(
    body: WorkspaceUpdate, current: UserPublic = Depends(get_current_user)
) -> dict:
    ws = store.update_workspace(
        current.id, current.full_name, current.email, **body.model_dump()
    )
    return _ws_public(ws)


@router.get("/members")
async def get_members(current: UserPublic = Depends(get_current_user)) -> dict:
    members = store.list_members(current.id, current.full_name, current.email)
    return {"members": [_member_public(m) for m in members]}


@router.post("/members", status_code=201)
async def post_member(
    body: MemberCreate, current: UserPublic = Depends(get_current_user)
) -> dict:
    try:
        m = store.add_member(
            current.id, body.name, body.email, body.role,
            owner_name=current.full_name, owner_email=current.email,
        )
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return _member_public(m)


@router.put("/members/{member_id}")
async def put_member(
    member_id: str, body: MemberUpdate, current: UserPublic = Depends(get_current_user)
) -> dict:
    m = store.update_member(current.id, member_id, **body.model_dump())
    if m is None:
        raise HTTPException(404, "Member not found")
    return _member_public(m)


@router.delete("/members/{member_id}")
async def delete_member(
    member_id: str, current: UserPublic = Depends(get_current_user)
) -> dict:
    try:
        removed = store.remove_member(current.id, member_id)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    if not removed:
        raise HTTPException(404, "Member not found")
    return {"deleted": member_id}
