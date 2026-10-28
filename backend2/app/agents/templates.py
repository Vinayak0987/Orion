"""The 7 agent templates (Plan 05 — Templates section).

Pre-built configurations users start from. Seeded idempotently at startup. Each
base_config has the same shape as the agents table fields.
"""

from __future__ import annotations

from app.agents.store import create_template, get_template

TOOL_HINT = (
    "\n\nTo use a tool, reply with ONLY a JSON object: "
    '{"tool": "<name>", "input": {...}}. '
    "When finished, reply with normal prose (no JSON)."
)

TEMPLATES = [
    {
        "id": "tpl-marketing", "name": "Marketing Agent", "category": "Marketing",
        "description": "Creates campaigns, content, and go-to-market strategy.",
        "tags": ["content", "campaigns", "seo"], "is_featured": True,
        "base_config": {
            "agent_type": "marketing", "name": "Marketing Agent",
            "purpose": "Create compelling, data-driven marketing content and strategy.",
            "system_prompt": "You are a senior marketing strategist. Create compelling, practical "
            "marketing content and strategies grounded in data and audience insight." + TOOL_HINT,
            "tools": ["web_search", "web_scraper", "document_rag", "content_rewriter", "keyword_extractor"],
            "model": "groq:llama-3.3-70b-versatile", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-finance", "name": "Financial Analyst", "category": "Finance",
        "description": "Analyzes financials, builds projections, assesses risk.",
        "tags": ["analysis", "projections", "risk"], "is_featured": True,
        "base_config": {
            "agent_type": "finance", "name": "Financial Analyst",
            "purpose": "Analyze financial data and produce clear, numerate recommendations.",
            "system_prompt": "You are a financial analyst. Analyze data, build projections, state your "
            "assumptions, and give clear, numerate recommendations." + TOOL_HINT,
            "tools": ["web_search", "document_rag", "calculator", "statistics_tool", "forecasting_tool",
                      "csv_tool", "data_aggregator"],
            "model": "groq:llama-3.3-70b-versatile", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-operations", "name": "Operations Agent", "category": "Operations",
        "description": "Plans and optimizes operational workflows.",
        "tags": ["workflow", "process", "logistics"],
        "base_config": {
            "agent_type": "operations", "name": "Operations Agent",
            "purpose": "Design practical, systematic operational plans and workflows.",
            "system_prompt": "You are an operations planner. Design practical, systematic, actionable "
            "operational plans and workflows." + TOOL_HINT,
            "tools": ["web_search", "document_rag", "data_transformer", "data_filter", "datetime_tool"],
            "model": "groq:llama-3.1-8b-instant", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-research", "name": "Research Agent", "category": "Research",
        "description": "Finds, verifies, and synthesizes current information.",
        "tags": ["web", "synthesis", "citations"], "is_featured": True,
        "base_config": {
            "agent_type": "research", "name": "Research Agent",
            "purpose": "Find accurate, current information and summarize it clearly with sources.",
            "system_prompt": "You are a research specialist. Use web search and documents to find "
            "accurate, current information. Cite sources and summarize clearly." + TOOL_HINT,
            "tools": ["web_search", "web_search_news", "web_scraper", "wikipedia_search",
                      "arxiv_search", "document_rag", "text_summarizer"],
            "model": "groq:llama-3.3-70b-versatile", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-hr", "name": "HR Agent", "category": "HR",
        "description": "Drafts policies, job posts, and people-ops documents.",
        "tags": ["policy", "hiring", "people"],
        "base_config": {
            "agent_type": "general", "name": "HR Agent",
            "purpose": "Draft clear HR policies, job descriptions, and people-ops documents.",
            "system_prompt": "You are an HR specialist. Draft clear, compliant, people-first HR "
            "documents, policies, and communications." + TOOL_HINT,
            "tools": ["web_search", "document_rag", "content_rewriter", "readability_analyzer"],
            "model": "groq:llama-3.1-8b-instant", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-sales", "name": "Sales Agent", "category": "Sales",
        "description": "Builds outreach, qualifies leads, drafts proposals.",
        "tags": ["outreach", "leads", "proposals"],
        "base_config": {
            "agent_type": "general", "name": "Sales Agent",
            "purpose": "Research prospects and draft persuasive, personalized sales outreach.",
            "system_prompt": "You are a sales specialist. Research prospects and draft persuasive, "
            "personalized outreach and proposals." + TOOL_HINT,
            "tools": ["web_search", "web_scraper", "document_rag", "content_rewriter", "entity_extractor"],
            "model": "groq:llama-3.1-8b-instant", "memory_enabled": True,
        },
    },
    {
        "id": "tpl-support", "name": "Customer Support Agent", "category": "Support",
        "description": "Resolves tickets using the knowledge base and past cases.",
        "tags": ["tickets", "knowledge", "resolution"],
        "base_config": {
            "agent_type": "general", "name": "Customer Support Agent",
            "purpose": "Resolve customer issues accurately using the knowledge base and past cases.",
            "system_prompt": "You are a customer support specialist. Resolve issues accurately and "
            "empathetically, grounding answers in the knowledge base and remembered past resolutions." + TOOL_HINT,
            "tools": ["document_rag", "keyword_search", "memory_search", "memory_write", "web_search"],
            "model": "groq:llama-3.1-8b-instant", "memory_enabled": True,
        },
    },
]


def seed_templates() -> int:
    for spec in TEMPLATES:
        if get_template(spec["id"]) is None:
            create_template(**spec)
    return len(TEMPLATES)
