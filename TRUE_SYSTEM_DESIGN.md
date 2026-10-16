# Orion — True System Design
# What the Frontend Is Telling You to Build

---

## The Real Vision (Read From the Frontend)

Your frontend is not showing a "business plan generator."
It is showing an **AI Company Operating System** — like having an entire company
staff made of AI agents that you create, configure, deploy, and manage.

The user does not "generate a plan." The user **runs a company with AI.**

Here is what the frontend screens are actually describing:

```
You have a goal: "Build a SaaS product" or "Grow my cafe" or "Launch a campaign"
         ↓
You go to Command Center and describe it in natural language
         ↓
Orion's Planner breaks it into a list of tasks / sub-tasks automatically
         ↓
Tasks are assigned to AI Agents (dynamically, based on what is needed)
         ↓
Agents call Tools (Web Search, Maps, Documents, APIs, etc.) to complete tasks
         ↓
The result is tracked as a Mission with full execution trace
         ↓
Departments manage ongoing operations (not one-off tasks)
         ↓
Everything is observable, approvable, and auditable
```

This is not a "generate once" system. It is a **continuous AI workforce.**

---

## The Four Core Concepts

Everything in the frontend maps to exactly four concepts.
If you understand these four, the entire system becomes clear.

---

### CONCEPT 1: MISSION
**What it is**: A goal given to the system in natural language.

A Mission is created when the user types something in the Command Center:
- "I want to open a cafe in Thane"
- "Create a Q4 marketing campaign"
- "Analyze our top 5 competitors"
- "Build a financial model for next year"

A Mission is **not fixed**. The system figures out:
- What tasks are needed to accomplish this goal
- Which agents should handle each task
- In what order tasks should run
- What tools each agent will need

A Mission has a lifecycle: `Created → Planning → In Progress → Completed`

It produces outputs: research documents, plans, reports, decisions.

**Every other concept serves the Mission.**

---

### CONCEPT 2: AGENT
**What it is**: An AI worker that can accomplish a specific type of task.

An Agent has:
- A **name** (e.g., "Research Agent", "Financial Analyst", "Content Creator")
- A **purpose** (what it is good at doing)
- **Instructions / System Prompt** (how it should behave)
- **Tools it can use** (Web Search, Notion, Slack, etc.)
- **Memory** (what it remembers from past runs)
- **Permissions** (what it is allowed to do)
- **Sub-agents** (it can call other agents to help)

An Agent is **reusable across multiple missions**. The same Marketing Agent that
ran a competitor analysis can run a content creation mission next.

Agents are **user-created and user-configured**. This is why you have:
- Agent Builder (visual node graph to design agent + sub-agents + tools)
- Agent Templates (pre-built starting points)
- Agent Testing (try the agent before deploying)
- Agent Performance (track how well it is doing over time)

**This is the key insight: agents are not hardcoded. Users build and own them.**

---

### CONCEPT 3: DEPARTMENT
**What it is**: A group of agents organized around a business function that runs continuously.

A Department is not just a label. It is an **ongoing operational unit**:
- Marketing Department: agents that continuously manage campaigns, content, SEO, brand
- Finance Department: agents that track revenue, costs, forecast, generate reports
- Operations Department: agents that manage inventory, suppliers, workflows
- Sales Department: agents that track pipeline, outreach, conversions
- HR Department: agents that handle hiring plans, employee info, performance
- Research Department: agents that do ongoing market monitoring, competitor tracking

The difference between a Department and a Mission:
- A Mission is a **one-time goal** ("create a Q4 campaign")
- A Department is **always running** ("Marketing Department is always active, doing its regular work")

Departments have their own:
- Agent roster (which agents belong to this dept)
- Activity feed (what agents in this dept have been doing)
- Members management (add/remove agents)
- Settings (configure how the dept runs)
- Missions (missions assigned to this dept)

**Users can create custom departments** — the "Create Department" screen shows
a chat interface where you describe what department you want, and Orion
proposes agents, responsibilities, and structure.

---

### CONCEPT 4: TOOL
**What it is**: An external capability that an Agent can call during task execution.

Tools are what give agents real-world grounding. Without tools, an agent is
just an LLM making things up. With tools, an agent can:
- **Web Search**: Search the internet for real information
- **Maps API**: Find real businesses, locations, distances
- **Document RAG**: Search through uploaded documents
- **Notion**: Read from and write to Notion pages
- **Slack**: Send messages, read channels
- **Google Drive**: Read and write files
- **Analytics**: Query data from analytics platforms
- **Custom APIs**: Call any API the user configures

Tools are:
- **Registered in the system** with a name, description, schema
- **Assigned to agents** (each agent has a list of tools it can call)
- **Tracked in observability** (which tools ran, how fast, success rate)
- **User-extensible** (Custom Tools lets users add their own)

**MCP Servers (Model Context Protocol)**: This is the standard for connecting
AI agents to external tools. An MCP Server exposes a set of tools over a
standard protocol. Orion connects to MCP Servers so agents can use any
tool in the MCP ecosystem.

---

## How It All Connects — The Full Flow

```
┌─────────────────────────────────────────────────────────┐
│                    USER (in Command Center)              │
│                                                         │
│  "I want to create a Q4 marketing campaign for          │
│   my cafe in Thane with ₹50K budget"                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    MISSION PLANNER                       │
│                                                         │
│  Breaks the goal into tasks:                            │
│  1. Research current market trends (Research Agent)     │
│  2. Analyze competitor campaigns (Research Agent)       │
│  3. Define target audience (Marketing Agent)            │
│  4. Create campaign strategy (Marketing Agent)          │
│  5. Design content calendar (Content Creator Agent)     │
│  6. Calculate budget allocation (Finance Agent)         │
│  7. Write ad copy (Content Creator Agent)               │
│                                                         │
│  Tasks have dependencies:                               │
│  3 depends on 1,2 → 4 depends on 3 → 5 depends on 4   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION                       │
│                                                         │
│  Research Agent runs:                                   │
│   → calls Web Search tool: "cafe marketing trends 2026"│
│   → calls Web Search tool: "Thane cafe competitor ads" │
│   → produces: research_summary.json                     │
│                                                         │
│  Marketing Agent runs (reads research_summary):         │
│   → calls Document RAG: searches knowledge base        │
│   → produces: target_audience.json, strategy.json      │
│                                                         │
│  Finance Agent runs (reads strategy.json):              │
│   → produces: budget_breakdown.json                     │
│                                                         │
│  Content Creator Agent runs (reads all above):          │
│   → calls Notion tool: writes content calendar         │
│   → produces: content_calendar.json, ad_copy.json      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    HUMAN IN THE LOOP                     │
│                                                         │
│  Approvals triggered:                                   │
│  - "Budget allocation: ₹50K breakdown — Approve?"      │
│  - "Post this to Slack? — Approve?"                    │
│                                                         │
│  User approves or rejects in Approvals section          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    RESULTS                               │
│                                                         │
│  Mission: "Q4 Marketing Campaign" → Completed           │
│  Outputs: strategy doc, content calendar, ad copy       │
│  Stored in Knowledge Base for future reference          │
│  Visible in Missions list                               │
│  Full trace in Observability                            │
└─────────────────────────────────────────────────────────┘
```

---

## Full System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│                                                                  │
│  ENTRY POINTS              MANAGEMENT              MONITORING    │
│  ────────────              ──────────              ──────────    │
│  Command Center            Departments             Observability  │
│  (start missions)          (org structure)         (all traces)  │
│                            Agents                  Missions      │
│                            (create/configure)      (track goals) │
│                            Tools                               │
│                            (connect tools)                       │
│                            Knowledge               Approvals     │
│                            (documents)             (HITL gate)   │
│                            Settings                Notifications │
└──────────────────┬───────────────────────────────────────────────┘
                   │  REST API + WebSocket
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                         │
│                                                                  │
│  MISSION ENGINE            AGENT RUNTIME           TOOL LAYER   │
│  ─────────────             ─────────────           ──────────   │
│  Natural language          Agent definition        Tool registry │
│  → task decomposition      store                   Tool executor │
│  → dependency graph        Dynamic agent           MCP client    │
│  → agent assignment        instantiation           Web Search    │
│  → execution scheduling    LLM call routing        Maps API      │
│  → result aggregation      Tool call dispatch      Doc RAG       │
│                            Memory read/write       Custom APIs   │
│                                                                  │
│  GOVERNANCE                DATA STORES             LLM LAYER    │
│  ──────────                ───────────             ─────────    │
│  Approval gate             SQLite (missions,       Groq          │
│  Constitution rules        agents, tools,          Gemini        │
│  Audit logging             executions)             Ollama        │
│  HITL triggers             ChromaDB (vectors,      (fallback     │
│                            knowledge, memory)      chain)        │
│                            MongoDB (users,                       │
│                            API keys, auth)                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## What Needs to Be Built (Backend First Principles)

The frontend tells you the full vision. Now here is what backend needs to exist
to make each frontend section real.

---

### 1. COMMAND CENTER BACKEND

What the screen shows: user types a goal → Live Agent Tree appears showing
Orion Planner → Research → Analysis → Execution → leaf tasks stream in.
Tools being used panel updates live. Chat history persists.

**What needs to be built:**

```
POST /missions
  body: { prompt: string, department_id?: string }
  returns: { mission_id, status: "planning" }

WS /ws/missions/{mission_id}
  streams:
    { event: "planning", tasks: [...] }           # task decomposition live
    { event: "task_started", task_id, agent_id }  # agent picked up a task
    { event: "tool_call", task_id, tool, input }  # agent calling a tool
    { event: "tool_result", task_id, tool, output }
    { event: "task_completed", task_id, result }
    { event: "approval_required", decision_id }   # HITL gate hit
    { event: "mission_completed", outputs }

GET /missions
  returns: list of missions with status, progress

GET /missions/{id}
  returns: full mission with all tasks, agent assignments, outputs, traces
```

**How task decomposition works (the dynamic part):**
The user's prompt goes to a **Planner LLM call** that returns a task list in
structured JSON:
```json
{
  "mission_title": "Q4 Marketing Campaign",
  "tasks": [
    {
      "id": "t1",
      "title": "Research market trends",
      "agent_type": "research",
      "tools_needed": ["web_search"],
      "depends_on": []
    },
    {
      "id": "t2",
      "title": "Analyze competitors",
      "agent_type": "research",
      "tools_needed": ["web_search", "maps_api"],
      "depends_on": []
    },
    {
      "id": "t3",
      "title": "Define target audience",
      "agent_type": "marketing",
      "tools_needed": ["document_rag"],
      "depends_on": ["t1", "t2"]
    }
  ]
}
```

Then a **Task Executor** runs tasks in dependency order, assigning each to
the appropriate agent dynamically. This replaces the hardcoded 21-agent
fixed pipeline.

---

### 2. AGENT RUNTIME BACKEND

What the screen shows: Agent Builder lets users create agents with a visual
node graph (Orchestrator → Specialists → Tools). Agents have name, purpose,
instructions, tools, memory, permissions. Users test agents directly.

**What needs to be built:**

```
Agent Definition Store (new DB table: agents)
  id, name, purpose, system_prompt, tools (JSON list),
  memory_type, memory_ttl, permissions (JSON),
  sub_agents (JSON list of agent_ids),
  created_by, created_at, version

POST /agents                    → create agent
GET  /agents                    → list agents
GET  /agents/{id}               → get agent
PUT  /agents/{id}               → update agent
DELETE /agents/{id}             → delete agent

POST /agents/{id}/test
  body: { message: string }
  streams: execution trace (same as WS missions but single-agent)

Agent Templates Store (new DB table: agent_templates)
  Standard pre-built agents users can clone

GET /agents/templates           → list templates
POST /agents/from-template/{template_id}  → clone template → agent
```

**How an agent runs dynamically:**
When the Task Executor assigns a task to an agent:
1. Load the agent definition from the DB
2. Build the system prompt from the agent's definition
3. Give it the task description and any context from previous tasks
4. For each tool call the agent makes → look up tool in Tool Registry → execute
5. Return result to the mission

This is the fundamental difference from hardcoded agents:
**any agent can run any task that matches its capabilities.**

---

### 3. TOOL LAYER BACKEND

What the screen shows: Toolbox lists all available tools (Web Search, Maps,
Notion, Slack, etc.) with status. API Keys section stores credentials.
MCP Servers section connects to MCP protocol servers.

**What needs to be built:**

```
Tool Registry (new DB table: tools)
  id, name, description, type (builtin | mcp | custom),
  input_schema (JSON), config_schema (JSON), enabled

Built-in tools (implemented as Python functions):
  web_search(query)           → returns search results
  maps_places(query, location) → returns places/businesses
  document_rag(query)          → searches ChromaDB knowledge base
  http_request(url, method, body) → generic HTTP call

MCP Client:
  Connects to any MCP server URL
  Discovers tools from the server
  Proxies tool calls to the MCP server

User API Keys Store (in MongoDB user profile):
  { groq_key, gemini_key, google_places_key, serper_key, openai_key, ... }
  Used when making LLM/tool calls on behalf of that user

POST /tools/execute
  body: { tool_id, input: {} }
  returns: { output, latency_ms, success }

GET /tools                → list all registered tools
GET /tools/mcp            → list MCP servers
POST /tools/mcp           → connect a new MCP server
```

---

### 4. DEPARTMENT BACKEND

What the screen shows: Department Overview with agent roster (visual cards),
active missions, knowledge items count, success rate. Department has tabs:
Overview, Activity, Members, Settings. "Create Department" is a chat
interface — describe what you want and Orion proposes the structure.

**What needs to be built:**

```
Department Store (new DB table: departments)
  id, name, purpose, icon, color, agent_ids (JSON list),
  created_by, created_at

POST /departments
  body: { prompt: string }  ← chat-driven creation
  AI generates: name, purpose, suggested_agents list
  returns: proposed department (not yet saved)

POST /departments/confirm
  body: { proposal_id, modifications? }
  saves the department

GET /departments            → list departments with agent count, mission count
GET /departments/{id}       → full department with agents, missions, activity
GET /departments/{id}/activity → activity feed for this department
GET /departments/{id}/members  → agents in this department
```

---

### 5. KNOWLEDGE BASE BACKEND

What the screen shows: Knowledge Base has document list (PDF, DOC, XLS, Folder)
with status (Active/Review). Upload Sources has drag-drop upload. Memory
Overview shows memory entries per department/agent.

**What needs to be built:**

```
Document Store (new DB table: documents)
  id, name, type, size, status, department_id,
  chroma_collection_id, uploaded_by, uploaded_at

POST /knowledge/documents
  body: multipart file upload
  pipeline: → parse (PDF/DOCX/URL) → chunk → embed → store in ChromaDB
  returns: document_id

GET /knowledge/documents    → list documents
GET /knowledge/documents/{id} → document details
DELETE /knowledge/documents/{id}

POST /knowledge/search
  body: { query, filters? }
  returns: relevant chunks from ChromaDB

GET /knowledge/memory
  returns: episodic memory entries (per agent/department)
```

---

### 6. OBSERVABILITY BACKEND

What the screen shows: Dashboard with KPIs (success rate, latency, total runs,
total cost). Bar chart: run volume per hour. Line chart: latency over time.
System health per component. Runs list with trace detail. LLM usage per
provider with token counts. Tool usage stats. Error log.

**What needs to be built:**

All observability data comes from **execution traces** stored during agent runs.
Every LLM call and tool call needs to be logged:

```
Execution Trace Store (new DB table: execution_traces)
  id, mission_id, task_id, agent_id, trace_type (llm|tool|agent),
  provider, model, input_tokens, output_tokens, latency_ms,
  tool_name, tool_input, tool_output, success, error,
  created_at

GET /observability/summary
  returns: aggregated KPIs (success rate, avg latency, total runs, total cost)

GET /observability/runs
  returns: list of recent mission executions with status, latency, tokens

GET /observability/runs/{mission_id}/trace
  returns: full execution trace for a mission (every step)

GET /observability/llm
  returns: token usage and cost breakdown per LLM provider

GET /observability/tools
  returns: tool call counts, success rates, latency per tool

GET /observability/errors
  returns: error log with type, agent, message, mission
```

---

### 7. APPROVALS BACKEND

What the screen shows: List of pending approval requests from agents.
Each request has: title, requesting agent, description, priority, business context,
proposed action, expected impact, supporting files. Buttons: Approve, Reject,
Request Changes.

This is the **Human-in-the-Loop gate**. Agents do not take high-impact
actions automatically — they request approval first.

**What needs to be built:**

```
Decisions Store (already exists in operating layer — reuse/extend)
  id, mission_id, agent_id, title, description, priority,
  proposed_action (JSON), expected_impact (text),
  evidence_files (JSON list), status (pending|approved|rejected|returned),
  created_at, resolved_at, resolved_by, resolution_reason

When does an agent trigger an approval?
  - Spending above a threshold (configurable per agent)
  - Sending external messages (Slack, email)
  - Making irreversible actions
  - Hiring / contracts
  - Anything flagged in the agent's permission model

GET /approvals              → list pending decisions
GET /approvals/{id}         → full decision detail
POST /approvals/{id}/approve  body: { by }
POST /approvals/{id}/reject   body: { by, reason }
POST /approvals/{id}/return   body: { by, reason }
```

---

## What Does NOT Need to Be Built (Honest Assessment)

| Item | Why Not Now |
|------|------------|
| Billing / Subscription | You are free tier only. No payment needed. |
| Workspace / Team | Single-user system for now. |
| Real-time collaboration | Not needed until multi-user. |
| OAuth (Google/Slack login buttons) | Auth works with email. OAuth can come later. |
| Custom Tool code editor | Start with built-in tools + MCP. Custom code execution is a security problem. |

---

## Complete Data Model

```
users               → id, email, full_name, password_hash, api_keys (JSON)
departments         → id, name, purpose, agent_ids, created_by
agents              → id, name, purpose, system_prompt, tools, memory_config, permissions, sub_agents
agent_templates     → id, name, desc, base_config (JSON), category
tools               → id, name, description, type, input_schema, enabled
missions            → id, prompt, status, department_id, created_by, created_at, completed_at
mission_tasks       → id, mission_id, title, agent_id, status, depends_on, result, created_at
execution_traces    → id, mission_id, task_id, agent_id, trace_type, provider, tokens, latency, success, error
decisions           → id, mission_id, agent_id, title, proposed_action, priority, status, resolved_by
documents           → id, name, type, chroma_id, department_id, uploaded_by
```

---

## The Technology That Drives Dynamic Agents

This is the core: how does a task get assigned to the right agent dynamically?

### Step 1: The Planner
User input → one LLM call → structured task list with `agent_type` per task.
`agent_type` is a category ("research", "marketing", "finance", "operations", "hr").
NOT a specific agent name. The planner does not know about specific agents.

### Step 2: Agent Router
For each task, look in the agents DB:
- Find agents where `department_category` matches `agent_type`
- If user has a custom agent for that category → use it
- If not → use a system default agent for that category
- Multiple agents of same type? Pick by least busy / highest success rate.

### Step 3: Agent Executor
Load the selected agent definition.
Build the full prompt: system_prompt + task_description + context_from_previous_tasks.
Make the LLM call through the provider chain.
Intercept tool calls → execute via Tool Registry → return results to LLM.
Continue until agent signals completion.

### Step 4: Context Passing
Tasks in a mission share a **Mission Context** object.
When task t3 depends on t1 and t2, it gets their outputs as context.
The agent can read previous task results through Document RAG on the mission context.

**This is why it is fully dynamic:**
- Any prompt → any task list → any agent handles any task
- Users create new agents → immediately available for new missions
- New tools → registered once → any agent can use them
- No fixed pipeline. No hardcoded 21 agents.

---

## Build Order (Phase by Phase)

### Phase 1: Core Mission Flow (3 weeks)
Goal: User can type a goal → tasks appear → agents run → result shown.

1. **Planner LLM call** — prompt → structured task list
2. **Task executor** — run tasks in dependency order
3. **Agent definition store** — store agents in DB (start with 5 system defaults)
4. **Built-in tool: web_search** — Serper or DuckDuckGo
5. **Built-in tool: document_rag** — ChromaDB search
6. **Mission store** — persist missions, tasks, traces
7. **WS /ws/missions** — stream all events to frontend
8. **Wire Command Center** to new WS endpoint
9. **Wire Missions list** to GET /missions

**Deliverable**: Type a goal → see tasks appear → see agents run → see result.

---

### Phase 2: Agent Management (2 weeks)
Goal: Users can create and configure their own agents.

1. **Agent definition store** — full CRUD
2. **Agent Builder** — wire to POST/PUT /agents
3. **Agent Templates** — seed 6 default templates
4. **Agent Testing** — wire ViewAgentTesting to POST /agents/{id}/test
5. **Agent Performance** — wire to execution_traces aggregation

**Deliverable**: User creates a custom "Competitor Research Agent" → uses it in missions.

---

### Phase 3: Tools & MCP (2 weeks)
Goal: Agents can use real tools. Users can connect tools.

1. **Tool Registry** — register built-in tools
2. **Built-in tool: maps_api** — Google Places / OpenStreetMap
3. **MCP Client** — connect to MCP servers
4. **API Keys management** — store in MongoDB, use in tool calls
5. **Wire Toolbox** to tool registry
6. **Wire API Keys view** to user profile API keys

**Deliverable**: Research Agent calls Web Search + Maps. User connects their own API keys.

---

### Phase 4: Departments (1 week)
Goal: Users can organize agents into departments.

1. **Department store** — CRUD
2. **Chat-driven department creation** — POST /departments with prompt
3. **Wire Department views** to /departments API
4. **Department activity feed** — from mission_tasks filtered by department

**Deliverable**: Marketing Department has its agents, its missions, its activity.

---

### Phase 5: Approvals & Knowledge (2 weeks)
Goal: Human oversight works. Documents boost agent quality.

1. **Approval trigger** — agents flag decisions via a built-in "request_approval" tool
2. **Wire Approvals view** to /approvals API
3. **Document ingestion** — upload → parse → chunk → embed → store
4. **Wire Knowledge views** to /knowledge API

**Deliverable**: Agent asks for approval before posting to Slack. User uploads business docs and agents use them.

---

### Phase 6: Observability (1 week)
Goal: Everything is visible and measurable.

1. **Execution trace logging** — log every LLM call and tool call
2. **Aggregation endpoints** — summary, runs, llm usage, errors
3. **Wire Observability views** to new endpoints

**Deliverable**: User sees exactly which LLM calls ran, how fast, how many tokens, what failed.

---

## The Three-Line Summary

**What Orion is**: An AI company operating system where you create AI agents, assign them to departments, give them goals (missions), and they use tools to accomplish tasks with human oversight at key decision points.

**What makes it different**: The agent-task-tool system is fully dynamic. Any goal → any task breakdown → any agent → any tool. Users own and configure their agents. No fixed pipelines.

**What to build first**: The mission engine (planner → tasks → agents → tools → results) streamed live to the Command Center. Everything else in the sidebar supports and extends this core loop.
