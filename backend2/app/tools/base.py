"""Built-in tool framework.

Every built-in tool is a `BuiltinTool`. The contract is strict and uniform so
the whole pool behaves predictably and the Executor can trust it:

  • `run(tool_input, ctx)` MUST return a dict and MUST NOT raise. Any failure is
    caught and converted to `{"error": ..., "degraded": true}` by `safe_run`.
  • Bad/missing input returns `{"error": ...}` — never an exception.
  • Tools that need an optional dependency or an API key degrade gracefully:
    they return `{"error": ..., "degraded": true, "hint": "..."}` instead of
    crashing, and the mission continues on LLM knowledge alone.

Tools register themselves by instantiating with `register=True` (the helpers in
each builtins/* module do this). `REGISTRY` is the name→tool map the DB-backed
registry dispatches through.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

# name -> BuiltinTool
REGISTRY: dict[str, "BuiltinTool"] = {}

ToolFn = Callable[[dict, "ToolContext"], Any]


@dataclass
class ToolContext:
    """Runtime context passed to every tool.

    Carries the caller's API keys (for keyed tools), the acting user/agent/
    mission ids (for memory + sandboxing), and nothing else. Tools must not
    reach into global state beyond this + settings.
    """

    user_keys: dict | None = None
    user_id: str = "default-user"
    agent_id: str | None = None
    mission_id: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class BuiltinTool:
    name: str
    display_name: str
    description: str
    category: str
    fn: ToolFn
    input_schema: dict = field(default_factory=dict)
    requires_key: str | None = None
    degraded: bool = False  # registered but running in fallback/opt-in mode
    enabled_by_default: bool = True

    async def safe_run(self, tool_input: dict | None, ctx: ToolContext | None = None) -> dict:
        """Invoke the tool, guaranteeing a dict result and never raising."""
        ctx = ctx or ToolContext()
        tool_input = tool_input if isinstance(tool_input, dict) else {}
        try:
            result = self.fn(tool_input, ctx)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                return {"error": f"{self.name} returned a non-dict result", "degraded": True}
            return result
        except Exception as e:  # noqa: BLE001 — the whole point: never propagate
            return {"error": f"{self.name} failed: {e}", "degraded": True}


def tool(
    name: str,
    *,
    display_name: str | None = None,
    description: str,
    category: str = "utility",
    input_schema: dict | None = None,
    requires_key: str | None = None,
    degraded: bool = False,
    enabled_by_default: bool = True,
) -> Callable[[ToolFn], ToolFn]:
    """Decorator: register a function as a built-in tool.

    The wrapped function receives (tool_input: dict, ctx: ToolContext) and may be
    sync or async. It should return a dict. Returning/raising anything else is
    normalised by `safe_run`.
    """

    def decorate(fn: ToolFn) -> ToolFn:
        bt = BuiltinTool(
            name=name,
            display_name=display_name or name.replace("_", " ").title(),
            description=description,
            category=category,
            fn=fn,
            input_schema=input_schema or {},
            requires_key=requires_key,
            degraded=degraded,
            enabled_by_default=enabled_by_default,
        )
        if name in REGISTRY:
            raise ValueError(f"Duplicate built-in tool name: {name}")
        REGISTRY[name] = bt
        return fn

    return decorate


def load_all() -> dict[str, BuiltinTool]:
    """Import every builtins submodule so decorators populate REGISTRY. Idempotent."""
    import importlib
    import pkgutil

    from app.tools import builtins as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{pkg.__name__}.{mod.name}")
    return REGISTRY


# -- shared helpers used across tools ----------------------------------------

def ok(**data: Any) -> dict:
    return dict(data)


def err(message: str, *, degraded: bool = False, **extra: Any) -> dict:
    out = {"error": message}
    if degraded:
        out["degraded"] = True
    out.update(extra)
    return out


def need(tool_input: dict, *keys: str) -> str | None:
    """Return an error message if any required key is missing/empty, else None."""
    for k in keys:
        v = tool_input.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            return f"Missing required field: '{k}'"
    return None
