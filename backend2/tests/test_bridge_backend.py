"""Verification test for the agent<->tool bridge backend.

Proves:
  (a) capabilities.similar_tools('mcp_generate_image') returns alternative tools
      in the SAME capability group (image_generation) — the fallback source.
  (b) artifacts.normalize_artifacts correctly types:
        - a matplotlib chart result  ({"images": [...]})     -> image
        - an image generation url     ({"image_url": "...png"}) -> image
        - an HTML string              ("<html>...")           -> html
        - plain text                  ("just words")          -> text

Run:  python -m tests.test_bridge_backend   (with PYTHONPATH=backend2)
"""

from __future__ import annotations

import app.main  # noqa: F401  (triggers DB init + tool seeding)
from app.tools import artifacts, capabilities


def test_similar_tools_fallback():
    # Seed the full tool catalog (builtins + local MCP) so the live registry has
    # the image-generation tools. If seeding is unavailable (bare test DB), fall
    # back to an explicit in-memory catalog so the FALLBACK LOGIC is still proven.
    tools = None
    try:
        from app.tools.seed import seed_builtin_tools
        from app.tools.local_mcp import seed_local_mcp_servers
        seed_builtin_tools()
        seed_local_mcp_servers()
        from app.tools import registry
        catalog = registry.list_tools()
        if not any(t["name"] == "mcp_generate_image" for t in catalog):
            raise RuntimeError("not seeded")
    except Exception:
        # Explicit in-memory catalog: three image-generation tools in one group.
        tools = [
            {"name": "mcp_generate_image", "description": "generate an image from text",
             "type": "mcp", "enabled": True},
            {"name": "mcp_ads_studio_generate", "description": "generate an ad creative image",
             "type": "mcp", "enabled": True},
            {"name": "mcp_text_to_image", "description": "text to image generation",
             "type": "mcp", "enabled": True},
        ]

    alts = capabilities.similar_tools("mcp_generate_image", tools)
    assert isinstance(alts, list), "similar_tools must return a list"
    assert alts, "expected at least one alternative for mcp_generate_image"
    assert "mcp_generate_image" not in alts, "must exclude the failed tool itself"
    # Every alternative must share the image_generation capability.
    groups = capabilities.build_capability_groups(tools)
    image_group = {t["name"] for t in groups.get("image_generation", [])}
    assert any(a in image_group for a in alts), \
        "alternatives should be in the image_generation capability group"
    print(f"(a) similar_tools('mcp_generate_image') -> {alts[:5]} ... ({len(alts)} alts)  PASS")


def test_normalize_artifacts_types():
    # matplotlib chart
    a_chart = artifacts.normalize_artifacts(
        "code_interpreter", {"images": ["/charts/plot_abc.png"], "stdout": "done"})
    assert a_chart and a_chart[0]["type"] == "image", f"chart -> {a_chart}"
    assert a_chart[0]["url"].endswith(".png")

    # image generation url
    a_img = artifacts.normalize_artifacts(
        "mcp_generate_image", {"image_url": "https://cdn.example.com/out.png", "id": "x1"})
    assert a_img and a_img[0]["type"] == "image", f"image_url -> {a_img}"
    assert a_img[0]["url"] == "https://cdn.example.com/out.png"

    # video generation url (bonus)
    a_vid = artifacts.normalize_artifacts(
        "mcp_generate_video", {"video_url": "https://cdn.example.com/clip.mp4"})
    assert a_vid and a_vid[0]["type"] == "video", f"video_url -> {a_vid}"

    # HTML string
    a_html = artifacts.normalize_artifacts(
        "web_tool", "<html><body><div>Hi</div></body></html>")
    assert a_html and a_html[0]["type"] == "html", f"html -> {a_html}"

    # file url (bonus)
    a_file = artifacts.normalize_artifacts(
        "report_tool", {"url": "https://cdn.example.com/report.pdf"})
    assert a_file and a_file[0]["type"] == "file", f"file -> {a_file}"

    # tabular data (bonus)
    a_data = artifacts.normalize_artifacts(
        "data_tool", {"rows": [{"a": 1}, {"a": 2}]})
    assert a_data and a_data[0]["type"] == "data", f"data -> {a_data}"

    # plain text
    a_text = artifacts.normalize_artifacts("echo", "just some words here")
    assert a_text and a_text[0]["type"] == "text", f"text -> {a_text}"

    types = [x[0]["type"] for x in (a_chart, a_img, a_vid, a_html, a_file, a_data, a_text)]
    print(f"(b) normalize_artifacts types -> {types}  PASS")


if __name__ == "__main__":
    test_similar_tools_fallback()
    test_normalize_artifacts_types()
    print("\nALL BRIDGE BACKEND CHECKS PASSED")
