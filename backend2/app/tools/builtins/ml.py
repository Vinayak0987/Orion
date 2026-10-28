"""AI/ML built-in tools (LLM-powered) + a sandboxed code_interpreter.

The ML tools delegate the hard semantic work to the configured LLM (no numpy/
sklearn needed) and degrade to a safe heuristic/empty result if the LLM is
unavailable. forecasting_tool is pure statistics (linear trend).

code_interpreter runs Python in an isolated subprocess with:
  • a timeout, • captured stdout/stderr, • cwd = workspace sandbox,
  • DISABLED by default (settings.code_interpreter_enabled must be true).
It never uses exec() in-process — the child is a separate `python -I -S` process.
"""

from __future__ import annotations

import json

from app.config import settings
from app.llm.repair import extract_json
from app.tools.base import ToolContext, err, need, ok, tool


async def _llm(prompt: str, ctx: ToolContext, tier: str = "fast") -> str | None:
    try:
        from app.llm.client import LLMClient

        res = await LLMClient(user_keys=ctx.user_keys).call([{"role": "user", "content": prompt}], tier=tier)
        return (res.text or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


# --- 190. text_classifier (classification_tool) ------------------------------
@tool(
    "text_classifier",
    description="Classify text into one of the provided labels (zero-shot via LLM). Input: "
    "{text: str, labels: [str]}.",
    category="ml",
    input_schema={"text": {"type": "string", "required": True}, "labels": {"type": "array", "required": True}},
)
async def text_classifier(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    labels = ti.get("labels")
    if not isinstance(labels, list) or not labels:
        return err("'labels' must be a non-empty array")
    out = await _llm(f"Classify the text into exactly one of these labels: {labels}.\n"
                     f"Reply with ONLY the label.\n\nText: {ti['text'][:4000]}", ctx)
    if out:
        chosen = next((l for l in labels if l.lower() in out.lower()), out.strip())
        return ok(label=chosen, method="llm")
    # Fallback: keyword overlap with label names.
    tl = ti["text"].lower()
    scored = sorted(labels, key=lambda l: tl.count(l.lower()), reverse=True)
    return ok(label=scored[0], method="heuristic", degraded=True)


# --- 202. sentiment_analyzer -------------------------------------------------
@tool(
    "sentiment_analyzer",
    description="Analyze sentiment of text (positive/negative/neutral) with a short rationale. Input: {text: str}.",
    category="ml",
    input_schema={"text": {"type": "string", "required": True}},
)
async def sentiment_analyzer(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text")):
        return err(m)
    out = await _llm('Classify the sentiment of this text as positive, negative, or neutral. '
                     'Reply ONLY JSON: {"sentiment":"...","confidence":0..1}.\n\n' + ti["text"][:4000], ctx)
    if out:
        try:
            d = extract_json(out)
            if isinstance(d, dict) and d.get("sentiment"):
                return ok(sentiment=str(d["sentiment"]).lower(), confidence=d.get("confidence"), method="llm")
        except Exception:  # noqa: BLE001
            pass
    pos = sum(ti["text"].lower().count(w) for w in ("good", "great", "love", "excellent", "happy"))
    neg = sum(ti["text"].lower().count(w) for w in ("bad", "terrible", "hate", "poor", "sad", "awful"))
    s = "positive" if pos > neg else "negative" if neg > pos else "neutral"
    return ok(sentiment=s, method="heuristic", degraded=True)


# --- 26 (ml). translator -----------------------------------------------------
@tool(
    "translator",
    description="Translate text into a target language (via LLM). Input: {text: str, to: str (language), from?: str}.",
    category="ml",
    input_schema={"text": {"type": "string", "required": True}, "to": {"type": "string", "required": True}},
)
async def translator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "text", "to")):
        return err(m)
    out = await _llm(f"Translate the following text into {ti['to']}. Return ONLY the translation.\n\n{ti['text'][:5000]}", ctx)
    if out:
        return ok(translation=out, to=ti["to"], method="llm")
    return ok(translation=ti["text"], to=ti["to"], method="passthrough", degraded=True)


# --- 198. prompt_template ----------------------------------------------------
@tool(
    "prompt_template",
    description="Fill a prompt template with variables ({name} placeholders). Pure string formatting, "
    "no LLM. Input: {template: str, variables: object}.",
    category="ml",
    input_schema={"template": {"type": "string", "required": True}, "variables": {"type": "object"}},
)
def prompt_template(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "template")):
        return err(m)
    vars_ = ti.get("variables") or {}
    try:
        import string

        rendered = string.Template(ti["template"].replace("{", "${").replace("}", "}")).safe_substitute(vars_) \
            if False else ti["template"].format_map(_Default(vars_))
        return ok(prompt=rendered)
    except Exception as e:  # noqa: BLE001
        return err(f"prompt_template: {e}")


class _Default(dict):
    def __missing__(self, key):  # leave unknown placeholders intact
        return "{" + key + "}"


# --- 200. structured_output_generator ----------------------------------------
@tool(
    "structured_output_generator",
    description="Ask the LLM to extract/produce structured JSON matching a described shape. Input: "
    "{instruction: str, text?: str, schema_hint?: str}.",
    category="ml",
    input_schema={"instruction": {"type": "string", "required": True}, "text": {"type": "string"}},
)
async def structured_output_generator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "instruction")):
        return err(m)
    prompt = (f"{ti['instruction']}\n\nReturn ONLY valid JSON"
              + (f" matching: {ti['schema_hint']}" if ti.get("schema_hint") else "") + "."
              + (f"\n\nInput:\n{ti['text'][:5000]}" if ti.get("text") else ""))
    out = await _llm(prompt, ctx)
    if not out:
        return err("LLM unavailable", degraded=True, data=None)
    try:
        return ok(data=extract_json(out), method="llm")
    except Exception:  # noqa: BLE001
        return ok(data=None, raw=out, degraded=True, note="LLM did not return valid JSON")


# --- 201. output_quality_evaluator -------------------------------------------
@tool(
    "output_quality_evaluator",
    description="Score how well an output satisfies a task/criteria (LLM judge, 0-10 + rationale). "
    "Input: {task: str, output: str, criteria?: str}.",
    category="ml",
    input_schema={"task": {"type": "string", "required": True}, "output": {"type": "string", "required": True}},
)
async def output_quality_evaluator(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "task", "output")):
        return err(m)
    prompt = (f"Task: {ti['task']}\nCriteria: {ti.get('criteria') or 'accuracy, completeness, clarity'}\n"
              f"Output to evaluate:\n{ti['output'][:4000]}\n\n"
              'Reply ONLY JSON: {"score":0-10,"rationale":"..."}.')
    out = await _llm(prompt, ctx)
    if out:
        try:
            d = extract_json(out)
            if isinstance(d, dict):
                return ok(score=d.get("score"), rationale=d.get("rationale"), method="llm")
        except Exception:  # noqa: BLE001
            pass
    return err("LLM unavailable", degraded=True, score=None)


# --- 203. recommendation_tool ------------------------------------------------
@tool(
    "recommendation_tool",
    description="Recommend top items from a list for a goal/context (LLM-ranked). Input: "
    "{goal: str, items: [str], top?: int=3}.",
    category="ml",
    input_schema={"goal": {"type": "string", "required": True}, "items": {"type": "array", "required": True}},
)
async def recommendation_tool(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "goal")):
        return err(m)
    items = ti.get("items")
    if not isinstance(items, list) or not items:
        return err("'items' must be a non-empty array")
    top = int(ti.get("top") or 3)
    out = await _llm(f"Goal: {ti['goal']}\nItems: {items}\n"
                     f"Pick the {top} best items for the goal. Reply ONLY a JSON array of the chosen items.", ctx)
    if out:
        try:
            d = extract_json(out)
            if isinstance(d, list):
                return ok(recommendations=d[:top], method="llm")
        except Exception:  # noqa: BLE001
            pass
    return ok(recommendations=items[:top], method="passthrough", degraded=True)


# --- 204. forecasting_tool ---------------------------------------------------
@tool(
    "forecasting_tool",
    description="Forecast future values from a numeric series using linear trend (least squares). "
    "Input: {series: [number], periods?: int=3}.",
    category="ml",
    input_schema={"series": {"type": "array", "required": True}, "periods": {"type": "integer"}},
)
def forecasting_tool(ti: dict, ctx: ToolContext) -> dict:
    series = ti.get("series")
    if not isinstance(series, list) or len(series) < 2:
        return err("'series' must be an array of at least 2 numbers")
    ys = [v for v in series if isinstance(v, (int, float))]
    if len(ys) < 2:
        return err("series needs at least 2 numeric values")
    n = len(ys)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs) or 1e-9
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / denom
    intercept = my - slope * mx
    periods = int(ti.get("periods") or 3)
    forecast = [round(slope * (n + i) + intercept, 4) for i in range(periods)]
    return ok(forecast=forecast, slope=round(slope, 6), intercept=round(intercept, 6), method="linear_trend")


# --- code_interpreter --------------------------------------------------------
@tool(
    "code_interpreter",
    description="Execute a short Python script in a time-limited sandbox subprocess and return "
    "stdout/stderr. Matplotlib is available: any figures you create (plt.plot(...), etc.) are "
    "AUTOMATICALLY captured and returned as chart images — you do NOT need to call plt.savefig or "
    "plt.show. Always set a title and axis labels. DISABLED unless enabled in settings. Input: {code: str}.",
    category="code",
    input_schema={"properties": {"code": {"type": "string"}}, "required": ["code"]},
    enabled_by_default=True,
    degraded=False,
)
def code_interpreter(ti: dict, ctx: ToolContext) -> dict:
    if (m := need(ti, "code")):
        return err(m)
    if not settings.code_interpreter_enabled:
        return err("code_interpreter is disabled. Set CODE_INTERPRETER_ENABLED=true to allow it.",
                   degraded=True, hint="disabled by default for safety")
    import subprocess
    import sys
    import uuid
    from pathlib import Path

    # Per-run charts dir under the workspace (served at /charts/<file>).
    run_id = uuid.uuid4().hex[:12]
    charts_dir = Path(settings.workspace_dir) / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Harness: force a headless matplotlib backend, run the user's code, then
    # save every open figure as PNG. No savefig/show needed by the user.
    user_code = ti["code"]
    harness = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as _plt\n"
        "import json as _json, sys as _sys\n"
        "_CHART_PREFIX = " + repr(str(charts_dir / run_id)) + "\n"
        "def _orion_user_code():\n"
        + "\n".join("    " + ln for ln in user_code.splitlines()) + "\n"
        "try:\n"
        "    _orion_user_code()\n"
        "except Exception as _e:\n"
        "    import traceback as _tb; _tb.print_exc()\n"
        "_saved = []\n"
        "for _i, _num in enumerate(_plt.get_fignums()):\n"
        "    _fig = _plt.figure(_num)\n"
        "    _p = f'{_CHART_PREFIX}_{_i}.png'\n"
        "    _fig.savefig(_p, dpi=130, bbox_inches='tight', facecolor='white')\n"
        "    _saved.append(_p)\n"
        "_sys.stderr.write('\\n__ORION_CHARTS__=' + _json.dumps(_saved) + '\\n')\n"
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", harness],
            capture_output=True, text=True, timeout=settings.code_interpreter_timeout_seconds,
            cwd=str(settings.workspace_dir),
        )
    except subprocess.TimeoutExpired:
        return err(f"timed out after {settings.code_interpreter_timeout_seconds}s", degraded=True)
    except Exception as e:  # noqa: BLE001
        return err(f"code_interpreter: {e}", degraded=True)

    # Extract the saved chart paths from the sentinel line.
    import json as _json
    import re as _re
    stderr = proc.stderr
    images = []
    m2 = _re.search(r"__ORION_CHARTS__=(\[.*\])", stderr)
    if m2:
        stderr = stderr.replace(m2.group(0), "").strip()
        try:
            for p in _json.loads(m2.group(1)):
                name = Path(p).name
                images.append({"url": f"/charts/{name}", "filename": name})
        except Exception:  # noqa: BLE001
            pass
    return ok(stdout=proc.stdout[:10000], stderr=stderr[:4000],
              exit_code=proc.returncode, images=images)
