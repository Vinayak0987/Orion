"""The Planner — turns a natural-language goal into a task list.

One fast LLM call. Returns a validated list of task dicts. Invalid depends_on
references are dropped rather than failing the whole plan.
"""

from __future__ import annotations

from app.llm.client import LLMClient

VALID_AGENT_TYPES = {
    "research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general",
}


def _known_tools() -> set[str]:
    """The real set of tool names the executor can dispatch (full catalog), so the
    planner is no longer capped to a hardcoded pair."""
    try:
        from app.tools import registry
        return {t["name"] for t in registry.list_tools()}
    except Exception:  # noqa: BLE001 — registry not ready
        return {"web_search", "document_rag"}

PLANNER_SYSTEM = """You are a task planner for an AI company operating system.
Break the user's goal into a short list of concrete, ordered tasks (2-8 tasks).

Each task is a JSON object with:
  - "title": a short action phrase (unique within the plan)
  - "agent_type": one of [research, marketing, finance, operations, hr, analysis, writing, general]
  - "tools_needed": the tool names this task needs, chosen from the AVAILABLE TOOLS list
     provided below (or [] if the task is pure reasoning/writing)
  - "depends_on": a list of earlier task titles that must finish first, or []

Rules:
- Independent tasks have "depends_on": [] so they can run in parallel.
- A task that synthesizes earlier work depends_on those task titles exactly.
- IMPORTANT: any task that needs CURRENT or EXTERNAL information MUST include
  "web_search" (or "web_search_news") in tools_needed. Any task about the user's
  uploaded files MUST include "document_rag" or "query_document". Tasks doing math/data MUST include
  the relevant data tool. Only pure writing/formatting tasks may have [].

REASONING BEYOND THE LITERAL REQUEST — this is critical:
- Infer implied steps the user didn't explicitly mention but which are OBVIOUSLY required.
  Example: "send a campaign from the CSV" implies: read CSV, validate recipients, draft a
  template, preview it, then send — even if the user only said "send".
- If the task involves data the agent needs to discover first (a CSV, a product page, an API
  result), always include a preceding research/validation task.
- If the task involves generating content the user will need to review (a template, a report,
  a plan), include a "Draft and present X for review" task BEFORE any send/publish/post task.
  This gives the user a chance to see the output before it goes out.
- If the task involves sending to multiple recipients or performing a repeated action, include
  a "Preview/verify before sending" task so results can be checked.
- Verification tasks ("verify X before proceeding") are valuable — include them for any
  task that touches external data or sends irreversible actions.
- Tasks that produce real-world side effects (send email, post, publish) should always be
  preceded by a task that surfaces what will be sent/posted/published.

Keep it focused — don't invent unnecessary tasks, but don't omit obviously-required steps.

Return ONLY a JSON array of task objects. No prose, no markdown."""

TITLE_SYSTEM = """Generate a short title (3-6 words) for this goal. Return ONLY the title text."""

CLARIFY_SYSTEM = """You are the intake step of an AI company operating system.
Decide whether the user's goal is clear enough to plan and execute, OR whether
one short clarifying question would materially improve the result.

Only ask when the goal is genuinely ambiguous or missing a critical detail
(e.g. "make a plan" with no subject, "analyze it" with no target). If the goal
is actionable as-is, do NOT ask.

Return ONLY a JSON object:
  {"needs_clarification": false}
or
  {"needs_clarification": true, "question": "<one concise question>"}"""

MEMORY_SYSTEM = """You extract durable, reusable facts about the user or their
company from a conversation — things worth remembering for ALL future chats.
Examples: company name, industry, product, target audience, preferred tone,
recurring goals. Ignore one-off task details.

Return ONLY a JSON array of {"key": "...", "value": "..."} objects (0-5 items).
Keys are short slugs (e.g. "company", "industry", "tone"). Return [] if nothing
durable is present."""


async def plan(goal: str, llm: LLMClient, context: str = "", memory: str = "",
               tool_catalog: str = "") -> list[dict]:
    parts = []
    if context:
        parts.append(context)
    if memory:
        parts.append(memory)
    if tool_catalog:
        parts.append("AVAILABLE TOOLS (choose tools_needed ONLY from these names):\n" + tool_catalog)
    parts.append(f"Goal: {goal}")
    user = "\n\n".join(parts)
    # Use the reasoning tier for complex goals that likely have implied steps
    # (data files, multiple recipients, send/publish actions, campaigns).
    # The fast tier plans mechanically; the reasoning tier infers implied steps.
    import re as _re
    _complex = bool(_re.search(
        r"\b(csv|xlsx?|spreadsheet|campaign|multiple|recipients?|send|publish|post|email|"
        r"template|personali[sz]|outreach|from the|all the|each|every|for each|per)\b",
        goal, _re.IGNORECASE))
    tier = "reasoning" if _complex else "fast"
    raw = await llm.call_structured(user, system=PLANNER_SYSTEM, tier=tier)
    if not isinstance(raw, list):
        return []
    return _validate(raw)


def tool_catalog_text(mode: str = "planning", goal: str = "") -> str:
    """Compact 'name: description' catalog for the planner prompt. Combines a
    small set of always-useful tools with GOAL-RELEVANT tools discovered from the
    FULL registry (incl. the 290 MCP tools) — so e.g. an 'image/ad/banner'
    goal surfaces mcp_ads_studio_generate / mcp_generate_image, and the planner
    can actually assign them. The executor still allows any valid tool at runtime."""
    priority = [
        "web_search", "web_search_news", "document_rag", "keyword_search", "query_document",
        "web_scraper", "web_content_extractor", "wikipedia_search", "http_request",
        "calculator", "statistics_tool", "csv_tool", "json_tool", "data_aggregator",
        "code_interpreter", "summarizer", "text_summarizer", "sentiment_analyzer",
        "entity_extractor", "translator", "pdf_reader", "file_reader",
        "gmail_send", "http_action",
    ]
    try:
        from app.tools import registry
        from app.tools import modes as _tmodes
        by_name = {t["name"]: t for t in registry.list_tools()}
    except Exception:  # noqa: BLE001
        return "- web_search: search the web for current information\n- document_rag: search the user's uploaded documents"

    chosen: list[str] = []
    # 1. Goal-relevant tools FIRST (incl. MCP action tools) so the planner sees them.
    if goal:
        for t in _tmodes.discover_tools(goal, mode=mode, limit=18):
            if t["name"] not in chosen:
                chosen.append(t["name"])
    # 2. Then the always-useful priority tools.
    for name in priority:
        if name in by_name and name not in chosen:
            chosen.append(name)

    lines = []
    for name in chosen[:40]:
        t = by_name.get(name)
        if t:
            lines.append(f"- {name}: {(t.get('description','') or '')[:100]}")
    return "\n".join(lines)


async def clarify(goal: str, llm: LLMClient, context: str = "") -> dict:
    """Decide if a clarifying question is needed. Returns {} if not, else {question}."""
    try:
        user = f"{context}\n\nGoal: {goal}" if context else f"Goal: {goal}"
        raw = await llm.call_structured(user, system=CLARIFY_SYSTEM, tier="fast")
        if isinstance(raw, dict) and raw.get("needs_clarification") and raw.get("question"):
            return {"question": str(raw["question"]).strip()[:300]}
    except Exception:
        pass
    return {}


async def extract_memory(conversation_text: str, llm: LLMClient) -> list[dict]:
    """Best-effort: pull durable facts from a conversation. Never raises."""
    try:
        raw = await llm.call_structured(conversation_text[:6000], system=MEMORY_SYSTEM, tier="fast")
        if not isinstance(raw, list):
            return []
        facts = []
        for item in raw[:5]:
            if isinstance(item, dict) and item.get("key") and item.get("value"):
                facts.append({"key": str(item["key"]).strip()[:80], "value": str(item["value"]).strip()[:500]})
        return facts
    except Exception:
        return []


async def generate_title(goal: str, llm: LLMClient) -> str:
    try:
        result = await llm.call_text(f"Goal: {goal}", system=TITLE_SYSTEM, tier="fast")
        title = result.text.strip().strip('"').strip()
        return title[:80] or goal[:80]
    except Exception:
        return goal[:80]


def _validate(tasks: list) -> list[dict]:
    known = _known_tools()
    clean: list[dict] = []
    titles: set[str] = set()
    for t in tasks:
        if not isinstance(t, dict):
            continue
        title = str(t.get("title", "")).strip()
        atype = str(t.get("agent_type", "general")).strip().lower()
        if not title:
            continue
        if atype not in VALID_AGENT_TYPES:
            atype = "general"
        tools = [tool for tool in t.get("tools_needed", []) if tool in known]
        clean.append({
            "title": title, "agent_type": atype, "tools_needed": tools,
            "depends_on": [],  # filled in the second pass once all titles are known
            "_raw_depends": t.get("depends_on", []),
        })
        titles.add(title)

    # Second pass: keep only depends_on references that point to real titles.
    for t in clean:
        t["depends_on"] = [d for d in t.pop("_raw_depends", []) if d in titles and d != t["title"]]
    return clean
