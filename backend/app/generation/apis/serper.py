"""F39 - Market intelligence search via Serper.dev.

Endpoint: POST https://google.serper.dev/search
Free tier: 2,500 searches/month, 1 credit per search. No card required.

Feeds the Market Research agent (F20) real figures instead of recalled ones. On a
live probe the top results for "ice cream market size India" carried
"INR 243.50 Billion in 2025" from IMARC and "Rs. 30,000 crore" from IBEF - both
citable, which is what F54's accuracy scoring needs.

Two deliberate constraints:

* A fixed number of queries per run (`QUERIES_PER_RUN`). The monthly budget has
  to cover 30+ evaluation prompts across several arms; uncapped searching would
  exhaust it mid-experiment and make the run non-reproducible.
* Snippets are passed to the agent verbatim with their source domain attached.
  Paraphrasing them through another LLM call would reintroduce the hallucination
  this feature exists to remove.
"""

from __future__ import annotations

import time

import httpx
import structlog
from pydantic import BaseModel, Field

from app.generation.apis.freshness import Freshness
from app.generation.config import settings
from app.generation.models.intent import BusinessIntent
from app.generation.models.state import ApiCallTrace

log = structlog.get_logger(__name__)

SERPER_ENDPOINT = "https://google.serper.dev/search"

# Keep in step with the free-tier budget: 2,500/month across all evaluation arms.
QUERIES_PER_RUN = 3
RESULTS_PER_QUERY = 5


class SearchSnippet(BaseModel):
    """One organic result, reduced to what an agent prompt needs."""

    title: str = ""
    snippet: str = ""
    link: str = ""
    position: int | None = None

    @property
    def domain(self) -> str:
        without_scheme = self.link.split("://", 1)[-1]
        return without_scheme.split("/", 1)[0]

    def as_prompt_line(self) -> str:
        return f"- {self.snippet.strip()} [source: {self.domain}]"


class MarketIntelligence(BaseModel):
    """Aggregated search findings for one business intent."""

    queries: list[str] = Field(default_factory=list)
    snippets: list[SearchSnippet] = Field(default_factory=list)
    answer_boxes: list[str] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.snippets and not self.answer_boxes

    def as_prompt_block(self, freshness: Freshness | None = None, limit: int = 12) -> str:
        """Render for injection into an agent prompt."""
        if self.is_empty:
            return ""
        lines: list[str] = []
        if freshness is not None:
            lines.append(f"(retrieved from web search - {freshness.label()})")
        for box in self.answer_boxes[:2]:
            lines.append(f"- {box.strip()} [source: search answer box]")
        for snippet in self.snippets[:limit]:
            if snippet.snippet.strip():
                lines.append(snippet.as_prompt_line())
        return "\n".join(lines)

    def source_domains(self) -> list[str]:
        seen: list[str] = []
        for snippet in self.snippets:
            domain = snippet.domain
            if domain and domain not in seen:
                seen.append(domain)
        return seen


def build_queries(intent: BusinessIntent) -> list[str]:
    """The fixed query set. Deterministic so a re-run hits the same cache keys."""
    label = intent.business_type_label or intent.business_type.replace("_", " ")
    city = intent.location.city
    sector = intent.sector.value.replace("_", " ")
    return [
        f"{label} market size India {city} industry statistics",
        f"{label} business {city} startup cost profit margin",
        f"{sector} industry growth rate India trends MSME",
    ][:QUERIES_PER_RUN]


class SerperClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        from app.net_timeouts import client_timeout

        self._client = client or httpx.AsyncClient(timeout=client_timeout(25.0))
        self._owns_client = client is None

    def available(self) -> bool:
        return settings.serper_available

    async def search(self, query: str) -> tuple[MarketIntelligence, ApiCallTrace]:
        started = time.perf_counter()
        empty = MarketIntelligence(queries=[query])

        try:
            response = await self._client.post(
                SERPER_ENDPOINT,
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "gl": "in", "hl": "en", "num": RESULTS_PER_QUERY},
            )
        except httpx.HTTPError as exc:
            return empty, self._trace(query, started, error=f"transport error: {exc}")

        if response.status_code == 429:
            return empty, self._trace(query, started, error="429 free-tier quota exhausted")
        if response.status_code >= 400:
            return empty, self._trace(
                query, started, error=f"HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json() or {}
        snippets = [
            SearchSnippet(
                title=item.get("title") or "",
                snippet=item.get("snippet") or "",
                link=item.get("link") or "",
                position=item.get("position"),
            )
            for item in (data.get("organic") or [])
        ]
        answer_boxes: list[str] = []
        box = data.get("answerBox") or {}
        for key in ("answer", "snippet"):
            if box.get(key):
                answer_boxes.append(str(box[key]))
                break

        intelligence = MarketIntelligence(
            queries=[query], snippets=snippets, answer_boxes=answer_boxes
        )
        return intelligence, self._trace(query, started, count=len(snippets))

    def _trace(
        self, query: str, started: float, count: int = 0, error: str | None = None
    ) -> ApiCallTrace:
        return ApiCallTrace(
            api="serper",
            endpoint=SERPER_ENDPOINT,
            query=query,
            result_count=count,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


async def research_market(
    intent: BusinessIntent,
    *,
    client: SerperClient | None = None,
) -> tuple[MarketIntelligence, list[ApiCallTrace], Freshness | None]:
    """Run the fixed query set and merge the findings (F39).

    Returns (intelligence, api_traces, freshness). Empty intelligence means the
    agent falls back to LLM-only recall - the RQ3 control condition.
    """
    active = client or SerperClient()
    if not active.available():
        log.info("serper.disabled", reason="SERPER_API_KEY not configured")
        return MarketIntelligence(), [], None

    merged = MarketIntelligence()
    traces: list[ApiCallTrace] = []

    for query in build_queries(intent):
        intelligence, trace = await active.search(query)
        traces.append(trace)
        if trace.error:
            log.warning("serper.query_failed", query=query, error=trace.error[:150])
            continue
        merged.queries.append(query)
        merged.snippets.extend(intelligence.snippets)
        merged.answer_boxes.extend(intelligence.answer_boxes)

    if merged.is_empty:
        return merged, traces, None

    log.info(
        "serper.researched",
        queries=len(merged.queries),
        snippets=len(merged.snippets),
        domains=merged.source_domains()[:5],
    )
    return merged, traces, Freshness.live("serper")
