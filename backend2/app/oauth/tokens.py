"""Tool-execution token provider.

The single entry point the tool/execution layer uses to obtain a valid access
token for a given user + provider. Auto-refreshes when expired. Returns None if
the user has no OAuth connection for that provider (the tool then degrades with
a clear "connect <provider> first" message — never a crash, never a fake token).

Tokens obtained here are injected into the provider's API client ONLY — never
returned to the LLM, the frontend, or another user.
"""

from __future__ import annotations

from app.oauth import service


async def token_for(user_id: str, provider_id: str) -> str | None:
    """Valid access token for this user's connection, or None."""
    if not user_id or not provider_id:
        return None
    return await service.get_valid_access_token(user_id, provider_id)
