"""File uploads to Cloudinary via signed REST (no SDK).

Cloudinary's signed upload: POST multipart/form-data to
  https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload
with params (timestamp, folder, public_id, …) plus a `signature` that is the
hex SHA-1 of the sorted params joined as 'k=v&k=v' + the API secret, and the
`api_key`.

resource_type:
  - "image" for avatars/images
  - "raw"   for documents (pdf, docx, txt, …)
  - "auto"  lets Cloudinary detect

Returns the secure (https) URL of the stored asset. Raises UploadError on any
failure; callers decide how to surface it.
"""

from __future__ import annotations

import hashlib
import time

import httpx

from app.config import settings


class UploadError(RuntimeError):
    """Cloudinary upload failed or is not configured."""


def _creds() -> tuple[str, str, str]:
    name = settings.cloud_name.strip()
    key = settings.cloud_api_key.strip()
    secret = settings.cloud_api_secret.strip()
    if not (name and key and secret):
        raise UploadError(
            "Cloudinary is not configured. Set CLOUD_NAME, CLOUD_API_KEY, "
            "CLOUD_API_SECRET in .env."
        )
    return name, key, secret


def _sign(params: dict, secret: str) -> str:
    """Cloudinary signature: SHA-1 hex of sorted 'k=v' params joined by '&' + secret.

    Only non-empty params (excluding file, api_key, signature, resource_type)
    participate in the signature.
    """
    to_sign = {
        k: v
        for k, v in params.items()
        if v not in (None, "") and k not in ("file", "api_key", "resource_type")
    }
    canonical = "&".join(f"{k}={to_sign[k]}" for k in sorted(to_sign))
    return hashlib.sha1((canonical + secret).encode()).hexdigest()


async def upload_bytes(
    data: bytes,
    filename: str,
    *,
    resource_type: str = "auto",
    folder: str = "orion",
    public_id: str | None = None,
) -> dict:
    """Upload raw bytes to Cloudinary. Returns {secure_url, public_id, bytes, format, resource_type}."""
    name, key, secret = _creds()

    timestamp = int(time.time())
    sign_params: dict = {"timestamp": timestamp, "folder": folder}
    if public_id:
        sign_params["public_id"] = public_id
    signature = _sign(sign_params, secret)

    form = {
        "api_key": key,
        "timestamp": str(timestamp),
        "folder": folder,
        "signature": signature,
    }
    if public_id:
        form["public_id"] = public_id

    url = f"https://api.cloudinary.com/v1_1/{name}/{resource_type}/upload"
    files = {"file": (filename, data)}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, data=form, files=files)
    except httpx.HTTPError as e:
        raise UploadError(f"Cloudinary transport error: {e}") from e

    if resp.status_code >= 400:
        detail = resp.text[:300]
        raise UploadError(f"Cloudinary {resp.status_code}: {detail}")

    body = resp.json()
    return {
        "secure_url": body.get("secure_url"),
        "public_id": body.get("public_id"),
        "bytes": body.get("bytes"),
        "format": body.get("format"),
        "resource_type": body.get("resource_type"),
        "original_filename": body.get("original_filename"),
    }
