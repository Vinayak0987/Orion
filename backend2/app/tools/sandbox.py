"""Shared helpers for built-in tools: a filesystem sandbox and an HTTP fetcher.

`safe_path` guarantees that every path a tool touches resolves INSIDE the
configured workspace directory — an agent cannot read or write outside it, even
with `..` or absolute paths. `fetch` is a single hardened httpx GET used by the
web tools (timeout, size cap, redirect handling, UA header).
"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.config import settings

UA = "OrionAgent/1.0 (+https://orion.local)"
MAX_FETCH_BYTES = 5 * 1024 * 1024  # 5 MB cap on any single web fetch


class SandboxError(Exception):
    pass


def safe_path(rel: str, *, must_exist: bool = False) -> Path:
    """Resolve `rel` strictly inside the workspace root. Raises SandboxError
    if it escapes. Accepts both relative and absolute inputs; absolutes are
    re-anchored under the workspace so an agent can't reach the real FS root."""
    root = settings.workspace_dir
    rel = (rel or "").strip()
    if not rel:
        raise SandboxError("empty path")
    p = Path(rel)
    # Re-anchor absolute paths under the sandbox root.
    if p.is_absolute():
        p = root / p.relative_to(p.anchor)
    else:
        p = root / p
    resolved = p.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as e:
        raise SandboxError(f"path escapes workspace: {rel}") from e
    if must_exist and not resolved.exists():
        raise SandboxError(f"not found: {rel}")
    return resolved


def rel_to_workspace(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(settings.workspace_dir.resolve()))
    except Exception:
        return str(p)


async def fetch(url: str, *, timeout: float = 15.0, headers: dict | None = None) -> httpx.Response:
    """Hardened GET. Caller handles the Response. Raises httpx errors (callers
    catch them and degrade)."""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=h) as client:
        resp = await client.get(url)
        return resp


def valid_url(url: str) -> bool:
    return isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
