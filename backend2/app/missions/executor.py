"""The Executor — runs one task through an agent using a ReAct loop.

The agent is prompted to either (a) emit a JSON tool call, or (b) give a final
prose answer. The executor parses each LLM reply: if it is a tool call, it
dispatches the tool and feeds the result back; otherwise the task is done.

Every LLM call and tool call is logged to execution_traces. The loop is capped
at settings.max_task_steps to prevent runaway tool-calling.
"""

from __future__ import annotations

import json

from app.agents.store import create_agent, get_agent
from app.config import settings
from app.llm.client import LLMClient
from app.llm.repair import extract_json
from app.tools import registry
from app.traces import store as traces


def _tier_for(agent: dict) -> str:
    model = agent.get("model", "")
    # 70b / reasoning-class models → reasoning tier; else fast.
    return "reasoning" if "70b" in model or "reasoning" in model else "fast"


def _parse_tool_call(text: str) -> dict | None:
    """If the reply is (or contains) a tool-call JSON object, return it. Else None."""
    stripped = text.strip()
    if "{" not in stripped:
        return None

    # 1) Try the whole/standard extraction first.
    try:
        obj = extract_json(stripped)
        if isinstance(obj, dict) and "tool" in obj:
            return {"tool": obj["tool"], "input": obj.get("input", {})}
    except Exception:  # noqa: BLE001
        pass

    # 2) Robust fallback: scan every BALANCED {...} span and return the first one
    #    that parses to an object with a "tool" key. This handles trailing stray
    #    braces, surrounding prose, or a tool call embedded mid-text (the common
    #    weak-model failure where the JSON "leaks" into the answer).
    for candidate in _balanced_objects(stripped):
        try:
            o = json.loads(candidate)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(o, dict) and "tool" in o:
            return {"tool": o["tool"], "input": o.get("input", {})}
    return None


def _balanced_objects(text: str):
    """Yield each top-level balanced {...} substring, in order."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    yield text[start:i + 1]
                    start = -1


# --- Capability-group fallback ------------------------------------------------
# A tool result is "unusable" (the tool exists but can't do the job here) when it
# matches one of these patterns — NOT a normal task failure. On a match we try
# the next tool in the same capability group instead of giving up.
import re as _re  # noqa: E402

_UNUSABLE_PATTERNS = [
    r"not enough credits", r"no_?credits", r"insufficient credits", r"out of credits",
    r"quota (?:exceeded|exhausted)", r"rate.?limit",
    r"account isn.?t created", r"account not created", r"no account",
    r"not provisioned", r"not configured", r"needs setup", r"setup required",
    r"needs a file", r"no \w+ is open", r"create one \w+ first", r"before authoring",
    r"invalid arguments?", r"validation error", r"invalid input", r"schema",
    r"not found", r"\b404\b", r"does not exist",
    r"disabled", r"coming soon", r"not available", r"unavailable",
    r"unauthorized", r"\b401\b", r"forbidden", r"\b403\b",
    r"no server_url", r"has no implementation", r"unsupported tool type",
]
_UNUSABLE_RE = _re.compile("|".join(_UNUSABLE_PATTERNS), _re.IGNORECASE)

# "invalid arguments / validation error" is only treated as unusable AFTER one
# retry (give the model a chance to fix its own args first).
_ARG_ERROR_RE = _re.compile(r"invalid arguments?|validation error|invalid input|schema", _re.IGNORECASE)


def _unusable_reason(tool_result: dict, already_retried_args: bool = False) -> str | None:
    """If the tool result looks 'tool-unusable', return a short reason; else None."""
    if not isinstance(tool_result, dict):
        return None
    if "error" not in tool_result:
        return None
    blob = ""
    for k in ("error", "message", "detail"):
        v = tool_result.get(k)
        if isinstance(v, str):
            blob += " " + v
    blob = blob.strip()
    if not blob:
        blob = str(tool_result.get("error", ""))
    m = _UNUSABLE_RE.search(blob)
    if not m:
        return None
    # Arg/validation errors: only count as "unusable" after a retry.
    if _ARG_ERROR_RE.search(m.group(0)) and not already_retried_args:
        return None
    return blob[:160]


def _max_fallbacks() -> int:
    return 3



def _effective_tools(agent: dict, task: dict, mission: dict | None = None) -> list[str]:
    """The tools an agent may use for THIS task = its own allowlist UNION the
    tools the planner marked the task as needing. In ACTION mode, agents also
    get the registered ACTION tools (gated by the approval flow) so they can
    actually perform real-world actions; in Planning mode they do not."""
    tools = list(agent.get("tools", []) or [])
    for t in (task.get("tools_needed") or []):
        if t not in tools:
            tools.append(t)
    # Knowledge read tools are always available — they're read-only and let any
    # agent use uploaded/attached documents (query_document = lazy, type-aware).
    for t in ("query_document", "document_rag", "list_documents"):
        if t not in tools:
            tools.append(t)
    # code_interpreter is always available for data analysis and visualization
    if "code_interpreter" not in tools:
        tools.append("code_interpreter")
    if mission and mission.get("mode", "action") == "action":
        # Core built-in action tools are always offered.
        core_actions = ["gmail_send", "http_action"]
        for t in core_actions:
            if t not in tools:
                tools.append(t)
        # Relevance-based discovery: pull the task-relevant ACTION tools from the
        # FULL registry (incl. the 290 MCP tools like Hiigsfield/fal) by matching
        # the task title + subtask + the mission goal — this is the agent↔tool
        # bridge for actions (replaces the brittle title-word overlap).
        try:
            from app.tools import modes as _tmodes
            query = " ".join(str(x) for x in (
                task.get("title"), task.get("subtask"), task.get("description"),
                (mission or {}).get("prompt"),
            ) if x)
            for t in _tmodes.discover_tools(query, mode="action", limit=8, action_only=True):
                if t["name"] not in tools:
                    tools.append(t["name"])
        except Exception:  # noqa: BLE001
            pass
    return tools


def _build_messages(agent: dict, task: dict, context: dict, memory: str = "", mission: dict | None = None) -> list[dict]:
    tools = _effective_tools(agent, task, mission)

    def _schema_hint(t: dict) -> str:
        """A compact arg hint from the tool's input_schema so the agent calls it
        with the RIGHT arguments (critical for MCP tools with strict schemas).
        Handles both JSON Schema format (properties/required) and flat format."""
        sch = t.get("input_schema") or {}
        # Check if it's JSON Schema format (has properties)
        if "properties" in sch:
            props = sch.get("properties") or {}
            required = set(sch.get("required") or [])
            parts = []
            for pname, pdef in list(props.items())[:8]:
                pdef = pdef if isinstance(pdef, dict) else {}
                ptype = pdef.get("type") or ("object" if "properties" in pdef else
                                             "any" if "anyOf" in pdef else "")
                desc = (pdef.get("description") or "")[:50]
                flag = "*" if pname in required else ""
                parts.append(f"{pname}{flag}" + (f"({ptype})" if ptype else "") + (f": {desc}" if desc else ""))
            return "  args: {" + "; ".join(parts) + "}  (*=required)"
        # Handle flat format: {"field": {"type": "string", "required": True}}
        props = sch if isinstance(sch, dict) else {}
        if not props:
            return ""
        parts = []
        for pname, pdef in list(props.items())[:8]:
            pdef = pdef if isinstance(pdef, dict) else {}
            ptype = pdef.get("type") or "any"
            is_required = pdef.get("required", False)
            flag = "*" if is_required else ""
            parts.append(f"{pname}{flag}({ptype})")
        return "  args: {" + "; ".join(parts) + "}  (*=required)"

    # Full tool records (name + description + input_schema + type + category) so
    # we can show the capability tag and, for MCP tools, the FULL description.
    from app.tools import capabilities

    records = {r["name"]: r for r in registry.list_tools(full=True) if r["name"] in tools}

    def _cap_tag(rec: dict) -> str:
        caps = capabilities.classify_tool(rec)
        return f"  [cap: {caps[0]}]" if caps else ""

    def _desc_for(rec: dict) -> str:
        desc = rec.get("description") or ""
        # MCP tools have strict schemas + nuanced behaviour → give the FULL
        # description so the agent calls them correctly. Others stay compact.
        if rec.get("type") == "mcp":
            return desc[:400]
        return desc[:140]

    tool_lines = "\n".join(
        f"- {rec['name']}{_cap_tag(rec)}: {_desc_for(rec)}{_schema_hint(rec)}"
        for name, rec in records.items()
    ) or "(no tools available — rely on your own knowledge)"

    context_block = ""
    if context:
        context_block = "\n\nResults from previous tasks:\n" + json.dumps(context, indent=2)[:4000]

    memory_block = f"\n\n{memory}" if memory else ""

    tool_instruction = (
        "\n\nTo use a tool, reply with ONLY this JSON (no other text):\n"
        '{"tool": "<tool_name>", "input": { ... }}\n'
        "Use a tool whenever it would improve accuracy (e.g. web_search for current "
        "facts, document_rag for uploaded docs). After a tool returns, either call "
        "another tool or give your FINAL answer as normal prose (no JSON).\n"
        "If the task asks for a chart, plot, graph, or any visualization, you MUST call "
        "the code_interpreter tool with Python matplotlib code (set a title and axis labels). "
        "Do NOT describe a chart in words instead of generating it — the image is required.\n"
        "If the task is to GENERATE or CREATE something (an image, banner, ad, video, logo, "
        "design, website, etc.) and a matching tool is listed above (e.g. a tool whose name "
        "contains 'generate', 'image', 'ads_studio', 'create'), you MUST call that tool to "
        "actually produce it. Do NOT fall back to web_search or just describe it in words — "
        "call the real generation tool with the exact brand, product, offer and price from the task.\n"
        "CRITICAL: use the EXACT values from the task — real email addresses, "
        "subjects, names, URLs and body text VERBATIM. NEVER substitute placeholders "
        'like "user@example.com", "Test Email", or "example.com".\n'
        "If the task refers to any file, dataset, document, or data that may have been uploaded "
        "(including CSV, Excel, PDF, text files, or data from Drive/OneDrive), first call "
        "list_documents to discover what files are available and get their document_id. "
        "Then use query_document with that document_id to retrieve the data. For CSV/Excel files, "
        "this returns complete rows with all columns intact; for PDF/text, it returns relevant passages."
    ) if tools and tool_lines.startswith("-") else ""

    orig = (mission or {}).get("prompt", "")
    orig_block = f"\n\nORIGINAL USER REQUEST (use its exact details verbatim):\n{orig}" if orig else ""

    user = (
        f"Available tools:\n{tool_lines}{tool_instruction}{memory_block}{context_block}{orig_block}\n\n"
        f"Your task: {task['title']}\n\n"
        "Work step by step. Call tools as needed, then give your final answer."
    )
    return [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": user},
    ]


async def run_task(agent_id: str, task: dict, context: dict, mission: dict, emit) -> dict:
    agent = get_agent(agent_id)
    if agent is None:
        return {"summary": "Agent not found", "error": f"no agent {agent_id}"}

    # DEPARTMENT HEAD: decompose + delegate to specialists (built dynamically).
    if task.get("_delegate_head") and task.get("_department_id"):
        return await _run_department_head(agent, task, context, mission, emit)

    # MASTER agent with a sub-agent pipeline → sequential orchestration.
    sub_agents = agent.get("sub_agents") or []
    if sub_agents:
        return await _run_pipeline(agent, sub_agents, task, context, mission, emit)
    return await _run_single(agent, agent_id, task, context, mission, emit)


# Capability → relevant tool CATEGORIES. Specialists get a real, capability-
# appropriate slice of the full tool catalog (not a hardcoded pair), so e.g. an
# analysis agent gets data+math tools, a research agent gets web+knowledge, etc.
_CAP_CATEGORIES = {
    "research":   ["web", "knowledge", "text"],
    "marketing":  ["web", "knowledge", "text", "ml"],
    "writing":    ["text", "knowledge", "ml"],
    "analysis":   ["data", "math", "knowledge", "ml"],
    "finance":    ["data", "math", "knowledge"],
    "operations": ["web", "knowledge", "data", "utility"],
    "general":    ["web", "knowledge", "text", "data"],
}
# Always-useful core tools every specialist should have.
_CORE_TOOLS = ["web_search", "document_rag", "query_document"]
# Cap how many tools a specialist is given (too many overwhelms a small model).
_MAX_SPECIALIST_TOOLS = 12


def _tools_for_capability(capability: str) -> list[str]:
    """Pick a capability-appropriate set of REAL tools from the registry by
    category (round-robin across categories for a balanced mix), instead of a
    hardcoded pair. Focused (<=12), excludes the huge MCP bucket."""
    cats = _CAP_CATEGORIES.get(capability, _CAP_CATEGORIES["general"])
    picked: list[str] = list(_CORE_TOOLS)
    try:
        from app.tools import store as _tstore
        per_cat = {cat: [t["name"] for t in _tstore.list_tools(category=cat, enabled=True)
                         if not t["name"].startswith("mcp_")] for cat in cats}
        # Round-robin: take one from each category in turn until full.
        idx = 0
        while len(picked) < _MAX_SPECIALIST_TOOLS:
            progressed = False
            for cat in cats:
                lst = per_cat.get(cat, [])
                if idx < len(lst):
                    name = lst[idx]
                    if name not in picked:
                        picked.append(name)
                    progressed = True
                    if len(picked) >= _MAX_SPECIALIST_TOOLS:
                        break
            if not progressed:
                break
            idx += 1
    except Exception:  # noqa: BLE001
        pass
    return picked


async def _run_department_head(head: dict, task: dict, context: dict, mission: dict, emit) -> dict:
    """The department Head decomposes a task into subtasks and delegates each to
    a department specialist — REUSING an eligible existing member or DYNAMICALLY
    creating one. Bounded by max_delegation_fanout/depth. Reuses _run_single."""
    from app.departments import store as dept_store

    depth = int(task.get("_depth", 0))
    dept_id = task["_department_id"]
    dept = dept_store.get_department(dept_id)
    dept_name = dept["name"] if dept else dept_id
    await emit("head_planning", task_id=task["id"], department_id=dept_id,
               department_name=dept_name, head=head.get("name"), agent_id=head["id"])

    if depth >= settings.max_delegation_depth:
        return await _run_single(head, head["id"], task, context, mission, emit)

    # Ask the Head to break the task into specialist subtasks.
    plan_prompt = (
        f"You are the head of the {dept_name} department. Break the task into at most "
        f"{settings.max_delegation_fanout} focused subtasks, each handled by ONE specialist. "
        f'Return STRICT JSON: a list of {{"role":"<specialist role, e.g. SEO Specialist>", '
        f'"capability":"<one of: research|marketing|writing|analysis|finance|operations|general>", '
        f'"subtask":"<what they must do>"}}.\n\nTask: {task["title"]}\n\nReturn ONLY the JSON array.'
    )
    llm = LLMClient(user_keys=mission.get("user_keys"))
    try:
        plan = await llm.call_structured(plan_prompt, tier=_tier_for(head))
    except Exception:  # noqa: BLE001
        plan = None
    subtasks = plan if isinstance(plan, list) else []
    if not subtasks:
        # Head couldn't decompose → handle directly.
        return await _run_single(head, head["id"], task, context, mission, emit)

    user_id = mission.get("created_by") or "default-user"
    existing = {m["agent_type"]: m for m in dept_store.list_members(dept_id, status="active")
                if m.get("role") != "head"}
    results: list[dict] = []
    pipeline_ctx = dict(context or {})
    delegated = 0

    for i, st in enumerate(subtasks):
        if delegated >= settings.max_delegation_fanout or not isinstance(st, dict):
            break
        cap = str(st.get("capability") or "general").lower()
        if cap not in _CAP_CATEGORIES:
            cap = "general"
        role = (st.get("role") or f"{cap.title()} Specialist").strip()[:80]
        subtask = st.get("subtask") or task["title"]

        # Reuse a matching active specialist, else dynamically create one.
        member = existing.get(cap)
        reused = member is not None
        if reused:
            spec_id = member["agent_id"]
            spec = get_agent(spec_id)
        else:
            _spec_tools = _tools_for_capability(cap)
            spec_id = create_agent(
                name=role, role_title=role, agent_type=cap,
                purpose=f"{role} in the {dept_name} department.",
                system_prompt=(
                    f"You are a {role} in the {dept_name} department. Do your assigned subtask "
                    "precisely and thoroughly, using tools for evidence. Report a clear result."
                ),
                tools=_spec_tools, model="groq:openai/gpt-oss-20b",
                department_id=dept_id, created_by=user_id,
                origin="specialist", source_mission_id=mission["id"],
            )
            dept_store.add_member(dept_id, spec_id, role="specialist", instructions=role)
            existing[cap] = {"agent_id": spec_id, "agent_type": cap}
            spec = get_agent(spec_id)
            await emit("specialist_created", task_id=task["id"], department_id=dept_id,
                       agent_id=spec_id, name=role, capability=cap, tools=_spec_tools)

        if spec is None:
            continue
        sub_task = {"id": f"{task['id']}-d{i+1}", "title": subtask,
                    "agent_type": cap, "_depth": depth + 1}
        await emit("specialist_started", task_id=task["id"], agent_id=spec_id,
                   name=spec.get("name"), capability=cap, reused=reused, subtask=subtask[:160])
        res = await _run_single(spec, spec_id, sub_task, pipeline_ctx, mission, emit)
        out = res.get("data") or res.get("summary") or ""
        await emit("specialist_done", task_id=task["id"], agent_id=spec_id,
                   name=spec.get("name"), success="error" not in res)
        results.append({"role": role, "capability": cap, "subtask": subtask,
                        "output": out, "error": res.get("error")})
        pipeline_ctx[f"{role}"] = out[:1500]
        delegated += 1

    if not results:
        return await _run_single(head, head["id"], task, context, mission, emit)

    # Head synthesizes the specialists' outputs.
    synth_input = "\n\n".join(
        f"### {r['role']} — {r['subtask']}\n{(r['error'] and ('FAILED: ' + r['error'])) or r['output']}"
        for r in results)
    synth_prompt = (
        f"You are the {dept_name} department head. Consolidate your specialists' results into a "
        f"single, coherent final answer for: {task['title']}\n\nSpecialist outputs:\n{synth_input}\n\n"
        "Produce the final departmental result. Note any failures honestly.")
    try:
        synth = await llm.call(
            [{"role": "system", "content": head["system_prompt"]},
             {"role": "user", "content": synth_prompt}],
            tier=_tier_for(head), temperature=head.get("temperature", 0.7))
        traces.record_llm(mission["id"], task["id"], head["id"], provider=synth.provider,
                          model=synth.model, input_tokens=synth.input_tokens,
                          output_tokens=synth.output_tokens, cost_usd=synth.cost_usd,
                          latency_ms=synth.latency_ms, success=True)
        final = synth.text.strip() or synth_input
    except Exception:  # noqa: BLE001
        final = synth_input
    await emit("head_done", task_id=task["id"], department_id=dept_id,
               specialists=len(results), success=not any(r["error"] for r in results))
    return {"summary": final[:500], "data": final, "delegation": results, "department_id": dept_id}



async def _run_pipeline(master: dict, sub_agents: list[dict], task: dict, context: dict,
                        mission: dict, emit) -> dict:
    """Run a master agent's sub-agents in order, piping each step's output into
    the next step's input. Each sub-agent is constrained to its OWN tools."""
    ordered = sorted(sub_agents, key=lambda s: s.get("order", 0))
    master_id = master["id"]
    prev_output = ""                     # feeds the next step's input
    step_results: list[dict] = []
    pipeline_ctx = dict(context or {})   # accumulates every step output

    await emit("pipeline_start", task_id=task["id"], agent_id=master_id,
               steps=[s.get("name") for s in ordered])

    for idx, sub in enumerate(ordered):
        step_name = sub.get("name") or f"Step {idx + 1}"
        # Build a synthetic agent for this sub-agent: its own tools + prompt,
        # inheriting the master's model/temperature/type.
        sub_prompt = sub.get("system_prompt") or (
            f"You are '{step_name}', one step in a pipeline. Role: {sub.get('role', '')}. "
            f"You receive: {sub.get('input', 'the previous step output')}. "
            f"You must produce: {sub.get('output', 'a result for the next step')}."
        )
        sub_agent = {
            "id": master_id,                       # traces attribute to the master
            "name": step_name,
            "system_prompt": sub_prompt,
            "agent_type": master.get("agent_type", "general"),
            "tools": sub.get("tools", []),
            "model": master.get("model"),
            "temperature": master.get("temperature", 0.7),
            "memory_enabled": master.get("memory_enabled"),
            "memory_ttl_days": master.get("memory_ttl_days"),
        }
        # The step's task: original goal + what the previous step produced.
        step_title = (
            f"{task['title']}\n\nYour specific job ({step_name}): {sub.get('role', '')}\n"
            f"Expected input: {sub.get('input', '')}\n"
            f"Expected output: {sub.get('output', '')}"
        )
        if prev_output:
            step_title += f"\n\nInput from the previous step:\n{prev_output[:3000]}"
        step_task = {"id": f"{task['id']}-s{idx + 1}", "title": step_title,
                     "agent_type": sub_agent["agent_type"]}

        await emit("step_start", task_id=task["id"], step=step_name, order=idx + 1)
        result = await _run_single(sub_agent, master_id, step_task, pipeline_ctx, mission, emit)
        out = result.get("data") or result.get("summary") or ""
        await emit("step_done", task_id=task["id"], step=step_name, order=idx + 1,
                   success="error" not in result)

        step_results.append({"step": step_name, "order": idx + 1,
                             "output": out, "error": result.get("error")})
        pipeline_ctx[f"step_{idx + 1}_{step_name}"] = out[:2000]
        prev_output = out
        if result.get("error"):
            # Stop the pipeline on a hard failure but return what we have.
            await emit("pipeline_done", task_id=task["id"], agent_id=master_id, success=False)
            return {"summary": f"Pipeline stopped at '{step_name}': {result['error']}",
                    "error": result["error"], "steps": step_results}

    await emit("pipeline_done", task_id=task["id"], agent_id=master_id, success=True)
    final = prev_output or "Pipeline produced no output."
    return {"summary": final[:500], "data": final, "steps": step_results}


async def _maybe_spawn_subagents(specialist: dict, spec_id: str, task: dict, context: dict,
                                 mission: dict, emit) -> dict | None:
    """A specialist decides whether its task needs breaking into SUBAGENTS. If so,
    it dynamically creates focused subagents, runs them, and synthesizes. Returns
    the synthesized result, or None if the task is simple (→ normal ReAct loop)."""
    depth = int(task.get("_depth", 0))
    llm = LLMClient(user_keys=mission.get("user_keys"))
    decide_prompt = (
        f"You are '{specialist.get('name')}'. Decide if this task is COMPLEX enough to split "
        f"into 2-3 smaller independent sub-steps, each done by a focused subagent. "
        f'Return STRICT JSON: {{"split": <true|false>, "subagents": [{{"name":"<short>", '
        f'"capability":"<research|writing|analysis|finance|operations|general>", '
        f'"subtask":"<what to do>"}}]}}. If the task is simple, return {{"split": false}}.\n\n'
        f"Task: {task['title']}\n\nReturn ONLY the JSON object."
    )
    try:
        decision = await llm.call_structured(decide_prompt, tier=_tier_for(specialist))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(decision, dict) or not decision.get("split"):
        return None
    subs = decision.get("subagents") or []
    subs = [s for s in subs if isinstance(s, dict) and s.get("subtask")][:settings.max_delegation_fanout]
    if len(subs) < 2:
        return None  # not worth a subagent layer

    await emit("specialist_planning", task_id=task["id"], agent_id=spec_id,
               name=specialist.get("name"), subagents=len(subs))
    user_id = mission.get("created_by") or "default-user"
    dept_id = specialist.get("department_id")
    results, ctx = [], dict(context or {})
    for i, s in enumerate(subs):
        cap = str(s.get("capability") or "general").lower()
        if cap not in _CAP_CATEGORIES:
            cap = "general"
        sub_name = (s.get("name") or f"{cap.title()} Subagent").strip()[:80]
        sub_tools = _tools_for_capability(cap)
        sub_id = create_agent(
            name=sub_name, role_title=sub_name, agent_type=cap,
            purpose=f"Subagent of {specialist.get('name')}.",
            system_prompt=(f"You are '{sub_name}', a subagent. Do ONLY your assigned sub-step "
                           "precisely using tools for evidence, then report a concise result."),
            tools=sub_tools, model="groq:openai/gpt-oss-20b",
            department_id=dept_id, created_by=user_id,
            origin="subagent", source_mission_id=mission["id"],
        )
        await emit("subagent_created", task_id=task["id"], parent_id=spec_id,
                   parent_name=specialist.get("name"), agent_id=sub_id, name=sub_name,
                   capability=cap, tools=sub_tools)
        sub_task = {"id": f"{task['id']}-sa{i+1}", "title": s["subtask"],
                    "agent_type": cap, "_depth": depth + 1, "_no_subagents": True}
        sub_agent = get_agent(sub_id)
        await emit("subagent_started", task_id=task["id"], agent_id=sub_id,
                   name=sub_name, subtask=s["subtask"][:160])
        res = await _run_single(sub_agent, sub_id, sub_task, ctx, mission, emit)
        out = res.get("data") or res.get("summary") or ""
        await emit("subagent_done", task_id=task["id"], agent_id=sub_id,
                   name=sub_name, success="error" not in res)
        results.append({"name": sub_name, "subtask": s["subtask"], "output": out, "error": res.get("error")})
        ctx[sub_name] = out[:1200]

    if not results:
        return None
    synth_input = "\n\n".join(f"### {r['name']} — {r['subtask']}\n{r['error'] and ('FAILED: '+r['error']) or r['output']}"
                             for r in results)
    try:
        synth = await llm.call(
            [{"role": "system", "content": specialist["system_prompt"]},
             {"role": "user", "content": f"Consolidate your subagents' results for: {task['title']}\n\n{synth_input}"}],
            tier=_tier_for(specialist), temperature=specialist.get("temperature", 0.7))
        traces.record_llm(mission["id"], task["id"], spec_id, provider=synth.provider, model=synth.model,
                          input_tokens=synth.input_tokens, output_tokens=synth.output_tokens,
                          cost_usd=synth.cost_usd, latency_ms=synth.latency_ms, success=True)
        final = synth.text.strip() or synth_input
    except Exception:  # noqa: BLE001
        final = synth_input
    await emit("specialist_subagents_done", task_id=task["id"], agent_id=spec_id,
               name=specialist.get("name"), subagents=len(results))
    return {"summary": final[:500], "data": final, "subagents": results}


async def _run_single(agent: dict, agent_id: str, task: dict, context: dict,
                       mission: dict, emit) -> dict:
    """The single-agent ReAct loop (one agent, its tools, one task).

    If the agent is a SPECIALIST with a complex task and depth budget remains, it
    first decomposes into SUBAGENTS (one more level of the hierarchy) before
    falling back to its own ReAct loop."""
    depth = int(task.get("_depth", 0))
    if (agent.get("origin") == "specialist" and depth < settings.max_delegation_depth
            and not task.get("_no_subagents")):
        sub_result = await _maybe_spawn_subagents(agent, agent_id, task, context, mission, emit)
        if sub_result is not None:
            return sub_result

    allowed_tools = set(_effective_tools(agent, task, mission))
    llm = LLMClient(user_keys=mission.get("user_keys"))
    tier = _tier_for(agent)
    # Code / chart / MCP-action tasks need the stronger model to reliably emit
    # the tool call (the fast model stalls on structured tool JSON).
    _needs = task.get("tools_needed") or []
    if "code_interpreter" in _needs or any(t.startswith("mcp_") for t in _needs):
        tier = "reasoning"
    messages = _build_messages(agent, task, context, memory=mission.get("short_term_memory", ""), mission=mission)
    collected_images: list = []  # chart images from any code_interpreter calls this task
    collected_artifacts: list = []  # typed, renderable artifacts from every tool call
    _arg_retry_counts: dict = {}  # per-tool: how many times we've seen an arg error

    # Pre-task: inject the agent's relevant long-term memory (gated by memory_enabled
    # + global/per-agent settings). Never fatal.
    try:
        from app.knowledge.memory import retrieve_memory

        mem_block = await retrieve_memory(agent, task.get("title", ""))
        if mem_block:
            messages.insert(1, {"role": "system", "content": mem_block})
    except Exception:  # noqa: BLE001
        pass

    for _ in range(settings.max_task_steps):
        # --- LLM step ---
        try:
            result = await llm.call(messages, tier=tier, temperature=agent.get("temperature", 0.7))
        except Exception as e:  # AllProvidersFailedError or any provider issue
            traces.record_llm(
                mission["id"], task["id"], agent_id, provider="none", model="none",
                input_tokens=0, output_tokens=0, cost_usd=0.0, latency_ms=0,
                success=False, error=str(e),
            )
            return {"summary": "LLM unavailable", "error": str(e)}

        traces.record_llm(
            mission["id"], task["id"], agent_id, provider=result.provider, model=result.model,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            cost_usd=result.cost_usd, latency_ms=result.latency_ms, success=True,
        )

        tool_call = _parse_tool_call(result.text)
        if tool_call is None:
            # Final answer. If the model returned nothing usable, retry once
            # with an explicit instruction before giving up (prevents blank "—").
            answer = result.text.strip()
            if not answer:
                # Empty reply. If this task has tools, first nudge the model to
                # emit its tool call; only then fall back to a prose answer.
                if allowed_tools:
                    hint = next(iter(allowed_tools))
                    messages.append({"role": "assistant", "content": result.text})
                    messages.append({
                        "role": "user",
                        "content": "Your reply was empty. If you need information, call a tool "
                        'NOW by replying with ONLY this JSON: {"tool": "' + hint + '", "input": {...}}. '
                        "Otherwise give your complete final answer in prose.",
                    })
                else:
                    messages.append({"role": "assistant", "content": result.text})
                    messages.append({
                        "role": "user",
                        "content": "Your reply was empty. Provide the complete answer to the task "
                        "now, in clear prose/markdown. Do not call a tool.",
                    })
                try:
                    retry = await llm.call(messages, tier=tier, temperature=agent.get("temperature", 0.7))
                    traces.record_llm(
                        mission["id"], task["id"], agent_id, provider=retry.provider, model=retry.model,
                        input_tokens=retry.input_tokens, output_tokens=retry.output_tokens,
                        cost_usd=retry.cost_usd, latency_ms=retry.latency_ms, success=True,
                    )
                    # The retry might itself be a tool call — handle it next loop.
                    retry_call = _parse_tool_call(retry.text)
                    if retry_call is not None:
                        result = retry
                        tool_call = retry_call
                    else:
                        answer = retry.text.strip()
                except Exception:
                    pass
            if tool_call is None:
                if not answer:
                    return {"summary": "No output produced",
                            "error": "The agent returned an empty response for this task."}
                # Guard: if the "answer" is essentially a leaked tool-call JSON
                # (model emitted a call we couldn't run), ask once for clean prose
                # rather than surfacing raw {"tool":...} to the user.
                if answer.lstrip().startswith("{") and '"tool"' in answer:
                    messages.append({"role": "assistant", "content": result.text})
                    messages.append({
                        "role": "user",
                        "content": "Do NOT output tool-call JSON. Give your final answer to the "
                        "task in clear prose/markdown now, using what you already know.",
                    })
                    try:
                        fix = await llm.call(messages, tier=tier, temperature=agent.get("temperature", 0.7))
                        traces.record_llm(
                            mission["id"], task["id"], agent_id, provider=fix.provider, model=fix.model,
                            input_tokens=fix.input_tokens, output_tokens=fix.output_tokens,
                            cost_usd=fix.cost_usd, latency_ms=fix.latency_ms, success=True,
                        )
                        clean = fix.text.strip()
                        if clean and not (clean.lstrip().startswith("{") and '"tool"' in clean):
                            answer = clean
                    except Exception:  # noqa: BLE001
                        pass
                return {"summary": answer[:500], "data": answer, "images": collected_images,
                        "artifacts": collected_artifacts}

        tool_name = tool_call["tool"]
        tool_input = tool_call["input"]

        # Enforce the agent's allowed-tools list.
        if tool_name not in allowed_tools:
            messages.append({"role": "assistant", "content": result.text})
            messages.append({
                "role": "user",
                "content": f"You are not allowed to use '{tool_name}'. "
                f"Use only: {sorted(allowed_tools) or 'no tools'}. Continue.",
            })
            continue

        # PLANNING MODE: block any real-world ACTION tool. The agent may only
        # plan/draft — it cannot send, post, upload, etc. Switch to Action mode
        # to actually perform the action.
        if mission.get("mode", "action") == "planning":
            from app.tools import modes as tool_modes
            if tool_modes.is_action_tool({"name": tool_name}):
                messages.append({"role": "assistant", "content": result.text})
                messages.append({
                    "role": "user",
                    "content": f"'{tool_name}' performs a real-world action, which is NOT "
                    "allowed in Planning mode. Instead, DESCRIBE what you would do (draft the "
                    "email/post/plan) and continue, or give your final answer.",
                })
                await emit("action_blocked_planning", task_id=task["id"], tool=tool_name)
                continue

        # --- Approval gate: ACTION tools in action mode pause for the user ---
        from app.tools import modes as _tmodes
        if _tmodes.is_action_tool({"name": tool_name}):
            _always = mission.setdefault("_always_allow", set())
            if tool_name not in _always:
                from app.missions import approvals
                decision = await approvals.request_approval(
                    mission_id=mission["id"], task_id=task["id"], agent_id=agent_id,
                    tool=tool_name, tool_input=tool_input,
                    reason=f"'{tool_name}' performs a real-world action.", emit=emit,
                )
                if not decision.get("approved"):
                    messages.append({"role": "assistant", "content": result.text})
                    messages.append({
                        "role": "user",
                        "content": f"The user DENIED '{tool_name}'. Do not attempt it again. "
                        "Continue with other work or give your final answer.",
                    })
                    await emit("action_denied", task_id=task["id"], tool=tool_name)
                    continue
                if decision.get("always"):
                    _always.add(tool_name)
                await emit("action_approved", task_id=task["id"], tool=tool_name)

        # --- Tool step (with capability-group fallback) ---
        await emit("tool_call", task_id=task["id"], tool=tool_name, input=tool_input)
        import time
        from app.tools import artifacts as _artifacts
        from app.tools import capabilities as _caps
        from app.tools.base import ToolContext

        tool_ctx = ToolContext(
            user_keys=mission.get("user_keys"),
            user_id=mission.get("created_by") or "default-user",
            agent_id=agent_id,
            mission_id=mission["id"],
        )

        # Build the ordered list of tools to TRY: the requested tool first, then
        # its same-capability alternatives (capped) if it turns out unusable.
        _try_order = [tool_name]
        try:
            for alt in _caps.similar_tools(tool_name):
                if alt in allowed_tools and alt not in _try_order:
                    _try_order.append(alt)
        except Exception:  # noqa: BLE001
            pass
        _try_order = _try_order[: _max_fallbacks() + 1]  # original + up to N alts

        tool_result = None
        used_tool = tool_name
        ok = False
        for _idx, _attempt_tool in enumerate(_try_order):
            t0 = time.monotonic()
            tool_result = await registry.dispatch(
                _attempt_tool, tool_input, mission.get("user_keys"), ctx=tool_ctx)
            latency = int((time.monotonic() - t0) * 1000)
            ok = "error" not in tool_result
            traces.record_tool(
                mission["id"], task["id"], agent_id, tool_name=_attempt_tool, tool_input=tool_input,
                tool_output=tool_result, latency_ms=latency, success=ok,
                error=tool_result.get("error") if not ok else None,
            )
            used_tool = _attempt_tool
            if ok:
                break
            # Is this a "tool-unusable" error we should fall back on? Arg errors
            # only count after we've let the model retry its own args once.
            _retried = _arg_retry_counts.get(_attempt_tool, 0) > 0
            reason = _unusable_reason(tool_result, already_retried_args=_retried)
            _arg_retry_counts[_attempt_tool] = _arg_retry_counts.get(_attempt_tool, 0) + 1
            if reason is None:
                break  # a normal failure — let the model react, no auto-fallback
            # Any next alternative to try?
            if _idx + 1 < len(_try_order):
                _next_tool = _try_order[_idx + 1]
                await emit("tool_fallback", task_id=task["id"],
                           from_tool=_attempt_tool, to_tool=_next_tool, reason=reason)
                continue
            break  # exhausted alternatives → return the honest error below

        tool_name = used_tool  # the tool that actually ran (for the feedback msg)

        await emit("tool_result", task_id=task["id"], tool=tool_name, success=ok,
                   images=(tool_result.get("images") or []))
        if tool_result.get("images"):
            collected_images.extend(tool_result["images"])
        # Collect typed, renderable artifacts from this tool call (best-effort).
        try:
            _arts = _artifacts.normalize_artifacts(tool_name, tool_result)
            if _arts:
                collected_artifacts.extend(_arts)
                await emit("tool_result", task_id=task["id"], tool=tool_name,
                           success=ok, artifacts=_arts)
        except Exception:  # noqa: BLE001
            pass

        # Feed the tool result back to the agent.
        messages.append({"role": "assistant", "content": result.text})
        messages.append({
            "role": "user",
            "content": f"Tool '{tool_name}' returned:\n{json.dumps(tool_result)[:3000]}\n\n"
            "Continue, or give your final answer.",
        })

    # Hit the step cap — force a final answer.
    messages.append({
        "role": "user",
        "content": "You have reached the tool-call limit. Give your final answer now, as prose.",
    })
    try:
        final = await llm.call(messages, tier=tier)
        traces.record_llm(
            mission["id"], task["id"], agent_id, provider=final.provider, model=final.model,
            input_tokens=final.input_tokens, output_tokens=final.output_tokens,
            cost_usd=final.cost_usd, latency_ms=final.latency_ms, success=True,
        )
        answer = final.text.strip()
        if not answer:
            return {"summary": "No output produced",
                    "error": "The agent reached the tool-call limit without producing an answer."}
        return {"summary": answer[:500], "data": answer, "images": collected_images,
                "artifacts": collected_artifacts}
    except Exception as e:
        return {"summary": "Could not complete", "error": str(e)}
