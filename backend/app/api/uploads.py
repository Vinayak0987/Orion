"""Uploads API — store images/documents in Cloudinary.

POST /uploads          generic image/document upload → returns the stored URL
POST /auth/avatar      upload a profile photo → stores avatar_url on the user

Both require Cloudinary to be configured (CLOUD_* in .env). If not configured,
they return 503 with a clear message.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import store as auth_store
from app.auth.deps import _to_public, get_current_user
from app.auth.models import UserPublic
from app.config import settings
from app.core.uploads import UploadError, upload_bytes

router = APIRouter(tags=["uploads"])

# 10 MB cap for images, 25 MB for documents.
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DOC_BYTES = 25 * 1024 * 1024

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
    "text/markdown",
}


def _require_cloudinary() -> None:
    if not settings.cloudinary_available:
        raise HTTPException(
            503, "File storage is not configured. Set CLOUD_NAME, CLOUD_API_KEY, "
            "CLOUD_API_SECRET in .env."
        )


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Generic upload: images → resource_type 'image', documents → 'raw'."""
    _require_cloudinary()
    data = await file.read()
    ctype = file.content_type or ""

    if ctype in IMAGE_TYPES:
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image exceeds 10 MB.")
        resource_type, folder = "image", "orion/images"
    elif ctype in DOC_TYPES:
        if len(data) > MAX_DOC_BYTES:
            raise HTTPException(413, "Document exceeds 25 MB.")
        resource_type, folder = "raw", "orion/documents"
    else:
        raise HTTPException(
            422, f"Unsupported file type '{ctype}'. Accepted: images, PDF, Word, TXT, CSV, MD."
        )

    try:
        result = await upload_bytes(
            data, file.filename or "upload", resource_type=resource_type, folder=folder
        )
    except UploadError as e:
        raise HTTPException(502, str(e)) from e

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "bytes": result["bytes"],
        "format": result["format"],
        "resource_type": result["resource_type"],
        "filename": file.filename,
    }


@router.post("/auth/avatar", response_model=UserPublic)
async def upload_avatar(
    file: UploadFile = File(...), current: UserPublic = Depends(get_current_user)
) -> UserPublic:
    """Upload a profile photo and store its URL on the user."""
    _require_cloudinary()
    data = await file.read()
    if (file.content_type or "") not in IMAGE_TYPES:
        raise HTTPException(422, "Avatar must be an image (PNG, JPEG, WebP, GIF).")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image exceeds 10 MB.")

    try:
        result = await upload_bytes(
            data,
            file.filename or "avatar",
            resource_type="image",
            folder="orion/avatars",
            public_id=f"avatar_{current.id}",
        )
    except UploadError as e:
        raise HTTPException(502, str(e)) from e

    auth_store.update_user(current.id, avatar_url=result["secure_url"])
    user = auth_store.get_user_by_id(current.id)
    return _to_public(user)
