# 05 — AGENTS PLAN

---

## What Agents Are in the System

An Agent is an **AI worker** — the entity that actually does the work in a mission.

An agent has:
- **Identity**: name, purpose, description
- **Behavior**: system_prompt (instructions for how it should think and respond)
- **Capabilities**: list of tools it can call, list of sub-agents it can delegate to
- **Memory**: whether it retains knowledge from past runs
- **Permissions**: what it is allowed to do autonomously vs what needs approval
- **Configuration**: which LLM model, what temperature

Agents are **stored in the database**. This is what makes the system dynamic. The Task Router reads from this DB to assign tasks. Change an agent's system prompt → every future task it handles immediately uses the new behavior.

Users create and own their agents. Orion provides 7 default templates to start from. The same agent can run across dozens of missions — it is reusable, not single-use.

---

## The 7 Agent Sub-Sections

### Overview
- **What it shows:** All agents in the system. Two views: org chart (visual circles + agent nodes connected to Orion center) and table (name, dept, status, missions run, success rate, last active).
- **Data source:** `GET /agents` — list all agents with aggregated stats from `execution_traces`
- **Purpose in system:** Shows the user their entire AI workforce at a glance.

### Create
- **What it shows:** Two-mode form — AI-Assisted and Manual.
  - AI-Assisted: user types what they want the agent to do → system proposes name, purpose, system_prompt, suggested tools, knowledge sources, permissions
  - Manual: user fills every field directly
- **Data flow:** `POST /agents` → agent stored in DB → immediately available to Task Router
- **Purpose in system:** This is how users expand their agent workforce dynamically.

### Builder
- **What it shows:** Visual node graph editor. Three layers: Orchestrator (the agent itself, top) → Specialist sub-agents (middle row) → Tools (bottom row). Lines connect them. Configuration panel on the right for the selected node.
- **What it represents:** The agent's internal delegation structure. A "Marketing Agent" orchestrator can call "Content Agent" + "SEO Agent" as sub-agents. Builder is the visual editor for this hierarchy.
- **Data flow:** Editing the graph → `PUT /agents/{id}` updating `sub_agents[]` and `tools[]` fields
- **Purpose in system:** Allows users to build sophisticated multi-agent workflows visually.

### Templates
- **What it shows:** Pre-built agent configurations ready to use. Featured template + grid of 7 categories (Marketing, Finance, Operations, Research, HR, Sales, Customer Support).
- **Data flow:** `GET /agents/templates` → user clicks "Use Template" → `POST /agents/from-template/{id}` → creates agent in their workspace → navigates to Settings to configure
- **Purpose in system:** Reduces the friction of creating agents from zero. New users start here.

### Testing
- **What it shows:** Three-column layout: saved test cases | execution trace | test results
  - User selects a test case (e.g., "Social media post generation")
  - Sends a test message
  - Sees FULL execution trace: Initialize → Retrieve Memory → Plan → Tool Calls → Generate Response → Complete
  - Sees the actual output in the results panel
- **Data flow:** `POST /agents/{id}/test { message }` → streams execution trace → same engine as real missions but isolated
- **Purpose in system:** Users validate agents work correctly before deploying in real missions. Catches bad prompts early.

### Performance
- **What it shows:** 6 KPI cards (Success Rate, Total Runs, Avg Latency, Token Usage, Estimated Cost, Error Rate). Line chart (success rate + latency over time). Bar chart (run volume). Tool usage breakdown. Sub-agent performance. Recent runs table.
- **Data source:** `GET /agents/{id}/performance` — aggregated queries on `execution_traces WHERE agent_id = ?`
- **Purpose in system:** Users see the ROI of their agents. Which agents are underperforming? Which tools are being overused? Where is the cost coming from?

### Settings
- **What it shows:** Edit the agent's full configuration. Basic info (name, description, department, type, autonomy level, model, temperature, tags, icon). Version history (snapshots of past configs). Quick actions (Clone, Export, Reset, Audit Logs). Danger Zone (Disable, Delete).
- **Data flow:** `PUT /agents/{id}` → updates agent config → creates version snapshot in `agent_versions` table
- **Purpose in system:** Ongoing tuning. When an agent's performance drops or behavior needs adjustment, this is where it gets fixed.

---

## The Sub-Agent Mechanism (How Builder Connects to Execution)

This is the most important concept in this plan.

```
Marketing Agent is configured with sub_agents: [content_agent_id, seo_agent_id]

When Task Executor runs Marketing Agent on task "Create blog post":
  1. LLM call with Marketing Agent's system_prompt
  2. LLM responds: { "tool": "call_agent", "input": { "agent_id": "content_agent_id", "task": "Write 800-word blog post about AI trends" } }
  3. Executor sees call_agent tool call
  4. Looks up content_agent_id in DB → loads Content Agent definition
  5. Runs Content Agent as a nested task (same executor, same trace logging)
  6. Content Agent runs, possibly calls its own tools (web_search, etc.)
  7. Content Agent returns result to Marketing Agent
  8. Marketing Agent continues with "Here is the blog post: ..."
  9. Marketing Agent also calls call_agent for SEO Agent in parallel
  10. Marketing Agent combines both outputs → final result
```

**Builder's visual graph is an exact representation of this execution flow.** The lines in the graph = the `call_agent` delegation relationships at runtime.

---

## Database Tables

```sql
CREATE TABLE agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    purpose         TEXT,
    system_prompt   TEXT NOT NULL,
    agent_type      TEXT NOT NULL,        -- research | marketing | finance | operations | hr | analysis | writing | general
    tools           TEXT NOT NULL DEFAULT '[]',     -- json array of tool_ids
    sub_agents      TEXT NOT NULL DEFAULT '[]',     -- json array of agent_ids
    department_id   TEXT,
    model           TEXT DEFAULT 'groq:llama-3.1-8b-instant',
    temperature     REAL DEFAULT 0.7,
    memory_enabled  INTEGER DEFAULT 1,
    memory_ttl_days INTEGER DEFAULT 30,
    permissions     TEXT DEFAULT '{"can_spend": false, "spend_limit_usd": 0, "can_send_external": false}',
    status          TEXT DEFAULT 'active',
    version         TEXT DEFAULT 'v1.0.0',
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE agent_templates (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    category    TEXT,               -- Marketing | Finance | Operations | Research | HR | Sales | Support
    base_config TEXT NOT NULL,      -- json: same shape as agents table fields
    tags        TEXT DEFAULT '[]',  -- json array
    is_featured INTEGER DEFAULT 0
);

CREATE TABLE agent_versions (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    version     TEXT NOT NULL,
    config      TEXT NOT NULL,      -- full agent config snapshot as json
    note        TEXT,
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
```

---

## API Endpoints

```
POST   /agents                          create agent
GET    /agents                          list agents (filter: dept, status, type)
GET    /agents/{id}                     get agent
PUT    /agents/{id}                     update agent (creates version snapshot)
DELETE /agents/{id}                     soft delete (status = 'deleted')
POST   /agents/{id}/test                body: {message} → stream execution trace
GET    /agents/{id}/performance         aggregated metrics from execution_traces
GET    /agents/{id}/versions            version history
POST   /agents/{id}/clone               create a copy
GET    /agents/templates                list templates
POST   /agents/from-template/{id}       create agent from template
```

---

## How Agents Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Mission Engine | Router reads `agents` DB to assign tasks. Executor loads `system_prompt`, `tools[]`, `model` from agents DB. |
| Tools | `agent.tools[]` = allowed tools. Executor checks this list before dispatching any tool call. Builder shows tools as nodes. |
| Departments | `agent.department_id` links agent to dept. Dept Overview shows its agents. Dept Members tab manages this link. |
| Knowledge | `agent.memory_enabled` → memory runs after each task. `document_rag` tool in `tools[]` → searches knowledge base. |
| Approvals | `agent.permissions` defines when approval triggers. Executor checks permissions before high-stakes actions. |
| Observability | Every agent run → `execution_traces` rows. Performance tab reads those traces aggregated by `agent_id`. |
| Settings | `agent.model` uses LLM from user's API keys (stored in Settings). |
| Command Center | Live Agent Tree shows real `agent.name` values from DB as tasks are assigned. |

---

## Default Agents to Seed in DB

| Type | Name | System Prompt Summary |
|------|------|-----------------------|
| research | Research Agent | "Find accurate, current information using web search. Summarize findings clearly." |
| marketing | Marketing Agent | "Create compelling marketing content and strategies. Be creative and data-driven." |
| finance | Financial Analyst | "Analyze financial data, build projections, and provide clear financial recommendations." |
| analysis | Analysis Agent | "Analyze data and information. Find patterns, draw insights, and present conclusions clearly." |
| writing | Writing Agent | "Write clear, well-structured content. Match the requested format and tone." |
| operations | Operations Agent | "Plan and optimize operational workflows. Be systematic and practical." |
| general | General Agent | "Handle any task intelligently and thoroughly. Ask for clarification if needed." |

---

## Build Order

**Phase 2 (after Mission Engine):**
1. DB tables (agents, agent_templates, agent_versions) + seed 7 defaults + 7 templates
2. CRUD endpoints
3. Wire Agent Overview (`GET /agents`)
4. Wire Agent Create form (`POST /agents`, AI-Assisted mode)
5. Wire Agent Templates (`GET /agents/templates` + `POST /agents/from-template/{id}`)
6. `POST /agents/{id}/test` endpoint + stream trace + wire Testing view
7. `GET /agents/{id}/performance` aggregation + wire Performance view
8. Wire Agent Settings (`PUT /agents/{id}`, version history)
9. Wire Agent Builder (sub_agents + tools visual edit → `PUT /agents/{id}`)
