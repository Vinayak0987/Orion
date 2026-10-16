# ORION — STREAMLINED PROJECT PLAN
# The Single Source of Truth. Read this before building anything.

---

## WHAT ORION IS IN ONE SENTENCE

Orion is a platform where you create AI Agents, give them Tools,
organize them into Departments, and assign them Goals (Missions) —
and they do real work for you autonomously.

---

## THE 5 BUILDING BLOCKS

Everything in the entire system is built from exactly 5 things.
If you understand how these 5 connect, the whole system is clear.

```
MISSION ──assigned to──► AGENTS ──call──► TOOLS
   │                        │
   │                    belong to
   │                        │
   └────────────────────► DEPARTMENTS
                              │
                           track in
                              │
                         OBSERVABILITY
```

### 1. MISSION
A goal described in natural language.
"Create a Q4 marketing campaign" / "Find 3 office locations in Pune" / "Analyze our competitors"

A Mission produces: a task list, agent runs, results, outputs.

### 2. AGENT
An AI worker. Has a name, instructions (system prompt), tools it can use, memory.
Users CREATE their own agents. Orion provides default templates.
An agent can call sub-agents.

### 3. TOOL
Something an agent can call to interact with the real world.
Web Search / Maps / Documents / Notion / Slack / Custom APIs / MCP Servers.
Tools are registered in the system. Agents pick tools from the registry.

### 4. DEPARTMENT
A group of agents organized around a business function.
Marketing / Finance / Operations / Sales / HR / Research.
A department runs Missions and has ongoing activity.
Users CREATE custom departments by describing them.

### 5. OBSERVABILITY
The full trace of everything that happened.
Every agent run, every tool call, every LLM call, every token, every cost.
Used for debugging, monitoring, and improving.

---

## HOW THE SYSTEM WORKS — THE COMPLETE FLOW

```
Step 1: USER TYPES A GOAL in Command Center
        "I want to analyze my top 5 competitors and their pricing"

Step 2: PLANNER (1 LLM call) breaks it into tasks
        Task 1: Find competitors online       → needs: web_search tool
        Task 2: Get their pricing pages       → needs: web_search tool
        Task 3: Extract pricing data          → needs: document_rag tool
        Task 4: Compare and summarize         → needs: no tool
        Task 5: Generate report               → needs: no tool

Step 3: TASK ROUTER assigns each task to an Agent
        Tasks 1,2,3 → Research Agent (best match for research tasks)
        Task 4,5    → Analysis Agent (best match for analysis tasks)
        (Router picks from the user's agent library, or uses defaults)

Step 4: AGENTS RUN their assigned tasks
        Research Agent calls web_search("top competitors [business name]")
        Research Agent calls web_search("competitor pricing pages")
        Research Agent calls document_rag to search uploaded docs
        Analysis Agent reads all results and writes comparison + report

Step 5: APPROVAL GATE (if needed)
        If an agent wants to POST to Slack or spend money → waits for human approval

Step 6: RESULTS saved to Mission
        All outputs stored, mission marked Completed
        User sees results in Command Center and Missions section

Step 7: TRACE stored in Observability
        Every LLM call, tool call, token count, latency, cost — all logged
```

This flow happens DYNAMICALLY. No fixed pipeline. Any goal → any tasks → any agents → any tools.

---

## EVERY SCREEN — WHAT IT IS FOR AND WHY IT EXISTS

### DASHBOARD
**Purpose**: Home screen. Shows what is happening across the whole system.
**Data it needs**: Mission counts (from missions table), agent status (from agents table), recent activity (from execution_traces), pending approvals count (from decisions table)
**Is it needed?** YES. It is the landing page after login.

---

### COMMAND CENTER
**Purpose**: The main workspace. Type a goal, watch agents work, see results.
**Data it needs**: WebSocket stream of mission execution events
**Is it needed?** YES. It is THE core feature of the entire system. Everything else supports this.
**How it works**:
- User types goal → POST /missions
- WebSocket /ws/missions/{id} streams the live agent tree building
- Right panel shows tools being used in real time
- Chat history shows previous missions as a conversation thread

---

### MISSIONS
**Purpose**: Track all goals (past and current). Find results from previous runs.
**Data it needs**: GET /missions (list), GET /missions/{id} (detail with task tree)
**Is it needed?** YES. Without this, users cannot find their previous work.
**Mission Details sub-page**: Shows the execution graph (which agents ran, in what order, with what tools), task-by-task results, current status.

---

### APPROVALS
**Purpose**: Human review before agents take high-stakes actions.
**Data it needs**: GET /decisions, POST /decisions/{id}/approve|reject
**Is it needed?** YES. This is the safety net of the whole system.
**When does it trigger?**: Agent tries to spend money, send a message externally, make an irreversible action → approval required before it can proceed.
**Without this**: Agents could do dangerous things automatically.

---

### NOTIFICATIONS
**Purpose**: Alert the user when something needs attention.
**Data it needs**: Notification events generated by the system (mission completed, approval requested, agent failed)
**Is it needed?** YES for UX. But it is the LAST thing to build. Build everything else first, then add notifications.
**The badge "12" on the sidebar is fake right now. Remove it until real.**

---

### DEPARTMENTS
**Purpose**: Organize agents into business functions. Run ongoing operations.
**Data it needs**: GET /departments, GET /departments/{id}, agents assigned to each dept
**Is it needed?** YES. This is what makes Orion feel like a real company, not just a task runner.
**How it connects to everything**:
- A Department OWNS a set of Agents
- A Department runs Missions (missions can be assigned to a dept)
- A Department has its own Activity (missions run by its agents)
- A Department has its own Knowledge (documents relevant to that dept)

**Create Department screen**: Chat interface → user describes what dept they need → Orion proposes dept name, purpose, suggested agents → user confirms → dept created.

---

### AGENTS (7 sub-tabs)

**Overview**
What it is: All agents in the system, their status, their department.
Data: GET /agents — list all agents with name, dept, status, mission count, success rate
Is it needed? YES.

**Create**
What it is: Form to create a new agent from scratch (AI-assisted).
Data: POST /agents
Is it needed? YES. This is how users add custom agents.
How it connects: Created agent → available to be assigned to tasks → can be added to a department.

**Builder**
What it is: Visual node graph editor for designing an agent's sub-agent tree and tool connections.
What the screen shows: Orchestrator node → Specialist nodes → Tool nodes, all connected by lines.
Is it needed? YES — but simplified. The visual graph is for EDITING an existing agent's structure. An agent can have sub-agents (e.g., "Marketing Agent" orchestrates "Content Agent" + "SEO Agent" + "Campaign Agent"). This is the visual representation of that hierarchy.
How it connects: The agent defined in Builder is stored in the agents table. When the task router assigns a task to "Marketing Agent", it runs the whole sub-tree (Marketing Agent → calls Content Agent + SEO Agent in parallel).

**Templates**
What it is: Pre-built agent starting points. Click "Use Template" → creates an agent from that template.
Data: GET /agents/templates, POST /agents/from-template/{id}
Is it needed? YES. New users need a starting point. Without templates, creating an agent is intimidating.
Templates to include: Research Agent, Marketing Agent, Financial Analyst, Operations Agent, HR Agent, Sales Agent, Customer Support Agent.

**Testing**
What it is: Send a test message to an agent and see its execution trace (which tools it called, what it returned, how long each step took).
Data: POST /agents/{id}/test → streams execution trace
Is it needed? YES. Users need to validate an agent works before deploying it in real missions.
How it connects: Uses the same execution engine as real missions but in isolation.

**Performance**
What it is: Charts and metrics for how an agent is performing over time. Success rate, latency, token usage, cost, error rate.
Data: GET /agents/{id}/performance — aggregated from execution_traces table
Is it needed? YES. Users need to know if their agent is working well.

**Settings**
What it is: Edit an agent's configuration: name, department, model, temperature, version history, permissions, danger zone (disable/delete).
Data: PUT /agents/{id}, DELETE /agents/{id}
Is it needed? YES. This is how users tune and maintain their agents.

---

### KNOWLEDGE (5 sub-tabs)

**Knowledge Base**
What it is: Documents the agents can search during task execution. PDFs, URLs, Word docs, folders.
Data: GET /documents, POST /documents (upload)
Is it needed? YES. Without this, agents only know what the LLM knows (training data). With uploaded documents, agents know your specific business context.
How it connects: When an agent runs a task, if it needs to look something up, it calls the document_rag tool → searches ChromaDB → returns relevant passages.

**Upload Sources**
What it is: Drag-and-drop file upload. Also supports URLs (scrape and embed).
Data: POST /documents/upload (file), POST /documents/from-url
Is it needed? YES. This is the entry point for getting documents into the system.

**Memory Overview**
What it is: View the episodic memory agents have built up over time. What did the Research Agent remember from its last 10 runs?
Data: GET /memory?agent_id=...
Is it needed? YES. Memory is what makes agents get better over time. Seeing it builds user trust.

**Memory Details**
What it is: Inspect a specific memory entry.
Is it needed? YES but low priority.

**Memory Settings**
What it is: Configure how long memory is kept (TTL), which agents have memory enabled.
Is it needed? YES but low priority.

---

### TOOLS (5 sub-tabs)

**All Tools (Toolbox)**
What it is: Every tool registered in the system. Status (active/inactive), category, last used.
Data: GET /tools
Is it needed? YES. Users need to see what tools are available.

**MCP Servers**
What it is: Connect external MCP servers so their tools become available to agents.
Data: GET /tools/mcp, POST /tools/mcp (connect new server)
Is it needed? YES. MCP is the standard for extending agent capabilities. Filesystem MCP, Notion MCP, Brave Search MCP are shown in the design.
How it connects: Admin adds an MCP server URL → system discovers its tools → tools appear in the Toolbox → any agent can be configured to use them.

**Integrations**
What it is: Marketplace of third-party integrations (Slack, Google Drive, Notion, Stripe, etc.)
Is it needed? For MVP: NO. Add later. Real OAuth flows required for each one.
For now: Show the page as "Coming Soon" or show only the ones that actually work.

**Custom Tools**
What it is: Define a custom tool by giving it a name, description, and an HTTP endpoint it should call.
Data: POST /tools/custom
Is it needed? YES — but simplified. A custom tool is just: name + description + URL + HTTP method + input schema. No code editor. Any HTTP API becomes a tool.
How it connects: Tool registered → available to agents → agent calls tool during task → system calls the HTTP endpoint → returns result to agent.

**API Keys**
What it is: The user's own API keys (Groq, Gemini, Google Places, Serper, OpenAI) stored in their profile. Used when making calls on behalf of that user.
Data: GET /settings/api-keys, POST /settings/api-keys
Is it needed? YES. This is how users bring their own LLM/tool API keys.
How it connects: Keys stored in MongoDB user profile → when an agent runs for this user, the system uses their keys for LLM and tool calls.

---

### OPERATIONS (10 sub-tabs)

**Purpose of this whole section**: Show how the business is actually running. Real-time metrics from what the agents have been doing.

**Overview**: Total operations, active workflows, tasks completed, success rate. Area chart of activity over time.
**Finance**: Revenue metrics from what Finance agents have tracked/reported.
**Sales**: Pipeline metrics from what Sales agents have tracked.
**Inventory**: Stock/supply data from Operations agents.
**Marketing Campaigns**: Campaign metrics from Marketing agents.
**Customers/CRM**: Customer data from CRM agents.
**Employees/HR**: HR data from HR agents.
**Research**: Research outputs from Research agents.
**Suppliers**: Supplier data from Operations agents.
**Website**: Website performance metrics.

**Is this whole section needed?** YES — but it gets populated ORGANICALLY.
As departments run missions and agents produce outputs, this section fills up with real data.
It does NOT need a separate data source. The data comes from mission outputs.

**How it connects**:
- Finance Department runs missions → produces financial data → Finance tab shows it
- Marketing Department runs campaigns → produces campaign metrics → Marketing tab shows it
- You do not build a "finance tracking system." You build a system where Finance agents produce structured outputs, and Operations/Finance tab reads those outputs.

---

### OBSERVABILITY (9 sub-tabs)

**Dashboard**: Summary KPIs across all runs. Success rate, avg latency, total runs, total cost.
**Runs/Sessions**: Table of all agent runs with status, duration, tokens, cost.
**Trace Details**: Step-by-step execution for one run. Each LLM call, each tool call, input/output, latency.
**Tool Usage**: Which tools are called most, their success rates, avg latency.
**LLM Usage & Costs**: Token counts and costs per LLM provider (Groq/Gemini/Ollama/OpenAI).
**Errors & Failures**: Error log with type, agent, message, recovery status.
**Evaluations**: Score distributions for mission quality (completeness, accuracy).
**Audit Logs**: Immutable log of every approval decision.
**Website**: Frontend performance metrics (page load, etc.).

**Is this whole section needed?** YES — the data already exists (every run generates traces).
The work is building the aggregation endpoints and wiring the charts.
Without observability, the system is a black box. Users lose trust.

---

### SETTINGS (8 sub-tabs)

**Profile**: Name, email, avatar. Wire to /auth/me.
**Workspace Settings**: Workspace name, preferences. Low priority.
**Security**: Password change, active sessions. Medium priority.
**Billing**: Plan info. NOT needed for MVP (free tier only).
**API Access**: The Orion platform's own API keys for developers building on top of Orion. Low priority.
**Preferences**: Theme, language, notification settings. Low priority.
**Help & Support**: Links to docs. Static page. Low priority.
**Logout**: Already works (calls onLogout prop).

---

## HOW THE PIECES CONNECT — THE CONNECTION MAP

```
AGENT BUILDER (creates agents)
    │
    ├──► AGENT stored in DB with: name, system_prompt, tools[], sub_agents[], dept_id
    │
    ├──► DEPARTMENT (agent added to dept's agent_ids[])
    │         │
    │         └──► DEPARTMENT OVERVIEW shows this agent in its roster
    │
    └──► TASK ROUTER (when a mission runs, router looks in agents DB to find the right agent)
              │
              └──► MISSION EXECUTION (agent runs, calls tools, produces outputs)
                        │
                        ├──► MISSION RESULTS (shown in Command Center + Missions)
                        │
                        ├──► EXECUTION TRACE (logged to execution_traces table)
                        │         │
                        │         └──► OBSERVABILITY (reads from execution_traces)
                        │
                        ├──► APPROVAL (if needed → goes to Approvals queue)
                        │
                        └──► OUTPUTS (stored → appear in Operations section)
```

---

## WHAT IS NOT NEEDED (HONEST CUT LIST)

| Feature | Decision | Reason |
|---------|----------|--------|
| Billing / Subscription | ❌ Remove | Free tier only. Add later when monetizing. |
| Workspace / Team / Members | ❌ Remove | Single-user system. Add later. |
| OAuth buttons (Google/GitHub login) | ❌ Remove | Email auth works. OAuth needs per-provider work. |
| Notification badge "12" (fake) | ❌ Remove the number | Either make it real or show nothing. Fake data = broken trust. |
| Approval badge "5" (fake) | ⚠️ Make real | Replace with real count from /decisions?status=pending |
| Operations → Website tab | ❌ Low priority | This is web analytics. Not core to the system. |
| Knowledge → Memory Details/Settings | ⚠️ Low priority | Build Overview first. Details/Settings later. |
| Custom Tool code editor | ❌ Replace | Use URL-based custom tools (call an HTTP endpoint). No code execution needed. |
| "Integration marketplace" (Slack, etc.) | ⚠️ Show as Coming Soon | Real OAuth flows for each integration = weeks per integration. |
| Agent version history | ⚠️ Low priority | Build agent CRUD first, versioning is a nice-to-have. |
| Evaluations (Observability sub-tab) | ⚠️ Low priority | Only useful after significant usage data exists. |

---

## THE DATA MODEL (WHAT NEEDS TO BE IN THE DATABASE)

```sql
-- USER ACCOUNTS (MongoDB Atlas)
users: { id, email, full_name, password_hash, api_keys: { groq, gemini, serper, ... } }

-- AGENTS
agents: {
  id, name, purpose, system_prompt, tools (json array of tool_ids),
  sub_agents (json array of agent_ids), department_id,
  model, temperature, memory_enabled, memory_ttl_days,
  permissions (json), status (active|inactive|deleted),
  created_by, created_at, updated_at, version
}

agent_templates: {
  id, name, description, category, base_config (json),
  tags (json array)
}

-- DEPARTMENTS
departments: {
  id, name, purpose, icon, color, agent_ids (json array),
  created_by, created_at
}

-- TOOLS
tools: {
  id, name, description, type (builtin|mcp|custom|integration),
  input_schema (json), config (json), enabled,
  mcp_server_url (for mcp type),
  http_endpoint (for custom type)
}

-- MISSIONS
missions: {
  id, prompt, title, status (planning|running|waiting_approval|completed|failed),
  department_id, created_by, created_at, completed_at
}

mission_tasks: {
  id, mission_id, title, agent_type, agent_id (assigned),
  depends_on (json array of task_ids), status, result (json),
  created_at, completed_at
}

-- EXECUTION TRACES
execution_traces: {
  id, mission_id, task_id, agent_id, trace_type (llm|tool|agent),
  provider, model, input_tokens, output_tokens, cost_usd,
  tool_name, tool_input (json), tool_output (json),
  latency_ms, success, error_message, created_at
}

-- APPROVALS / DECISIONS
decisions: {
  id, mission_id, task_id, agent_id, title, description,
  priority (high|medium|low), proposed_action (json),
  expected_impact, status (pending|approved|rejected|returned),
  created_at, resolved_at, resolved_by, resolution_reason
}

-- KNOWLEDGE BASE
documents: {
  id, name, type (pdf|docx|url|txt), size_bytes, status (active|review),
  department_id, chroma_collection_id,
  uploaded_by, uploaded_at
}

-- MEMORY
memory_entries: {
  id, agent_id, department_id, content, embedding_id (in chroma),
  source_mission_id, created_at, expires_at
}
```

---

## THE BACKEND API (EVERY ENDPOINT NEEDED)

```
AUTH
  POST /auth/signup
  POST /auth/login
  POST /auth/refresh
  POST /auth/logout
  GET  /auth/me
  PUT  /auth/me          (update profile)
  PUT  /auth/api-keys    (store LLM/tool API keys)

MISSIONS
  POST /missions                    (create + start planning)
  GET  /missions                    (list all missions)
  GET  /missions/{id}               (detail with tasks)
  WS   /ws/missions/{id}            (live stream of execution events)

AGENTS
  POST /agents                      (create agent)
  GET  /agents                      (list all agents)
  GET  /agents/{id}                 (get agent)
  PUT  /agents/{id}                 (update agent)
  DELETE /agents/{id}               (delete agent)
  POST /agents/{id}/test            (test an agent with a message, stream trace)
  GET  /agents/{id}/performance     (aggregated metrics from traces)
  GET  /agents/templates            (list templates)
  POST /agents/from-template/{id}   (create agent from template)

DEPARTMENTS
  POST /departments                 (create - AI proposes from prompt)
  GET  /departments                 (list departments)
  GET  /departments/{id}            (department detail)
  PUT  /departments/{id}            (update)
  DELETE /departments/{id}          (delete)
  GET  /departments/{id}/activity   (missions run by agents in this dept)
  POST /departments/{id}/agents     (add agent to dept)
  DELETE /departments/{id}/agents/{agent_id}  (remove agent from dept)

TOOLS
  GET  /tools                       (list all tools)
  POST /tools/custom                (register a custom HTTP tool)
  DELETE /tools/{id}                (remove a tool)
  POST /tools/execute               (test a tool directly)
  GET  /tools/mcp                   (list MCP servers)
  POST /tools/mcp                   (connect new MCP server)
  DELETE /tools/mcp/{id}            (disconnect MCP server)

KNOWLEDGE
  POST /knowledge/documents         (upload document - multipart)
  POST /knowledge/documents/url     (ingest from URL)
  GET  /knowledge/documents         (list documents)
  GET  /knowledge/documents/{id}    (document detail)
  DELETE /knowledge/documents/{id}  (delete document)
  POST /knowledge/search            (search documents)
  GET  /knowledge/memory            (list memory entries - optional agent_id filter)

APPROVALS
  GET  /decisions                   (list decisions - filter by status)
  GET  /decisions/{id}              (decision detail)
  POST /decisions/{id}/approve      (approve)
  POST /decisions/{id}/reject       (reject)
  POST /decisions/{id}/return       (return for changes)

OBSERVABILITY
  GET  /observability/summary       (KPIs: success rate, latency, runs, cost)
  GET  /observability/runs          (list agent runs from traces)
  GET  /observability/runs/{id}/trace  (full trace for one run)
  GET  /observability/llm           (LLM usage breakdown by provider)
  GET  /observability/tools         (tool usage stats)
  GET  /observability/errors        (error log)

HEALTH
  GET  /health                      (system health, LLM provider status)
```

---

## BUILD ORDER — PHASE BY PHASE

### PHASE 1 — CORE LOOP (Weeks 1-3)
**Goal: User types a goal → agents run → results appear.**

Build order (strict sequence, each depends on previous):

1. **Mission Planner** (backend)
   - `POST /missions` → call LLM → generate task list → store in DB → return mission_id
   - The LLM call returns structured JSON: list of tasks with title, agent_type, depends_on, tools_needed

2. **Default Agent Library** (backend)
   - Seed 5 default agents in DB: Research, Marketing, Finance, Operations, HR
   - Each has a system_prompt and a list of default tools

3. **Task Router** (backend)
   - Matches task.agent_type → finds best agent from DB
   - If no matching agent exists → uses a generic agent

4. **Task Executor** (backend)
   - Runs tasks in dependency order (tasks with no depends_on run first, in parallel)
   - For each task: load agent → build prompt → LLM call → handle tool calls → store result

5. **Built-in Tools** (backend)
   - `web_search(query)` → calls Serper API or DuckDuckGo
   - `document_rag(query)` → searches ChromaDB

6. **Execution Trace Logger** (backend)
   - Every LLM call and tool call → insert row in execution_traces

7. **WS /ws/missions/{id}** (backend)
   - Stream all execution events in real time

8. **Wire Command Center** (frontend)
   - Call `POST /missions` on submit
   - Connect to WS and stream events into the Live Agent Tree
   - Show tools being used in real time

9. **Wire Missions list** (frontend)
   - Call `GET /missions` and display real missions

**End of Phase 1**: The system does real work. The core loop is alive.

---

### PHASE 2 — AGENT MANAGEMENT (Weeks 4-5)
**Goal: Users can create and manage their own agents.**

1. **Agent CRUD endpoints** (backend)
2. **Agent Templates seeded in DB** (backend, 7 templates)
3. **Wire Agent Overview** → GET /agents (frontend)
4. **Wire Agent Create form** → POST /agents (frontend)
5. **Wire Agent Templates** → GET /agents/templates (frontend)
6. **Wire Agent Testing** → POST /agents/{id}/test (frontend)
7. **Wire Agent Performance** → GET /agents/{id}/performance (frontend)
8. **Wire Agent Settings / Builder** → PUT /agents/{id} (frontend)

**End of Phase 2**: Users own their agents. The agent system is fully dynamic.

---

### PHASE 3 — DEPARTMENTS (Week 6)
**Goal: Agents are organized. Department views show real data.**

1. **Department CRUD endpoints** (backend)
2. **Department creation from prompt** — POST /departments with AI proposal step (backend)
3. **Wire Departments view** (frontend)
4. **Wire Department detail** (Marketing, Finance, Operations, Sales, HR, Research) (frontend)
5. **Wire Department activity** (frontend)

**End of Phase 3**: The org structure is real and navigable.

---

### PHASE 4 — TOOLS & KNOWLEDGE (Weeks 7-8)
**Goal: Agents are grounded. Users can upload docs and connect tools.**

1. **Tool registry + built-in tools listed** (backend)
2. **MCP client** — connect to MCP server URLs (backend)
3. **Custom HTTP tool registration** (backend)
4. **Document upload + ChromaDB ingestion pipeline** (backend)
5. **Wire Toolbox** (frontend)
6. **Wire MCP Servers** (frontend)
7. **Wire Knowledge upload** (frontend)
8. **Wire Knowledge Base list** (frontend)
9. **Wire API Keys storage** → PUT /auth/api-keys (frontend + backend)

**End of Phase 4**: Agents use real tools and real documents.

---

### PHASE 5 — APPROVALS & OBSERVABILITY (Weeks 9-10)
**Goal: The system is safe and transparent.**

1. **Approval trigger built into agent executor** (backend) — agent calls `request_approval(...)` tool → creates decision → task pauses
2. **WS pauses task, emits approval_required event to frontend**
3. **Approval resume** — when user approves/rejects, task continues or is cancelled
4. **Wire Approvals view** (frontend)
5. **Aggregation endpoints for observability** (backend)
6. **Wire Observability Dashboard, Runs, Trace, LLM, Errors** (frontend)

**End of Phase 5**: Human oversight works. Everything is visible.

---

### PHASE 6 — POLISH (Week 11)
**Goal: The UI feels complete and trustworthy.**

1. **Real notification badges** (pending approvals count on sidebar)
2. **Dashboard real data** (missions summary, recent activity from traces)
3. **Profile wired to /auth/me**
4. **Fix Topbar** (real user name from auth, real date)
5. **Remove fake data** from all views that are now wired
6. **Memory Overview wired**
7. **Operations section wired** (data flows from mission outputs)
8. **Error states** for all views (loading, error, empty states)

---

## THE DEPENDENCY CHAIN (WHAT BLOCKS WHAT)

```
Auth (already built)
  └─► Mission Engine (Phase 1) ──────────────────────────► EVERYTHING
           │
           ├─► Agent CRUD (Phase 2)
           │        └─► Agent Builder / Templates / Testing / Performance
           │
           ├─► Department CRUD (Phase 3)
           │        └─► connects agents to departments
           │
           ├─► Tool Registry (Phase 4)
           │        └─► connects tools to agents
           │        └─► connects MCP servers to tool registry
           │
           ├─► Knowledge (Phase 4)
           │        └─► document_rag tool uses ChromaDB
           │
           ├─► Approvals (Phase 5)
           │        └─► agent executor calls request_approval
           │
           └─► Observability (Phase 5)
                    └─► execution_traces filled by agent executor
```

**The mission engine is the single dependency of everything.**
Build it first. Then every other phase builds on top of it.

---

## THE ANSWER TO "HOW DOES AGENT BUILDER CONNECT TO THE SYSTEM"

When you build an agent in Agent Builder:
1. The agent is SAVED to the agents table with: name, system_prompt, tools[], sub_agents[]
2. That agent now exists in the system's agent library
3. When the next mission runs, the Task Router checks the agents table
4. The router finds this new agent and CAN assign tasks to it based on its capabilities
5. The agent runs, calls its configured tools, optionally calls its sub-agents
6. Its runs are logged in execution_traces
7. Performance tab reads those traces to show metrics

**That is the complete connection. Agent Builder → DB → Task Router → Execution → Traces → Performance.**

---

## THE ANSWER TO "HOW DOES CREATE DEPARTMENT CONNECT"

When you create a department:
1. You describe it in the chat: "A customer success team that handles retention"
2. Orion calls the LLM with your description and returns a proposal:
   - Department name: "Customer Success"
   - Suggested agents: Customer Support Agent, Churn Prediction Agent, Retention Agent
3. You confirm → department saved to departments table with those agent_ids
4. Now in the sidebar, "Customer Success" appears under Departments
5. You can run missions specifically for this department (department_id on the mission)
6. The department's Activity tab shows all missions run by its agents
7. The Operations section pulls data from what these agents have produced

**That is the complete connection. Description → Proposal → Confirm → DB → Sidebar → Missions → Operations.**

---

## FINAL SUMMARY: THE THREE RULES

**Rule 1**: Everything in the system serves the Mission.
Agents exist to run tasks in missions. Tools exist so agents can do real work in missions.
Departments exist to organize who runs what missions. Knowledge exists to ground mission outputs.
Observability exists to understand mission execution. Approvals exist to gate mission actions.

**Rule 2**: The system is dynamic because of the Task Router.
The router is the intelligence that connects a task (from the mission planner) to an agent (from the agents DB).
A dynamic system means: change the agents → change what gets assigned → change what gets done.
A fixed system would hardcode "research tasks → Research Agent." A dynamic system asks: "who is the best Research Agent in the DB right now?"

**Rule 3**: Build the Mission Engine first. Everything else is secondary.
A user who can type a goal and watch agents work is already using the core value.
Departments, builder, templates, tools, knowledge — all make it better, faster, more powerful.
But without the mission engine, the system does nothing.
