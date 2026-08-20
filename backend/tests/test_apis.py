"""Tests for F38-F41 - external data grounding.

All HTTP is mocked with respx, so this suite verifies the real client code -
request payloads, header names, response parsing, degradation paths - without
spending a single Serper credit or Overpass query.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from app.apis.cache import (
    COLLECTION_COMPETITORS,
    COLLECTION_MARKET_RESEARCH,
    KnowledgeCache,
    cache_key,
)
from app.apis.freshness import (
    STALE_AFTER_DAYS,
    Freshness,
    age_days,
    cutoff_iso,
    is_stale,
    now_iso,
    parse_iso,
)
from app.apis.places import (
    NOMINATIM_ENDPOINT,
    OVERPASS_ENDPOINT,
    PLACES_ENDPOINT,
    GooglePlacesProvider,
    OverpassProvider,
    build_overpass_query,
    discover_competitors,
    osm_tags_for,
    select_provider,
)
from app.apis.serper import (
    SERPER_ENDPOINT,
    MarketIntelligence,
    SearchSnippet,
    SerperClient,
    build_queries,
    research_market,
)
from app.models.intent import Budget, BusinessIntent, Location, Sector


def ice_cream_intent() -> BusinessIntent:
    return BusinessIntent(
        business_type="ice_cream_shop",
        business_type_label="Ice Cream Shop",
        sector=Sector.FOOD_AND_BEVERAGE,
        location=Location(area="Andheri West"),
        budget=Budget(amount=1_500_000, specified=True),
    )


# =============================================================================
# F41 - freshness
# =============================================================================


def test_now_iso_round_trips() -> None:
    assert parse_iso(now_iso()) is not None


def test_age_days_for_fresh_timestamp() -> None:
    assert age_days(now_iso()) == pytest.approx(0.0, abs=0.01)


def test_age_days_for_old_timestamp() -> None:
    old = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    assert age_days(old) == pytest.approx(10.0, abs=0.01)


def test_age_days_returns_none_for_garbage() -> None:
    assert age_days("not a date") is None


def test_naive_timestamp_is_treated_as_utc() -> None:
    naive = datetime.now().replace(tzinfo=None).isoformat()  # noqa: DTZ005
    assert age_days(naive) is not None


def test_fresh_data_is_not_stale() -> None:
    assert is_stale(now_iso()) is False


def test_data_older_than_threshold_is_stale() -> None:
    old = (datetime.now(UTC) - timedelta(days=STALE_AFTER_DAYS + 1)).isoformat()
    assert is_stale(old) is True


def test_unparseable_timestamp_counts_as_stale() -> None:
    """Unknown provenance is not fresh."""
    assert is_stale("") is True
    assert is_stale("yesterday") is True


def test_freshness_live_label() -> None:
    freshness = Freshness.live("google_places")
    assert freshness.cached is False
    assert freshness.stale is False
    assert "google_places" in freshness.label()
    assert "live" in freshness.label()


def test_freshness_cached_label_flags_staleness() -> None:
    old = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    freshness = Freshness.from_cache("serper", old)
    assert freshness.cached is True
    assert freshness.stale is True
    assert "POTENTIALLY STALE" in freshness.label()


def test_freshness_as_dict_shape() -> None:
    payload = Freshness.live("serper").as_dict()
    assert set(payload) == {"source", "retrieved_at", "cached", "stale", "age_days"}


def test_cutoff_iso_is_in_the_past() -> None:
    assert parse_iso(cutoff_iso()) < datetime.now(UTC)


# =============================================================================
# F38 - Google Places
# =============================================================================


def places_payload() -> dict:
    return {
        "places": [
            {
                "id": "ChIJ_natural",
                "displayName": {"text": "Naturals Ice Cream"},
                "formattedAddress": "Andheri West, Mumbai",
                "rating": 4.4,
                "userRatingCount": 1832,
                "priceLevel": "PRICE_LEVEL_MODERATE",
            },
            {
                "id": "ChIJ_baskin",
                "displayName": {"text": "Baskin Robbins"},
                "formattedAddress": "Lokhandwala, Andheri West",
                "rating": 4.1,
                "userRatingCount": 640,
                "priceLevel": "PRICE_LEVEL_EXPENSIVE",
            },
            {"id": "ChIJ_noname", "displayName": {"text": ""}},
        ]
    }


@respx.mock
@pytest.mark.asyncio
async def test_google_places_sends_correct_request(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "google_places_api_key", "test-key")
    monkeypatch.setattr(module.settings, "enable_places_api", True)
    route = respx.post(PLACES_ENDPOINT).mock(
        return_value=httpx.Response(200, json=places_payload())
    )

    provider = GooglePlacesProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 2000, 8)
    await provider.aclose()

    request = route.calls.last.request
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "places.rating" in request.headers["x-goog-fieldmask"]
    body = request.read().decode()
    assert "Ice Cream Shop in Andheri West" in body
    assert '"regionCode":"IN"' in body.replace(" ", "")

    assert trace.api == "google_places"
    assert trace.error is None
    assert trace.result_count == 2  # blank-name entry dropped
    assert [c.name for c in competitors] == ["Naturals Ice Cream", "Baskin Robbins"]


@respx.mock
@pytest.mark.asyncio
async def test_google_places_maps_price_level_enum(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "google_places_api_key", "k")
    monkeypatch.setattr(module.settings, "enable_places_api", True)
    respx.post(PLACES_ENDPOINT).mock(return_value=httpx.Response(200, json=places_payload()))

    provider = GooglePlacesProvider()
    competitors, _ = await provider.search(ice_cream_intent(), 2000, 8)
    await provider.aclose()

    assert competitors[0].price_level == 2  # MODERATE
    assert competitors[1].price_level == 3  # EXPENSIVE
    assert competitors[0].review_count == 1832
    assert all(c.source == "google_places" for c in competitors)


@respx.mock
@pytest.mark.asyncio
async def test_google_places_http_error_returns_empty_with_trace(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "google_places_api_key", "k")
    monkeypatch.setattr(module.settings, "enable_places_api", True)
    respx.post(PLACES_ENDPOINT).mock(return_value=httpx.Response(403, text="billing off"))

    provider = GooglePlacesProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 2000, 8)
    await provider.aclose()

    assert competitors == []
    assert "403" in (trace.error or "")


def test_google_places_unavailable_without_key(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "google_places_api_key", "")
    assert GooglePlacesProvider().available() is False


# =============================================================================
# F38 - OpenStreetMap / Overpass
# =============================================================================


@pytest.mark.parametrize(
    ("business_type", "expected_tag"),
    [
        ("ice_cream_shop", "amenity=ice_cream"),
        ("bakery", "shop=bakery"),
        ("unisex_salon", "shop=hairdresser"),
        ("dental_clinic", "amenity=dentist"),
        ("gym", "leisure=fitness_centre"),
    ],
)
def test_osm_tags_prefer_specific_business_type(business_type: str, expected_tag: str) -> None:
    intent = BusinessIntent(business_type=business_type, sector=Sector.SERVICES)
    assert expected_tag in osm_tags_for(intent)


def test_osm_tags_fall_back_to_sector() -> None:
    intent = BusinessIntent(business_type="something_unusual", sector=Sector.HEALTHCARE)
    tags = osm_tags_for(intent)
    assert "amenity=clinic" in tags


def test_overpass_query_structure() -> None:
    query = build_overpass_query(19.13, 72.83, ("amenity=ice_cream",), 1500, 5)
    assert "[out:json]" in query
    assert 'nwr(around:1500,19.13,72.83)["amenity"~"^(ice_cream)$"]["name"]' in query
    assert query.rstrip().endswith(";")


def test_overpass_query_groups_tags_by_key() -> None:
    """One clause per key, not per tag.

    A live probe showed the per-tag form (12 statements for a six-tag sector)
    drawing 429s and 504s from the public endpoint and taking 20-40s when it did
    answer. Grouped, the same search returns in about a second.
    """
    query = build_overpass_query(
        19.13,
        72.83,
        ("amenity=ice_cream", "amenity=cafe", "amenity=restaurant", "shop=bakery"),
        2000,
        6,
    )
    assert query.count("nwr(around:") == 2  # one for amenity, one for shop
    assert '"amenity"~"^(ice_cream|cafe|restaurant)$"' in query
    assert '"shop"~"^(bakery)$"' in query


def test_overpass_query_uses_nwr_for_all_element_types() -> None:
    query = build_overpass_query(19.13, 72.83, ("shop=bakery",), 1000, 3)
    assert "node(around" not in query
    assert "way(around" not in query
    assert "nwr(around" in query


@respx.mock
@pytest.mark.asyncio
async def test_overpass_geocodes_then_queries(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    geocode = respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.1364", "lon": "72.8296"}])
    )
    overpass = respx.post(OVERPASS_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "node",
                        "id": 111,
                        "tags": {
                            "name": "Apsara Ice Creams",
                            "amenity": "ice_cream",
                            "addr:street": "SV Road",
                            "addr:city": "Mumbai",
                        },
                    },
                    {"type": "way", "id": 222, "tags": {"name": "Gokul Ice Cream"}},
                    {"type": "node", "id": 333, "tags": {"amenity": "ice_cream"}},
                    {"type": "node", "id": 444, "tags": {"name": "Apsara Ice Creams"}},
                ]
            },
        )
    )

    provider = OverpassProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 1500, 8)
    await provider.aclose()

    assert geocode.called
    assert USER_AGENT_PRESENT(geocode.calls.last.request)
    assert overpass.called

    names = [c.name for c in competitors]
    assert names == ["Apsara Ice Creams", "Gokul Ice Cream"]  # unnamed + duplicate dropped
    assert competitors[0].address == "SV Road, Mumbai"
    assert competitors[0].place_id == "node/111"
    assert all(c.source == "openstreetmap" for c in competitors)
    # OSM has no ratings; they must stay None rather than be invented.
    assert all(c.rating is None and c.review_count is None for c in competitors)
    assert trace.error is None


def USER_AGENT_PRESENT(request) -> bool:
    """Nominatim's usage policy requires an identifying User-Agent."""
    return "MABGP" in request.headers.get("user-agent", "")


@respx.mock
@pytest.mark.asyncio
async def test_overpass_geocode_failure_is_reported(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(return_value=httpx.Response(200, json=[]))

    provider = OverpassProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 1500, 8)
    await provider.aclose()

    assert competitors == []
    assert "could not geocode" in (trace.error or "")


@respx.mock
@pytest.mark.asyncio
async def test_overpass_respects_limit(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.1", "lon": "72.8"}])
    )
    respx.post(OVERPASS_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "elements": [
                    {"type": "node", "id": i, "tags": {"name": f"Shop {i}"}} for i in range(20)
                ]
            },
        )
    )

    provider = OverpassProvider()
    competitors, _ = await provider.search(ice_cream_intent(), 1500, 3)
    await provider.aclose()

    assert len(competitors) == 3


@respx.mock
@pytest.mark.asyncio
async def test_overpass_broadens_to_sector_when_specific_tags_find_nothing(
    monkeypatch,
) -> None:
    """Measured on live OSM: Bandra has 30 named restaurants and 30 hairdressers
    within 2 km but zero `amenity=ice_cream`, because Indian ice cream shops are
    not tagged that way. Broadening turns an empty result into a usable one."""
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.06", "lon": "72.83"}])
    )
    responses = [
        httpx.Response(200, json={"elements": []}),  # specific tags: nothing
        httpx.Response(
            200,
            json={"elements": [{"type": "node", "id": 9, "tags": {"name": "Naturals"}}]},
        ),  # broadened to sector
    ]
    route = respx.post(OVERPASS_ENDPOINT).mock(side_effect=responses)

    provider = OverpassProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 2000, 6)
    await provider.aclose()

    assert route.call_count == 2
    assert [c.name for c in competitors] == ["Naturals"]
    assert trace.error is None


@respx.mock
@pytest.mark.asyncio
async def test_overpass_does_not_broaden_when_specific_tags_succeed(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.06", "lon": "72.83"}])
    )
    route = respx.post(OVERPASS_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json={"elements": [{"type": "node", "id": 1, "tags": {"name": "Snowbite"}}]}
        )
    )

    provider = OverpassProvider()
    competitors, _ = await provider.search(ice_cream_intent(), 2000, 6)
    await provider.aclose()

    assert route.call_count == 1
    assert [c.name for c in competitors] == ["Snowbite"]


@respx.mock
@pytest.mark.asyncio
async def test_overpass_rate_limit_is_reported_and_not_retried(monkeypatch) -> None:
    """The public endpoint throttles hard - observed on the third query in a row."""
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.06", "lon": "72.83"}])
    )
    route = respx.post(OVERPASS_ENDPOINT).mock(return_value=httpx.Response(429, text="too many"))

    provider = OverpassProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 2000, 6)
    await provider.aclose()

    assert competitors == []
    assert "429" in (trace.error or "")
    assert route.call_count == 1  # broadening must not hammer a throttled endpoint


@respx.mock
@pytest.mark.asyncio
async def test_overpass_overload_is_reported(monkeypatch) -> None:
    from app.apis import places as module

    monkeypatch.setattr(module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.06", "lon": "72.83"}])
    )
    respx.post(OVERPASS_ENDPOINT).mock(return_value=httpx.Response(504, text="gateway timeout"))

    provider = OverpassProvider()
    competitors, trace = await provider.search(ice_cream_intent(), 2000, 6)
    await provider.aclose()

    assert competitors == []
    assert "504" in (trace.error or "")


# =============================================================================
# F38 - provider selection and degradation
# =============================================================================


class FakeProvider:
    def __init__(self, name: str, is_available: bool) -> None:
        self.name = name
        self._available = is_available

    def available(self) -> bool:
        return self._available

    async def search(self, intent, radius_m, limit):
        from app.models.state import ApiCallTrace

        return [], ApiCallTrace(api=self.name)


def test_places_is_preferred_over_openstreetmap() -> None:
    chosen = select_provider(
        [FakeProvider("google_places", True), FakeProvider("openstreetmap", True)]
    )
    assert chosen.name == "google_places"


def test_openstreetmap_used_when_places_unavailable() -> None:
    chosen = select_provider(
        [FakeProvider("google_places", False), FakeProvider("openstreetmap", True)]
    )
    assert chosen.name == "openstreetmap"


def test_no_provider_when_all_disabled() -> None:
    assert select_provider([FakeProvider("google_places", False), FakeProvider("openstreetmap", False)]) is None


@pytest.mark.asyncio
async def test_discover_competitors_degrades_to_empty() -> None:
    """No provider means the agent falls back to LLM recall - the RQ3 control."""
    competitors, traces, freshness = await discover_competitors(
        ice_cream_intent(), providers=[FakeProvider("google_places", False)]
    )
    assert competitors == []
    assert traces == []
    assert freshness is None


@pytest.mark.asyncio
async def test_discover_competitors_tags_freshness() -> None:
    from app.models.departments import Competitor
    from app.models.state import ApiCallTrace

    class WorkingProvider(FakeProvider):
        async def search(self, intent, radius_m, limit):
            return [Competitor(name="Naturals", source="google_places")], ApiCallTrace(
                api="google_places", result_count=1
            )

    competitors, traces, freshness = await discover_competitors(
        ice_cream_intent(), providers=[WorkingProvider("google_places", True)]
    )
    assert len(competitors) == 1
    assert len(traces) == 1
    assert freshness is not None
    assert freshness.source == "google_places"
    assert freshness.stale is False


# =============================================================================
# F39 - Serper
# =============================================================================


def serper_payload() -> dict:
    return {
        "searchParameters": {"q": "test"},
        "organic": [
            {
                "title": "Ice Cream Market in India Size 2034",
                "snippet": "The ice cream market in India was valued at INR 243.50 Billion in 2025.",
                "link": "https://www.imarcgroup.com/ice-cream-market-india",
                "position": 1,
            },
            {
                "title": "India's Ice Cream Industry",
                "snippet": "estimated at Rs. 30,000 crore (US$ 3.50 billion) in 2023",
                "link": "https://www.ibef.org/research/case-study/scooping-success",
                "position": 2,
            },
        ],
        "credits": 1,
    }


def test_build_queries_is_deterministic() -> None:
    intent = ice_cream_intent()
    assert build_queries(intent) == build_queries(intent)


def test_build_queries_is_capped_and_localized() -> None:
    queries = build_queries(ice_cream_intent())
    assert len(queries) == 3
    assert any("Mumbai" in q for q in queries)
    assert any("Ice Cream Shop" in q for q in queries)


@respx.mock
@pytest.mark.asyncio
async def test_serper_sends_india_scoped_request(monkeypatch) -> None:
    from app.apis import serper as module

    monkeypatch.setattr(module.settings, "serper_api_key", "test-key")
    monkeypatch.setattr(module.settings, "enable_serper_api", True)
    route = respx.post(SERPER_ENDPOINT).mock(
        return_value=httpx.Response(200, json=serper_payload())
    )

    client = SerperClient()
    intelligence, trace = await client.search("ice cream market size India")
    await client.aclose()

    request = route.calls.last.request
    assert request.headers["x-api-key"] == "test-key"
    body = request.read().decode().replace(" ", "")
    assert '"gl":"in"' in body

    assert trace.error is None
    assert trace.result_count == 2
    assert len(intelligence.snippets) == 2
    assert "INR 243.50 Billion" in intelligence.snippets[0].snippet


@respx.mock
@pytest.mark.asyncio
async def test_serper_quota_exhaustion_is_reported(monkeypatch) -> None:
    from app.apis import serper as module

    monkeypatch.setattr(module.settings, "serper_api_key", "k")
    monkeypatch.setattr(module.settings, "enable_serper_api", True)
    respx.post(SERPER_ENDPOINT).mock(return_value=httpx.Response(429, text="quota"))

    client = SerperClient()
    intelligence, trace = await client.search("q")
    await client.aclose()

    assert intelligence.is_empty
    assert "429" in (trace.error or "")


@respx.mock
@pytest.mark.asyncio
async def test_research_market_merges_all_queries(monkeypatch) -> None:
    from app.apis import serper as module

    monkeypatch.setattr(module.settings, "serper_api_key", "k")
    monkeypatch.setattr(module.settings, "enable_serper_api", True)
    route = respx.post(SERPER_ENDPOINT).mock(
        return_value=httpx.Response(200, json=serper_payload())
    )

    intelligence, traces, freshness = await research_market(ice_cream_intent())

    assert route.call_count == 3  # QUERIES_PER_RUN, capped for budget
    assert len(traces) == 3
    assert len(intelligence.snippets) == 6
    assert freshness is not None
    assert "www.imarcgroup.com" in intelligence.source_domains()


@pytest.mark.asyncio
async def test_research_market_disabled_without_key(monkeypatch) -> None:
    from app.apis import serper as module

    monkeypatch.setattr(module.settings, "enable_serper_api", False)
    intelligence, traces, freshness = await research_market(ice_cream_intent())

    assert intelligence.is_empty
    assert traces == []
    assert freshness is None


def test_snippet_domain_extraction() -> None:
    snippet = SearchSnippet(link="https://www.ibef.org/research/case-study/x")
    assert snippet.domain == "www.ibef.org"


def test_prompt_block_cites_sources_and_freshness() -> None:
    intelligence = MarketIntelligence(
        snippets=[
            SearchSnippet(snippet="market valued at INR 243 Billion", link="https://imarcgroup.com/x")
        ],
        answer_boxes=["India ice cream market grew 14%"],
    )
    block = intelligence.as_prompt_block(Freshness.live("serper"))

    assert "imarcgroup.com" in block
    assert "answer box" in block
    assert "serper" in block


def test_prompt_block_is_empty_when_no_findings() -> None:
    assert MarketIntelligence().as_prompt_block() == ""


# =============================================================================
# F40 - ChromaDB cache
# =============================================================================


class FakeCollection:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def upsert(self, ids, documents, metadatas):
        for id_, document, metadata in zip(ids, documents, metadatas, strict=True):
            self.store[id_] = {"document": document, "metadata": metadata}

    def get(self, ids, include=None):
        found = [self.store[i] for i in ids if i in self.store]
        return {
            "ids": [i for i in ids if i in self.store],
            "documents": [f["document"] for f in found],
            "metadatas": [f["metadata"] for f in found],
        }

    def query(self, query_texts, n_results, include=None):
        entries = list(self.store.values())[:n_results]
        return {
            "metadatas": [[e["metadata"] for e in entries]],
            "distances": [[0.11 for _ in entries]],
        }

    def count(self) -> int:
        return len(self.store)


class FakeChromaClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def heartbeat(self) -> int:
        return 1

    def get_or_create_collection(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


def test_cache_key_is_chromadb_safe() -> None:
    key = cache_key("competitors", "ice_cream_shop", "Andheri West, Mumbai, Maharashtra")
    assert key.replace("_", "").replace("-", "").isalnum()
    assert 3 <= len(key) <= 200


def test_cache_key_is_stable_and_case_insensitive() -> None:
    assert cache_key("A", "B") == cache_key("a", "b")


def test_cache_key_handles_empty_parts() -> None:
    assert cache_key("", "  ") == "empty"


def test_cache_round_trip(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())

    stored = cache.put(
        COLLECTION_COMPETITORS,
        "key1",
        {"competitors": [{"name": "Naturals"}]},
        source="google_places",
        searchable_text="ice cream competitors andheri",
        extra_metadata={"city": "Mumbai", "count": 1},
    )
    assert stored is True

    payload, freshness = cache.get(COLLECTION_COMPETITORS, "key1")
    assert payload == {"competitors": [{"name": "Naturals"}]}
    assert freshness is not None
    assert freshness.cached is True
    assert freshness.source == "google_places"
    assert freshness.stale is False


def test_cache_miss_returns_none(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())
    assert cache.get(COLLECTION_COMPETITORS, "absent") == (None, None)


def test_cache_rejects_stale_entry(monkeypatch) -> None:
    """A cache hit must still age out, or grounding would look permanently fresh."""
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())
    old = (datetime.now(UTC) - timedelta(days=STALE_AFTER_DAYS + 5)).isoformat()

    cache.put(
        COLLECTION_MARKET_RESEARCH, "k", {"snippets": []}, source="serper", retrieved_at=old
    )
    payload, freshness = cache.get(COLLECTION_MARKET_RESEARCH, "k")

    assert payload is None
    assert freshness is None


def test_cache_max_age_override(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())
    five_days_old = (datetime.now(UTC) - timedelta(days=5)).isoformat()

    cache.put(
        COLLECTION_MARKET_RESEARCH, "k", {"a": 1}, source="serper", retrieved_at=five_days_old
    )

    assert cache.get(COLLECTION_MARKET_RESEARCH, "k", max_age_days=10)[0] == {"a": 1}
    assert cache.get(COLLECTION_MARKET_RESEARCH, "k", max_age_days=2)[0] is None


def test_cache_semantic_similar(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())
    cache.put(COLLECTION_MARKET_RESEARCH, "k", {"topic": "ice cream"}, source="serper")

    matches = cache.similar(COLLECTION_MARKET_RESEARCH, "frozen dessert market")
    assert matches
    assert matches[0][0] == {"topic": "ice cream"}


def test_cache_disabled_by_flag(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", False)
    cache = KnowledgeCache()

    assert cache.connect() is False
    assert cache.put(COLLECTION_COMPETITORS, "k", {}, source="x") is False
    assert cache.get(COLLECTION_COMPETITORS, "k") == (None, None)
    assert cache.similar(COLLECTION_COMPETITORS, "text") == []
    assert cache.count(COLLECTION_COMPETITORS) == 0


def test_cache_survives_a_broken_backend(monkeypatch) -> None:
    """An unreachable ChromaDB must not fail the run."""
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)

    class BrokenClient:
        def heartbeat(self):
            return 1

        def get_or_create_collection(self, name):
            raise RuntimeError("chroma exploded")

    cache = KnowledgeCache(client=BrokenClient())
    assert cache.put(COLLECTION_COMPETITORS, "k", {}, source="x") is False
    assert cache.get(COLLECTION_COMPETITORS, "k") == (None, None)


def test_cache_health_reports_collections(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", True)
    cache = KnowledgeCache(client=FakeChromaClient())
    cache.put(COLLECTION_COMPETITORS, "k", {"a": 1}, source="x")

    health = cache.health()
    assert health["enabled"] is True
    assert health["collections"][COLLECTION_COMPETITORS] == 1


def test_cache_health_when_disabled(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", False)
    health = KnowledgeCache().health()
    assert health["enabled"] is False
    assert "ENABLE_CHROMA_CACHE" in health["reason"]


# =============================================================================
# Grounding integration - the RQ3 mechanism
# =============================================================================


class StubClient:
    """Minimal LLMClient stand-in that records the prompt it was given."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.last_prompt = ""

    async def complete_json(self, request, schema, repair_attempts: int = 1):
        from app.llm.base import LLMResponse, ProviderName

        self.last_prompt = request.prompt
        return schema.model_validate(self._payload), LLMResponse(
            text="{}", provider=ProviderName.GROQ, model="llama-3.1-8b-instant"
        )


COMPETITIVE_PAYLOAD = {
    "competitors": [
        {"name": "Cold Stone Creamery", "rating": 4.5, "price_level": 3, "note": "recalled"}
    ],
    "market_gaps": ["no sugar-free range"],
    "positioning": "Premium artisanal gelato.",
}

RESEARCH_PAYLOAD = {
    "market_overview": "Mumbai frozen dessert demand is growing among young families.",
    "market_statistics": ["14% CAGR"],
    "industry_growth_rate_pct": 14.0,
}


def grounded_state():
    from app.models.state import new_state

    state = new_state("rq3", "Ice cream shop in Andheri West, Rs 15L budget")
    state["intent"] = ice_cream_intent()
    return state


def disable_cache(monkeypatch) -> None:
    from app.apis import cache as module

    monkeypatch.setattr(module.settings, "enable_chroma_cache", False)
    monkeypatch.setattr(module.knowledge_cache, "_enabled", False, raising=False)
    monkeypatch.setattr(module.knowledge_cache, "_client", None, raising=False)
    monkeypatch.setattr(module.knowledge_cache, "_attempted", True, raising=False)


@respx.mock
@pytest.mark.asyncio
async def test_verified_competitors_replace_llm_recalled_ones(monkeypatch) -> None:
    """RQ3 experimental arm: real places overwrite the model's recollection."""
    from app.agents.strategy import CompetitiveAnalysisAgent
    from app.apis import places as places_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(places_module.settings, "google_places_api_key", "k")
    monkeypatch.setattr(places_module.settings, "enable_places_api", True)
    respx.post(PLACES_ENDPOINT).mock(return_value=httpx.Response(200, json=places_payload()))

    client = StubClient(COMPETITIVE_PAYLOAD)
    update = await CompetitiveAnalysisAgent().run(grounded_state(), client=client)

    names = [c.name for c in update["strategy"].competitors]
    assert names == ["Naturals Ice Cream", "Baskin Robbins"]
    assert "Cold Stone Creamery" not in names  # LLM recall discarded
    assert all(c.source == "google_places" for c in update["strategy"].competitors)
    # Non-competitor fields still come from the model.
    assert update["strategy"].positioning == "Premium artisanal gelato."
    # The verified list is also injected into the prompt.
    assert "Naturals Ice Cream" in client.last_prompt
    assert "VERIFIED EXTERNAL DATA" in client.last_prompt
    # F46: the API call is recorded on the run.
    assert update["api_traces"][0].api == "google_places"


@respx.mock
@pytest.mark.asyncio
async def test_llm_competitors_kept_when_grounding_unavailable(monkeypatch) -> None:
    """RQ3 control arm: no provider, so source stays llm_inferred."""
    from app.agents.strategy import CompetitiveAnalysisAgent
    from app.apis import places as places_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(places_module.settings, "google_places_api_key", "")
    monkeypatch.setattr(places_module.settings, "enable_places_api", False)
    monkeypatch.setattr(places_module.settings, "enable_overpass", False)

    client = StubClient(COMPETITIVE_PAYLOAD)
    update = await CompetitiveAnalysisAgent().run(grounded_state(), client=client)

    competitors = update["strategy"].competitors
    assert [c.name for c in competitors] == ["Cold Stone Creamery"]
    assert all(c.source == "llm_inferred" for c in competitors)
    assert "VERIFIED EXTERNAL DATA" not in client.last_prompt


@respx.mock
@pytest.mark.asyncio
async def test_openstreetmap_grounding_notes_absent_ratings(monkeypatch) -> None:
    from app.agents.strategy import CompetitiveAnalysisAgent
    from app.apis import places as places_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(places_module.settings, "google_places_api_key", "")
    monkeypatch.setattr(places_module.settings, "enable_places_api", False)
    monkeypatch.setattr(places_module.settings, "enable_overpass", True)
    respx.get(NOMINATIM_ENDPOINT).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.13", "lon": "72.83"}])
    )
    respx.post(OVERPASS_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json={"elements": [{"type": "node", "id": 1, "tags": {"name": "Apsara Ice Creams"}}]}
        )
    )

    client = StubClient(COMPETITIVE_PAYLOAD)
    update = await CompetitiveAnalysisAgent().run(grounded_state(), client=client)

    assert [c.name for c in update["strategy"].competitors] == ["Apsara Ice Creams"]
    assert update["strategy"].competitors[0].source == "openstreetmap"
    # The model must not be tempted to fill in the missing ratings.
    assert "do not invent" in client.last_prompt.lower()


@respx.mock
@pytest.mark.asyncio
async def test_market_research_prompt_carries_cited_figures(monkeypatch) -> None:
    from app.agents.strategy import MarketResearchAgent
    from app.apis import serper as serper_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(serper_module.settings, "serper_api_key", "k")
    monkeypatch.setattr(serper_module.settings, "enable_serper_api", True)
    respx.post(SERPER_ENDPOINT).mock(return_value=httpx.Response(200, json=serper_payload()))

    client = StubClient(RESEARCH_PAYLOAD)
    update = await MarketResearchAgent().run(grounded_state(), client=client)

    assert "INR 243.50 Billion" in client.last_prompt
    assert "www.imarcgroup.com" in client.last_prompt
    assert "VERIFIED EXTERNAL DATA" in client.last_prompt
    assert update["strategy"].industry_growth_rate_pct == 14.0
    assert len(update["api_traces"]) == 3  # one per capped query


@pytest.mark.asyncio
async def test_market_research_ungrounded_prompt_has_no_data_block(monkeypatch) -> None:
    from app.agents.strategy import MarketResearchAgent
    from app.apis import serper as serper_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(serper_module.settings, "enable_serper_api", False)

    client = StubClient(RESEARCH_PAYLOAD)
    update = await MarketResearchAgent().run(grounded_state(), client=client)

    assert "VERIFIED EXTERNAL DATA" not in client.last_prompt
    assert "api_traces" not in update


@respx.mock
@pytest.mark.asyncio
async def test_cache_hit_avoids_a_second_api_call(monkeypatch) -> None:
    """This is what keeps the evaluation harness inside the free tier."""
    from app.agents.strategy import CompetitiveAnalysisAgent
    from app.apis import cache as cache_module
    from app.apis import places as places_module

    monkeypatch.setattr(cache_module.settings, "enable_chroma_cache", True)
    shared_cache = KnowledgeCache(client=FakeChromaClient())
    monkeypatch.setattr(cache_module, "knowledge_cache", shared_cache)
    import app.agents.strategy as strategy_module

    monkeypatch.setattr(strategy_module, "knowledge_cache", shared_cache)

    monkeypatch.setattr(places_module.settings, "google_places_api_key", "k")
    monkeypatch.setattr(places_module.settings, "enable_places_api", True)
    route = respx.post(PLACES_ENDPOINT).mock(
        return_value=httpx.Response(200, json=places_payload())
    )

    agent = CompetitiveAnalysisAgent()
    first = await agent.run(grounded_state(), client=StubClient(COMPETITIVE_PAYLOAD))
    second = await agent.run(grounded_state(), client=StubClient(COMPETITIVE_PAYLOAD))

    assert route.call_count == 1  # second run served from cache
    assert [c.name for c in first["strategy"].competitors] == [
        c.name for c in second["strategy"].competitors
    ]
    assert second["api_traces"][0].cached is True


@respx.mock
@pytest.mark.asyncio
async def test_grounding_failure_degrades_instead_of_failing_agent(monkeypatch) -> None:
    from app.agents.strategy import CompetitiveAnalysisAgent
    from app.apis import places as places_module

    disable_cache(monkeypatch)
    monkeypatch.setattr(places_module.settings, "google_places_api_key", "k")
    monkeypatch.setattr(places_module.settings, "enable_places_api", True)
    respx.post(PLACES_ENDPOINT).mock(side_effect=httpx.ConnectError("network down"))

    client = StubClient(COMPETITIVE_PAYLOAD)
    update = await CompetitiveAnalysisAgent().run(grounded_state(), client=client)

    assert update["agent_traces"][0].status == "completed"
    assert [c.name for c in update["strategy"].competitors] == ["Cold Stone Creamery"]
    assert update["api_traces"][0].error is not None


@pytest.mark.asyncio
async def test_grounding_exception_never_propagates(monkeypatch) -> None:
    """A bug in a grounding hook must not take the agent down."""
    from app.agents.strategy import MarketResearchAgent

    async def exploding(self, state):
        raise RuntimeError("grounding bug")

    monkeypatch.setattr(MarketResearchAgent, "gather_grounding", exploding)

    client = StubClient(RESEARCH_PAYLOAD)
    update = await MarketResearchAgent().run(grounded_state(), client=client)

    assert update["agent_traces"][0].status == "completed"
    assert update["strategy"].industry_growth_rate_pct == 14.0


@pytest.mark.asyncio
async def test_ungrounded_agents_have_no_grounding_overhead() -> None:
    """The other 19 agents must not gain an API dependency."""
    from app.agents import all_agents
    from app.agents.base import Agent

    grounded = {"competitive_analysis", "market_research"}
    for agent in all_agents():
        overrides = type(agent).gather_grounding is not Agent.gather_grounding
        assert overrides == (agent.spec.agent_id in grounded), agent.spec.agent_id
