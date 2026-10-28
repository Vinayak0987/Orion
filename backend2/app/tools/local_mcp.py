"""Local MCP servers — self-contained, zero external setup.

These are themed bundles of Orion's own built-in tools, surfaced in the MCP
Servers page as ready-to-use "connected" servers. They need NO external account,
URL, or token: the server_url uses a `local://` scheme and dispatch runs the
underlying built-in tool in-process (see registry._dispatch_mcp).

Each registered tool is named `mcp_<server>_<tool>` and its config carries the
underlying built-in `impl` name, so the executor runs the real implementation.
"""

from __future__ import annotations

from app.tools import mcp as mcpstore
from app.tools import store as toolstore
from app.tools.base import REGISTRY, load_all

# Each server: slug, name, description, and the built-in tool names it bundles.
LOCAL_SERVERS = [
    {
        "slug": "filesystem",
        "name": "Filesystem Server",
        "description": "Read, write, search, and manage files in the agent workspace.",
        "tools": ["file_reader", "file_writer", "file_search", "directory_manager",
                  "file_metadata", "file_copy", "file_move", "file_delete"],
    },
    {
        "slug": "web",
        "name": "Web Toolkit Server",
        "description": "Search the web, scrape pages, read metadata, and call HTTP APIs.",
        "tools": ["web_search", "web_scraper", "web_crawler", "wikipedia_search",
                  "read_webpage_metadata", "http_request", "rss_reader"],
    },
    {
        "slug": "datalab",
        "name": "Data Lab Server",
        "description": "Transform, filter, aggregate, and analyze JSON/CSV data.",
        "tools": ["json_tool", "csv_tool", "yaml_tool", "data_filter", "data_sorter",
                  "data_aggregator", "data_grouping", "statistics_tool"],
    },
    {
        "slug": "knowledge",
        "name": "Knowledge Server",
        "description": "Search uploaded documents and the agent's long-term memory.",
        "tools": ["document_rag", "keyword_search", "chunk_retriever",
                  "memory_read", "memory_write", "memory_search"],
    },
    {
        "slug": "utility",
        "name": "Utility Belt Server",
        "description": "Everyday helpers: math, dates, ids, hashing, and summaries.",
        "tools": ["calculator", "scientific_calculator", "datetime_tool", "date_parser",
                  "uuid_generator", "hash_tool", "base64_tool", "text_summarizer"],
    },
]

LOCAL_PREFIX = "local://"


def _local_url(slug: str) -> str:
    return f"{LOCAL_PREFIX}{slug}"


def seed_local_mcp_servers() -> int:
    """Idempotent. Registers each local server + its tools (as type='mcp')."""
    load_all()  # ensure built-in impls are available
    count = 0
    for spec in LOCAL_SERVERS:
        url = _local_url(spec["slug"])
        # Only bundle tools that actually exist as built-ins.
        bundled = [t for t in spec["tools"] if t in REGISTRY]
        server_id = mcpstore.create_server(
            name=spec["name"], server_url=url, description=spec["description"],
            tool_count=len(bundled),
        )
        for impl in bundled:
            bt = REGISTRY[impl]
            local_name = f"mcp_{spec['slug']}_{impl}"
            toolstore.upsert_tool(
                name=local_name,
                display_name=bt.display_name,
                description=bt.description,
                type="mcp",
                category="mcp",
                input_schema=bt.input_schema,
                config={"server_url": url, "mcp_server_id": server_id,
                        "remote_name": impl, "impl": impl, "local": True},
            )
        count += 1
    return count
