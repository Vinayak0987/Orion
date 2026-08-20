"""F53 - single-LLM baseline.

The control group for RQ1. One prompt, one LLM call, asked to produce the same
business plan the 21-agent pipeline produces, and coerced into the identical
`SharedBusinessState` shape so every metric scores both arms with the same code.

Fairness is the whole point of this module, so three choices are deliberate:

* The baseline gets the STRONGER model (`GEMINI_BASELINE_MODEL`, currently
  gemini-3.6-flash), not the cheap one the pipeline uses for intent extraction.
  Beating a deliberately weakened opponent would prove nothing.
* It gets a large token budget and an explicit list of every field the rubric
  checks. A baseline that scores badly because it was never told what to produce
  would be measuring prompt design, not architecture.
* It reuses the same deterministic intent classifier, so both arms agree on
  budget, location and sector. Otherwise F54's MAPE would partly reflect a
  different reading of the prompt rather than different financial reasoning.

What the baseline does NOT get is the multi-agent machinery: no staged
dependencies, no shared state, no per-department specialisation, and no external
grounding. That difference is the independent variable.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import structlog
from pydantic import model_validator

from app.agents.base import AgentOutput
from app.config import settings
from app.intent import classify_intent
from app.llm.base import (
    AllProvidersFailed,
    FreeTierTracker,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelTier,
    ProviderName,
    ProviderUnavailable,
)
from app.llm.gemini_provider import GeminiProvider
from app.llm.chain import JSONParseError, LLMClient, llm_client
from app.models.departments import (
    BrandingOutput,
    FinanceOutput,
    MarketingOutput,
    OperationsOutput,
    StrategyOutput,
)
from app.models.state import (
    AgentTrace,
    Department,
    RunStatus,
    SharedBusinessState,
    new_state,
)
from app.orchestrator.completeness import score_completeness

log = structlog.get_logger(__name__)

BASELINE_MAX_TOKENS = 8000
BASELINE_AGENT_ID = "single_llm_baseline"
# Below this many populated fields the response is a failure, not a plan.
MIN_FILLED_FIELDS = 8

SYSTEM_PROMPT = (
    "You are a complete business consulting firm. You produce full, structured "
    "business plans for Indian entrepreneurs in a single response, covering "
    "strategy, finance, branding, marketing and operations. You return only JSON."
)


class BaselineOutput(AgentOutput):
    """Everything the rubric checks, in one flat response.

    Inherits the same lenient coercion the agents use (nested lists, nulls,
    "Rs 4,50,000") so the baseline is not penalised for shape errors the
    multi-agent arm is forgiven for.
    """

    @model_validator(mode="before")
    @classmethod
    def _flatten_department_wrappers(cls, data: object) -> object:
        """Accept output nested under department headings.

        Observed on a real run: the model mirrored the prompt's section headers
        and returned `{"STRATEGY": {...}, "FINANCE": {...}, ...}`. Every field
        was then missing, and because all fields here are optional the result
        validated as an empty plan and was reported as a successful baseline
        scoring 0% - which would have handed RQ1 a false landslide.

        Merging one level of nesting keeps a well-formed answer that happened to
        be wrapped, and the emptiness guard below catches anything still blank.
        """
        if not isinstance(data, dict):
            return data

        known = set(cls.model_fields)
        if known & data.keys():
            return data  # already flat

        flattened: dict = {}
        for value in data.values():
            if isinstance(value, dict):
                flattened.update(value)
        return flattened or data

    # Strategy
    executive_summary: str = ""
    vision: str = ""
    mission: str = ""
    business_model_type: str = ""
    value_proposition: str = ""
    tam_inr: int | None = None
    sam_inr: int | None = None
    som_inr: int | None = None
    market_overview: str = ""
    market_statistics: list[str] = []
    industry_growth_rate_pct: float | None = None
    competitors: list[dict] = []
    market_gaps: list[str] = []
    positioning: str = ""
    location_score: float | None = None
    location_rationale: str = ""
    risks: list[dict] = []

    # Finance
    revenue_streams: list[dict] = []
    pricing_strategy: str = ""
    projected_revenue_y1_inr: int | None = None
    projected_revenue_y2_inr: int | None = None
    projected_revenue_y3_inr: int | None = None
    setup_costs: list[dict] = []
    recurring_costs: list[dict] = []
    total_setup_cost_inr: int | None = None
    total_monthly_cost_inr: int | None = None
    funding_approach: str = ""
    funding_schemes: list[str] = []
    gross_margin_pct: float | None = None
    net_margin_pct: float | None = None
    break_even_month: int | None = None

    # Branding
    recommended_name: str = ""
    personality_traits: list[str] = []
    primary_hex: str = ""
    taglines: list[str] = []
    logo_style: str = ""

    # Marketing
    channels: list[dict] = []
    personas: list[dict] = []
    campaign_phases: list[dict] = []
    target_keywords: list[str] = []
    content_topics: list[str] = []

    # Operations
    vendors: list[dict] = []
    roles: list[dict] = []
    tools: list[dict] = []
    daily_workflow: list[dict] = []


PROMPT_TEMPLATE = """Produce a complete business plan for this venture.

BUSINESS: {business_type}
SECTOR: {sector}
LOCATION: {location}
BUDGET: {budget}
PHYSICAL PREMISES: {physical}
ORIGINAL REQUEST: "{raw_prompt}"

Return ONE JSON object with exactly these keys. Fill every key you reasonably can.

STRATEGY
  executive_summary        4-5 sentences a bank would accept
  vision, mission          one sentence each
  business_model_type      e.g. B2C retail
  value_proposition        2 sentences
  tam_inr, sam_inr, som_inr   market size in INR per year; TAM > SAM > SOM
  market_overview          3-4 sentences on demand and trends
  market_statistics        4-6 statistics, each with a number and unit
  industry_growth_rate_pct annual growth rate, e.g. 12.5
  competitors              [{{"name":..., "rating":4.2, "price_level":2}}] up to 6 real nearby businesses
  market_gaps              3-5 gaps
  positioning              2-3 sentences
  location_score           0-10
  location_rationale       2-3 sentences
  risks                    6-8 of [{{"category":"financial|operational|regulatory|market|competitive","description":...,"severity":"high|medium|low","likelihood":"high|medium|low","mitigation":...}}]

FINANCE
  revenue_streams          2-4 of [{{"name":...,"description":...,"monthly_estimate_inr":...,"share_pct":...}}]
  pricing_strategy         2-3 sentences with actual INR price points
  projected_revenue_y1_inr / y2 / y3
  setup_costs              5-8 of [{{"name":...,"subcategory":...,"amount_inr":...}}] totalling no more than the budget
  recurring_costs          5-8 of [{{"name":...,"subcategory":...,"amount_inr":...}}] per month
  total_setup_cost_inr, total_monthly_cost_inr
  funding_approach         2-3 sentences
  funding_schemes          2-4 named Indian schemes
  gross_margin_pct, net_margin_pct    year-1 percentages
  break_even_month         month index in year 1

BRANDING
  recommended_name         one brand name
  personality_traits       4-6 adjectives
  primary_hex              #RRGGBB
  taglines                 4-5 options
  logo_style               wordmark / lettermark / icon / combination, with reasoning

MARKETING
  channels                 4-6 of [{{"name":...,"budget_share_pct":...,"primary_kpi":...,"kpi_target":...}}]
  personas                 3 of [{{"name":...,"age_range":...,"occupation":...,"income_range_inr":...,"pain_points":[...],"buying_triggers":[...]}}]
  campaign_phases          3 of [{{"phase":"pre_launch|launch|post_launch","day_range":...,"objective":...,"activities":[...]}}]
  target_keywords          12-15 keywords, most including the locality
  content_topics           8-10 content ideas

OPERATIONS
  vendors                  4-6 of [{{"category":...,"supplies":...,"sourcing_type":"local|wholesale|online|direct_manufacturer"}}]
  roles                    3-6 of [{{"title":...,"headcount":...,"monthly_salary_inr":...,"responsibilities":[...]}}]
  tools                    6-9 of [{{"name":...,"purpose":...,"cost":"free|freemium|paid"}}]
  daily_workflow           6-9 of [{{"order":1,"name":...,"description":...,"owner_role":...}}]

All monetary amounts are plain integers in INR with no symbols or commas.
Return ONLY the JSON object - no markdown fences, no commentary."""


def baseline_client() -> LLMClient:
    """A Gemini-only client for the baseline.

    A model name is provider-specific, so pinning `gemini-3.6-flash` and letting
    the request walk the normal chain made Groq answer with
    `model_not_found`. More importantly, RQ1's control must be ONE named model or
    a recorded failure - a baseline that silently falls back to a local 3B model
    is not the baseline the paper describes.

    `complete_json`'s validation and repair logic is still reused; only the
    provider set is narrowed.
    """
    return LLMClient(
        groq=_Disabled(ProviderName.GROQ),
        gemini=GeminiProvider(),
        ollama=_Disabled(ProviderName.OLLAMA),
    )


class _Disabled(LLMProvider):
    """Placeholder that removes a provider from the chain."""

    def __init__(self, name: ProviderName) -> None:
        self.name = name
        self.tracker = FreeTierTracker(name=name.value)

    def model_for(self, tier: ModelTier) -> str:
        return "disabled"

    async def is_available(self) -> bool:
        return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise ProviderUnavailable(f"{self.name.value} is excluded from the baseline arm")


async def generate_baseline(
    prompt: str,
    *,
    session_id: str | None = None,
    client: LLMClient | None = None,
    model: str | None = None,
) -> SharedBusinessState:
    """Produce a baseline plan in the same state shape as a multi-agent run.

    Never raises on model failure: a failed baseline is recorded with
    status=FAILED and scores zero, which is a legitimate data point rather than
    an aborted experiment.
    """
    # Intent classification may use the full chain - both arms share it, so it is
    # not part of the manipulation. The plan itself must come from the named model.
    intent_client = client or llm_client
    plan_client = client or baseline_client()
    sid = session_id or f"baseline-{int(time.time() * 1000)}"
    started = time.perf_counter()

    intent = await classify_intent(prompt, client=intent_client)

    state = new_state(sid, prompt)
    state["intent"] = intent
    run = state["metadata"]
    run.status = RunStatus.RUNNING
    # The baseline has no departments; it is scored over all five so it is not
    # advantaged by a smaller denominator than the multi-agent arm.
    run.active_departments = list(Department)
    run.routing_reason = "single-LLM baseline: no routing"

    request = LLMRequest(
        prompt=PROMPT_TEMPLATE.format(
            business_type=intent.business_type_label or intent.business_type,
            sector=intent.sector.value,
            location=intent.location.query_string,
            budget=intent.budget.display if intent.budget.specified else "not specified",
            physical="yes" if intent.is_physical else "no",
            raw_prompt=prompt,
        ),
        system=SYSTEM_PROMPT,
        tier=ModelTier.REASONING,
        temperature=0.3,
        max_tokens=BASELINE_MAX_TOKENS,
        # Pin the model. Without this the request walks the normal fallback chain
        # and a real run served the baseline from Ollama's 3B model while the
        # paper would have reported gemini-3.6-flash.
        model=model or settings.gemini_baseline_model,
    )

    try:
        parsed, response = await plan_client.complete_json(request, BaselineOutput)
    except (AllProvidersFailed, JSONParseError) as exc:
        return _record_failure(state, str(exc), started)

    filled = _filled_field_count(parsed)
    if filled < MIN_FILLED_FIELDS:
        # A response this empty is a failure, not a plan. Reporting it as a
        # completed 0% baseline would flatter the multi-agent arm.
        return _record_failure(
            state,
            f"baseline returned only {filled} populated fields "
            f"(minimum {MIN_FILLED_FIELDS}); treated as a failed run",
            started,
        )

    if response.model != request.model:
        # Report, do not silently accept: RQ1's control must be a named model.
        log.warning(
            "baseline.model_substituted",
            requested=request.model,
            served_by=response.provider.value,
            served_model=response.model,
        )

    _populate(state, parsed)

    elapsed = int((time.perf_counter() - started) * 1000)
    state["agent_traces"] = [
        AgentTrace(
            agent_id=BASELINE_AGENT_ID,
            department=Department.STRATEGY,
            status="completed",
            provider=response.provider.value,
            model=model or response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=elapsed,
        )
    ]

    report = score_completeness(state, list(Department))
    run.status = RunStatus.COMPLETED
    run.total_duration_ms = elapsed
    run.completed_at = datetime.now(UTC).isoformat()
    run.completeness_score = report.score
    run.validation_warnings = [f"missing: {key}" for key in report.missing]

    log.info(
        "baseline.generated",
        session=sid,
        provider=response.provider.value,
        model=response.model,
        tokens=response.total_tokens,
        duration_ms=elapsed,
        completeness=report.score,
    )
    return state


def _filled_field_count(parsed: BaselineOutput) -> int:
    """How many of the requested fields carry content."""
    return sum(
        1
        for value in parsed.model_dump().values()
        if value not in (None, "", [], {}, 0)
    )


def _record_failure(
    state: SharedBusinessState, message: str, started: float
) -> SharedBusinessState:
    elapsed = int((time.perf_counter() - started) * 1000)
    log.warning("baseline.failed", session=state["session_id"], error=message[:250])
    state["agent_traces"] = [
        AgentTrace(
            agent_id=BASELINE_AGENT_ID,
            department=Department.STRATEGY,
            status="failed",
            latency_ms=elapsed,
            error=message[:400],
        )
    ]
    state["errors"] = [f"{BASELINE_AGENT_ID}: {message[:200]}"]
    run = state["metadata"]
    run.status = RunStatus.FAILED
    run.total_duration_ms = elapsed
    run.completed_at = datetime.now(UTC).isoformat()
    run.completeness_score = 0.0
    return state


def _populate(state: SharedBusinessState, parsed: BaselineOutput) -> None:
    """Map the flat baseline response onto the five department sections.

    Written directly rather than through `apply_department_patch` because the
    baseline is one writer touching all five sections at once - the append-only
    contract exists to police concurrent agents, which do not exist here.
    """
    market_size = None
    if any(v is not None for v in (parsed.tam_inr, parsed.sam_inr, parsed.som_inr)):
        market_size = {
            "tam_inr": parsed.tam_inr,
            "sam_inr": parsed.sam_inr,
            "som_inr": parsed.som_inr,
        }

    state["strategy"] = StrategyOutput.model_validate(
        {
            "executive_summary": parsed.executive_summary,
            "vision": parsed.vision,
            "mission": parsed.mission,
            "business_model_type": parsed.business_model_type,
            "value_proposition": parsed.value_proposition,
            "market_size": market_size,
            "market_overview": parsed.market_overview,
            "market_statistics": parsed.market_statistics,
            "industry_growth_rate_pct": parsed.industry_growth_rate_pct,
            "competitors": [
                {**c, "source": "llm_inferred"}
                for c in parsed.competitors
                if isinstance(c, dict) and c.get("name")
            ],
            "market_gaps": parsed.market_gaps,
            "positioning": parsed.positioning,
            "location_score": _clamp(parsed.location_score, 0.0, 10.0),
            "location_rationale": parsed.location_rationale,
            "risks": [r for r in parsed.risks if isinstance(r, dict) and r.get("description")],
        }
    )

    state["finance"] = FinanceOutput.model_validate(
        {
            "revenue_streams": [r for r in parsed.revenue_streams if isinstance(r, dict) and r.get("name")],
            "pricing_strategy": parsed.pricing_strategy,
            "projected_revenue_y1_inr": parsed.projected_revenue_y1_inr,
            "projected_revenue_y2_inr": parsed.projected_revenue_y2_inr,
            "projected_revenue_y3_inr": parsed.projected_revenue_y3_inr,
            "setup_costs": _costs(parsed.setup_costs, "setup"),
            "recurring_costs": _costs(parsed.recurring_costs, "recurring"),
            "total_setup_cost_inr": parsed.total_setup_cost_inr,
            "total_monthly_cost_inr": parsed.total_monthly_cost_inr,
            "funding_approach": parsed.funding_approach,
            "funding_schemes": parsed.funding_schemes,
            "gross_margin_pct": parsed.gross_margin_pct,
            "net_margin_pct": parsed.net_margin_pct,
            "break_even_month": parsed.break_even_month,
        }
    )

    palette = {"primary_hex": parsed.primary_hex} if parsed.primary_hex.startswith("#") else None
    state["branding"] = BrandingOutput.model_validate(
        {
            "recommended_name": parsed.recommended_name or None,
            "personality_traits": parsed.personality_traits,
            "color_palette": palette,
            "taglines": parsed.taglines,
            "logo_style": parsed.logo_style,
        }
    )

    state["marketing"] = MarketingOutput.model_validate(
        {
            "channels": [c for c in parsed.channels if isinstance(c, dict) and c.get("name")],
            "personas": [p for p in parsed.personas if isinstance(p, dict) and p.get("name")],
            "campaign_phases": [
                p for p in parsed.campaign_phases if isinstance(p, dict) and (p.get("objective") or p.get("activities"))
            ],
            "target_keywords": parsed.target_keywords,
            "content_topics": parsed.content_topics,
        }
    )

    state["operations"] = OperationsOutput.model_validate(
        {
            "vendors": [v for v in parsed.vendors if isinstance(v, dict) and v.get("category")],
            "roles": [r for r in parsed.roles if isinstance(r, dict) and r.get("title")],
            "tools": [t for t in parsed.tools if isinstance(t, dict) and t.get("name")],
            "daily_workflow": _workflow(parsed.daily_workflow),
        }
    )


def _clamp(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    return max(low, min(high, float(value)))


_VALID_SUBCATEGORIES = {
    "rent", "salary", "equipment", "utilities", "marketing", "licences",
    "inventory", "interiors", "deposit", "other",
}


def _costs(rows: list[dict], category: str) -> list[dict]:
    out = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        subcategory = str(row.get("subcategory", "")).strip().lower()
        out.append(
            {
                "name": row["name"],
                "category": category,
                "subcategory": subcategory if subcategory in _VALID_SUBCATEGORIES else "other",
                "amount_inr": max(0, int(row.get("amount_inr") or 0)),
                "notes": str(row.get("notes", "")),
            }
        )
    return out


def _workflow(rows: list[dict]) -> list[dict]:
    steps = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("name"):
            continue
        order = row.get("order")
        steps.append(
            {
                "order": int(order) if isinstance(order, (int, float)) and order else index + 1,
                "name": row["name"],
                "description": str(row.get("description", "")),
                "owner_role": str(row.get("owner_role", "")),
                "depends_on": row.get("depends_on") or [],
            }
        )
    return sorted(steps, key=lambda s: s["order"])


def baseline_model_name() -> str:
    """The model the baseline is configured to use, for the paper's setup table."""
    return settings.gemini_baseline_model
