# PHASE 1 — BUILD SPEC
# The Exact File-by-File Plan to Build the Mission Engine

> This is the bridge between the architecture plans (01–16) and actual code.
> The architecture plans say WHAT to build. This says HOW, file by file.
> Decision made: **fresh backend**. Legacy `backend/app/` stays on disk as
> reference only — we do not build on it or migrate it.

---

## Decision Record

| Question | Decision |
|----------|----------|
| Legacy backend | SCRAP (keep on disk, do not build on or migrate). Reference only for auth + LLM provider patterns. |
| New backend location | `backend2/` (fresh tree) OR replace `backend/app/` contents gradually. **Chosen: `backend2/` fresh tree** so the legacy app keeps running during the build and there is zero risk of breaking it. |
| LLM tool-calling format | **JSON-in-prompt + ReAct loop** (not native function calling). Reason: works identically across Groq/Gemini/Ollama; native function-calling support differs per provider and Ollama's is weak. The agent is instructed to reply with a JSON block; the executor parses it. |
| WebSocket protocol | One socket per mission: `WS /ws/missions/{id}`. Server pushes typed events. Client is a pure viewer — dropping it never aborts the mission. |
| What carries over from legacy | Auth (`app/auth/`), LLM provider classes (`app/llm/`), ChromaDB cache pattern (`app/apis/cache.py`), config pattern (`app/config.py`). Copied and adapted, not imported. |

---

## The New Backend Tree (what Phase 1 creates)

```
backend2/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, router registration
│   ├── config.py               # settings (copy legacy pattern)
│   ├── db/
│   │   ├── sqlite.py           # connection, init_db, migrations
│   │   └── schema.sql          # all CREATE TABLE statements
│   ├── llm/
│   │   ├── client.py           # LLMClient — the fallback chain (Plan 13)
│   │   ├── providers.py        # Groq, Gemini, Ollama provider classes
│   │   ├── ratelimit.py        # RateLimitTracker
│   │   └── repair.py           # JSON repair for structured calls
│   ├── tools/
│   │   ├── registry.py         # tool lookup + dispatch
│   │   ├── web_search.py       # Serper-backed built-in tool
│   │   └── document_rag.py     # ChromaDB-backed built-in tool
│   ├── agents/
│   │   ├── store.py            # agents table CRUD
│   │   └── defaults.py         # 7 seeded default agents
│   ├── missions/
│   │   ├── store.py            # missions + mission_tasks CRUD
│   │   ├── planner.py          # goal → task list (one LLM call)
│   │   ├── router.py           # task → agent_id
│   │   ├── executor.py         # agent run loop (ReAct)
│   │   ├── engine.py           # dependency graph runner (orchestrates all)
│   │   └── events.py           # WS event types + emitter
│   ├── traces/
│   │   └── store.py            # execution_traces CRUD (write-only during Phase 1)
│   └── api/
│       ├── missions.py         # POST /missions, GET /missions, WS
│       ├── settings.py         # GET/PUT /settings/api-keys
│       └── health.py           # GET /health
└── tests/
    ├── test_planner.py
    ├── test_router.py
    ├── test_executor.py
    ├── test_engine.py
    └── test_missions_api.py
```

---

## Build Steps in Strict Order

### STEP 1 — Project skeleton + config + DB
**Files:** `main.py`, `config.py`, `db/sqlite.py`, `db/schema.sql`

`schema.sql` creates exactly 3 tables for Phase 1:
```sql
CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY, prompt TEXT NOT NULL, title TEXT,
    status TEXT NOT NULL, department_id TEXT, created_by TEXT NOT NULL,
    created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS mission_tasks (
    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, title TEXT NOT NULL,
    agent_type TEXT NOT NULL, agent_id TEXT, tools_needed TEXT DEFAULT '[]',
    depends_on TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL,
    result TEXT, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS execution_traces (
    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL, trace_type TEXT NOT NULL, provider TEXT, model TEXT,
    input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL,
    tool_name TEXT, tool_input TEXT, tool_output TEXT,
    latency_ms INTEGER, success INTEGER NOT NULL, error_message TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, purpose TEXT,
    system_prompt TEXT NOT NULL, agent_type TEXT NOT NULL,
    tools TEXT DEFAULT '[]', sub_agents TEXT DEFAULT '[]',
    department_id TEXT, model TEXT DEFAULT 'groq:llama-3.1-8b-instant',
    temperature REAL DEFAULT 0.7, memory_enabled INTEGER DEFAULT 0,
    permissions TEXT DEFAULT '{}', status TEXT DEFAULT 'active',
    created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
```
Phase 1 uses `created_by = 'default-user'` (no auth integration yet — auth wired in a later step).

**Test:** `init_db()` creates all tables idempotently in a tmp DB.

---

### STEP 2 — LLM Provider chain (Plan 13)
**Files:** `llm/providers.py`, `llm/ratelimit.py`, `llm/repair.py`, `llm/client.py`

`LLMClient.call(prompt, tier, user_id=None) -> LLMResult`
Returns `{ text, provider, model, input_tokens, output_tokens, cost_usd, latency_ms }`.

`LLMClient.call_structured(prompt, tier) -> dict` wraps `call` + repair.

Providers try in order: Groq → Gemini → Ollama. Skip rate-limited. Raise `AllProvidersFailedError` if all fail.

**Test:** mock each provider; verify fallback on 429; verify JSON repair; verify cost calc.

---

### STEP 3 — Built-in tools (Plan 06 basics)
**Files:** `tools/registry.py`, `tools/web_search.py`, `tools/document_rag.py`

```python
# registry.py
TOOLS = {
    "web_search":   web_search_fn,     # (input: {query}) -> {results: [...]}
    "document_rag": document_rag_fn,   # (input: {query}) -> {passages: [...]}
}

async def dispatch(tool_name, tool_input, user_id) -> dict:
    fn = TOOLS.get(tool_name)
    if not fn:
        return {"error": f"Unknown tool: {tool_name}"}
    return await fn(tool_input, user_id)
```

`web_search`: calls Serper with user's key (or system key). On failure → return `{"error": ..., "degraded": true}` (Plan 16 Layer 2).
`document_rag`: queries ChromaDB. Empty collection → return `{"passages": []}` (no crash).

**Test:** mock Serper with respx; mock ChromaDB; verify degraded-mode return on failure.

---

### STEP 4 — Agents store + defaults (Plan 05 minimal)
**Files:** `agents/store.py`, `agents/defaults.py`

`defaults.py` seeds 7 agents (`created_by='system'`): research, marketing, finance, analysis, writing, operations, general — each with system_prompt and default tools from Plan 05.

`store.py`: `get_agent(id)`, `find_agents_by_type(agent_type, user_id, department_id)`, `list_agents()`, `seed_defaults()`.

**Test:** seed is idempotent; find_agents_by_type returns system default when no custom agent exists.

---

### STEP 5 — The Planner (Plan 04 Part A)
**File:** `missions/planner.py`

```python
PLANNER_PROMPT = """You are a task planner for an AI operating system.
Break the user's goal into concrete tasks. Return ONLY a JSON array.
Each task: {"title": str, "agent_type": one of [research,marketing,finance,
operations,hr,analysis,writing,general], "tools_needed": subset of
[web_search,document_rag], "depends_on": [list of task titles]}

Goal: {goal}"""

async def plan(goal: str, llm: LLMClient) -> list[dict]:
    tasks = await llm.call_structured(PLANNER_PROMPT.format(goal=goal), tier="fast")
    # validate: each has title+agent_type; depends_on references real titles
    return validate_tasks(tasks)
```

Also generate a short `title` for the mission (second cheap call or derive from goal).

**Test:** scripted LLM returns a known task list; verify parsing; verify invalid depends_on is dropped; verify a vague goal → empty list → mission fails cleanly (Plan 16 Layer 4).

---

### STEP 6 — The Router (Plan 04 Part B)
**File:** `missions/router.py`

```python
async def route(task: dict, mission: dict) -> str:
    agents = find_agents_by_type(task["agent_type"], mission["created_by"], mission["department_id"])
    if agents:
        return agents[0]["id"]           # user/dept custom agent wins
    return get_system_default(task["agent_type"])["id"]
```

**Test:** custom agent preferred over default; default used when no custom; never returns None.

---

### STEP 7 — The Executor (Plan 04 Part C, ReAct loop)
**File:** `missions/executor.py`

The core loop. This is the most important file in Phase 1.

```python
async def run_task(agent, task, context, mission, emit) -> dict:
    agent_def = get_agent(agent_id)
    messages = build_initial_prompt(agent_def, task, context)  # system + task + context

    for step in range(MAX_STEPS := 10):          # loop cap (Plan 16 Layer 3)
        llm_result = await llm.call(messages, tier=tier_for(agent_def))
        record_trace(mission, task, agent_id, "llm", llm_result)   # Plan 10

        tool_call = parse_tool_call(llm_result.text)   # looks for JSON block
        if tool_call is None:
            return extract_final_result(llm_result.text)   # agent is done

        # agent wants to call a tool
        if tool_call["tool"] not in agent_def["tools"]:
            messages.append(tool_error(f"You cannot use {tool_call['tool']}"))
            continue

        await emit("tool_call", task_id=task["id"], tool=tool_call["tool"], input=tool_call["input"])
        tool_result = await tools.dispatch(tool_call["tool"], tool_call["input"], mission["created_by"])
        record_trace(mission, task, agent_id, "tool", tool_result)   # Plan 10
        await emit("tool_result", task_id=task["id"], tool=tool_call["tool"], success="error" not in tool_result)

        messages.append(tool_result_message(tool_result))   # feed back to LLM

    # hit MAX_STEPS → force final answer (Plan 16)
    return force_final(messages)
```

**The tool-call format the agent is taught (in every system prompt):**
```
To use a tool, reply with ONLY this JSON and nothing else:
{"tool": "web_search", "input": {"query": "..."}}
When you have your final answer, reply with normal text (no JSON).
```

**Test:** scripted LLM that emits one tool call then a final answer → verify dispatch happens, result fed back, final returned. Test loop cap. Test disallowed tool rejection.

---

### STEP 8 — The Engine (Plan 04 dependency graph)
**File:** `missions/engine.py`

```python
async def run_mission(mission_id, emit):
    mission = get_mission(mission_id)
    goal = mission["prompt"]

    await emit("planning_started")
    tasks = await plan(goal, llm)
    save_tasks(mission_id, tasks)
    for t in tasks: await emit("task_created", task=t)
    await emit("planning_complete", task_count=len(tasks))

    completed, running, results = set(), set(), {}

    async def execute(task):
        agent_id = await route(task, mission)
        await emit("task_started", task_id=task["id"], agent_id=agent_id)
        try:
            result = await run_task(agent_id, task, results, mission, emit)
            results[task["title"]] = result
            set_task_status(task["id"], "completed", result)
            await emit("task_completed", task_id=task["id"], result_summary=summarize(result))
        except Exception as e:
            set_task_status(task["id"], "failed", {"error": str(e)})
            await emit("task_failed", task_id=task["id"], error=str(e))
        completed.add(task["id"])
        await start_unblocked()

    async def start_unblocked():
        for t in tasks:
            if t["id"] in completed or t["id"] in running: continue
            if all(dep_done(d, completed) for d in t["depends_on"]):
                running.add(t["id"]); asyncio.create_task(execute(t))

    await start_unblocked()
    await wait_until_all_done(tasks, completed)
    set_mission_status(mission_id, "completed")
    await emit("mission_completed", outputs=collect_outputs(results))
```

**Test:** 4-task mission with deps [T1,T2 parallel → T3 → T4] → verify execution order, parallel start, final completion. Fully offline with scripted LLM + mocked tools.

---

### STEP 9 — WebSocket + REST API (Plan 03 + 04)
**Files:** `api/missions.py`, `missions/events.py`

```python
@router.post("/missions")
async def create_mission(req: {prompt, department_id?}):
    mission_id = create_mission_record(req.prompt, "default-user", req.department_id)
    asyncio.create_task(run_mission(mission_id, make_emitter(mission_id)))
    return {"mission_id": mission_id}   # 202, non-blocking

@router.websocket("/ws/missions/{id}")
async def ws(websocket, id):
    await websocket.accept()
    queue = subscribe(id)              # events.py pub/sub (in-memory asyncio.Queue)
    async for event in queue:
        await websocket.send_json(event)

@router.get("/missions")        -> list
@router.get("/missions/{id}")   -> detail with tasks
```

`events.py`: an in-memory `{mission_id: asyncio.Queue}` registry. `emit()` puts to the queue; WS handler drains it. If no WS connected, mission still runs (events just queue/drop).

**Test:** TestClient POST /missions → mission runs → GET /missions/{id} shows completed with results. WS test: connect → receive event sequence.

---

### STEP 10 — Settings API keys + Health (Plan 02 + 13)
**Files:** `api/settings.py`, `api/health.py`

`GET/PUT /settings/api-keys` — Phase 1 stores in a simple local table or env (full MongoDB integration comes in Phase 4 with auth). For now: a `user_settings` row keyed by `'default-user'`.

`GET /health` — probe each LLM provider, return availability + rate limit state.

**Test:** PUT then GET returns masked keys; health reflects provider state.

---

### STEP 11 — Frontend wiring (Plan 03 + 14 basic)
**Files:** `frontend/src/api.js`, `ViewCommandCenter.jsx`, `ViewMissions.jsx`

1. Add to `api.js`: `createMission(prompt)`, `streamMission(id, callbacks)` (WS), `missions()`, `mission(id)`
2. `ViewCommandCenter`: submit → `createMission` → connect WS → render events into chat + Live Agent Tree + Tools panel
3. `ViewMissions`: list from `GET /missions`; row click → `ViewMissionDetails` with `GET /missions/{id}`

**Verify:** `npm run build` passes. Manual: type a goal, watch agents run live, see result, find it in Missions.

---

## Phase 1 Exit Criteria

- [ ] `backend2` runs: `uvicorn app.main:app --port 8081`
- [ ] POST a goal → planner produces tasks → agents run → result returned
- [ ] Dependency order respected (parallel where possible, sequential where required)
- [ ] Every LLM + tool call logged to `execution_traces`
- [ ] WebSocket streams the full event sequence live
- [ ] All provider failures fall back gracefully; all providers down → clean error
- [ ] Command Center shows live agent tree; Missions list + detail work
- [ ] Tests pass offline (scripted LLM, mocked tools, no live API keys)
- [ ] Legacy `backend/` untouched and still runnable

---

## What Phase 1 Deliberately Does NOT Do

(These come in later phases — do not scope-creep into them now.)
- Agent CRUD UI / Builder / Templates (Phase 2)
- Departments (Phase 3)
- MCP, custom tools, maps_api, document upload pipeline (Phase 4)
- Approvals gate, full Observability UI (Phase 5)
- Operations dashboard, Notifications, real Dashboard data (Phase 6)
- Full MongoDB auth integration (uses `'default-user'` placeholder in Phase 1)

---

## The One Sentence

Phase 1 builds a fresh `backend2/` with the LLM chain, built-in tools, default agents, and the Planner→Router→Executor→Engine mission loop — streamed live to the Command Center — so a user can type a goal and watch real agents complete it. Everything else builds on this.
