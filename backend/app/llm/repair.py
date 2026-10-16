"""JSON repair for structured LLM calls.

LLMs occasionally wrap JSON in markdown fences or add prose. This extracts the
JSON robustly before giving up.
"""

from __future__ import annotations

import json
import re
from typing import Any

_CODE_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```", re.IGNORECASE)
_FIRST_JSON = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


class JSONParseError(RuntimeError):
    """All repair strategies failed."""


def extract_json(text: str) -> Any:
    """Best-effort parse of a JSON value from raw LLM text.

    Order: direct parse → fenced code block → first {...}/[...] span.
    Raises JSONParseError if none succeed.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = _CODE_BLOCK.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m = _FIRST_JSON.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    raise JSONParseError(f"Could not extract JSON from: {text[:200]}")
