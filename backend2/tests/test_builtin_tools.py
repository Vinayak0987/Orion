"""Contract + behaviour tests for the built-in tools pool.

The contract test runs across EVERY registered tool and asserts the universal
guarantees: safe_run always returns a dict and never raises, even on empty/bad
input. Per-category tests assert real behaviour for representative tools, all
offline (no network).
"""

from __future__ import annotations

import asyncio

import pytest

from app.tools.base import ToolContext, load_all


@pytest.fixture(scope="module")
def registry():
    return load_all()


def test_registry_has_expected_pool(registry):
    assert len(registry) >= 100, f"expected 100+ tools, got {len(registry)}"
    # Every tool has the required metadata.
    for name, bt in registry.items():
        assert bt.name == name
        assert bt.description and len(bt.description) > 10
        assert bt.category
        assert isinstance(bt.input_schema, dict)


def test_no_duplicate_names(registry):
    names = list(registry.keys())
    assert len(names) == len(set(names))


@pytest.mark.asyncio
async def test_contract_empty_input_never_raises(registry):
    """Every tool, called with {} and no context, returns a dict and does not raise.
    code_interpreter is disabled by default and must return an error dict (not raise)."""
    ctx = ToolContext()
    for name, bt in registry.items():
        result = await bt.safe_run({}, ctx)
        assert isinstance(result, dict), f"{name} did not return a dict"


@pytest.mark.asyncio
async def test_contract_bad_input_types_never_raise(registry):
    """Passing wrong-typed fields must degrade to {error}, never raise."""
    ctx = ToolContext()
    junk = {"query": 123, "text": None, "records": "notalist", "url": 42,
            "numbers": "x", "expression": {"nope": 1}, "path": 7}
    for name, bt in registry.items():
        result = await bt.safe_run(junk, ctx)
        assert isinstance(result, dict), f"{name} returned non-dict on junk input"


# -- Math --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calculator_safe_and_correct(registry):
    assert (await registry["calculator"].safe_run({"expression": "2+3*4"}, ToolContext()))["result"] == 14
    # Dangerous expression is blocked with an error, not executed.
    bad = await registry["calculator"].safe_run({"expression": "__import__('os').system('echo x')"}, ToolContext())
    assert "error" in bad


@pytest.mark.asyncio
async def test_statistics(registry):
    r = await registry["statistics_tool"].safe_run({"numbers": [1, 2, 3, 4, 5]}, ToolContext())
    assert r["mean"] == 3 and r["min"] == 1 and r["max"] == 5


@pytest.mark.asyncio
async def test_unit_converter(registry):
    r = await registry["unit_converter"].safe_run({"value": 1000, "from": "m", "to": "km"}, ToolContext())
    assert r["result"] == 1.0


# -- Text --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_regex_tool(registry):
    r = await registry["regex_tool"].safe_run(
        {"text": "a1 b2 c3", "pattern": r"\d", "mode": "findall"}, ToolContext())
    assert r["matches"] == ["1", "2", "3"]


@pytest.mark.asyncio
async def test_string_similarity(registry):
    r = await registry["string_similarity"].safe_run({"a": "kitten", "b": "kitten"}, ToolContext())
    assert r["score"] == 1.0


# -- Data --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_json_and_csv_roundtrip(registry):
    parsed = await registry["json_tool"].safe_run({"text": '{"x": [1,2,3]}', "mode": "parse"}, ToolContext())
    assert parsed["data"]["x"] == [1, 2, 3]
    recs = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv = await registry["csv_tool"].safe_run({"records": recs, "mode": "write"}, ToolContext())
    back = await registry["csv_tool"].safe_run({"text": csv["text"], "mode": "parse"}, ToolContext())
    assert back["count"] == 2


@pytest.mark.asyncio
async def test_data_filter_and_sort(registry):
    recs = [{"n": 3}, {"n": 1}, {"n": 2}]
    f = await registry["data_filter"].safe_run(
        {"records": recs, "where": {"n": {"op": "gt", "value": 1}}}, ToolContext())
    assert f["count"] == 2
    s = await registry["data_sorter"].safe_run({"records": recs, "by": "n"}, ToolContext())
    assert [r["n"] for r in s["records"]] == [1, 2, 3]


# -- Files (sandboxed) -------------------------------------------------------
@pytest.mark.asyncio
async def test_file_write_read_roundtrip_sandboxed(registry):
    ctx = ToolContext()
    w = await registry["file_writer"].safe_run({"path": "t/sample.txt", "content": "hello orion"}, ctx)
    assert w.get("bytes_written")
    r = await registry["file_reader"].safe_run({"path": "t/sample.txt"}, ctx)
    assert r["content"] == "hello orion"


@pytest.mark.asyncio
async def test_file_sandbox_escape_blocked(registry):
    r = await registry["file_reader"].safe_run({"path": "../../etc/passwd"}, ToolContext())
    # Re-anchored under the sandbox → simply not found, never reads the real file.
    assert "error" in r


# -- Utilities / DB ----------------------------------------------------------
@pytest.mark.asyncio
async def test_base64_roundtrip(registry):
    enc = await registry["base64_tool"].safe_run({"text": "orion", "mode": "encode"}, ToolContext())
    dec = await registry["base64_tool"].safe_run({"text": enc["result"], "mode": "decode"}, ToolContext())
    assert dec["result"] == "orion"


@pytest.mark.asyncio
async def test_url_parser(registry):
    r = await registry["url_parser"].safe_run({"url": "https://x.com/a?b=1"}, ToolContext())
    assert r["host"] == "x.com" and r["query"]["b"] == ["1"]


# -- code_interpreter enabled by default ------------------------------------
@pytest.mark.asyncio
async def test_code_interpreter_enabled_by_default(registry):
    r = await registry["code_interpreter"].safe_run({"code": "print('x')"}, ToolContext())
    # Should work without error (enabled by default now)
    assert "error" not in r
    assert r.get("stdout") == "x\n"
