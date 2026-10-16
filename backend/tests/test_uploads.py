"""Upload tests — signature generation + Cloudinary upload mocked offline."""

from __future__ import annotations

import hashlib

import httpx
import pytest
import respx


# --- signature ---------------------------------------------------------------

def test_sign_matches_cloudinary_spec():
    from app.core.uploads import _sign

    params = {"timestamp": 1700000000, "folder": "orion/avatars", "public_id": "avatar_u1"}
    secret = "mysecret"
    # Expected: sorted "k=v" joined by & + secret, SHA-1 hex.
    canonical = "folder=orion/avatars&public_id=avatar_u1&timestamp=1700000000"
    expected = hashlib.sha1((canonical + secret).encode()).hexdigest()
    assert _sign(params, secret) == expected


def test_sign_excludes_file_and_api_key():
    from app.core.uploads import _sign

    params = {"timestamp": 1, "api_key": "KEY", "file": b"...", "resource_type": "image"}
    # Only timestamp participates.
    canonical = "timestamp=1"
    expected = hashlib.sha1((canonical + "s").encode()).hexdigest()
    assert _sign(params, "s") == expected


# --- upload (mocked) ---------------------------------------------------------

@pytest.fixture
def cloudinary_configured(monkeypatch):
    import app.config as config
    monkeypatch.setattr(config.settings, "cloud_name", "testcloud")
    monkeypatch.setattr(config.settings, "cloud_api_key", "123")
    monkeypatch.setattr(config.settings, "cloud_api_secret", "shh")
    # core.uploads reads settings at call time, so patching the live object works.
    import app.core.uploads as up
    monkeypatch.setattr(up.settings, "cloud_name", "testcloud")
    monkeypatch.setattr(up.settings, "cloud_api_key", "123")
    monkeypatch.setattr(up.settings, "cloud_api_secret", "shh")


@respx.mock
async def test_upload_bytes_returns_secure_url(cloudinary_configured):
    from app.core.uploads import upload_bytes

    route = respx.post("https://api.cloudinary.com/v1_1/testcloud/image/upload").mock(
        return_value=httpx.Response(
            200,
            json={
                "secure_url": "https://res.cloudinary.com/testcloud/image/upload/orion/avatars/avatar_u1.png",
                "public_id": "orion/avatars/avatar_u1",
                "bytes": 1234,
                "format": "png",
                "resource_type": "image",
                "original_filename": "me",
            },
        )
    )
    result = await upload_bytes(b"\x89PNG...", "me.png", resource_type="image",
                               folder="orion/avatars", public_id="avatar_u1")
    assert route.called
    assert result["secure_url"].endswith("avatar_u1.png")
    assert result["format"] == "png"


async def test_upload_not_configured_raises(monkeypatch):
    import app.core.uploads as up
    from app.core.uploads import UploadError, upload_bytes

    monkeypatch.setattr(up.settings, "cloud_name", "")
    monkeypatch.setattr(up.settings, "cloud_api_key", "")
    monkeypatch.setattr(up.settings, "cloud_api_secret", "")
    with pytest.raises(UploadError):
        await upload_bytes(b"x", "f.png")


@respx.mock
async def test_upload_bytes_surfaces_error(cloudinary_configured):
    from app.core.uploads import UploadError, upload_bytes

    respx.post("https://api.cloudinary.com/v1_1/testcloud/image/upload").mock(
        return_value=httpx.Response(401, text="Invalid signature")
    )
    with pytest.raises(UploadError) as exc:
        await upload_bytes(b"x", "f.png", resource_type="image")
    assert "401" in str(exc.value)


# --- API: uploads disabled when not configured -------------------------------

def test_uploads_endpoint_503_when_not_configured():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        # No Cloudinary creds in the test env → 503.
        resp = c.post(
            "/uploads",
            files={"file": ("x.png", b"data", "image/png")},
        )
        # Either 503 (not configured) is the expected behaviour here.
        assert resp.status_code in (503, 502)
