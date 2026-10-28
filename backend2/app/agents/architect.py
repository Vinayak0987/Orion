"""Agent Architect — turns a natural-language goal into a structured
multi-agent pipeline.

Given a description like "a customer-outreach agent that scores users from their
interactions, scrapes product images they viewed, drafts a personalized email
per user, and sends it via Gmail", the architect returns an ordered list of
SUB-AGENTS. Each sub-agent gets:
  • a focused role,
  • an input/output contract (output of step N feeds input of step N+1),
  • and ONLY the tools it actually needs (built-ins picked by capability +
    external tools where a real-world action like send/post/generate happens).

The master agent's own tool list is the UNION of all sub-agent tools, so the
executor's allow-list still works.

Everything is LLM-derived (no hard-coded templates), then normalized + validated
against the real tool catalog so we never attach a tool that doesn't exist.
"""

from __future__ import annotations

import uuid

from app.llm.client import LLMClient
from app.tools import registry
from app.tools import store as tool_store


def _tool_catalog() -> list[dict]:
    """Compact catalog: name, description, category, kind (builtin/custom/mcp)."""
    try:
        rows = tool_store.list_tools(enabled=True)
        if rows:
            return [
                {"name": r["name"], "description": (r.get("description") or "")[:140],
                 "category": r.get("category") or "", "kind": r.get("type") or "builtin"}
                for r in rows
            ]
    except Exception:  # noqa: BLE001 — DB not ready
        pass
    return [{"name": t["name"], "description": t["description"][:140], "category": "", "kind": "builtin"}
            for t in registry.list_tools()]


def _catalog_text(catalog: list[dict]) -> str:
    """Group the catalog by category for a compact, LLM-friendly listing."""
    by_cat: dict[str, list[dict]] = {}
    for t in catalog:
        by_cat.setdefault(t["category"] or t["kind"], []).append(t)
    lines: list[str] = []
    for cat in sorted(by_cat):
        lines.append(f"\n[{cat}]")
        for t in by_cat[cat]:
            tag = "" if t["kind"] == "builtin" else f" ({t['kind']})"
            lines.append(f"  - {t['name']}{tag}: {t['description']}")
    return "\n".join(lines)


_SYSTEM = (
    "You are Orion's Agent Architect. You design multi-agent pipelines for an AI "
    "company operating system. A MASTER agent decomposes a business goal into an "
    "ordered list of SUB-AGENTS, each doing ONE focused job, passing its output to "
    "the next. You assign each sub-agent ONLY the tools it truly needs — never the "
    "whole catalog. Prefer built-in tools for analysis/scraping/writing/data work; "
    "use EXTERNAL tools (integrations) only for real-world actions like sending "
    "email/messages, generating media, or posting to social accounts. "
    "Return STRICT JSON only."
)


def _prompt(description: str, department: str, agent_type: str, catalog_text: str) -> str:
    return f"""Design a multi-agent pipeline for this goal.

DEPARTMENT: {department or "General"}
AGENT TYPE: {agent_type or "general"}
GOAL (user's words):
\"\"\"{description.strip()}\"\"\"

AVAILABLE TOOLS (choose tool `name`s ONLY from this list; do not invent tools):
{catalog_text}

Return STRICT JSON with this exact shape:
{{
  "name": "<concise master agent name>",
  "agent_type": "<one of: research|marketing|finance|operations|hr|analysis|writing|general>",
  "purpose": "<one sentence on what the master agent accomplishes>",
  "system_prompt": "<2-4 sentences instructing the master orchestrator>",
  "sub_agents": [
    {{
      "name": "<short sub-agent name>",
      "role": "<what this sub-agent does, 1 sentence>",
      "input": "<what it receives: mission input or the previous step's output>",
      "output": "<what it produces for the next step>",
      "tools": ["<tool name from the catalog>", "..."],
      "system_prompt": "<2-3 sentence instruction for this sub-agent>"
    }}
  ]
}}

RULES:
- 2 to 6 sub-agents, in execution order (first consumes the mission input, last produces the final result).
- Each sub-agent's `input` should reference the previous sub-agent's `output` (except the first).
- Assign the MINIMAL set of tools per sub-agent (often 1-3). Do not attach tools a step doesn't use.
- Only the step that performs an external action (send/post/generate) should use an external/integration tool.
- Use ONLY tool names that appear in the catalog above.
Return ONLY the JSON object."""


def _normalize(raw: dict, catalog: list[dict], *, department: str) -> dict:
    """Validate + clean the LLM output: keep only real tools, add ids/order, and
    compute the master tool union."""
    valid = {t["name"] for t in catalog}
    subs_in = raw.get("sub_agents") or []
    subs: list[dict] = []
    for i, s in enumerate(subs_in):
        if not isinstance(s, dict):
            continue
        tools = [t for t in (s.get("tools") or []) if t in valid]
        subs.append({
            "id": "sa_" + uuid.uuid4().hex[:8],
            "name": (s.get("name") or f"Step {i + 1}").strip()[:120],
            "role": (s.get("role") or "").strip(),
            "input": (s.get("input") or ("Mission input" if i == 0 else "Previous step output")).strip(),
            "output": (s.get("output") or "").strip(),
            "tools": tools,
            "system_prompt": (s.get("system_prompt") or "").strip(),
            "order": i + 1,
        })
    union: list[str] = []
    for s in subs:
        for t in s["tools"]:
            if t not in union:
                union.append(t)
    agent_type = (raw.get("agent_type") or "general").strip().lower()
    valid_types = {"research", "marketing", "finance", "operations", "hr", "analysis", "writing", "general"}
    if agent_type not in valid_types:
        agent_type = "general"
    return {
        "name": (raw.get("name") or "New Agent").strip()[:120],
        "agent_type": agent_type,
        "purpose": (raw.get("purpose") or "").strip(),
        "system_prompt": (raw.get("system_prompt")
                          or f"You orchestrate a {department or 'general'} pipeline.").strip(),
        "department": department or "",
        "sub_agents": subs,
        "tools": union,  # master agent allow-list = union of sub-agent tools
    }


async def design_pipeline(description: str, *, department: str = "", agent_type: str = "general",
                          user_keys: dict | None = None) -> dict:
    """Derive the pipeline. Raises AllProvidersFailedError if no LLM is reachable."""
    catalog = _tool_catalog()
    llm = LLMClient(user_keys=user_keys)
    raw = await llm.call_structured(
        _prompt(description, department, agent_type, _catalog_text(catalog)),
        system=_SYSTEM, tier="reasoning",
    )
    if not isinstance(raw, dict):
        raw = {}
    return _normalize(raw, catalog, department=department)
