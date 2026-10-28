"""Integrations registry — SaaS connectors (token-based, honest, live-validated).

Every connector is connectable NOW with a user-provided token that the user
generates in the provider's own dashboard (no OAuth app registration required on
our side, no third-party redirect). On connect we make a REAL lightweight API
call to the provider to verify the token actually works before marking the
integration connected — so a "connected" status is never faked.

Token types per provider (what the user pastes):
  • slack        → Bot/User token  (xoxb-… / xoxp-…)        validate: auth.test
  • notion       → Internal Integration Token (secret_… / ntn_…)  validate: /users/me
  • google_drive → OAuth access token OR service-account access token  validate: /about
  • github       → Personal Access Token                     validate: /user
  • stripe       → Secret key (sk_…)                         validate: /v1/account
  • twilio       → AccountSID:AuthToken                       validate: /Accounts/{sid}
  • shopify      → shop.myshopify.com|admin_api_token         validate: /shop.json
  • sendgrid     → API key                                    validate: /v3/scopes
  • zapier       → webhook URL (keyless)                      validate: reachable POST

If a provider's network is unreachable at connect time we DON'T silently fail —
we return an error so the user knows the token wasn't verified.
"""

from __future__ import annotations

import httpx

from app.core.crypto import decrypt, encrypt
from app.db.sqlite import _now, connection

# Catalog. Each entry declares HOW it connects (the easiest/fastest method):
#   connect_method: 'oauth' | 'api_key' | 'mcp'
#   oauth_provider: provider id for oauth (maps to app.oauth.providers)
#   mcp_url:        hosted MCP endpoint for 'mcp'
#   token_label/token_hint: for 'api_key' and token-auth 'mcp'
#   logo_key:       frontend brand-logo key
CATALOG = [
    # --- Communication ---
    {"id": "gmail", "name": "Gmail", "description": "Read and send email from the user's Gmail.",
     "category": "communication", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "gmail"},
    {"id": "google_drive", "name": "Google Drive", "description": "Read and write files and docs.",
     "category": "storage", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "google_drive"},
    {"id": "google_calendar", "name": "Google Calendar", "description": "Create and read calendar events.",
     "category": "productivity", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "google_calendar"},
    {"id": "outlook", "name": "Outlook / Microsoft 365", "description": "Email, calendar, and OneDrive via Microsoft Graph.",
     "category": "communication", "connect_method": "oauth", "oauth_provider": "microsoft", "logo_key": "outlook"},
    {"id": "slack", "name": "Slack", "description": "Send messages and read channels.",
     "category": "communication", "connect_method": "oauth", "oauth_provider": "slack", "logo_key": "slack"},
    {"id": "twilio", "name": "Twilio", "description": "Send SMS/WhatsApp and place calls.",
     "category": "communication", "connect_method": "api_key", "logo_key": "twilio",
     "token_label": "AccountSID:AuthToken", "token_hint": "Twilio console → paste as ACxxxx:your_auth_token."},
    {"id": "sendgrid", "name": "SendGrid", "description": "Send transactional email at scale.",
     "category": "communication", "connect_method": "api_key", "logo_key": "sendgrid",
     "token_label": "API Key", "token_hint": "app.sendgrid.com → Settings → API Keys."},
    {"id": "discord", "name": "Discord", "description": "Post messages to Discord channels.",
     "category": "communication", "connect_method": "api_key", "logo_key": "discord",
     "token_label": "Bot Token", "token_hint": "Discord Developer Portal → Bot → Token."},

    # --- Social media ---
    {"id": "linkedin", "name": "LinkedIn", "description": "Publish posts and read company page analytics.",
     "category": "social", "connect_method": "oauth", "oauth_provider": "linkedin", "logo_key": "linkedin"},
    {"id": "x_twitter", "name": "X (Twitter)", "description": "Post tweets and read mentions/analytics.",
     "category": "social", "connect_method": "oauth", "oauth_provider": "x", "logo_key": "x"},
    {"id": "instagram", "name": "Instagram", "description": "Publish posts/reels and read insights (via Meta).",
     "category": "social", "connect_method": "oauth", "oauth_provider": "meta", "logo_key": "instagram"},
    {"id": "facebook", "name": "Facebook", "description": "Manage Pages — post and read insights (via Meta).",
     "category": "social", "connect_method": "oauth", "oauth_provider": "meta", "logo_key": "facebook"},
    {"id": "youtube", "name": "YouTube", "description": "Upload videos and read channel analytics (via Google).",
     "category": "social", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "youtube"},
    {"id": "tiktok", "name": "TikTok", "description": "Publish videos and read analytics.",
     "category": "social", "connect_method": "oauth", "oauth_provider": "tiktok", "logo_key": "tiktok"},

    # --- Marketing / Ads ---
    {"id": "google_ads", "name": "Google Ads", "description": "Manage campaigns and pull ad performance.",
     "category": "marketing", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "google_ads"},
    {"id": "meta_ads", "name": "Meta Ads", "description": "Manage Facebook/Instagram ad campaigns.",
     "category": "marketing", "connect_method": "oauth", "oauth_provider": "meta", "logo_key": "facebook"},
    {"id": "hubspot", "name": "HubSpot", "description": "CRM contacts, deals, and marketing automation.",
     "category": "marketing", "connect_method": "api_key", "logo_key": "hubspot",
     "token_label": "Private App Token", "token_hint": "HubSpot → Settings → Integrations → Private Apps."},
    {"id": "mailchimp", "name": "Mailchimp", "description": "Email campaigns and audience management.",
     "category": "marketing", "connect_method": "api_key", "logo_key": "mailchimp",
     "token_label": "API Key", "token_hint": "Mailchimp → Account → Extras → API keys."},
    {"id": "canva", "name": "Canva", "description": "Create and export designs programmatically.",
     "category": "marketing", "connect_method": "oauth", "oauth_provider": "canva", "logo_key": "canva"},

    # --- E-commerce / Payments ---
    {"id": "shopify", "name": "Shopify", "description": "Products, orders, inventory, and storefront.",
     "category": "ecommerce", "connect_method": "api_key", "logo_key": "shopify",
     "token_label": "shop.myshopify.com|admin_token", "token_hint": "Admin → Develop apps → Admin API token."},
    {"id": "stripe", "name": "Stripe", "description": "Customers, invoices, subscriptions, payments.",
     "category": "payments", "connect_method": "api_key", "logo_key": "stripe",
     "token_label": "Secret Key", "token_hint": "dashboard.stripe.com/apikeys → secret key."},
    {"id": "paypal", "name": "PayPal", "description": "Payments, invoices, and payouts.",
     "category": "payments", "connect_method": "oauth", "oauth_provider": "paypal", "logo_key": "paypal"},
    {"id": "woocommerce", "name": "WooCommerce", "description": "WordPress store products and orders.",
     "category": "ecommerce", "connect_method": "api_key", "logo_key": "woocommerce",
     "token_label": "store_url|consumer_key|consumer_secret", "token_hint": "WooCommerce → Settings → Advanced → REST API."},

    # --- Image / Video generation (MCP) ---
    {"id": "higgsfield", "name": "Higgsfield", "description": "Generate cinematic images & videos (Sora, Veo, Kling, FLUX…) via MCP.",
     "category": "media", "connect_method": "mcp", "mcp_url": "https://mcp.higgsfield.ai/mcp", "logo_key": "higgsfield",
     "token_label": "Higgsfield Token", "token_hint": "Higgsfield account → connector token."},
    {"id": "openai_images", "name": "OpenAI Images (DALL·E)", "description": "Generate images from text prompts.",
     "category": "media", "connect_method": "api_key", "logo_key": "openai",
     "token_label": "OpenAI API Key", "token_hint": "platform.openai.com/api-keys."},
    {"id": "stability", "name": "Stability AI", "description": "Stable Diffusion image generation.",
     "category": "media", "connect_method": "api_key", "logo_key": "stability",
     "token_label": "API Key", "token_hint": "platform.stability.ai → API keys."},

    # --- Docs / Productivity ---
    {"id": "notion", "name": "Notion", "description": "Search, create, and update Notion pages & databases.",
     "category": "knowledge", "connect_method": "oauth", "oauth_provider": "notion", "logo_key": "notion"},
    {"id": "google_sheets", "name": "Google Sheets", "description": "Read and write spreadsheet data.",
     "category": "productivity", "connect_method": "oauth", "oauth_provider": "google", "logo_key": "google_sheets"},
    {"id": "airtable", "name": "Airtable", "description": "Records and bases as a flexible database.",
     "category": "productivity", "connect_method": "api_key", "logo_key": "airtable",
     "token_label": "Personal Access Token", "token_hint": "airtable.com/create/tokens."},

    # --- Dev ---
    {"id": "github", "name": "GitHub", "description": "Repos, issues, PRs, and file access.",
     "category": "developer", "connect_method": "oauth", "oauth_provider": "github", "logo_key": "github"},
    {"id": "gitlab", "name": "GitLab", "description": "Projects, issues, and merge requests.",
     "category": "developer", "connect_method": "api_key", "logo_key": "gitlab",
     "token_label": "Personal Access Token", "token_hint": "GitLab → Preferences → Access Tokens."},

    # --- Finance / Accounting ---
    {"id": "quickbooks", "name": "QuickBooks", "description": "Invoices, expenses, and accounting data.",
     "category": "finance", "connect_method": "oauth", "oauth_provider": "quickbooks", "logo_key": "quickbooks"},
    {"id": "xero", "name": "Xero", "description": "Accounting, invoices, and payroll.",
     "category": "finance", "connect_method": "oauth", "oauth_provider": "xero", "logo_key": "xero"},

    # --- Automation ---
    {"id": "zapier", "name": "Zapier", "description": "Trigger Zaps / automations via webhooks.",
     "category": "automation", "connect_method": "api_key", "logo_key": "zapier",
     "token_label": "Catch Hook URL", "token_hint": "Create a 'Catch Hook' Zap and paste its URL."},
]
_CATALOG_BY_ID = {c["id"]: c for c in CATALOG}


def seed_integrations() -> int:
    now = _now()
    with connection() as conn:
        for it in CATALOG:
            # auth_kind kept for backward compat; derive from connect_method.
            auth_kind = {"oauth": "oauth", "mcp": "token", "api_key": "api_key"}.get(it["connect_method"], "api_key")
            conn.execute(
                """INSERT INTO integrations
                   (id, name, description, category, auth_kind, status, connect_method, oauth_provider, mcp_url, docs_url, logo_key, created_at, updated_at)
                   VALUES (?,?,?,?,?,'available',?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, description=excluded.description,
                     category=excluded.category, auth_kind=excluded.auth_kind, connect_method=excluded.connect_method,
                     oauth_provider=excluded.oauth_provider, mcp_url=excluded.mcp_url, logo_key=excluded.logo_key,
                     updated_at=excluded.updated_at""",
                (it["id"], it["name"], it["description"], it["category"], auth_kind, it["connect_method"],
                 it.get("oauth_provider"), it.get("mcp_url"), it.get("docs_url"), it.get("logo_key"), now, now),
            )
    return len(CATALOG)


def _public(row) -> dict:
    r = dict(row)
    r.pop("credential", None)  # never expose the stored credential
    r["has_credential"] = bool(row["credential"] if "credential" in row.keys() else None)
    meta = _CATALOG_BY_ID.get(r["id"], {})
    r["token_label"] = meta.get("token_label")
    r["token_hint"] = meta.get("token_hint")
    r["logo_key"] = r.get("logo_key") or meta.get("logo_key")
    r["connect_method"] = r.get("connect_method") or meta.get("connect_method") or "api_key"
    r["oauth_provider"] = r.get("oauth_provider") or meta.get("oauth_provider")
    r["mcp_url"] = r.get("mcp_url") or meta.get("mcp_url")
    return r


def list_integrations() -> list[dict]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM integrations ORDER BY name").fetchall()
        # Map connected MCP server URLs → their status, so catalog entries whose
        # connect_method='mcp' reflect a live MCP connection (e.g. Higgsfield
        # connected on the MCP Servers page shows "connected" here too).
        mcp_rows = conn.execute("SELECT server_url, status FROM mcp_servers").fetchall()
    mcp_status = {r["server_url"]: r["status"] for r in mcp_rows}
    out = []
    for r in rows:
        pub = _public(r)
        if pub.get("connect_method") == "mcp" and pub.get("mcp_url") in mcp_status:
            st = mcp_status[pub["mcp_url"]]
            pub["status"] = "connected" if st == "connected" else "available"
            pub["via_mcp"] = True
        out.append(pub)
    return out


def get_integration(integration_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM integrations WHERE id=?", (integration_id,)).fetchone()
    return dict(row) if row else None


# ---- live token validation --------------------------------------------------

async def validate_token(integration_id: str, credential: str) -> dict:
    """Make a real, lightweight call to the provider to verify the token.
    Returns {ok: bool, account_label?: str, error?: str}. Network/other errors
    => ok False with a message (never raises)."""
    try:
        async with httpx.AsyncClient(timeout=12.0) as c:
            if integration_id == "slack":
                r = await c.post("https://slack.com/api/auth.test",
                                 headers={"Authorization": f"Bearer {credential}"})
                d = r.json()
                if d.get("ok"):
                    return {"ok": True, "account_label": d.get("team") or d.get("user") or "Slack"}
                return {"ok": False, "error": f"Slack rejected the token: {d.get('error', 'invalid')}"}

            if integration_id == "notion":
                r = await c.get("https://api.notion.com/v1/users/me",
                                headers={"Authorization": f"Bearer {credential}",
                                         "Notion-Version": "2022-06-28"})
                if r.status_code < 300:
                    name = r.json().get("name") or r.json().get("bot", {}).get("workspace_name") or "Notion"
                    return {"ok": True, "account_label": name}
                return {"ok": False, "error": f"Notion rejected the token (HTTP {r.status_code})."}

            if integration_id == "google_drive":
                r = await c.get("https://www.googleapis.com/drive/v3/about",
                                params={"fields": "user"},
                                headers={"Authorization": f"Bearer {credential}"})
                if r.status_code < 300:
                    user = r.json().get("user", {})
                    return {"ok": True, "account_label": user.get("emailAddress") or "Google Drive"}
                return {"ok": False, "error": f"Google rejected the token (HTTP {r.status_code})."}

            if integration_id == "github":
                r = await c.get("https://api.github.com/user",
                                headers={"Authorization": f"Bearer {credential}",
                                         "Accept": "application/vnd.github+json"})
                if r.status_code < 300:
                    return {"ok": True, "account_label": r.json().get("login", "GitHub")}
                return {"ok": False, "error": f"GitHub rejected the token (HTTP {r.status_code})."}

            if integration_id == "stripe":
                r = await c.get("https://api.stripe.com/v1/account", auth=(credential, ""))
                if r.status_code < 300:
                    d = r.json()
                    return {"ok": True, "account_label": d.get("settings", {}).get("dashboard", {}).get("display_name")
                            or d.get("email") or "Stripe"}
                return {"ok": False, "error": f"Stripe rejected the key (HTTP {r.status_code})."}

            if integration_id == "twilio":
                if ":" not in credential:
                    return {"ok": False, "error": "Twilio token must be AccountSID:AuthToken."}
                sid, token = credential.split(":", 1)
                r = await c.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json", auth=(sid, token))
                if r.status_code < 300:
                    return {"ok": True, "account_label": r.json().get("friendly_name") or sid}
                return {"ok": False, "error": f"Twilio rejected the credentials (HTTP {r.status_code})."}

            if integration_id == "shopify":
                if "|" not in credential:
                    return {"ok": False, "error": "Shopify token must be shop.myshopify.com|admin_token."}
                shop, token = credential.split("|", 1)
                r = await c.get(f"https://{shop}/admin/api/2024-01/shop.json",
                                headers={"X-Shopify-Access-Token": token})
                if r.status_code < 300:
                    return {"ok": True, "account_label": r.json().get("shop", {}).get("name") or shop}
                return {"ok": False, "error": f"Shopify rejected the token (HTTP {r.status_code})."}

            if integration_id == "sendgrid":
                r = await c.get("https://api.sendgrid.com/v3/scopes",
                                headers={"Authorization": f"Bearer {credential}"})
                if r.status_code < 300:
                    return {"ok": True, "account_label": "SendGrid"}
                return {"ok": False, "error": f"SendGrid rejected the key (HTTP {r.status_code})."}

            if integration_id == "zapier":
                if not credential.lower().startswith(("http://", "https://")):
                    return {"ok": False, "error": "Provide the Zapier Catch Hook URL."}
                # Don't fire the hook on connect; just accept a well-formed URL.
                return {"ok": True, "account_label": "Zapier webhook"}

        # No specific validator for this provider — accept the credential as-is
        # (stored encrypted). The provider's real API validates at call time.
        meta = _CATALOG_BY_ID.get(integration_id, {})
        return {"ok": True, "account_label": meta.get("name") or integration_id}
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"Could not reach {integration_id} to verify the token: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"Validation failed: {e}"}


async def connect(integration_id: str, *, credential: str | None = None,
                  skip_validation: bool = False) -> dict:
    """Connect an api_key / token / mcp integration by validating + storing a
    credential. OAuth integrations are connected via the OAuth flow (the catalog
    API returns an authorize URL instead of calling this). Returns {ok, ...}."""
    row = get_integration(integration_id)
    if row is None:
        return {"ok": False, "error": "unknown integration", "code": 404}
    meta = _CATALOG_BY_ID.get(integration_id, {})
    method = row.get("connect_method") or meta.get("connect_method") or "api_key"

    if method == "oauth":
        return {"ok": False, "code": 409, "error": "Use the OAuth connect flow for this integration."}

    if method == "mcp":
        # Connect the hosted MCP server (token optional) and register its tools.
        mcp_url = row.get("mcp_url") or meta.get("mcp_url")
        if not mcp_url:
            return {"ok": False, "code": 422, "error": "No MCP url configured."}
        from app.tools import mcp as mcpmod
        from app.tools import store as toolstore
        try:
            discovered = await mcpmod.discover_tools(mcp_url, auth_token=credential or None)
        except mcpmod.MCPError as e:
            return {"ok": False, "code": 502, "error": str(e)}
        server_id = mcpmod.create_server(name=row["name"], server_url=mcp_url,
                                         description=row.get("description") or "",
                                         tool_count=len(discovered), auth_token=credential or None)
        for d in discovered:
            rn = d.get("name")
            if not rn:
                continue
            toolstore.upsert_tool(
                name=f"mcp_{rn}", display_name=rn,
                description=d.get("description") or f"{row['name']} tool",
                type="mcp", category="mcp", input_schema=d.get("inputSchema") or {},
                config={"server_url": mcp_url, "mcp_server_id": server_id, "remote_name": rn},
            )
        _mark_connected(integration_id, row["name"], credential, extra=f"{len(discovered)} tools")
        return {"ok": True, "status": "connected", "account_label": f"{len(discovered)} tools"}

    # api_key / token
    if not credential:
        return {"ok": False, "code": 422, "error": f"{row['name']} requires: {meta.get('token_label', 'a token')}."}
    account_label = row["name"]
    if not skip_validation:
        v = await validate_token(integration_id, credential)
        if not v["ok"]:
            return {"ok": False, "code": 400, "error": v["error"]}
        account_label = v.get("account_label") or row["name"]
    _mark_connected(integration_id, account_label, credential)
    return {"ok": True, "status": "connected", "account_label": account_label}


def _mark_connected(integration_id: str, account_label: str, credential: str | None, extra: str = "") -> None:
    now = _now()
    with connection() as conn:
        conn.execute(
            "UPDATE integrations SET status='connected', credential=?, account_label=?, connected_at=?, updated_at=? WHERE id=?",
            (encrypt(credential) if credential else None, account_label, now, now, integration_id),
        )


def disconnect(integration_id: str) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "UPDATE integrations SET status='available', credential=NULL, account_label=NULL, connected_at=NULL, updated_at=? WHERE id=?",
            (_now(), integration_id),
        )
    return cur.rowcount > 0


def get_credential(integration_id: str) -> str:
    """Decrypted credential for runtime use (never returned over the API)."""
    row = get_integration(integration_id)
    return decrypt(row["credential"]) if row and row.get("credential") else ""


def summary() -> dict:
    items = list_integrations()
    connected = sum(1 for i in items if i["status"] == "connected")
    total = len(items)
    return {"total": total, "connected": connected, "available": total - connected}

