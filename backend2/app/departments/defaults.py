"""Seed default departments + their pre-built Head agents (idempotent).

Gives Orion a working organization out of the box. Each default department has
one Head agent (origin='head') that the Master routes work to; the Head then
dynamically creates/reuses specialists per mission. Users can add custom
departments too.
"""

from __future__ import annotations

from app.agents.store import create_agent, get_agent
from app.departments import store as dept_store

# (dept_id, name, dept_type, purpose, head agent_type, head role title)
_DEFAULTS = [
    ("dept-marketing", "Marketing", "marketing",
     "Brand, growth, content, SEO, campaigns and marketing analytics.",
     "marketing", "Marketing Director"),
    ("dept-research", "Research", "research",
     "Market, competitor, technical and customer research with evidence.",
     "research", "Research Lead"),
    ("dept-operations", "Operations", "operations",
     "Process design, workflows, logistics and operational execution.",
     "operations", "Operations Director"),
    ("dept-finance", "Finance", "finance",
     "Financial analysis, projections, budgeting and reporting.",
     "finance", "Finance Director"),
    ("dept-content", "Content", "custom",
     "Writing, editing and content production across channels.",
     "writing", "Content Lead"),
    ("dept-general", "General", "custom",
     "Cross-functional tasks that don't fit a single department.",
     "general", "General Manager"),
]

_TOOL_HINT = (
    "\n\nTo use a tool, reply with ONLY a JSON object: "
    '{"tool": "<name>", "input": {...}}. Give your final answer as prose when done.'
)


def seed_default_departments() -> int:
    """Create each default department + its Head. Idempotent. Returns count."""
    n = 0
    for did, name, dtype, purpose, head_type, head_title in _DEFAULTS:
        if dept_store.get_department(did) is None:
            dept_store.create_department(
                id=did, name=name, dept_type=dtype, purpose=purpose,
                created_by="system", is_default=True, status="active",
            )
            n += 1
        # Ensure a Head agent exists + is assigned.
        head_id = f"head-{did}"
        if get_agent(head_id) is None:
            create_agent(
                id=head_id, name=f"{name} Head", role_title=head_title,
                purpose=f"Head of the {name} department. {purpose}",
                system_prompt=(
                    f"You are the {head_title}, head of the {name} department of an AI company. "
                    f"Department purpose: {purpose} "
                    "You coordinate the department: break a task into focused subtasks, delegate "
                    "each to the right specialist, and consolidate their results into a clear, "
                    "evidence-backed final answer. Be concise and practical." + _TOOL_HINT
                ),
                agent_type=head_type,
                tools=["web_search", "document_rag"],
                model="groq:openai/gpt-oss-120b",
                created_by="system", origin="head",
            )
        # Assign as head (idempotent).
        if dept_store.get_head(did) is None:
            dept_store.assign_head(did, head_id)
    return n
