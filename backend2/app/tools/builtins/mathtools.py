"""Math & Compute built-in tools (12).

Expression evaluation uses a safe AST walker — NO eval()/exec(). Only arithmetic,
comparisons, and a whitelist of math functions are permitted. All stdlib.
"""

from __future__ import annotations

import ast
import math
import operator
import random
import statistics
import time

from app.tools.base import ToolContext, err, need, ok, tool

_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin,
    "acos": math.acos, "atan": math.atan, "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "floor": math.floor, "ceil": math.ceil, "abs": abs, "round": round,
    "min": min, "max": max, "pow": pow, "factorial": math.factorial, "degrees": math.degrees,
    "radians": math.radians, "hypot": math.hypot,
}
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _safe_eval(expr: str, variables: dict | None = None) -> float:
    variables = variables or {}

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("only numeric constants allowed")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        if isinstance(node, ast.Name):
            if node.id in _CONSTS:
                return _CONSTS[node.id]
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"unknown name: {node.id}")
        raise ValueError(f"disallowed expression: {ast.dump(node)}")

    return ev(ast.parse(expr, mode="eval"))


# --- 111. calculator ---------------------------------------------------------
@tool(
    "calculator",
    description="Evaluate a basic arithmetic expression safely (no code execution). Input: {expression: str}.",
    category="math",
    input_schema={"expression": {"type": "string", "required": True}},
)
def calculator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "expression")):
        return err(m)
    try:
        return ok(result=_safe_eval(ti["expression"]))
    except Exception as e:  # noqa: BLE001
        return err(f"calculator: {e}")


# --- 112. scientific_calculator ----------------------------------------------
@tool(
    "scientific_calculator",
    description="Evaluate a scientific expression with functions (sqrt,sin,log,exp,...) and constants "
    "(pi,e). Input: {expression: str, variables?: {name: number}}.",
    category="math",
    input_schema={"expression": {"type": "string", "required": True}, "variables": {"type": "object"}},
)
def scientific_calculator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "expression")):
        return err(m)
    try:
        return ok(result=_safe_eval(ti["expression"], ti.get("variables")))
    except Exception as e:  # noqa: BLE001
        return err(f"scientific_calculator: {e}")


# --- 113. expression_evaluator -----------------------------------------------
@tool(
    "expression_evaluator",
    description="Evaluate an expression for a set of variable values. Input: {expression: str, "
    "variables: {name: number}}.",
    category="math",
    input_schema={"expression": {"type": "string", "required": True}, "variables": {"type": "object"}},
)
def expression_evaluator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "expression")):
        return err(m)
    try:
        return ok(result=_safe_eval(ti["expression"], ti.get("variables") or {}))
    except Exception as e:  # noqa: BLE001
        return err(f"expression_evaluator: {e}")


# --- 114. datetime_tool ------------------------------------------------------
@tool(
    "datetime_tool",
    description="Current date/time, add/subtract durations, or format. Input: "
    "{action?: now|add|format, timezone?: str, add_days?: int, add_hours?: int, base?: iso, format?: str}.",
    category="math",
    input_schema={"action": {"type": "string"}, "timezone": {"type": "string"}},
)
def datetime_tool(ti: dict, ctx: ToolContext) -> dict:
    import datetime as dt

    action = (ti.get("action") or "now").lower()
    tz = dt.UTC
    if ti.get("timezone"):
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(ti["timezone"])
        except Exception:  # noqa: BLE001
            return err(f"unknown timezone: {ti['timezone']}")
    base = dt.datetime.now(tz)
    if ti.get("base"):
        try:
            base = dt.datetime.fromisoformat(ti["base"])
        except Exception as e:  # noqa: BLE001
            return err(f"bad base datetime: {e}")
    if action in {"add", "subtract"}:
        delta = dt.timedelta(days=int(ti.get("add_days") or 0), hours=int(ti.get("add_hours") or 0),
                             minutes=int(ti.get("add_minutes") or 0))
        base = base - delta if action == "subtract" else base + delta
    if action == "format" and ti.get("format"):
        return ok(result=base.strftime(ti["format"]))
    return ok(iso=base.isoformat(), date=base.date().isoformat(), time=base.strftime("%H:%M:%S"),
              weekday=base.strftime("%A"), timestamp=base.timestamp())


# --- 115. date_parser --------------------------------------------------------
@tool(
    "date_parser",
    description="Parse a date/time string in almost any format into ISO 8601 (uses python-dateutil). "
    "Input: {text: str}.",
    category="math",
    input_schema={"text": {"type": "string", "required": True}},
)
def date_parser(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    try:
        from dateutil import parser as dparser

        d = dparser.parse(ti["text"])
        return ok(iso=d.isoformat(), date=d.date().isoformat(), year=d.year, month=d.month, day=d.day)
    except Exception as e:  # noqa: BLE001
        return err(f"could not parse date: {e}")


# --- 116. unit_converter -----------------------------------------------------
_UNITS = {
    "length": {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "ft": 0.3048,
               "in": 0.0254, "yd": 0.9144},
    "mass": {"kg": 1.0, "g": 0.001, "mg": 1e-6, "lb": 0.453592, "oz": 0.0283495, "t": 1000.0},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0, "ms": 0.001},
    "data": {"b": 1.0, "kb": 1024.0, "mb": 1024.0**2, "gb": 1024.0**3, "tb": 1024.0**4},
}


@tool(
    "unit_converter",
    description="Convert between units (length/mass/time/data, plus celsius<->fahrenheit). Input: "
    "{value: number, from: str, to: str}.",
    category="math",
    input_schema={"value": {"type": "number", "required": True}, "from": {"type": "string", "required": True},
                  "to": {"type": "string", "required": True}},
)
def unit_converter(ti: dict, ctx: ToolContext) -> dict:
    val, fr, to = ti.get("value"), (ti.get("from") or "").lower(), (ti.get("to") or "").lower()
    if not isinstance(val, (int, float)) or not fr or not to:
        return err("requires numeric 'value', 'from', 'to'")
    if {fr, to} <= {"c", "celsius", "f", "fahrenheit"}:
        if fr.startswith("c") and to.startswith("f"):
            return ok(result=val * 9 / 5 + 32)
        if fr.startswith("f") and to.startswith("c"):
            return ok(result=(val - 32) * 5 / 9)
        return ok(result=val)
    for family in _UNITS.values():
        if fr in family and to in family:
            return ok(result=val * family[fr] / family[to])
    return err(f"unknown or incompatible units: {fr} -> {to}")


# --- 117. statistics_tool ----------------------------------------------------
@tool(
    "statistics_tool",
    description="Descriptive statistics for a list of numbers (mean/median/mode/stdev/min/max/sum). "
    "Input: {numbers: [number]}.",
    category="math",
    input_schema={"numbers": {"type": "array", "required": True}},
)
def statistics_tool(ti: dict, ctx: ToolContext) -> dict:
    nums = ti.get("numbers")
    if not isinstance(nums, list) or not nums:
        return err("'numbers' must be a non-empty array")
    nums = [n for n in nums if isinstance(n, (int, float))]
    if not nums:
        return err("no numeric values")
    out = {"count": len(nums), "sum": sum(nums), "mean": statistics.mean(nums),
           "median": statistics.median(nums), "min": min(nums), "max": max(nums)}
    if len(nums) > 1:
        out["stdev"] = statistics.stdev(nums)
        out["variance"] = statistics.variance(nums)
    try:
        out["mode"] = statistics.mode(nums)
    except statistics.StatisticsError:
        out["mode"] = None
    return ok(**out)


# --- 118. probability_tool ---------------------------------------------------
@tool(
    "probability_tool",
    description="Basic probability helpers: combinations, permutations, factorial, simple event "
    "probability. Input: {action: combinations|permutations|factorial|probability, n?: int, k?: int, "
    "favorable?: int, total?: int}.",
    category="math",
    input_schema={"action": {"type": "string", "required": True}},
)
def probability_tool(ti: dict, ctx: ToolContext) -> dict:
    action = (ti.get("action") or "").lower()
    try:
        if action == "combinations":
            return ok(result=math.comb(int(ti["n"]), int(ti["k"])))
        if action == "permutations":
            return ok(result=math.perm(int(ti["n"]), int(ti["k"])))
        if action == "factorial":
            return ok(result=math.factorial(int(ti["n"])))
        if action == "probability":
            total = int(ti["total"])
            if total == 0:
                return err("total must be > 0")
            return ok(result=int(ti["favorable"]) / total)
        return err(f"unknown action: {action}")
    except (KeyError, ValueError) as e:
        return err(f"probability_tool: {e}")


# --- 119. formula_evaluator --------------------------------------------------
@tool(
    "formula_evaluator",
    description="Evaluate a named formula with variables (same safe evaluator as scientific_calculator). "
    "Input: {formula: str, variables: {name: number}}.",
    category="math",
    input_schema={"formula": {"type": "string", "required": True}, "variables": {"type": "object"}},
)
def formula_evaluator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "formula")):
        return err(m)
    try:
        return ok(result=_safe_eval(ti["formula"], ti.get("variables") or {}))
    except Exception as e:  # noqa: BLE001
        return err(f"formula_evaluator: {e}")


# --- 120. random_data_generator ----------------------------------------------
@tool(
    "random_data_generator",
    description="Generate random data: integers, floats, choices, uuid list, or a shuffled range. "
    "Input: {kind: int|float|choice|shuffle, count?: int, min?: number, max?: number, options?: [any]}.",
    category="math",
    input_schema={"kind": {"type": "string", "required": True}, "count": {"type": "integer"}},
)
def random_data_generator(ti: dict, ctx: ToolContext) -> dict:
    kind = (ti.get("kind") or "int").lower()
    count = min(int(ti.get("count") or 1), 1000)
    try:
        if kind == "int":
            lo, hi = int(ti.get("min", 0)), int(ti.get("max", 100))
            return ok(values=[random.randint(lo, hi) for _ in range(count)])
        if kind == "float":
            lo, hi = float(ti.get("min", 0.0)), float(ti.get("max", 1.0))
            return ok(values=[random.uniform(lo, hi) for _ in range(count)])
        if kind == "choice":
            opts = ti.get("options") or []
            if not opts:
                return err("'options' required for choice")
            return ok(values=[random.choice(opts) for _ in range(count)])
        if kind == "shuffle":
            opts = list(ti.get("options") or list(range(count)))
            random.shuffle(opts)
            return ok(values=opts)
        return err(f"unknown kind: {kind}")
    except Exception as e:  # noqa: BLE001
        return err(f"random_data_generator: {e}")


# --- 121. benchmark_timer ----------------------------------------------------
@tool(
    "benchmark_timer",
    description="Return a high-resolution timestamp, or elapsed time since a provided start. Input: "
    "{start?: number (perf_counter value)}.",
    category="math",
    input_schema={"start": {"type": "number"}},
)
def benchmark_timer(ti: dict, ctx: ToolContext) -> dict:
    now = time.perf_counter()
    if isinstance(ti.get("start"), (int, float)):
        return ok(now=now, elapsed_seconds=round(now - ti["start"], 6))
    return ok(now=now, note="pass this value back as 'start' to measure elapsed time")


# --- 122. number_formatter ---------------------------------------------------
@tool(
    "number_formatter",
    description="Format a number: thousands separators, fixed decimals, percent, or currency. Input: "
    "{value: number, style?: plain|percent|currency, decimals?: int, currency?: str}.",
    category="math",
    input_schema={"value": {"type": "number", "required": True}, "style": {"type": "string"}},
)
def number_formatter(ti: dict, ctx: ToolContext) -> dict:
    val = ti.get("value")
    if not isinstance(val, (int, float)):
        return err("'value' must be numeric")
    dec = int(ti.get("decimals", 2))
    style = (ti.get("style") or "plain").lower()
    if style == "percent":
        return ok(result=f"{val * 100:.{dec}f}%")
    if style == "currency":
        sym = {"usd": "$", "eur": "€", "gbp": "£", "inr": "₹"}.get((ti.get("currency") or "usd").lower(), "")
        return ok(result=f"{sym}{val:,.{dec}f}")
    return ok(result=f"{val:,.{dec}f}")
