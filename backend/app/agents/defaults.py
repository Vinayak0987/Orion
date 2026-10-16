"""The 7 default system agents.

Seeded on startup (idempotent). These are what the Router falls back to when a
user has not created their own agent of a given type. Users can create custom
agents in Phase 2 that override these.
"""

from __future__ import annotations

from app.agents.store import create_agent, get_agent

_TOOL_HINT = (
    "\n\nTo use a tool, reply with ONLY a JSON object and nothing else:\n"
    '{"tool": "web_search", "input": {"query": "..."}}\n'
    "Available tools are listed in your task context. "
    "When you have your final answer, reply with normal prose (no JSON)."
)

DEFAULTS = [
    {
        "id": "sys-research",
        "agent_type": "research",
        "name": "Research Agent",
        "purpose": "Find accurate, current information.",
        "system_prompt": "You are a research specialist. Use web search to find accurate, "
        "current information. Cite sources. Summarize findings clearly and concisely." + _TOOL_HINT,
        "tools": ["web_search", "document_rag"],
        "model": "groq:llama-3.3-70b-versatile",
    },
    {
        "id": "sys-marketing",
        "agent_type": "marketing",
        "name": "Marketing Agent",
        "purpose": "Create marketing strategies and content.",
        "system_prompt": "You are a marketing strategist. Create compelling, practical "
        "marketing strategies and content. Be creative but grounded in data." + _TOOL_HINT,
        "tools": ["web_search", "document_rag"],
        "model": "groq:llama-3.3-70b-versatile",
    },
    {
        "id": "sys-finance",
        "agent_type": "finance",
        "name": "Financial Analyst",
        "purpose": "Analyze finances and build projections.",
        "system_prompt": "You are a financial analyst. Analyze financial data, build "
        "projections, and give clear, numerate recommendations. Show your assumptions." + _TOOL_HINT,
        "tools": ["web_search", "document_rag"],
        "model": "groq:llama-3.3-70b-versatile",
    },
    {
        "id": "sys-analysis",
        "agent_type": "analysis",
        "name": "Analysis Agent",
        "purpose": "Analyze data and find insights.",
        "system_prompt": "You are an analyst. Examine the information available, find "
        "patterns, draw well-reasoned conclusions, and present them clearly." + _TOOL_HINT,
        "tools": ["document_rag"],
        "model": "groq:llama-3.3-70b-versatile",
    },
    {
        "id": "sys-writing",
        "agent_type": "writing",
        "name": "Writing Agent",
        "purpose": "Write clear, structured content.",
        "system_prompt": "You are a professional writer. Produce clear, well-structured "
        "content that matches the requested format and tone." + _TOOL_HINT,
        "tools": [],
        "model": "groq:llama-3.1-8b-instant",
    },
    {
        "id": "sys-operations",
        "agent_type": "operations",
        "name": "Operations Agent",
        "purpose": "Plan and optimize operations.",
        "system_prompt": "You are an operations planner. Design practical, systematic "
        "operational plans and workflows. Be concrete and actionable." + _TOOL_HINT,
        "tools": ["web_search", "document_rag"],
        "model": "groq:llama-3.1-8b-instant",
    },
    {
        "id": "sys-general",
        "agent_type": "general",
        "name": "General Agent",
        "purpose": "Handle any task thoroughly.",
        "system_prompt": "You are a capable generalist. Handle the task intelligently and "
        "thoroughly. If something is ambiguous, state your assumption and proceed." + _TOOL_HINT,
        "tools": ["web_search", "document_rag"],
        "model": "groq:llama-3.1-8b-instant",
    },
]


def seed_defaults() -> None:
    """Idempotent. Inserts any missing default agents."""
    for spec in DEFAULTS:
        if get_agent(spec["id"]) is None:
            create_agent(created_by="system", **spec)
