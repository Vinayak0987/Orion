# 04 — MISSION ENGINE PLAN (THE CORE)

---

## What It Is and Why It Exists in the System

The Mission Engine is the **brain and heart of Orion**. It is not a UI section. It is the backend system that powers everything.

Every other plan either feeds into it (Agents, Tools, Knowledge, Departments, Settings) or reads what it produces (Missions UI, Operations, Observability, Notifications). The Mission Engine is the center of gravity.

**Three parts, always in sequence:** Planner → Router → Executor

Without the Mission Engine: the entire system is a collection of beautiful screens with no behavior.

---

## Part A — The Planner

**Input:** user's natural language goal  
**Output:** structured list of tasks with titles, agent types, tool requirements, and dependency links  
**Cost:** exactly ONE fast LLM call

### How it works
```python
prompt = f"""
You are a task planner for an AI company operating system.
Given a goal, break it into a list of concrete tasks.
Each task must have:
  - title: short action phrase
  - agent_type: one of [research, marketing, finance, operations, hr, analysis, writing, general]
  - tools_needed: list from [web_search, maps_api, document_rag, http_request] or []
  - depends_on: list of task titles that must complete before this task starts

Return ONLY a valid JSON array. No explanation.

Goal: {user_prompt}
"""
response = await llm_client.call(prompt, tier="fast")
tasks = json.loads(response)
```

### Example output for "Analyze my 5 competitors and suggest pricing"
```json
[
  { "title": "Find top 5 competitors online",       "agent_type": "research",  "tools_needed": ["web_search"],  "depends_on": [] },
  { "title": "Get competitor pricing information",  "agent_type": "research",  "tools_needed": ["web_search"],  "depends_on": [] },
  { "title": "Compare and analyze pricing data",    "agent_type": "analysis",  "tools_needed": ["document_rag"], "depends_on": ["Find top 5 competitors online", "Get competitor pricing information"] },
  { "title": "Write pricing strategy report",       "agent_type": "writing",   "tools_needed": [],               "depends_on": ["Compare and analyze pricing data"] }
]
```

Tasks 1 and 2 have no dependencies — they run in **parallel** immediately.  
Task 3 depends on both 1 and 2 — it waits, then runs.  
Task 4 depends on 3 — it runs last.

---

## Part B — The Task Router

**Input:** one task + mission context (department_id, user_id)  
**Output:** specific `agent_id` to handle this task

### Priority order
```
1. User has a custom agent of matching type, assigned to this department → use it
2. User has a custom agent of matching type (any department) → use it  
3. System default agent for this type → use it
4. System generic agent → use it (never fails to assign)
```

### Implementation
```python
async def route_task(task, mission) -> str:
    agents = await db.query(
        "SELECT id FROM agents WHERE agent_type = ? AND created_by = ? AND status = 'active' ORDER BY department_id = ? DESC",
        [task.agent_type, mission.user_id, mission.department_id]
    )
    if agents:
        return agents[0].id
    # fall back to system defaults seeded in DB
    default = await db.query(
        "SELECT id FROM agents WHERE agent_type = ? AND created_by = 'system'",
        [task.agent_type]
    )
    return default[0].id
```

---

## Part C — The Executor

**Input:** agent_id + task + context from all previously completed tasks  
**Output:** task result + execution trace rows

### Step-by-step
```
1. Load agent definition from DB
   → system_prompt, allowed_tools[], sub_agents[], model, temperature

2. Build full prompt:
   system_prompt
   + "\n\nWhat you remember:\n" + memory_retrieval(agent_id, task.title)
   + "\n\nContext from previous tasks:\n" + json(context)
   + "\n\nYour task: " + task.title

3. Call LLM (via user API keys → Groq → Gemini → Ollama fallback)
   → log to execution_traces: type=llm, provider, model, input_tokens, output_tokens, latency_ms, cost_usd

4. Parse LLM response for tool calls
   Format the LLM is instructed to use:
   { "tool": "web_search", "input": { "query": "top cafes in Thane" } }

5. For each tool call:
   a. Check tool is in agent's allowed_tools[] list
   b. Check if approval required (agent permissions)
      → if yes: create decision record → pause task → emit approval_required event → wait
   c. Dispatch to tool registry → execute tool
   d. Log to execution_traces: type=tool, tool_name, input, output, latency_ms, success
   e. Append tool result to conversation history
   f. Continue LLM call with tool result

6. Repeat steps 4-5 until LLM response has no tool calls

7. Extract final result from last LLM response

8. Store result in mission_tasks: {task_id, result: {summary, data}}

9. Run memory extraction (if agent.memory_enabled):
   → Ask LLM: "What key facts from this task are worth remembering?"
   → Embed and store in ChromaDB memory collection

10. Emit task_completed WS event with result_summary

11. Check dependency graph: which waiting tasks now have all deps complete?
    → enqueue those tasks for execution (back to step 1)
```

---

## Dependency Graph Execution

```python
async def run_mission(mission_id):
    tasks = await load_tasks(mission_id)      # from Planner
    completed = set()
    running = set()
    results = {}

    async def execute(task):
        agent_id = await route_task(task, mission)
        result = await executor.run(agent_id, task, context=results)
        results[task.title] = result
        completed.add(task.id)
        await emit_ws(mission_id, "task_completed", task.id, result.summary)
        await check_and_start_unblocked(tasks, completed, running)

    async def check_and_start_unblocked(tasks, completed, running):
        for task in tasks:
            if task.id in completed or task.id in running:
                continue
            if all(dep in completed for dep in task.depends_on):
                running.add(task.id)
                asyncio.create_task(execute(task))

    # Start all tasks with no dependencies in parallel
    await check_and_start_unblocked(tasks, completed, running)
    await wait_for_all_tasks(mission_id)
```

---

## Database Tables

```sql
CREATE TABLE missions (
    id          TEXT PRIMARY KEY,
    prompt      TEXT NOT NULL,
    title       TEXT,                    -- generated by planner (short name for the mission)
    status      TEXT NOT NULL,           -- planning | running | waiting_approval | completed | failed
    department_id TEXT,                  -- optional, routes to dept's agents
    created_by  TEXT NOT NULL,           -- user_id
    created_at  TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE mission_tasks (
    id          TEXT PRIMARY KEY,
    mission_id  TEXT NOT NULL,
    title       TEXT NOT NULL,
    agent_type  TEXT NOT NULL,
    agent_id    TEXT,                    -- assigned by router
    tools_needed TEXT,                   -- json array
    depends_on  TEXT NOT NULL DEFAULT '[]', -- json array of task titles
    status      TEXT NOT NULL,           -- pending | running | waiting_approval | completed | failed
    result      TEXT,                    -- json {summary, data}
    created_at  TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (mission_id) REFERENCES missions(id)
);

CREATE TABLE execution_traces (
    id              TEXT PRIMARY KEY,
    mission_id      TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    trace_type      TEXT NOT NULL,    -- llm | tool
    provider        TEXT,             -- groq | gemini | ollama | openai
    model           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        REAL,
    tool_name       TEXT,
    tool_input      TEXT,             -- json
    tool_output     TEXT,             -- json
    latency_ms      INTEGER,
    success         INTEGER NOT NULL, -- 1 | 0
    error_message   TEXT,
    created_at      TEXT NOT NULL
);
```

---

## API Endpoints

```
POST   /missions
  body:    { prompt, department_id? }
  returns: { mission_id }   (202, non-blocking)

GET    /missions
  query:   limit, offset, status, department_id
  returns: list of missions with id, prompt, title, status, created_at, task_count, agent_count

GET    /missions/{id}
  returns: full mission with tasks[] (each with status, agent, result) and summary stats

DELETE /missions/{id}
  cancels if running, deletes record

WS     /ws/missions/{id}
  streams: all execution events in real time (see event list in Command Center Plan)
```

---

## How the Mission Engine Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Command Center | `POST /missions` called on submit. WS events drive the live UI. |
| Agents | Router reads `agents` DB. Executor loads agent `system_prompt`, `tools[]`, `model`. |
| Tools | Executor intercepts tool calls → dispatches to tool registry. |
| Knowledge | `document_rag` tool searches ChromaDB. Memory retrieved before each task, stored after. |
| Departments | `department_id` on mission → Router filters agents by department first. |
| Approvals | Executor calls `request_approval` → creates decision → pauses task. Resumes on approval. |
| Observability | Every LLM call and tool call → `execution_traces` row. |
| Operations | Post-mission processor classifies outputs → `operations_data` table. |
| Missions UI | `GET /missions` feeds Missions list. `GET /missions/{id}` feeds detail view. |
| Notifications | `mission_completed` / `mission_failed` → notification created. |
| Settings | Executor loads `user.api_keys` before every run for LLM and tool keys. |

---

## Build Order — PHASE 1 (Build This First, Everything Else Depends On It)

```
Week 1:
  Step 1: Create DB tables (missions, mission_tasks, execution_traces)
  Step 2: Planner — LLM call → JSON task list
  Step 3: Seed 5 default agents in DB (research, marketing, finance, analysis, writing)
  Step 4: Router — query agents DB by type

Week 2:
  Step 5: Built-in tools — web_search (Serper), document_rag (ChromaDB)
  Step 6: Executor — LLM call + tool dispatch + trace logging
  Step 7: Dependency graph runner (asyncio.gather for parallel tasks)

Week 3:
  Step 8: WebSocket event streaming
  Step 9: REST endpoints (POST /missions, GET /missions, GET /missions/{id})
  Step 10: Wire Command Center to these endpoints
```
