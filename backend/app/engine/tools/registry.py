"""Tool registry + dispatch.

The Executor calls dispatch(tool_name, input, user_keys). Unknown tools return
an error dict (not an exception) so a mis-planned tool name degrades gracefully.
"""

from __future__ import annotations

from app.engine.tools.document_rag import document_rag
from app.engine.tools.web_search import web_search

# Built-in tools available to every agent (subject to the agent's allowed list).
BUILTIN_TOOLS = {
    "web_search": {
        "fn": web_search,
        "description": "Search the web for current information. Input: {query: str}",
    },
    "document_rag": {
        "fn": document_rag,
        "description": "Search uploaded documents and knowledge base. Input: {query: str}",
    },
}


def list_tools() -> list[dict]:
    return [{"name": name, "description": meta["description"]} for name, meta in BUILTIN_TOOLS.items()]


async def dispatch(tool_name: str, tool_input: dict, user_keys: dict | None = None) -> dict:
    meta = BUILTIN_TOOLS.get(tool_name)
    if meta is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await meta["fn"](tool_input, user_keys)
