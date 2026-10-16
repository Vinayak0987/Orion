"""F38 - Competitor discovery from real-world place data.

This module is the mechanism RQ3 is tested with. The Competitive Analysis agent
(F19) either receives verified nearby businesses from here, or falls back to
LLM-recalled names. `Competitor.source` records which, so the two arms of the
experiment are distinguishable in the stored output:

    google_places   verified, with rating and review count
    openstreetmap   verified existence and location, no ratings
    llm_inferred    recalled by the model, unverified

Two providers implement one interface so the project is not blocked on billing:

    GooglePlacesProvider   Places API (New). $200/month free credit, but Google
                           requires a billing account even to consume it.
    OverpassProvider       OpenStreetMap via Overpass + Nominatim. No key, no
                           card, no quota. Sparser coverage of Indian small
                           businesses and no ratings at all.

Overpass is the default so the pipeline is grounded out of the box. Adding
GOOGLE_PLACES_API_KEY promotes Places automatically with no code change - which
is also how the RQ3 ablation is run.
"""

from __future__ import annotations

import re
import time
from typing import Protocol, runtime_checkable

import httpx
import structlog

from app.generation.apis.freshness import Freshness
from app.generation.config import settings
from app.generation.models.departments import Competitor
from app.generation.models.intent import BusinessIntent, Location, Sector
from app.generation.models.state import ApiCallTrace

log = structlog.get_logger(__name__)

PLACES_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"

# Nominatim's usage policy requires an identifying User-Agent and <=1 req/sec.
USER_AGENT = "MABGP-Research/0.2 (final-year academic project; contact via repo)"

DEFAULT_RADIUS_M = 2000
# Overpass server-side timeout, and the client bound around it. Kept tight: the
# whole pipeline targets 60-90s, so a slow public mirror must fail fast and let
# the agent fall back to LLM recall rather than stall the run.
OVERPASS_TIMEOUT_S = 20
OVERPASS_CLIENT_TIMEOUT_S = 25.0
DEFAULT_LIMIT = 8

# Sector -> OpenStreetMap tag filters. Overpass has no free-text search, so the
# business type must be mapped onto tags explicitly.
OSM_TAGS_BY_SECTOR: dict[Sector, tuple[str, ...]] = {
    Sector.FOOD_AND_BEVERAGE: (
        "amenity=ice_cream",
        "amenity=cafe",
        "amenity=restaurant",
        "amenity=fast_food",
        "shop=bakery",
        "shop=confectionery",
    ),
    Sector.RETAIL: (
        "shop=convenience",
        "shop=supermarket",
        "shop=clothes",
        "shop=general",
        "shop=variety_store",
    ),
    Sector.SERVICES: (
        "shop=hairdresser",
        "shop=beauty",
        "leisure=fitness_centre",
        "shop=laundry",
        "shop=dry_cleaning",
    ),
    Sector.HEALTHCARE: (
        "amenity=clinic",
        "amenity=doctors",
        "amenity=pharmacy",
        "amenity=dentist",
        "amenity=hospital",
    ),
    Sector.EDUCATION: (
        "amenity=school",
        "amenity=college",
        "amenity=language_school",
        "office=educational_institution",
    ),
    Sector.TECHNOLOGY: ("office=it", "office=company"),
    Sector.MANUFACTURING: ("man_made=works", "industrial=factory"),
    Sector.CREATIVE: ("shop=photo", "office=advertising_agency", "craft=photographer"),
    Sector.UNSPECIFIED: ("shop=convenience", "amenity=cafe"),
}

# More specific business types override the sector default.
#
# ORDER IS SIGNIFICANT: the first keyword found in the business type wins, so
# specific terms must precede the generic terms they contain or overlap with.
# "dental_clinic" has to reach "dental" (amenity=dentist) before "clinic"
# (amenity=clinic), and sorting by keyword length cannot decide that because both
# are six characters.
OSM_TAGS_BY_KEYWORD: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ice cream", ("amenity=ice_cream", "shop=ice_cream")),
    ("gelato", ("amenity=ice_cream", "shop=ice_cream")),
    ("dental", ("amenity=dentist",)),
    ("dentist", ("amenity=dentist",)),
    ("pharmacy", ("amenity=pharmacy",)),
    ("chemist", ("amenity=pharmacy",)),
    ("coaching", ("amenity=school", "office=educational_institution")),
    ("tuition", ("amenity=school", "office=educational_institution")),
    ("clinic", ("amenity=clinic", "amenity=doctors")),
    ("bakery", ("shop=bakery", "shop=pastry")),
    ("salon", ("shop=hairdresser", "shop=beauty")),
    ("parlour", ("shop=beauty", "shop=hairdresser")),
    ("boutique", ("shop=clothes",)),
    ("restaurant", ("amenity=restaurant",)),
    ("cafe", ("amenity=cafe",)),
    ("coffee", ("amenity=cafe",)),
    ("grocery", ("shop=convenience", "shop=supermarket")),
    ("kirana", ("shop=convenience",)),
    ("supermarket", ("shop=supermarket",)),
    ("gym", ("leisure=fitness_centre",)),
    ("fitness", ("leisure=fitness_centre",)),
    ("laundry", ("shop=laundry", "shop=dry_cleaning")),
)


@runtime_checkable
class PlacesProvider(Protocol):
    """One source of verified nearby businesses."""

    name: str

    def available(self) -> bool: ...

    async def search(
        self, intent: BusinessIntent, radius_m: int, limit: int
    ) -> tuple[list[Competitor], ApiCallTrace]: ...


def _search_query(intent: BusinessIntent) -> str:
    label = intent.business_type_label or intent.business_type.replace("_", " ")
    return f"{label} in {intent.location.query_string}".strip()


# =============================================================================
# Google Places (New)
# =============================================================================

_PLACES_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
    )
)

# Places API returns priceLevel as an enum string, not the 0-4 integer the
# Competitor schema stores.
_PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


class GooglePlacesProvider:
    name = "google_places"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(20.0))
        self._owns_client = client is None

    def available(self) -> bool:
        return settings.places_available

    async def search(
        self, intent: BusinessIntent, radius_m: int, limit: int
    ) -> tuple[list[Competitor], ApiCallTrace]:
        query = _search_query(intent)
        started = time.perf_counter()

        try:
            response = await self._client.post(
                PLACES_ENDPOINT,
                headers={
                    "X-Goog-Api-Key": settings.google_places_api_key,
                    "X-Goog-FieldMask": _PLACES_FIELD_MASK,
                    "Content-Type": "application/json",
                },
                json={
                    "textQuery": query,
                    "maxResultCount": limit,
                    "languageCode": "en",
                    "regionCode": "IN",
                },
            )
        except httpx.HTTPError as exc:
            return [], self._trace(query, started, error=f"transport error: {exc}")

        if response.status_code >= 400:
            return [], self._trace(
                query, started, error=f"HTTP {response.status_code}: {response.text[:200]}"
            )

        places = (response.json() or {}).get("places") or []
        competitors = [c for c in (self._to_competitor(p) for p in places) if c is not None]
        return competitors, self._trace(query, started, count=len(competitors))

    def _to_competitor(self, place: dict) -> Competitor | None:
        name = ((place.get("displayName") or {}).get("text") or "").strip()
        if not name:
            return None
        return Competitor(
            name=name,
            address=(place.get("formattedAddress") or "")[:250],
            rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
            price_level=_PRICE_LEVEL_MAP.get(place.get("priceLevel") or ""),
            place_id=place.get("id") or "",
            source=self.name,
        )

    def _trace(
        self, query: str, started: float, count: int = 0, error: str | None = None
    ) -> ApiCallTrace:
        return ApiCallTrace(
            api=self.name,
            endpoint=PLACES_ENDPOINT,
            query=query,
            result_count=count,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


# =============================================================================
# OpenStreetMap (Overpass + Nominatim) - no key, no card
# =============================================================================


def osm_tags_for(intent: BusinessIntent) -> tuple[str, ...]:
    """Resolve OSM tag filters, preferring the most specific business-type match.

    Relies on the declaration order of OSM_TAGS_BY_KEYWORD (most specific first).
    An earlier version iterated a dict and let "clinic" win over "dental", so an
    Overpass query for a dental practice searched for general clinics.
    """
    haystack = f"{intent.business_type} {intent.business_type_label}".lower().replace("_", " ")
    for keyword, tags in OSM_TAGS_BY_KEYWORD:
        if keyword in haystack:
            return tags
    return OSM_TAGS_BY_SECTOR.get(intent.sector, OSM_TAGS_BY_SECTOR[Sector.UNSPECIFIED])


def build_overpass_query(
    latitude: float, longitude: float, tags: tuple[str, ...], radius_m: int, limit: int
) -> str:
    """Overpass QL for named businesses of the given tags within a radius.

    Tags sharing a key are collapsed into one regex clause, and `nwr` covers
    nodes, ways and relations in a single statement. An earlier version emitted a
    separate node and way clause per tag - 12 statements for a six-tag sector -
    which the public endpoint answered with 429s and 504s or took 20-40s to
    serve. Grouped, the same search returns in about a second.
    """
    by_key: dict[str, list[str]] = {}
    for tag in tags:
        key, _, value = tag.partition("=")
        by_key.setdefault(key, []).append(value)

    clauses = []
    for key, values in by_key.items():
        pattern = "|".join(re.escape(v) for v in values)
        clauses.append(
            f'nwr(around:{radius_m},{latitude},{longitude})'
            f'["{key}"~"^({pattern})$"]["name"];'
        )

    body = "\n  ".join(clauses)
    return f"[out:json][timeout:{OVERPASS_TIMEOUT_S}];\n(\n  {body}\n);\nout center {limit * 3};"


class OverpassProvider:
    name = "openstreetmap"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(OVERPASS_CLIENT_TIMEOUT_S),
            headers={"User-Agent": USER_AGENT},
        )
        self._owns_client = client is None

    def available(self) -> bool:
        return settings.enable_overpass

    async def geocode(self, location: Location) -> tuple[float, float] | None:
        """Resolve a locality to coordinates via Nominatim."""
        try:
            response = await self._client.get(
                NOMINATIM_ENDPOINT,
                params={
                    "q": location.query_string,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "in",
                },
                headers={"User-Agent": USER_AGENT},
            )
        except httpx.HTTPError as exc:
            log.warning("overpass.geocode_failed", error=str(exc)[:200])
            return None

        if response.status_code >= 400:
            log.warning("overpass.geocode_http", status=response.status_code)
            return None

        results = response.json() or []
        if not results:
            return None
        try:
            return float(results[0]["lat"]), float(results[0]["lon"])
        except (KeyError, TypeError, ValueError):
            return None

    async def search(
        self, intent: BusinessIntent, radius_m: int, limit: int
    ) -> tuple[list[Competitor], ApiCallTrace]:
        query = _search_query(intent)
        started = time.perf_counter()

        coordinates = await self.geocode(intent.location)
        if coordinates is None:
            return [], self._trace(
                query, started, error=f"could not geocode '{intent.location.query_string}'"
            )

        latitude, longitude = coordinates

        # Try the specific tags, then broaden once to the sector.
        #
        # Indian OSM tagging is uneven by category. A live Bandra probe found 30
        # named `amenity=restaurant` and 30 `shop=hairdresser` within 2 km, but
        # zero `amenity=ice_cream` or `shop=ice_cream` anywhere nearby - ice cream
        # shops simply are not tagged that way here. Broadening to the sector
        # turns a zero-competitor result into a usable one, at the cost of listing
        # adjacent business types.
        attempts: list[tuple[str, ...]] = [osm_tags_for(intent)]
        sector_tags = OSM_TAGS_BY_SECTOR.get(intent.sector)
        if sector_tags and sector_tags != attempts[0]:
            attempts.append(tuple(dict.fromkeys(attempts[0] + sector_tags)))

        last_error: str | None = None
        for tags in attempts:
            elements, error = await self._run_query(
                latitude, longitude, tags, radius_m, limit
            )
            if error is not None:
                last_error = error
                break  # a rate limit or outage will not improve on retry
            competitors = self._to_competitors(elements, limit)
            if competitors:
                return competitors, self._trace(query, started, count=len(competitors))

        return [], self._trace(query, started, error=last_error)

    async def _run_query(
        self,
        latitude: float,
        longitude: float,
        tags: tuple[str, ...],
        radius_m: int,
        limit: int,
    ) -> tuple[list[dict], str | None]:
        overpass_ql = build_overpass_query(latitude, longitude, tags, radius_m, limit)
        try:
            response = await self._client.post(
                OVERPASS_ENDPOINT,
                content=overpass_ql.encode("utf-8"),
                headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT},
            )
        except httpx.HTTPError as exc:
            return [], f"transport error: {type(exc).__name__}"

        if response.status_code == 429:
            # The public endpoint throttles aggressively; this is expected, not a bug.
            return [], "429 Overpass rate limit - public endpoint throttled"
        if response.status_code in (503, 504):
            return [], f"{response.status_code} Overpass overloaded"
        if response.status_code >= 400:
            return [], f"HTTP {response.status_code}: {response.text[:150]}"

        try:
            elements = (response.json() or {}).get("elements") or []
        except ValueError:
            return [], "malformed Overpass response"
        return elements, None

    def _to_competitors(self, elements: list[dict], limit: int) -> list[Competitor]:
        seen: set[str] = set()
        competitors: list[Competitor] = []
        for element in elements:
            tags = element.get("tags") or {}
            name = (tags.get("name") or "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            competitors.append(
                Competitor(
                    name=name,
                    address=_osm_address(tags),
                    # OSM carries no ratings or review counts. Left as None rather
                    # than invented: a fabricated rating would corrupt F19's price
                    # positioning and feed a made-up number into F54's pricing.
                    rating=None,
                    review_count=None,
                    price_level=None,
                    place_id=f"{element.get('type', 'node')}/{element.get('id', '')}",
                    source=self.name,
                )
            )
            if len(competitors) >= limit:
                break
        return competitors

    def _trace(
        self, query: str, started: float, count: int = 0, error: str | None = None
    ) -> ApiCallTrace:
        return ApiCallTrace(
            api=self.name,
            endpoint=OVERPASS_ENDPOINT,
            query=query,
            result_count=count,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _osm_address(tags: dict) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
    ]
    address = ", ".join(p for p in parts if p)
    return address[:250]


# =============================================================================
# Selection
# =============================================================================


def select_provider(
    providers: list[PlacesProvider] | None = None,
) -> PlacesProvider | None:
    """Highest-fidelity available provider, or None if grounding is off.

    Order is deliberate: Places carries ratings and review counts that OSM
    cannot, and F19's price positioning plus F55's coverage ground truth are both
    stronger with them.
    """
    candidates = providers if providers is not None else [
        GooglePlacesProvider(),
        OverpassProvider(),
    ]
    for provider in candidates:
        if provider.available():
            return provider
    return None


async def discover_competitors(
    intent: BusinessIntent,
    *,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = DEFAULT_LIMIT,
    providers: list[PlacesProvider] | None = None,
) -> tuple[list[Competitor], list[ApiCallTrace], Freshness | None]:
    """Find real nearby competitors (F38).

    Returns (competitors, api_traces, freshness). An empty competitor list means
    the agent should fall back to LLM-only recall - the RQ3 control condition.
    """
    provider = select_provider(providers)
    if provider is None:
        log.info("places.disabled", reason="no provider available")
        return [], [], None

    competitors, trace = await provider.search(intent, radius_m, limit)

    if trace.error:
        log.warning("places.failed", provider=provider.name, error=trace.error[:200])
        return [], [trace], None

    log.info(
        "places.discovered",
        provider=provider.name,
        count=len(competitors),
        latency_ms=trace.latency_ms,
        query=trace.query,
    )
    return competitors, [trace], Freshness.live(provider.name)
