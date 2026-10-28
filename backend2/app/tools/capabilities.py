"""Capability registry — the backbone of the agent↔tool bridge.

Groups EVERY registered tool (built-in, MCP, integration, custom, API) by the
CAPABILITY it provides — i.e. *what it does*, not what server it came from. This
powers two things:

  1. Discovery — find the right tool for a task by capability, across all types.
  2. Fallback — if a tool fails (no credits, needs setup, bad account, invalid
     args after retry), try the NEXT tool in the SAME capability group.

It is derived LIVE from the registry on each call, so any newly-added tool
(a new MCP server, a new built-in, a new integration) is automatically slotted
into the correct capability group with no manual wiring — future-proof.
"""

from __future__ import annotations

import re

# --- Capability definitions --------------------------------------------------
# Each capability: keyword patterns matched against a tool's name + description.
# `priority` boosts tools whose NAME matches (strong signal) over description.
# `exclude` demotes tools that look similar but need heavy setup / are a poor
# general fit (e.g. 3D/Spline tools for a flat-image task).
#
# A tool can belong to multiple capabilities. Order within a group is by score
# (name match > desc match > generic), so fallback tries the best general tool
# first, then alternates.

CAPABILITIES: dict[str, dict] = {
    "image_generation": {
        "name_kw": ["generate_image", "generate_images", "image_generate", "create_image",
                    "ads_studio_generate", "text_to_image", "txt2img"],
        "desc_kw": ["generate an image", "create an image", "image from text", "ad creative",
                    "banner", "generate images", "image generation"],
        "exclude": ["3d", "spline", "pre-warm", "before authoring", "html", "edit_image", "upscale"],
    },
    "video_generation": {
        "name_kw": ["generate_video", "video_generate", "text_to_video", "create_video"],
        "desc_kw": ["generate a video", "create a video", "video from text", "video generation"],
        "exclude": ["edit", "trim", "subtitle"],
    },
    "audio_generation": {
        "name_kw": ["generate_audio", "text_to_speech", "tts", "generate_music", "generate_voice"],
        "desc_kw": ["generate audio", "text to speech", "voice over", "generate music"],
        "exclude": [],
    },
    "3d_design": {
        "name_kw": ["3d_generate", "generate_3d", "3d_model", "spline_create", "spline_open",
                    "3d_design", "model_3d"],
        "desc_kw": ["3d model", "3d product", "spline", "three-dimensional", "3d scene"],
        "exclude": [],
    },
    "web_search": {
        "name_kw": ["web_search", "search_web", "google_search", "bing_search", "serp",
                    "web_web_search", "wikipedia_search", "arxiv_search", "pubmed_search",
                    "search_news", "web_search_news", "search_docs", "duckduckgo"],
        "desc_kw": ["search the web", "web search", "current information", "search engine",
                    "search wikipedia", "search for", "look up", "find information online",
                    "news articles", "search results"],
        "exclude": ["image", "document_rag", "query_document", "keyword_search", "memory",
                    "asset", "folder", "template", "design", "model", "scene", "mention",
                    "citation", "history", "music"],
    },
    "web_scrape": {
        "name_kw": ["web_scraper", "scrape", "web_content_extractor", "crawl", "read_webpage",
                    "fetch_url", "http_request"],
        "desc_kw": ["scrape", "extract content from a web", "fetch a web page", "crawl"],
        "exclude": [],
    },
    "document_read": {
        "name_kw": ["document_rag", "query_document", "keyword_search", "chunk_retriever",
                    "document_reader", "pdf_reader", "read_document"],
        "desc_kw": ["uploaded document", "knowledge base", "read a document", "search documents"],
        "exclude": [],
    },
    "email_send": {
        "name_kw": ["gmail_send", "send_email", "email_send", "send_mail"],
        "desc_kw": ["send an email", "send email"],
        "exclude": [],
    },
    "code_execution": {
        "name_kw": ["code_interpreter", "run_code", "execute_python", "python_exec"],
        "desc_kw": ["execute python", "run a python script", "matplotlib", "chart", "plot"],
        "exclude": [],
    },
    "data_analysis": {
        "name_kw": ["data_aggregator", "statistics_tool", "csv_tool", "data_transformer",
                    "data_filter", "data_grouping", "calculator"],
        "desc_kw": ["aggregate data", "statistics", "analyze data", "csv"],
        "exclude": [],
    },
    "http_action": {
        "name_kw": ["http_action", "webhook_sender", "api_call", "post_request"],
        "desc_kw": ["http request that writes", "call an api", "webhook", "post to"],
        "exclude": [],
    },
    "translate": {
        "name_kw": ["translator", "translate"],
        "desc_kw": ["translate"],
        "exclude": [],
    },
    "summarize": {
        "name_kw": ["summarizer", "text_summarizer", "summarize"],
        "desc_kw": ["summarize"],
        "exclude": [],
    },
}


def _toks(s: str) -> str:
    return (s or "").lower()


def _score_tool_for_capability(tool: dict, cap: dict) -> int:
    """How well a tool fits a capability. 0 = not in this group."""
    name = _toks(tool.get("name", "")).replace("mcp_", "")
    desc = _toks(tool.get("description", ""))
    blob = name + " " + desc
    # Hard exclude.
    for ex in cap.get("exclude", []):
        if ex in blob:
            return 0
    score = 0
    for kw in cap.get("name_kw", []):
        if kw in name:
            score += 10
    for kw in cap.get("desc_kw", []):
        if kw in desc:
            score += 3
    return score


def classify_tool(tool: dict) -> list[str]:
    """Return every capability this tool provides (highest-scoring first)."""
    hits = []
    for cap_name, cap in CAPABILITIES.items():
        s = _score_tool_for_capability(tool, cap)
        if s > 0:
            hits.append((s, cap_name))
    hits.sort(reverse=True)
    return [c for _, c in hits]


def build_capability_groups(tools: list[dict] | None = None) -> dict[str, list[dict]]:
    """Live-group ALL registered tools by capability. Each group is ordered best
    tool first. Works across builtin / mcp / integration / custom / api types."""
    if tools is None:
        try:
            from app.tools import registry
            tools = registry.list_tools()
        except Exception:  # noqa: BLE001
            return {}
    groups: dict[str, list[tuple[int, dict]]] = {c: [] for c in CAPABILITIES}
    for t in tools:
        for cap_name, cap in CAPABILITIES.items():
            s = _score_tool_for_capability(t, cap)
            if s > 0:
                # Secondary ranking: prefer enabled, non-degraded, connected tools.
                bonus = 0
                if t.get("enabled", True):
                    bonus += 1
                if not t.get("degraded"):
                    bonus += 1
                groups[cap_name].append((s * 10 + bonus, t))
    out: dict[str, list[dict]] = {}
    for cap_name, lst in groups.items():
        lst.sort(key=lambda x: x[0], reverse=True)
        out[cap_name] = [t for _, t in lst]
    return out


def capability_for_task(text: str) -> list[str]:
    """Infer which capabilities a task text needs (best first). Used to steer
    discovery toward the right capability group(s)."""
    t = _toks(text)
    scored = []
    for cap_name, cap in CAPABILITIES.items():
        s = 0
        for kw in cap.get("name_kw", []):
            if kw.replace("_", " ") in t or kw in t:
                s += 3
        for kw in cap.get("desc_kw", []):
            if kw in t:
                s += 2
        # task-intent words
        if cap_name == "image_generation" and re.search(r"\b(image|banner|poster|logo|ad|advert|flyer|picture|graphic)\b", t):
            s += 4
        if cap_name == "video_generation" and re.search(r"\b(video|clip|reel|animation)\b", t):
            s += 4
        if cap_name == "3d_design" and re.search(r"\b(3d|three.?dimensional|product model|product design|mesh)\b", t):
            s += 6
        if cap_name == "code_execution" and re.search(r"\b(chart|plot|graph|matplotlib|visuali[sz])\b", t):
            s += 4
        if s > 0:
            scored.append((s, cap_name))
    scored.sort(reverse=True)
    return [c for _, c in scored]


def similar_tools(tool_name: str, tools: list[dict] | None = None) -> list[str]:
    """Other tools that provide the SAME capability as `tool_name` (for fallback).
    Returns names ordered best-alternative first, excluding the given tool."""
    groups = build_capability_groups(tools)
    caps_of_tool = set()
    for cap, lst in groups.items():
        if any(t.get("name") == tool_name for t in lst):
            caps_of_tool.add(cap)
    alts: list[str] = []
    for cap in caps_of_tool:
        for t in groups[cap]:
            n = t.get("name")
            if n and n != tool_name and n not in alts:
                alts.append(n)
    return alts
