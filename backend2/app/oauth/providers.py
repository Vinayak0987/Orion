"""OAuth provider registry — one entry per provider, driven by env config.

A `Provider` describes everything the shared OAuth service needs: endpoints,
scopes, PKCE capability, how to read the token response, and how to fetch the
account identity. Client id/secret come from settings (env) — NEVER hardcoded.
A provider with no client id is `configured=False` and the UI shows it as
"needs setup" rather than offering Connect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.config import settings


@dataclass
class Provider:
    id: str
    name: str
    authorize_url: str
    token_url: str
    scopes: list[str]
    client_id: str
    client_secret: str
    pkce: bool = False                      # S256 PKCE support
    uses_basic_auth: bool = False           # token exchange via HTTP Basic (Notion)
    extra_authorize_params: dict = field(default_factory=dict)
    revoke_url: str | None = None
    userinfo_url: str | None = None
    # account_from(token_response, userinfo) -> (account_id, account_label)
    account_from: Callable[[dict, dict], tuple[str, str]] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret) or (
            self.id == "notion" and bool(self.client_id and self.client_secret)
        )

    def redirect_uri(self) -> str:
        return f"{settings.oauth_redirect_base.rstrip('/')}/oauth/{self.id}/callback"


def _google_account(tok, info):
    return (info.get("email") or info.get("sub") or "", info.get("email") or "Google")


def _ms_account(tok, info):
    return (info.get("id") or info.get("userPrincipalName") or "",
            info.get("userPrincipalName") or info.get("displayName") or "Microsoft")


def _slack_account(tok, info):
    team = (tok.get("team") or {}).get("name") or tok.get("team_name")
    authed = (tok.get("authed_user") or {}).get("id")
    return (authed or team or "", team or "Slack")


def _github_account(tok, info):
    return (str(info.get("id") or ""), info.get("login") or "GitHub")


def _notion_account(tok, info):
    return (tok.get("workspace_id") or tok.get("bot_id") or "",
            tok.get("workspace_name") or "Notion")


def _build_registry() -> dict[str, Provider]:
    tenant = settings.oauth_microsoft_tenant or "common"
    return {
        "google": Provider(
            id="google", name="Google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["openid", "email",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/gmail.send"],
            client_id=settings.oauth_google_client_id,
            client_secret=settings.oauth_google_client_secret,
            pkce=True,
            extra_authorize_params={"access_type": "offline", "prompt": "consent"},
            revoke_url="https://oauth2.googleapis.com/revoke",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            account_from=_google_account,
        ),
        "microsoft": Provider(
            id="microsoft", name="Microsoft",
            authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            scopes=["offline_access", "openid", "email", "User.Read", "Files.ReadWrite"],
            client_id=settings.oauth_microsoft_client_id,
            client_secret=settings.oauth_microsoft_client_secret,
            pkce=True,
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            account_from=_ms_account,
        ),
        "slack": Provider(
            id="slack", name="Slack",
            authorize_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            scopes=["chat:write", "channels:read", "files:read"],
            client_id=settings.oauth_slack_client_id,
            client_secret=settings.oauth_slack_client_secret,
            pkce=False,
            revoke_url="https://slack.com/api/auth.revoke",
            account_from=_slack_account,
        ),
        "github": Provider(
            id="github", name="GitHub",
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["read:user", "repo"],
            client_id=settings.oauth_github_client_id,
            client_secret=settings.oauth_github_client_secret,
            pkce=True,
            userinfo_url="https://api.github.com/user",
            account_from=_github_account,
        ),
        "notion": Provider(
            id="notion", name="Notion",
            authorize_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            scopes=[],
            client_id=settings.oauth_notion_client_id,
            client_secret=settings.oauth_notion_client_secret,
            pkce=False, uses_basic_auth=True,
            extra_authorize_params={"owner": "user"},
            account_from=_notion_account,
        ),
    }


# Rebuilt lazily so tests can monkeypatch settings before first access.
_REGISTRY: dict[str, Provider] | None = None


def registry() -> dict[str, Provider]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def reset_registry() -> None:
    """For tests — forces a rebuild from current settings."""
    global _REGISTRY
    _REGISTRY = None


def get_provider(provider_id: str) -> Provider | None:
    return registry().get(provider_id)
