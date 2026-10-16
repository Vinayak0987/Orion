"""The Planner — turns a natural-language goal into a task list.

One fast LLM call. Returns a validated list of task dicts. Invalid depends_on
references are dropped rather than failing the whole plan.
"""

from __future__ import annotations

from app.llm.client import LLMClient

VALID_AGENT_TYPES = {
    "research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general",
}
VALID_TOOLS = {"web_search", "document_rag"}

PLANNER_SYSTEM = """You are a task planner for an AI company operating system.
Break the user's goal into a short list of concrete, ordered tasks (2-6 tasks).

Each task is a JSON object with:
  - "title": a short action phrase (unique within the plan)
  - "agent_type": one of [research, marketing, finance, operations, hr, analysis, writing, general]
  - "tools_needed": a subset of [web_search, document_rag], or []
  - "depends_on": a list of earlier task titles that must finish first, or []

Rules:
- Independent tasks have "depends_on": [] so they can run in parallel.
- A task that synthesizes earlier work depends_on those task titles exactly.
- Keep it minimal — do not invent unnecessary tasks.

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


async def plan(goal: str, llm: LLMClient, context: str = "", memory: str = "") -> list[dict]:
    parts = []
    if context:
        parts.append(context)
    if memory:
        parts.append(memory)
    parts.append(f"Goal: {goal}")
    user = "\n\n".join(parts)
    raw = await llm.call_structured(user, system=PLANNER_SYSTEM, tier="fast")
    if not isinstance(raw, list):
        return []
    return _validate(raw)


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
        tools = [tool for tool in t.get("tools_needed", []) if tool in VALID_TOOLS]
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
