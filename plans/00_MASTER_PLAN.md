# 00 — MASTER INTEGRATION PLAN
# How All 16 Plans Connect Into One System

---

## System Identity

Orion is an **AI company operating system**.

A user creates AI Agents, gives them Tools, organizes them into Departments, and assigns them Goals (Missions). Agents work autonomously to complete those goals using their tools and knowledge. Humans review key decisions through the Approvals gate. Everything that happens is recorded in Observability. The business outcomes accumulate in Operations. Users are alerted to important events via Notifications.

**The system in one sentence:** You describe what you want done → AI agents do it → you see everything that happened and approve any decisions that need a human.

---

## The Complete System Flow
### Tracing One Request Through All Plans

(This trace shows the 12 operational plans in sequence. Plan 13 — LLM Provider —
runs invisibly inside every "LLM call" step below. Plan 16 — Error Handling —
governs what happens if any step fails. Plan 14 — Mission Results — is where the
user reviews the output afterward. Plan 15 — Dashboard — is where the completed
mission's count and insights surface.)

User types: **"Analyze my top 5 competitors and suggest a pricing strategy"**

```
STEP 1 — AUTH PLAN
  System checks: Authorization: Bearer {token}
  Extracts: user_id = "usr_abc123"
  Provides to all downstream: user identity, ownership

STEP 2 — SETTINGS PLAN
  Mission Engine loads user's API keys from MongoDB:
  { groq_api_key: "gsk_...", serper_api_key: "srp_..." }
  These will be used for every LLM call and web_search call in this mission

STEP 3 — COMMAND CENTER PLAN (UI layer)
  User clicks Send
  Frontend calls POST /missions { prompt: "Analyze my top 5 competitors..." }
  Frontend connects: WS /ws/missions/{mission_id}
  Live Agent Tree initializes, waiting for first events

STEP 4 — MISSION ENGINE PLAN — PLANNER
  One LLM call (Groq, fast model, user's groq_api_key)
  Output: task list
    Task 1: "Find top 5 competitors"        → research, web_search,  depends_on: []
    Task 2: "Get competitor pricing"         → research, web_search,  depends_on: []
    Task 3: "Compare pricing strategies"     → analysis, document_rag, depends_on: [T1,T2]
    Task 4: "Write pricing recommendations"  → writing, none,          depends_on: [T3]
  
  WS emits: task_created × 4
  Command Center: Live Agent Tree builds 4 nodes

STEP 5 — AGENTS PLAN (read by Router)
  Tasks 1,2 → Router queries agents DB: type='research'
    → finds user's "Research Agent" (custom, Research Dept)
    → both tasks assigned to this agent (run in parallel)
  Task 3 → Router queries: type='analysis'
    → finds system default "Analysis Agent"
  Task 4 → Router queries: type='writing'
    → finds system default "Writing Agent"
  
  WS emits: task_started × 2 (T1 and T2 in parallel)
  Command Center: Research Agent node pulses green × 2

STEP 6a — TOOLS PLAN (T1 executing)
  Research Agent's LLM responds with tool call:
    { "tool": "web_search", "input": { "query": "top competitors in [business]" } }
  Executor checks: "web_search" in Research Agent's tools[] → yes
  Tool Registry: dispatch web_search → Serper API (user's serper_api_key)
  Returns: 10 search results with business names, descriptions, URLs
  
  WS emits: tool_call (web_search), tool_result
  Command Center: "Web Search" chip appears in Tools Being Used panel

STEP 6b — TOOLS PLAN (T2 executing in parallel)
  Research Agent (second instance) calls web_search("competitor pricing")
  Returns: pricing pages, price lists

STEP 7 — KNOWLEDGE PLAN (during T1, T2, T3)
  Before Task 1 starts:
    Memory retrieval: search ChromaDB for Research Agent's memories
    matching "competitors" → finds memory from 2 weeks ago about similar research
    Prepended to prompt: "What you remember: [previous findings]"
  
  After Task 1 completes:
    Memory extraction: key facts stored in ChromaDB
    "Found 5 main competitors: [names]. Market has 3 premium, 2 budget players."
  
  Task 3: Analysis Agent calls document_rag("competitor analysis")
    → searches ChromaDB → finds uploaded business plan PDF
    → returns relevant passages about market positioning
    → Agent uses these as additional context

STEP 8 — DEPARTMENTS PLAN (routing influence)
  User had set department_id = "Research Dept" on this mission
  Router preferred Research Agent from Research Dept (step 5)
  After completion: mission activity appears in Research Dept's Activity tab

STEP 9 — APPROVALS PLAN (mid-T4)
  Writing Agent finishes report and wants to post it to Slack
  Calls: { "tool": "request_approval", "input": { "title": "Post pricing report to #strategy" } }
  
  Executor: creates decision row (status=pending)
  Task 4: status → waiting_approval (paused)
  
  WS emits: approval_required { decision_id, title, priority: "medium" }
  Command Center: inline approval card appears in chat
  Approvals sidebar: badge count → 1
  Notifications: new notification "Approval required: Post to Slack"
  
  User clicks Approve in Command Center inline card
  POST /decisions/{id}/approve
  audit_logs row created
  Task 4 resumes

STEP 10 — OBSERVABILITY PLAN (throughout entire execution)
  execution_traces rows created for every step:
  - Planner LLM call: provider=groq, model=llama-3.1-8b, tokens=400, latency=820ms
  - T1 LLM call: provider=groq, model=llama-3.1-70b, tokens=1200, latency=2100ms
  - T1 web_search: tool=web_search, latency=1340ms, success=true
  - T2 LLM call: similar
  - T2 web_search: similar
  - T3 LLM call: provider=groq, tokens=2400, latency=3200ms
  - T3 document_rag: tool=document_rag, latency=340ms, success=true
  - T4 LLM call: provider=groq, tokens=1800, latency=2600ms
  Total: 8 trace rows, ~$0.04 cost
  
  Observability Dashboard: total_runs++, cost+=$0.04, success_rate recalculated

STEP 11 — OPERATIONS PLAN (after mission_completed)
  Post-mission processor runs
  Task 3 result classified: type=research_output, department=research
  Task 4 result classified: type=research_output, department=research (pricing strategy doc)
  Both stored in operations_data
  Operations/Research tab: new entry "Competitor Pricing Analysis — [date]"

STEP 12 — NOTIFICATIONS PLAN (final step)
  create_notification(user_id, "mission_completed", "Mission completed",
    "Competitor analysis and pricing strategy ready", "mission", mission_id)
  
  Notification appears in Notifications section
  If user is on another screen: bell badge shows 1
  User clicks → "View Mission" → sees full results
```

---

## The Connection Map

For each plan: what it reads from others and what it writes to others.

```
Plan                  READS FROM              WRITES TO
──────────────────────────────────────────────────────────────────────────
Auth               MongoDB users             user_id (to all plans)
Settings           Auth (user_id)            api_keys (to Mission Engine, Tools)
Command Center     Mission Engine (WS)       POST /missions (to Mission Engine)
                   Missions (history)        Inline approvals (to Approvals)
Mission Engine     Auth, Settings            missions, mission_tasks tables
                   Agents (router)           execution_traces (to Observability)
                   Tools (executor)          operations_data (post-processor)
                   Knowledge (memory)        notifications (create_notification)
                   Departments (routing)     decisions (approval trigger)
Agents             Mission Engine (reads     agents table
                   for router/executor)      agent_templates, agent_versions
Tools              Mission Engine (called    tool registry (read by executor)
                   by executor)              execution_traces (trace per call)
Knowledge          Mission Engine (read      documents, memory_entries tables
                   by memory+doc_rag)        ChromaDB collections
Departments        Agents (owns them)        departments table
                   Missions (organizes)      dept activity (reads mission_tasks)
Approvals          Mission Engine            decisions, audit_logs tables
                   (triggered by executor)   notifications (approval_required)
Observability      execution_traces          (nothing — pure reader)
                   audit_logs
                   missions, agents (joins)
Operations         operations_data           (nothing — pure reader)
                   (written by Mission Eng)
Notifications      All plans                 notifications table
                   (event sources)           sidebar badge counts
LLM Provider       Settings (user keys)      execution_traces (provider/model/
                   Mission Engine (callers)    tokens/cost per call)
Mission Results    Mission Engine (missions, (nothing — pure reader + export)
   (Missions UI)    mission_tasks, traces)
Dashboard          All plans (aggregates     (nothing — pure reader + nav)
                   missions/agents/decisions/
                   notifications/operations)
Error Handling     All plans (catches        execution_traces (error rows)
                   failures everywhere)       notifications (failure alerts)
```

---

## The Single Database View

All tables across all plans in one place:

### MongoDB Atlas (user data)
```
users               ← Auth Plan
  _id, email, full_name, password_hash, created_at
  api_keys: { groq, gemini, openai, serper, google_places }  ← Settings Plan
  preferences: { theme, language, notifications }  ← Settings Plan
```

### SQLite (agent/mission/operational data)
```
missions            ← Mission Engine Plan
  id, prompt, title, status, department_id, created_by, created_at, completed_at

mission_tasks       ← Mission Engine Plan
  id, mission_id, title, agent_type, agent_id, tools_needed, depends_on,
  status, result, created_at, completed_at

execution_traces    ← Mission Engine Plan (written by Executor)
  id, mission_id, task_id, agent_id, trace_type, provider, model,
  input_tokens, output_tokens, cost_usd, tool_name, tool_input, tool_output,
  latency_ms, success, error_message, created_at

agents              ← Agents Plan
  id, name, purpose, system_prompt, agent_type, tools, sub_agents,
  department_id, model, temperature, memory_enabled, memory_ttl_days,
  permissions, status, version, created_by, created_at, updated_at

agent_templates     ← Agents Plan
  id, name, description, category, base_config, tags, is_featured

agent_versions      ← Agents Plan
  id, agent_id, version, config, note, created_by, created_at

tools               ← Tools Plan
  id, name, description, type, category, input_schema, config, enabled

departments         ← Departments Plan
  id, name, purpose, icon, color, agent_ids, knowledge_collection_id,
  created_by, created_at, updated_at, status

decisions           ← Approvals Plan
  id, mission_id, task_id, agent_id, title, description, priority,
  proposed_action, expected_impact, evidence, status,
  created_at, resolved_at, resolved_by, resolution_reason

audit_logs          ← Approvals Plan
  id, decision_id, action, by, reason, created_at

documents           ← Knowledge Plan
  id, name, type, file_path, size_bytes, status, department_id,
  chroma_collection_id, uploaded_by, uploaded_at

memory_entries      ← Knowledge Plan
  id, agent_id, department_id, content, chroma_id,
  source_mission_id, created_at, expires_at

operations_data     ← Operations Plan
  id, type, department, title, data, source_mission_id,
  source_task_id, created_by, created_at

notifications       ← Notifications Plan
  id, user_id, type, title, description, entity_type,
  entity_id, priority, read, created_at
```

### ChromaDB (vector data)
```
Collection: documents_{user_id}     ← Knowledge Plan (document chunks)
Collection: memory_{agent_id}       ← Knowledge Plan (agent memories)
Collection: api_cache               ← (existing: caches external API results)
```

### Note on Plans 13–16 (no new tables)
```
LLM Provider (13)    → writes to existing execution_traces. No new table.
Mission Results (14) → pure reader of missions/mission_tasks/execution_traces. No new table.
Dashboard (15)       → pure reader, aggregates existing tables. No new table.
Error Handling (16)  → writes error rows to existing execution_traces. No new table.
```
These four plans add behavior and UI, not storage. The 15 tables above are the
complete data model for the entire 16-plan system.

---

## The Complete API Map

All ~65 endpoints grouped by plan:

### Auth (6)
```
POST /auth/signup
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
PUT  /auth/me
```

### Settings (4)
```
GET    /settings/api-keys
PUT    /settings/api-keys
DELETE /settings/api-keys/{provider}
PUT    /auth/password
```

### Missions / Command Center (5)
```
POST   /missions
GET    /missions
GET    /missions/{id}
DELETE /missions/{id}
WS     /ws/missions/{id}
```

### Agents (11)
```
POST   /agents
GET    /agents
GET    /agents/{id}
PUT    /agents/{id}
DELETE /agents/{id}
POST   /agents/{id}/test
GET    /agents/{id}/performance
GET    /agents/{id}/versions
POST   /agents/{id}/clone
GET    /agents/templates
POST   /agents/from-template/{id}
```

### Tools (8)
```
GET    /tools
POST   /tools/custom
PUT    /tools/{id}
DELETE /tools/{id}
POST   /tools/execute
GET    /tools/mcp
POST   /tools/mcp
DELETE /tools/mcp/{id}
```

### Knowledge (9)
```
POST   /knowledge/documents
POST   /knowledge/documents/url
GET    /knowledge/documents
GET    /knowledge/documents/{id}
DELETE /knowledge/documents/{id}
POST   /knowledge/search
GET    /knowledge/memory
DELETE /knowledge/memory/{id}
DELETE /knowledge/memory/agent/{id}
```

### Departments (8)
```
POST   /departments/propose
POST   /departments
GET    /departments
GET    /departments/{id}
PUT    /departments/{id}
DELETE /departments/{id}
GET    /departments/{id}/activity
POST   /departments/{id}/agents
DELETE /departments/{id}/agents/{agent_id}
```

### Approvals (5)
```
GET    /decisions
GET    /decisions/{id}
GET    /decisions/count
POST   /decisions/{id}/approve
POST   /decisions/{id}/reject
POST   /decisions/{id}/return
```

### Observability (7)
```
GET    /observability/summary
GET    /observability/runs
GET    /observability/runs/{id}/trace
GET    /observability/llm
GET    /observability/tools
GET    /observability/errors
GET    /observability/audit
```

### Operations (3)
```
GET    /operations/summary
GET    /operations/feed
GET    /operations/{category}
```

### Notifications (4)
```
GET    /notifications
GET    /notifications/count
POST   /notifications/{id}/read
POST   /notifications/read-all
```

### System (1)
```
GET    /health
```

### Mission Results — additional (Plan 14) (3)
```
GET    /missions/{id}/tools         aggregated tool stats for this mission
GET    /missions/{id}/evidence      tool outputs as evidence trail
GET    /missions/{id}/export.json   raw JSON export
```
(The HTML/PDF report endpoints `/missions/{id}/report` and `/report.pdf`
 are adapted from the existing `/sessions/{id}/report` endpoints.)

### Dashboard — optional aggregation (Plan 15) (1)
```
GET    /dashboard/summary           single call: metrics + activity + insights + approvals
```

### LLM Provider (Plan 13) & Error Handling (Plan 16)
```
No public endpoints. LLM Provider is an internal service (exposed only via
/health). Error Handling is a cross-cutting concern (no endpoints of its own —
it governs how every endpoint behaves on failure).
```

**Total: ~75 endpoints**

---

## The Build Dependency Chain

```
Auth (DONE)
  └─► Settings (API keys storage)
        └─► Mission Engine ◄─────────────────── THE CRITICAL PATH
              │  (requires: default agents seeded, web_search tool)
              │
              ├─► Command Center (UI layer over Mission Engine)
              │
              ├─► Agents CRUD ──────────────────► Agent Builder/Templates/Test/Perf/Settings
              │         └─► Departments ──────────► Dept Views
              │
              ├─► Tools (full registry) ─────────► MCP/Custom/Toolbox views
              │         └─► Knowledge ──────────────► Upload/Memory views
              │
              ├─► Approvals ────────────────────────► Inline cards in Command Center
              │
              └─► Observability ────────────────────► All 9 obs sub-views
                        └─► Operations ──────────────► All 10 ops sub-views
                                  └─► Notifications ──► Badges + notification views
```

**If Mission Engine is not built, nothing else can be built.**
Every other plan requires missions to be running to have any real data.

---

## The Phased Build Plan

### PHASE 1 — Weeks 1–3: The System Does Real Work
**Build:** Mission Engine core (Planner + Router + Executor), default agents seeded, web_search + document_rag tools, WebSocket streaming, Command Center wired, Missions list wired, Settings API keys endpoint, execution_traces logging

**What works at end:** User types a goal → agents run → results appear live → history saved

**Plans activated:** Auth, Settings (partial), Mission Engine, Command Center, Agents (defaults only)

---

### PHASE 2 — Weeks 4–5: Dynamic Agent System
**Build:** agents CRUD + versions, agent_templates seeded (7), test endpoint, performance aggregation, wire all 7 agent sub-tabs, agent Builder (sub-agent graph)

**What works at end:** Users create custom agents, test them, track performance, build multi-agent hierarchies

**Plans activated:** Agents (full)

---

### PHASE 3 — Week 6: Organizational Structure
**Build:** departments table, AI-proposal creation flow, CRUD endpoints, wire all dept views (Overview, Activity, Members, Settings), wire Create Department chat UI

**What works at end:** Agents organized into departments. Department-scoped missions route to dept agents. Dept activity feeds populate.

**Plans activated:** Departments (full)

---

### PHASE 4 — Weeks 7–8: Real-World Grounding
**Build:** Full tool registry UI, maps_api tool, http_request tool, MCP client (connect server → discover tools → proxy calls), custom tool registration, document upload pipeline (parse → chunk → embed → ChromaDB), memory extraction/retrieval in Executor, wire all Tool and Knowledge views, wire API Keys in Settings

**What works at end:** Agents use 5+ real tools. Users upload documents agents reference. Agents remember across missions. Users bring own API keys.

**Plans activated:** Tools (full), Knowledge (full), Settings (full)

---

### PHASE 5 — Weeks 9–10: Safety and Transparency
**Build:** decisions + audit_logs tables, `request_approval` virtual tool in Executor, task pause/resume, approval endpoints, wire Approvals view, inline approval cards in Command Center, observability aggregation endpoints, wire all 7 observability views (Dashboard, Runs, Trace, LLM, Tools, Errors, Audit)

**What works at end:** Human oversight on agent actions. Full execution traces visible. Every token and cost tracked.

**Plans activated:** Approvals (full), Observability (full)

---

### PHASE 6 — Week 11: System Feels Complete
**Build:** operations_data table + post-mission classifier + wire 10 ops views, notifications table + event functions + wire Notifications + real sidebar badges, wire Settings Profile, remove ALL hardcoded mock data from every view (replace with real API calls), error/loading/empty states for every view, fix Topbar (real user name, real date)

**What works at end:** The entire system shows real data. No mock data anywhere. Every section is live.

**Plans activated:** Operations (full), Notifications (full), Settings (full polish)

---

## The Frontend Wiring Checklist

Every view and its wiring status + which endpoint it needs + which phase:

| View | Current State | Endpoint Needed | Phase |
|------|--------------|-----------------|-------|
| Dashboard | Mock data | `GET /missions` + `GET /observability/summary` | 6 |
| Command Center | Not wired | `POST /missions` + `WS /ws/missions/{id}` | 1 |
| Missions list | Not wired | `GET /missions` | 1 |
| Mission Details | Not wired | `GET /missions/{id}` | 1 |
| Approvals | Not wired | `GET /decisions`, approve/reject/return | 5 |
| Notifications | Not wired | `GET /notifications` | 6 |
| Departments list | Not wired | `GET /departments` | 3 |
| Dept Overview (×6) | Not wired | `GET /departments/{id}` | 3 |
| Dept Activity (×6) | Not wired | `GET /departments/{id}/activity` | 3 |
| Dept Members (×6) | Not wired | `GET /departments/{id}` + member management | 3 |
| Create Department | Not wired | `POST /departments/propose` + confirm | 3 |
| Agents Overview | Not wired | `GET /agents` | 2 |
| Agent Create | Not wired | `POST /agents` | 2 |
| Agent Builder | Not wired | `PUT /agents/{id}` | 2 |
| Agent Templates | Not wired | `GET /agents/templates` | 2 |
| Agent Testing | Not wired | `POST /agents/{id}/test` | 2 |
| Agent Performance | Not wired | `GET /agents/{id}/performance` | 2 |
| Agent Settings | Not wired | `PUT /agents/{id}` | 2 |
| Toolbox | Not wired | `GET /tools` | 4 |
| MCP Servers | Not wired | `GET /tools/mcp` + connect | 4 |
| Integrations | Coming Soon | — | defer |
| Custom Tools | Not wired | `POST /tools/custom` | 4 |
| API Keys (Tools) | Not wired | `GET/PUT /settings/api-keys` | 1 |
| Knowledge Base | Not wired | `GET /knowledge/documents` | 4 |
| Upload Sources | Not wired | `POST /knowledge/documents` | 4 |
| Memory Overview | Not wired | `GET /knowledge/memory` | 4 |
| Operations Overview | Not wired | `GET /operations/summary` | 6 |
| Operations Finance | Not wired | `GET /operations/finance` | 6 |
| Operations Marketing | Not wired | `GET /operations/marketing` | 6 |
| Operations Sales | Not wired | `GET /operations/sales` | 6 |
| Operations (×6 more) | Not wired | `GET /operations/{category}` | 6 |
| Obs Dashboard | Not wired | `GET /observability/summary` | 5 |
| Obs Runs | Not wired | `GET /observability/runs` | 5 |
| Obs Trace | Not wired | `GET /observability/runs/{id}/trace` | 5 |
| Obs LLM Usage | Not wired | `GET /observability/llm` | 5 |
| Obs Tools | Not wired | `GET /observability/tools` | 5 |
| Obs Errors | Not wired | `GET /observability/errors` | 5 |
| Obs Audit | Not wired | `GET /observability/audit` | 5 |
| Settings Profile | Not wired | `GET/PUT /auth/me` | 6 |
| Settings API Access | Not wired | `GET/PUT /settings/api-keys` | 1 |
| Settings Security | Not wired | `PUT /auth/password` | 3 |
| Settings Billing | Remove/defer | — | never |
| Settings Workspace | Remove/defer | — | never |
| Settings Logout | ✅ Works | onLogout prop | done |

---

## What to Remove or Defer

### Remove from MVP
| Item | Action |
|------|--------|
| Billing sub-tab | Replace content with "Free Plan — bring your own API keys" static card |
| Workspace / Team sub-tab | Replace with "Coming Soon — team features" static card |
| OAuth buttons in SignIn/SignUp | Keep buttons, show "Not available yet — use email" message (already done) |
| Hardcoded "12" notification badge | Remove number until Notifications is wired (Phase 6) |
| Integration marketplace | Show "Coming Soon" badges on all non-working integrations |
| Hardcoded "Abhishek" in Topbar | Replace with real user name from auth object (Phase 6) |
| Hardcoded date in Topbar | Replace with `new Date().toLocaleDateString()` (Phase 6) |

### Defer to After v1
| Item | Reason |
|------|--------|
| Agent versioning (version history) | Nice-to-have. Build basic CRUD first. |
| Memory Details/Settings views | Build Memory Overview first. |
| Evaluations (Obs sub-tab) | Needs judge LLM + significant usage data. |
| Website analytics (Ops/Obs sub-tabs) | Not core to the system value. |
| Custom tool code editor | Security risk. URL-based custom tools are sufficient. |
| Password reset flow | Email sending infrastructure needed. |
| Email verification | Email sending infrastructure needed. |

---

## The Three Rules Every Decision Must Follow

### Rule 1: Everything Serves the Mission
Every feature exists either to help missions run better or to show what missions produced. When evaluating whether to build something, ask: "Does this make missions better or more visible?" If no — defer it.

### Rule 2: The System is Dynamic Because Agents Live in the Database
The reason the system is not a fixed pipeline is that agents are stored in the DB, not hardcoded. The Task Router queries the DB at runtime. This means: any user can create a new agent → it is immediately available for future missions. This principle must be preserved in all design decisions. Never hardcode agent behavior into the mission flow.

### Rule 3: Build Mission Engine First
A working Command Center → Mission Engine → real result is more valuable than any other combination of features. A user who can type a goal and watch agents work in real time is using the core value of the system. Departments, builder, templates, tools, knowledge — all of these make it better, more powerful, more organized. But without Mission Engine, the system does nothing.

---

## The Final Vision

When all 6 phases are complete, here is what a user experiences:

```
DAY 1:
  Signs up → customizes their agent library (create 3-4 agents from templates)
  Organizes agents into departments (Marketing, Research)
  Uploads their business plan PDF to Knowledge Base
  Types: "Research my 5 top competitors" → watches agents work live → results in 90 seconds

DAY 3:
  Creates a custom "Competitive Intelligence Agent" with specific instructions
  Tests it using Agent Testing → iterates on the system prompt
  Deploys it → it runs on the next competitor research mission

WEEK 2:
  Connects a Notion MCP server → agents can write to Notion
  Next mission result automatically written to Notion workspace
  Approval required → user reviews → approves → Notion page created

MONTH 1:
  Opens Observability → sees 47 missions run, $2.40 total cost, 96% success rate
  Sees Operations/Marketing → 4 campaign strategies accumulated
  Opens Knowledge/Memory → agents have built up 200+ memory entries
  System is getting smarter every time agents run
  
THE COMPLETE PICTURE:
  A real AI-powered company operating system that the user owns and controls.
  Every agent is theirs. Every tool they connected. Every department they designed.
  The system runs their business logic while they stay in control of every consequential decision.
```

---

## Plan Index

| File | Section | Build Phase |
|------|---------|-------------|
| `01_AUTH_PLAN.md` | Auth & User Identity | Done |
| `02_SETTINGS_PLAN.md` | Settings & API Keys | Phase 1 (partial) + Phase 6 |
| `03_COMMAND_CENTER_PLAN.md` | Command Center | Phase 1 |
| `04_MISSION_ENGINE_PLAN.md` | Mission Engine (THE CORE) | Phase 1 |
| `05_AGENTS_PLAN.md` | Agent Management | Phase 2 |
| `06_TOOLS_PLAN.md` | Tools | Phase 1 (basics) + Phase 4 (full) |
| `07_KNOWLEDGE_PLAN.md` | Knowledge Base & Memory | Phase 4 |
| `08_DEPARTMENTS_PLAN.md` | Departments | Phase 3 |
| `09_APPROVALS_PLAN.md` | Approvals & HITL | Phase 5 |
| `10_OBSERVABILITY_PLAN.md` | Observability | Phase 5 |
| `11_OPERATIONS_PLAN.md` | Operations Dashboard | Phase 6 |
| `12_NOTIFICATIONS_PLAN.md` | Notifications | Phase 6 |
| `13_LLM_PROVIDER_PLAN.md` | LLM Provider Chain | Phase 1 (foundation) |
| `14_MISSION_RESULTS_PLAN.md` | Mission Results UI | Phase 1 (basic) + Phase 2+ |
| `15_DASHBOARD_PLAN.md` | Dashboard (Home Screen) | Phase 6 |
| `16_ERROR_HANDLING_PLAN.md` | Error Handling (all layers) | All phases (cross-cutting) |
| `00_MASTER_PLAN.md` | This document | — |

> See the ADDENDUM below for how plans 13–16 close the gaps found in the
> original 12 and where they slot into each build phase.


---

## ADDENDUM — 4 New Plans (Plans 13–16)

After reviewing all 12 original plans, 4 gaps were identified where the plans referenced concepts without fully documenting them. Four additional plans were written to close these gaps.

---

### Gap 1 — LLM Provider Layer (Plan 13)

**What was missing:** Plans 02, 04, and 05 all say "call LLM via Groq→Gemini→Ollama chain" but none defined how this chain works internally. No plan covered: provider selection logic, rate limit tracking, cost calculation, JSON repair on malformed responses, or how user API keys take priority over system keys.

**Plan written:** `13_LLM_PROVIDER_PLAN.md`

**What it covers:**
- The three providers (Groq primary, Gemini fallback, Ollama last resort) and their free-tier limits
- The two call tiers (`fast` for planner/classifier, `reasoning` for main agent execution) and which model each tier uses per provider
- The fallback chain: user keys first → system keys → Ollama
- In-memory rate limit tracking with per-provider reset schedules
- Cost calculation per call stored in `execution_traces.cost_usd`
- JSON repair pipeline for structured calls (extract from markdown → repair prompt → fail)
- How this connects to Settings (user keys), Mission Engine (every LLM call), Observability (LLM Usage tab)

**Where it fits in the build:**
Phase 1 — must exist before Mission Engine can run. Phase 4 addition: load user keys from MongoDB.

---

### Gap 2 — Mission Results / Missions UI (Plan 14)

**What was missing:** Plan 03 (Command Center) covers the input side. Plan 04 (Mission Engine) covers execution. But the **Missions section UI** — the list view, the 7-tab detail view, downloading reports, viewing the execution graph — had no plan. It was referenced in passing but never designed.

**Plan written:** `14_MISSION_RESULTS_PLAN.md`

**What it covers:**
- Missions List screen: table of all missions with type badge, agent avatars, progress bar, status, filters, search, Selected Mission Preview bar
- Mission Details screen: 7 tabs (Overview/Tasks/Agents/Tools/Evidence/Results/Trace)
- The execution graph in Overview tab: SVG with orchestrator → agent nodes → leaf tasks, colored by status
- The Results tab: formatted task output cards with rendered markdown, key data highlighted
- Download/export: HTML Report, PDF, JSON export endpoints
- Real-time updates: polling every 2s for running missions, Stop Mission button
- New endpoints needed: `GET /missions/{id}/tools`, `GET /missions/{id}/evidence`, `GET /missions/{id}/export.json`

**Where it fits in the build:**
Phase 1 (basic list + basic detail), Phase 2 (richer detail + downloads), Phase 5 (Trace tab), Phase 6 (Evidence tab, search/filter)

---

### Gap 3 — Dashboard (Plan 15)

**What was missing:** The Dashboard (`ViewDashboard`) was listed in the master wiring checklist but had no plan. It aggregates data from almost every other plan. Without a plan, there was no guidance on what data it needs, where it comes from, or how the navigation shortcuts work.

**Plan written:** `15_DASHBOARD_PLAN.md`

**What it covers:**
- Welcome Banner: user name from `GET /auth/me` (not hardcoded)
- 4 KPI cards: Active Missions, Agents Online, Pending Approvals, System Health — each with real data source and click navigation
- Live Agent Network: SVG ellipse built from real `GET /agents` list
- Recent Activity: `GET /notifications?limit=5`
- Key Insights: 2-3 summaries from `GET /operations/feed?type=research_output&limit=3`
- Pending Approvals widget: `GET /decisions?status=pending&limit=3`
- Navigation role: every element is also a shortcut to the relevant section
- Optional `GET /dashboard/summary` aggregation endpoint for performance
- Why Phase 6: Dashboard only makes sense after other sections have real data

**Where it fits in the build:**
Phase 6 (polish) — built last after all sections have real data.

---

### Gap 4 — Error Handling (Plan 16)

**What was missing:** Every plan described the happy path. None described what happens when things fail. LLM failures, tool failures, mission timeouts, WebSocket drops, database errors, stuck missions — all cross-cutting concerns that belonged to no single plan, so none addressed them.

**Plan written:** `16_ERROR_HANDLING_PLAN.md`

**What it covers:**
- Layer 1 (LLM failures): 429/503 → invisible fallback, all providers down → user message, JSON repair pipeline
- Layer 2 (Tool failures): retry up to 2×, degraded mode (web_search fails → LLM-only with banner), custom tool hard failure
- Layer 3 (Task failures): agent loop detection (10-call limit), task timeout (120s), context window overflow → truncate, approval rejected → task cancelled
- Layer 4 (Mission failures): planner JSON failure, all tasks fail → partial results, mission timeout (600s), WebSocket drop → mission continues server-side
- Layer 5 (Infrastructure): SQLite retry, ChromaDB graceful degradation, MongoDB reconnect, stuck mission cleanup on startup
- Layer 6 (User errors): empty prompt, vague goal, unsupported file type, expired decision
- Frontend error states: every view needs loading/empty/error states
- Rule: log everything, surface only what the user can act on
- Error code reference table

**Where it fits in the build:**
Not a phase — built alongside every other phase. Phase 1 gets LLM fallback + mission failure events. Phase 3 gets tool retries. Phase 5 gets approval expiry. Phase 6 gets complete empty/error states for all views.

---

## Updated Plan Index (16 Plans Total)

| File | Section | Build Phase |
|------|---------|-------------|
| `01_AUTH_PLAN.md` | Auth & User Identity | Done |
| `02_SETTINGS_PLAN.md` | Settings & API Keys | Phase 1 (partial) + Phase 6 |
| `03_COMMAND_CENTER_PLAN.md` | Command Center | Phase 1 |
| `04_MISSION_ENGINE_PLAN.md` | Mission Engine — THE CORE | Phase 1 |
| `05_AGENTS_PLAN.md` | Agent Management | Phase 2 |
| `06_TOOLS_PLAN.md` | Tools | Phase 1 (basics) + Phase 4 (full) |
| `07_KNOWLEDGE_PLAN.md` | Knowledge Base & Memory | Phase 4 |
| `08_DEPARTMENTS_PLAN.md` | Departments | Phase 3 |
| `09_APPROVALS_PLAN.md` | Approvals & HITL | Phase 5 |
| `10_OBSERVABILITY_PLAN.md` | Observability | Phase 5 |
| `11_OPERATIONS_PLAN.md` | Operations Dashboard | Phase 6 |
| `12_NOTIFICATIONS_PLAN.md` | Notifications | Phase 6 |
| `13_LLM_PROVIDER_PLAN.md` | LLM Provider Chain | Phase 1 (foundation) |
| `14_MISSION_RESULTS_PLAN.md` | Mission Results UI | Phase 1 (basic) + Phase 2+ |
| `15_DASHBOARD_PLAN.md` | Dashboard (Home Screen) | Phase 6 |
| `16_ERROR_HANDLING_PLAN.md` | Error Handling (all layers) | All phases (cross-cutting) |
| `00_MASTER_PLAN.md` | Master Integration Plan | — |

---

## Updated Build Phase Summary (with new plans integrated)

### Phase 1 — Weeks 1–3: The System Does Real Work
**New plans now covered:** 13 (LLM Provider), 14 (Mission Results basic), 16 (Error handling Layer 1)
- LLM Provider chain built first (Plan 13)
- Mission Engine built on top of it (Plan 04)
- Command Center wired (Plan 03)
- Missions list + basic detail wired (Plan 14)
- LLM failure fallback + mission failed WS event (Plan 16)

### Phase 2 — Weeks 4–5: Dynamic Agent System
**New plans now covered:** 14 (Mission Results full detail + downloads)
- Agent management (Plan 05)
- Mission Details 7 tabs fully wired (Plan 14)
- HTML/PDF/JSON export (Plan 14)

### Phase 3 — Week 6: Organizational Structure
- Departments (Plan 08)
- Tool retry logic + degraded mode banners (Plan 16)

### Phase 4 — Weeks 7–8: Real-World Grounding
- Tools full + MCP + Custom (Plan 06)
- Knowledge upload + memory (Plan 07)
- User API keys → LLM Provider priority update (Plan 13)
- ChromaDB graceful degradation (Plan 16)

### Phase 5 — Weeks 9–10: Safety and Transparency
- Approvals (Plan 09)
- Observability (Plan 10)
- Frontend error/loading/empty states for all views (Plan 16)

### Phase 6 — Week 11: System Feels Complete
- Operations (Plan 11)
- Notifications (Plan 12)
- Dashboard wired with real data (Plan 15)
- Stuck mission cleanup, complete error message coverage (Plan 16)
- All mock data removed
