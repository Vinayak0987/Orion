"""Tool mode classification — read-only vs action.

Planning mode exposes only READ-ONLY tools (gather + reason: search, rag,
scrape, calculate, summarize…). Action mode additionally exposes ACTION tools
that cause real-world side effects (send email, post, upload, pay, write to a
system), which require approval before they run.

Classification is rule-based (no schema change): a tool is an ACTION tool if it
is explicitly flagged, or its name matches an action verb pattern. Everything
else — all the read/compute built-ins — is read-only and safe in planning mode.
"""

from __future__ import annotations

import re

# Name patterns that indicate a real-world side effect (an ACTION).
_ACTION_PATTERNS = re.compile(
    r"(^|_)("
    r"send|post|publish|upload|create|update|delete|remove|write|put|patch|"
    r"reply|message|dm|email|mail|tweet|share|schedule|book|pay|charge|refund|"
    r"deploy|execute_action|submit|register|invite|assign|move|archive|"
    r"generate|render|produce|make|draw|compose|synthesize|run|start|cancel|"
    r"webhook_send|place_order|checkout"
    r")($|_)",
    re.IGNORECASE,
)

# Built-in tools whose names match an action verb but are actually LOCAL/safe
# (no external side effect) — keep these read-only.
_SAFE_OVERRIDES = {
    "file_writer", "file_copy", "file_move", "file_delete",      # sandboxed workspace only
    "directory_manager", "archive_manager", "pdf_merger", "pdf_splitter",
    "key_value_store", "local_cache", "memory_write", "sqlite_tool",
    "database_backup", "structured_output_generator", "prompt_template",
    "uuid_generator", "random_data_generator", "citation_builder",
    "content_rewriter", "text_normalizer", "markdown_renderer", "json_tool",
    "csv_tool", "yaml_tool", "xml_tool", "jsonl_writer", "schema_validator",
    "document_chunker", "text_chunker", "recommendation_tool", "forecasting_tool",
}

# Tool types that are INHERENTLY actionable when they reach external systems.
# builtin/custom compute stays read-only unless the name says otherwise; mcp +
# integration tools are treated as potential actions (gated) when they match.
_ACTIONABLE_TYPES = {"mcp", "integration"}

# Known action tools by EXACT name (don't rely on a verb pattern).
_EXPLICIT_ACTIONS = {
    "http_action", "webhook_sender", "gmail_send", "browser_action",
}


def is_action_tool(tool: dict) -> bool:
    """True if using this tool causes a real-world side effect (needs action mode
    + approval). `tool` is a registry/store dict with at least name + type."""
    name = tool.get("name", "")
    if tool.get("action") is True:            # explicit flag wins
        return True
    if name in _EXPLICIT_ACTIONS:             # known action tools by exact name
        return True
    if name in _SAFE_OVERRIDES:
        return False
    # MCP + integration tools reach EXTERNAL systems — treat as actions (gated),
    # EXCEPT obviously read-only ones (list/get/read/search/browse/check/status).
    if tool.get("type") in _ACTIONABLE_TYPES:
        readonly = re.search(r"(^|_)(list|get|read|search|browse|check|status|"
                             r"quote|card|progress|fetch|view|query|describe|lookup|"
                             r"resolve|options|presets|schema|defaults)($|_)", name, re.IGNORECASE)
        return not bool(readonly)
    if _ACTION_PATTERNS.search(name):
        # An action-verb name: an action tool UNLESS it's a known-safe builtin.
        return True
    return False


def requires_approval(tool: dict) -> bool:
    """External actions require human approval before executing."""
    return is_action_tool(tool)


def filter_tools_for_mode(tools: list[dict], mode: str) -> list[dict]:
    """Return the tools allowed in the given mode.
    planning → read-only only.  action → everything."""
    if mode == "action":
        return tools
    return [t for t in tools if not is_action_tool(t)]


def allowed_tool_names_for_mode(mode: str) -> set[str]:
    """The set of tool names permitted in this mode (from the live registry)."""
    try:
        from app.tools import registry
        tools = registry.list_tools()
    except Exception:  # noqa: BLE001
        return set()
    return {t["name"] for t in filter_tools_for_mode(tools, mode)}


# --- Relevance-based tool discovery over the FULL registry -------------------
_STOP = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "our",
    "my", "your", "this", "that", "it", "is", "are", "be", "make", "create",
    "generate", "produce", "get", "list", "show", "me", "please", "using", "use",
    "task", "subtask", "step", "research", "collect", "final", "them", "all",
}


def _tokens(text: str) -> set[str]:
    import re as _re
    return {w for w in _re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2 and w not in _STOP}


def discover_tools(query_text: str, *, mode: str = "action", limit: int = 12,
                   action_only: bool = False) -> list[dict]:
    """Rank tools from the FULL registry (incl. MCP) by relevance to query_text.
    Scores name + description token overlap. Returns the top `limit` tool dicts.
    In action mode, action tools are eligible; in planning mode they're excluded.
    When action_only is True, only action tools are returned (for the creative/
    'generate' discovery path that needs MCP action tools like Hiigsfield)."""
    try:
        from app.tools import registry
        tools = registry.list_tools()
    except Exception:  # noqa: BLE001
        return []
    q = _tokens(query_text)
    if not q:
        return []
    # --- Capability-driven steering (PRIMARY) --------------------------------
    # Infer which capability group(s) the task needs and build the live group
    # membership so the RIGHT-capability tools win before keyword scoring kicks
    # in. New tools auto-join groups via the registry, so this is future-proof.
    try:
        from app.tools import capabilities as _caps
        wanted_caps = _caps.capability_for_task(query_text)  # best-first
        cap_groups = _caps.build_capability_groups(tools)
    except Exception:  # noqa: BLE001
        wanted_caps, cap_groups = [], {}
    # Map tool name -> its best rank within any WANTED capability group (lower is
    # better). This becomes a strong primary boost.
    cap_rank: dict[str, int] = {}
    cap_primary: set[str] = set()
    for ci, cap in enumerate(wanted_caps):
        for rank, t in enumerate(cap_groups.get(cap, [])):
            n = t.get("name")
            if not n:
                continue
            cap_primary.add(n)
            # Earlier capability + earlier in-group rank = better (smaller).
            combined = ci * 100 + rank
            if n not in cap_rank or combined < cap_rank[n]:
                cap_rank[n] = combined

    # Is this task actually about 3D product design? Then Spline is the RIGHT
    # tool and must not be penalized. Otherwise (banner/video/ad/image) prefer
    # Hiigsfield-style general generation and push Spline/3D down.
    ql = (query_text or "").lower()
    wants_3d = any(k in ql for k in ("3d", "three-dimensional", "product design",
                                     "product model", "model a ", "3-d", "mesh", "render a product"))
    scored = []
    for t in tools:
        act = is_action_tool(t)
        if mode != "action" and act:
            continue
        if action_only and not act:
            continue
        name = t.get("name", "")
        desc = t.get("description", "") or ""
        name_toks = _tokens(name.replace("mcp_", "").replace("_", " "))
        desc_toks = _tokens(desc)
        score = 3 * len(q & name_toks) + len(q & desc_toks)
        # PRIMARY: capability-group membership for the wanted capability. A big
        # boost, scaled by how good a fit the tool is within the group, so the
        # right-capability tools lead and keyword overlap is only a tiebreaker.
        if name in cap_primary:
            score += 20 - min(cap_rank.get(name, 0), 15)
        low = (name + " " + desc).lower()
        is_3d_tool = any(p in low for p in ("spline", "3d_", "_3d", " 3d ", "3-d"))
        if wants_3d:
            # 3D product-design task → BOOST Spline/3D tools.
            if is_3d_tool:
                score += 6
        else:
            # Non-3D (banner/video/ad) → prefer general gen, demote 3D/HTML-setup.
            if any(b in name.lower() for b in ("ads_studio_generate", "generate_image",
                                               "generate_video", "generate_audio")):
                score += 5
            if is_3d_tool or any(p in low for p in ("pre-warm", "before authoring",
                                                    "html", "no file is open", "needs a file")):
                score -= 6
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:limit]]
