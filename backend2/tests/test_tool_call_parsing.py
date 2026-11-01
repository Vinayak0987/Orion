"""Regression tests for tool-call argument parsing.

Guards the "Missing required field: 'code'" class of failure: the model DID
provide the argument, just under a wrapper key (arguments/args/parameters) or in
a flat/bare-string shape the executor used to drop, leaving tool_input empty.
"""

from __future__ import annotations

import json

from app.missions.executor import (
    _extract_input,
    _parse_tool_call,
    _single_required_field,
)


def _call(obj: dict) -> dict:
    return _parse_tool_call(json.dumps(obj))


def test_canonical_input_key():
    got = _call({"tool": "code_interpreter", "input": {"code": "print(1)"}})
    assert got == {"tool": "code_interpreter", "input": {"code": "print(1)"}}


def test_alias_wrapper_keys_are_recovered():
    for key in ("arguments", "args", "parameters", "params", "tool_input"):
        got = _call({"tool": "code_interpreter", key: {"code": f"v-{key}"}})
        assert got["input"] == {"code": f"v-{key}"}, key


def test_flat_top_level_code_is_recovered():
    got = _call({"tool": "code_interpreter", "code": "top=4"})
    assert got["input"] == {"code": "top=4"}


def test_json_string_arguments_are_parsed():
    got = _call({"tool": "code_interpreter", "arguments": json.dumps({"code": "s=1"})})
    assert got["input"] == {"code": "s=1"}


def test_bare_string_input_marked_for_wrapping():
    # A bare (non-dict) payload for a single-field tool is tagged __raw__ and
    # later placed on the correct key by the executor using the tool schema.
    got = _call({"tool": "code_interpreter", "input": "print(2)"})
    assert got["input"] == {"__raw__": "print(2)"}
    assert _single_required_field("code_interpreter") == "code"


def test_extract_input_ignores_envelope_metadata():
    assert _extract_input({"tool": "x", "thought": "hi", "a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_non_tool_text_is_not_a_call():
    assert _parse_tool_call("just prose, no json") is None
