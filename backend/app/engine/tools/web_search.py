"""web_search built-in tool — Serper-backed.

On any failure returns {"error": ..., "degraded": true} rather than raising, so
the agent can continue in degraded mode (LLM knowledge only). See Error
Handling Plan, Layer 2.
"""

from __future__ import annotations

import httpx

from app.config import settings

SERPER_URL = "https://google.serper.dev/search"


async def web_search(tool_input: dict, user_keys: dict | None = None) -> dict:
    query = (tool_input or {}).get("query", "").strip()
    if not query:
        return {"error": "web_search requires a 'query'", "degraded": True}

    key = (user_keys or {}).get("serper_api_key") or settings.serper_api_key
    if not key:
        return {
            "error": "No Serper API key configured. Add one in Settings → API Keys.",
            "degraded": True,
            "results": [],
        }

    try:
        from app.net_timeouts import client_timeout

        async with httpx.AsyncClient(timeout=client_timeout(15.0)) as client:
            resp = await client.post(
                SERPER_URL,
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "num": 10},
            )
    except httpx.HTTPError as e:
        return {"error": f"web_search transport: {e}", "degraded": True, "results": []}

    if resp.status_code == 429:
        return {"error": "Serper rate limit reached", "degraded": True, "results": []}
    if resp.status_code >= 400:
        return {"error": f"Serper {resp.status_code}", "degraded": True, "results": []}

    data = resp.json()
    results = [
        {"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
        for r in data.get("organic", [])[:10]
    ]
    return {"results": results, "count": len(results)}
