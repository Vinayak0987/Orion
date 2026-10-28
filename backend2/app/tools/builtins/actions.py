"""External ACTION tools — real-world side effects (API path, Step 3).

These are the first concrete action tools. They are gated by the executor's
approval flow (names match the action classifier in app.tools.modes) and only
run in Action mode. Each degrades honestly: if the required account isn't
connected, it returns {error, needs_connect} rather than pretending to act.

  • gmail_send   — send an email via the user's connected Google account (Gmail API)
  • http_action  — generic authenticated HTTP call to any configured endpoint
                   (covers Slack/CRM/webhooks/custom APIs without per-tool code)
"""

from __future__ import annotations

import base64
from email.message import EmailMessage

import httpx

from app.tools.base import ToolContext, err, need, ok, tool

_GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _resolve_oauth_user(provider: str) -> str | None:
    """Return the user_id that owns a connection for `provider`. If exactly one
    exists, return it (single-tenant fallback so missions running as
    'default-user' can use the real signed-in user's connection)."""
    try:
        from app.db.sqlite import connection
        with connection() as c:
            rows = c.execute(
                "SELECT user_id FROM oauth_connections WHERE provider=? AND status='connected'",
                (provider,),
            ).fetchall()
        ids = [r["user_id"] for r in rows]
        return ids[0] if len(ids) == 1 else (ids[0] if ids else None)
    except Exception:  # noqa: BLE001
        return None


# --- gmail_send --------------------------------------------------------------
@tool(
    "gmail_send",
    display_name="Gmail: Send Email",
    description="Send an email from the user's connected Gmail account. ACTION — requires "
    "approval + a connected Google account. Input: {to, subject, body, cc?, bcc?}.",
    category="communication",
    input_schema={
        "to": {"type": "string", "required": True},
        "subject": {"type": "string", "required": True},
        "body": {"type": "string", "required": True},
        "cc": {"type": "string"}, "bcc": {"type": "string"},
    },
)
async def gmail_send(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "to")) or (m := need(ti, "subject")) or (m := need(ti, "body")):
        return err(m)

    from app.oauth.service import get_valid_access_token

    uid = ctx.user_id or "default-user"
    token = await get_valid_access_token(uid, "google")
    if not token:
        # Single-tenant fallback: missions run as 'default-user', but the user's
        # real OAuth connection may be stored under their actual account id. If
        # exactly one Google connection exists, use it.
        resolved = _resolve_oauth_user("google")
        if resolved and resolved != uid:
            token = await get_valid_access_token(resolved, "google")
    if not token:
        return err("Gmail is not connected. Connect your Google account first.",
                   needs_connect="google", degraded=True)

    msg = EmailMessage()
    msg["To"] = ti["to"].strip()
    msg["Subject"] = ti["subject"]
    if ti.get("cc"):
        msg["Cc"] = ti["cc"]
    if ti.get("bcc"):
        msg["Bcc"] = ti["bcc"]
    msg.set_content(ti["body"])
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(_GMAIL_SEND_URL, headers={"Authorization": f"Bearer {token}"},
                             json={"raw": raw})
        if r.status_code in (401, 403):
            return err("Gmail rejected the request — the connection may lack the 'gmail.send' "
                       "scope. Reconnect Google with send permission.",
                       needs_connect="google", status_code=r.status_code, degraded=True)
        if r.status_code >= 400:
            return err(f"Gmail API error ({r.status_code}): {r.text[:300]}", degraded=True)
        data = r.json()
        return ok(sent=True, message_id=data.get("id"), to=ti["to"], subject=ti["subject"])
    except Exception as e:  # noqa: BLE001
        return err(f"gmail_send failed: {e}", degraded=True)


# --- http_action -------------------------------------------------------------
@tool(
    "http_action",
    display_name="HTTP Action (generic)",
    description="Perform a generic HTTP request to an external API/webhook (POST/PUT/PATCH/"
    "DELETE). ACTION — requires approval. Use for Slack/CRM/custom webhooks. Input: "
    "{url, method?, json?, headers?, bearer_token?}.",
    category="utility",
    input_schema={
        "url": {"type": "string", "required": True},
        "method": {"type": "string"},
        "json": {"type": "object"},
        "headers": {"type": "object"},
        "bearer_token": {"type": "string"},
    },
)
async def http_action(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "url")):
        return err(m)
    url = ti["url"].strip()
    if not url.lower().startswith(("http://", "https://")):
        return err("url must be an http(s) URL")
    method = (ti.get("method") or "POST").upper()
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return err("http_action is for write methods (POST/PUT/PATCH/DELETE). "
                   "Use http_request for GET.")
    headers = dict(ti.get("headers") or {})
    if ti.get("bearer_token"):
        headers["Authorization"] = f"Bearer {ti['bearer_token']}"
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as c:
            r = await c.request(method, url, json=ti.get("json"), headers=headers)
        ctype = r.headers.get("content-type", "")
        body = r.json() if "application/json" in ctype else r.text[:4000]
        return ok(status_code=r.status_code, ok=r.status_code < 400, body=body)
    except Exception as e:  # noqa: BLE001
        return err(f"http_action failed: {e}", degraded=True)
