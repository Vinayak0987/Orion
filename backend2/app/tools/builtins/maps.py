"""Google Maps / Places tools — use the Google Maps Platform API KEY.

IMPORTANT: Google Maps/Places is NOT an OAuth service — it is billed via an API
key (Google Cloud → Credentials → API Key, with the Places/Geocoding APIs
enabled). So these tools read the `google_places_api_key` from Settings, NOT the
Google OAuth connection. They degrade honestly when the key isn't set.

Tools:
  • maps_place_search — text search for places (restaurants, shops, landmarks…)
  • maps_geocode      — turn an address into coordinates (and vice-versa)
"""

from __future__ import annotations

import httpx

from app.tools.base import ToolContext, err, need, ok, tool

_PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def _key(ctx: ToolContext) -> str | None:
    # Prefer the per-mission user key, else the settings store.
    if ctx and ctx.user_keys and ctx.user_keys.get("google_places_api_key"):
        return ctx.user_keys["google_places_api_key"]
    try:
        from app.settings.store import decrypted_keys
        uid = (ctx.user_id if ctx else None) or "default-user"
        k = decrypted_keys(uid).get("google_places_api_key")
        if not k:
            # single-tenant fallback: any user's key
            from app.db.sqlite import connection
            with connection() as c:
                rows = c.execute("SELECT user_id FROM user_settings").fetchall()
            for r in rows:
                kk = decrypted_keys(r["user_id"]).get("google_places_api_key")
                if kk:
                    return kk
        return k
    except Exception:  # noqa: BLE001
        return None


@tool(
    "maps_place_search",
    display_name="Google Maps: Place Search",
    description="Search Google Maps/Places for places matching a text query (e.g. "
    "'coffee shops in Mumbai'). Returns names, addresses, ratings, coordinates. "
    "Input: {query: str, region?: str}.",
    category="web",
    input_schema={"query": {"type": "string", "required": True}, "region": {"type": "string"}},
    requires_key="google_places",
)
async def maps_place_search(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "query")):
        return err(m, results=[])
    key = _key(ctx)
    if not key:
        return err("Google Places API key not set. Add a Maps/Places API key in "
                   "Settings → API Keys (Google Places). Note: Maps uses an API key, not OAuth.",
                   needs_key="google_places", degraded=True, results=[])
    params = {"query": ti["query"].strip(), "key": key}
    if ti.get("region"):
        params["region"] = ti["region"]
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(_PLACES_URL, params=params)
        data = r.json()
        st = data.get("status")
        if st not in ("OK", "ZERO_RESULTS"):
            return err(f"Places API error: {st} — {data.get('error_message','')}", degraded=True, results=[])
        results = [{
            "name": p.get("name"), "address": p.get("formatted_address"),
            "rating": p.get("rating"), "user_ratings": p.get("user_ratings_total"),
            "location": (p.get("geometry") or {}).get("location"),
            "types": p.get("types", [])[:3],
        } for p in (data.get("results") or [])[:8]]
        return ok(results=results, count=len(results))
    except Exception as e:  # noqa: BLE001
        return err(f"maps_place_search failed: {e}", degraded=True, results=[])


@tool(
    "maps_geocode",
    display_name="Google Maps: Geocode",
    description="Convert an address into latitude/longitude (or reverse: coords → address) via "
    "Google Geocoding. Input: {address?: str, latlng?: str}.",
    category="web",
    input_schema={"address": {"type": "string"}, "latlng": {"type": "string"}},
    requires_key="google_places",
)
async def maps_geocode(ti: dict, ctx: ToolContext) -> dict:
    key = _key(ctx)
    if not key:
        return err("Google Places/Maps API key not set (Settings → API Keys → Google Places).",
                   needs_key="google_places", degraded=True)
    if not ti.get("address") and not ti.get("latlng"):
        return err("Provide 'address' or 'latlng'.")
    params = {"key": key}
    if ti.get("address"):
        params["address"] = ti["address"]
    if ti.get("latlng"):
        params["latlng"] = ti["latlng"]
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(_GEOCODE_URL, params=params)
        data = r.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            return err(f"Geocoding error: {data.get('status')} — {data.get('error_message','')}", degraded=True)
        out = [{"formatted_address": g.get("formatted_address"),
                "location": (g.get("geometry") or {}).get("location")}
               for g in (data.get("results") or [])[:5]]
        return ok(results=out, count=len(out))
    except Exception as e:  # noqa: BLE001
        return err(f"maps_geocode failed: {e}", degraded=True)
