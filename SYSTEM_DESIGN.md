# Orion — Full System Design & Vision Document

---

## What Orion Actually Is

One sentence: **You describe a business in plain English → Orion builds the plan, then runs the company.**

It has two modes and they are fundamentally different:

1. **Generation** — AI generates a complete founding business plan in 60–90s (strategy, finance, brand, marketing, operations)
2. **Operating** — AI agents run that plan as a living company day-by-day on department cadences

Your frontend has a third layer: a **Platform UI** (Sidebar with Departments, Agents, Knowledge, Tools, Operations, Observability, Settings) which is the *control center* for watching and managing both modes.

---

## The Core Problem You Are Solving

A person wants to start or run a business. They do not have:
- A strategy team
- A financial analyst
- A brand designer
- A marketing team
- An operations manager

Orion gives them all of these as AI agents — **not chatbots, but agents that produce structured, actionable output** tied to a real business context.

---

## What You Currently Have (Verified)

### Backend (BUILT, 989 tests passing)
- Intent classifier (extracts business type, location, sector, budget from a sentence)
- 21 specialized agents across 5 departments (Strategy, Finance, Branding, Marketing, Operations)
- LangGraph orchestrator that runs them in the right dependency order
- Output layer (JSON plan, HTML report, PDF export)
- Operating layer (runs the plan forward: ledger, anchors, monitors, governance, scheduler)
- Planning Report layer (pre-run inspection: show what will run, cost estimate, confirm before spending quota)
- Auth system (JWT + MongoDB Atlas user accounts)
- REST API + WebSocket streaming

### Frontend (BUILT, Platform UI)
- Full Sidebar with all sections
- All 76+ view components (mostly static mock data)
- Auth flow (sign up / sign in / landing / intro)
- Legacy generation UI (removed)

---

## The Puzzle You Cannot See

You have all the pieces. The confusion is: **what connects to what, what is real vs mock, what features make sense, what is duplicate, what order to build.**

Here is the answer, feature by feature.

---

# PART 1: FEATURE ANALYSIS

---

## FEATURE 1: Command Center (Chat Interface)

### What it is
A natural language interface. User types "I want to open a cafe in Thane" → Orion runs the full 21-agent pipeline → streams progress → delivers the business plan.

### What you have
- `ViewCommandCenter.jsx` — UI exists, fully static/mock
- `POST /generate` + `WS /ws/generate` — real backend, fully working
- `streamGeneration()` in `api.js` — real WebSocket client
- `ProgressPanel`, `ReportView` components — real components from legacy UI

### What is missing
- Command Center is NOT wired to the backend
- The chat bubble UI does not call `/ws/generate`
- Progress and result are hardcoded

### Is it needed? YES — this is the PRIMARY entry point for the whole system.

### Pros
- Most intuitive entry point for users
- Backend is 100% ready
- The hard work (21 agents) is done

### Cons
- Frontend-to-backend wiring is entirely missing
- The chat UI metaphor needs thought: is it a chat that persists, or a one-shot form? Currently it looks like a chat but behaves like a form.

### Decision
Wire `ViewCommandCenter` to `WS /ws/generate`. The "chat history" can show previous missions (from `/sessions`). This is **Priority 1**.

---

## FEATURE 2: Missions (Task/Project Tracking)

### What it is
A list of all business plans ("missions") the user has generated. Each mission has agents, progress, status. Clicking one shows the execution graph and task details.

### What you have
- `ViewMissions.jsx` — UI exists, static mock data (8 hardcoded rows)
- `GET /sessions` — real backend, returns all generation runs
- `ViewMissionDetails.jsx` — shows execution graph, task details (all hardcoded)

### What is missing
- `ViewMissions` does not call `GET /sessions`
- Mission rows are fake
- The execution graph in `ViewMissionDetails` is hardcoded SVG — it should show the real agent execution trace from `AgentTrace` records stored in the session
- Status (In Progress / Completed / Not Started) is not derived from real session status

### Is it needed? YES — without this, users cannot find their generated plans.

### Pros
- Backend has all the data (`/sessions`, `/sessions/{id}`, agent traces)
- UI structure is already designed

### Cons
- The "execution graph" (live bezier SVG) is one of the most complex UI components — rendering the real 21-agent DAG with live status is significant work
- `AgentTrace` data is stored but the API does not expose it as a structured graph yet

### Decision
Phase 1: Wire missions list to `/sessions`. Phase 2: Wire mission details to session data. Phase 3 (later): Build real execution graph from agent traces.

---

## FEATURE 3: Departments (AI Department Management)

### What it is
6 AI departments (Marketing, Finance, Operations, Sales, HR, Research). Each has agents assigned to it. Users can view activity, members, settings.

### What you have
- `ViewDepartments.jsx` and all 6 × 4 dept views — all static mock data
- Backend has `app/agents/` with real department agents (strategy, finance, branding, marketing, operations)
- Backend's operating layer has `app/operating/departments.py` running dept cadences

### THE CORE CONFUSION HERE
Your frontend has **6 departments**: Marketing, Finance, Operations, Sales, HR, Research.
Your backend has **5 generation departments**: Strategy, Finance, Branding, Marketing, Operations.
Your backend's operating layer has its own **department runners**.

**These do not map 1-to-1.** This is a design mismatch.

### What it should be
The departments in the sidebar are the **operating layer departments** — the AI agents that run the company day-to-day after the plan is generated. They correspond to the operating layer, not the generation layer.

- "Sales" = an operating agent that tracks revenue, runs sales cadences
- "HR" = an operating agent that manages hiring plans from the operations agent output
- "Research" = an ongoing research agent doing market monitoring

### Is it needed? YES but needs clarification.

### Pros
- The concept is correct and powerful
- Makes Orion feel like a real company with real departments

### Cons
- The 6 frontend departments do not match the 5 backend generation departments (and this will confuse the API wiring)
- The operating layer departments are not individually accessible via API yet (only bulk via `/operating/departments`)
- "Sales" and "HR" do not exist in the current backend at all — they are frontend-only concepts

### Decision
Map clearly:
- Generation departments (Strategy, Finance, Branding, Marketing, Operations) → shown in the mission/generation context
- Operating departments (the sidebar ones) → shown in the operations/company management context
- Add Sales and HR as operating layer departments in the backend (they are natural extensions of the staffing_plan and revenue_model agents)
- Keep both but label them clearly in the UI

---

## FEATURE 4: Agents

### What it is
Create, manage, configure, test, and monitor individual AI agents.

### What you have
- 7 subtab views: Overview, Create, Builder, Templates, Testing, Performance, Settings
- `ViewAgents.jsx` — organization map + table (all static)
- `ViewCreateAgent.jsx` — form to create a new agent (not wired to anything)
- Backend: `app/agents/registry.py` has a fixed registry of 21 agents — not user-extensible

### Is it needed? PARTIALLY — with major caveats.

### The honest truth
Your current system has **fixed, hardcoded agents** built for business planning. They are not user-configurable. The "Create Agent" feature implies users can build custom agents — **this does not exist in the backend at all.**

### Pros
- Agent Builder/Templates is the most exciting product feature
- Performance and Testing tabs are directly achievable (data exists in AgentTrace records)
- Overview is achievable (wire to `/sessions` agent data)

### Cons
- "Create Agent" and "Builder" require a completely new backend: an agent definition store, dynamic agent runner, prompt template system — this is a major multi-week build
- "Templates" needs a template store
- "Testing" needs a test runner endpoint

### Decision
- **Keep**: Overview (wire to real agents), Performance (wire to AgentTrace metrics), Settings (configure existing agents' models/tiers)
- **Defer**: Create, Builder, Templates — these require new backend infrastructure. Show as "Coming Soon" for now.
- **Priority**: Medium. Get the core generation flow working first.

---

## FEATURE 5: Knowledge Base & Memory

### What it is
Documents, files, URLs that agents can reference. Memory of past agent actions.

### What you have
- `ViewKnowledgeBase.jsx`, `ViewUploadSources.jsx`, `ViewMemoryOverview/Details/Settings.jsx` — all static mock data
- Backend: `app/apis/cache.py` — ChromaDB-backed caching for competitor/market research data (NOT user documents)
- Backend: `app/operating/memory.py` — ChromaDB episodic memory for the operating layer

### Is it needed? YES — but scope it correctly.

### Pros
- ChromaDB is already set up and working
- Memory is already storing operating layer data
- Knowledge base would make agents dramatically more useful (e.g. upload your existing business docs and agents use them)

### Cons
- The current ChromaDB usage is for caching API results, not user documents
- User document ingestion (PDF parsing, chunking, embedding, retrieval) requires additional implementation
- `app/operating/memory.py` is for agent episodic memory, not user knowledge — these are different things

### Decision
Phase 1: Wire Memory views to `/operating/memory` API (already exists). Phase 2: Build document upload + ChromaDB ingestion for user knowledge. The backend has the infrastructure; it needs a new endpoint and ingestion pipeline.

---

## FEATURE 6: Tools & Integrations

### What it is
Connect external tools (Google Drive, Slack, Notion, Stripe, etc.) that agents can use.

### What you have
- `ViewToolbox.jsx`, `ViewIntegrations.jsx`, `ViewCustomTools.jsx`, `ViewApiKeys.jsx`, `ViewMcpServers.jsx` — all static mock data
- Backend: `app/apis/places.py` + `app/apis/serper.py` — two real tool integrations
- The tool integrations are hardcoded, not user-configurable

### Is it needed? YES for API Keys specifically. Others are aspirational.

### Pros
- API Keys management (store Groq, Gemini, Google Places, Serper keys) is immediately useful
- Replaces the need to manually edit `.env` files
- MCP Servers is cutting-edge (Model Context Protocol)

### Cons
- Most "integrations" (Slack, Notion, Google Drive) require OAuth flows — entirely new backend infrastructure
- Custom Tools require a tool definition/execution framework
- MCP Servers require an MCP client implementation

### Decision
- **Keep & build now**: API Keys management (store user's API keys in their MongoDB profile, use them in agents)
- **Keep UI, defer implementation**: Integrations, Custom Tools, MCP Servers — show as "Coming Soon"
- Remove brand logos for tools that are not actually integrated

---

## FEATURE 7: Operations (Business Operations Dashboard)

### What it is
Live view of the operating company: Finance, Sales, Inventory, Marketing Campaigns, CRM, HR, Research, Suppliers, Website.

### What you have
- 10 views under Operations (all static mock data)
- Backend: full operating layer (`ledger`, `anchors`, `monitors`, `scheduler`, `governance`, `loops`)
- `/operating/*` endpoints: anchors, findings, decisions, ledger, memory, departments, loops, schedule, runs

### Is it needed? YES — this is the "run the company" half of Orion's core value.

### Pros
- Backend is fully built and tested
- The data model is correct (integer paise, computed anchors, append-only ledger)
- This is what makes Orion unique — not just planning but actually operating

### Cons
- Operations views (Finance, Sales, Inventory) are much richer than what the backend currently tracks
- The operating layer tracks financial metrics but not "inventory" or "CRM" as such
- Wiring all 10 sub-views is a significant effort

### Decision
Wire the backend's operating data to the Operations views:
- Overview → `/operating/anchors` + `/operating/runs`
- Finance → `/operating/ledger` (already computed)
- Sales → revenue anchors from ledger
- Others: show real data where it exists, "Not enough data yet" where it doesn't
- The existing `BusinessView`, `WorkView` from the legacy UI have the wiring code — extract and reuse it

---

## FEATURE 8: Observability

### What it is
Monitor all agent runs: latency, token usage, costs, errors, LLM usage, evaluations, audit logs.

### What you have
- 9 views under Observability (all static mock data, use recharts)
- Backend: `AgentTrace` records stored per run in sessions — contains provider, model, tokens, latency, status
- Backend: `/sessions` returns sessions but not the detailed AgentTrace data

### Is it needed? YES — essential for a system running AI agents that cost money.

### Pros
- `AgentTrace` data is already being collected and stored
- This is the key to users understanding what their agents are doing and what it costs
- recharts is already in the frontend

### Cons
- No API endpoint exposes AgentTrace data in aggregate (would need new routes)
- "Cost" tracking assumes paid API keys — most users are on free tiers with no dollar cost
- The evaluation system (`evaluation/`) is for the research paper, not for user-facing observability

### Decision
Add a new backend endpoint: `GET /observability/runs` that aggregates AgentTrace data across sessions. Wire Dashboard, Runs, and LLM Usage views to it. Audit and Evaluations can be built later.

---

## FEATURE 9: Approvals

### What it is
Human-in-the-loop: the operating layer's governance system requires human approval for certain agent decisions (budget allocation, hiring, tool access).

### What you have
- `ViewApprovals.jsx` — static mock data, approve/reject/request changes UI
- Backend: `app/operating/governance.py` — full governance gate chain
- `/operating/decisions` endpoint — lists pending decisions
- `/operating/decisions/{id}/approve|reject|return` — approve/reject endpoints

### Is it needed? YES — this is already fully built in the backend.

### Pros
- The backend is 100% complete
- This is a genuinely useful and differentiating feature
- The UI design is good (two-column: list + detail)

### Cons
- Currently wired to the operating layer only — generation layer does not require approvals
- The mock data shows "Marketing Budget" and "Hire Data Analyst" — these come from the operating layer, which requires a running company

### Decision
Wire `ViewApprovals` directly to `/operating/decisions`. This is **one of the easiest high-impact wires** to make. Priority: High.

---

## FEATURE 10: Notifications

### What it is
System-wide notification feed: mission updates, approval requests, agent activity, errors.

### What you have
- `ViewNotifications.jsx` — static mock data
- Backend: no notifications system exists

### Is it needed? YES but it is the last thing to build.

### Pros
- Good UX — users need to know when things happen

### Cons
- Requires a notification store (new table), a notification generation service (triggered by events in generation and operating layers), and a polling or WebSocket subscription
- Nothing in the backend currently generates notifications

### Decision
Defer. Build the functional features first, then add notifications as a polish layer. For now, the "12" badge on the sidebar is misleading — either remove it or make it reflect real pending approvals count.

---

## FEATURE 11: Settings

### What it is
Profile, Workspace, Security, Billing, API Access, Preferences, Help, Logout.

### What you have
- 8 settings views (mostly static forms)
- Backend: Auth system with MongoDB, JWT, user model
- `/auth/me` endpoint returns the current user

### Is it needed? YES — Profile, Security, API Access, Logout are immediately needed.

### Pros
- Auth backend is complete
- `ViewLogout` already calls the right prop
- Profile can be wired to `/auth/me` directly

### Cons
- Billing requires a payment system (not built, not needed for MVP)
- Workspace Settings (team/members) requires multi-user support (not built)

### Decision
Build: Profile (wire to `/auth/me`), Security (password change endpoint needed), API Access (store user's LLM API keys), Logout (already works). Defer: Billing, Workspace Settings.

---

## FEATURE 12: Planning Report (Pre-run Inspection)

### What it is
Before running 21 agents and spending quota, show the user exactly what will run, in what order, on which LLM providers, at what estimated cost. Let them confirm or cancel.

### What you have
- Full backend implementation (phases.md documents it in detail)
- `app/planning/` — store, service, API, all built and tested
- The old `PlanView` in the legacy UI wired to this (now removed)

### Is it needed? YES — this is a critical UX feature for trust and cost control.

### Pros
- Backend is 100% complete
- Prevents users from accidentally burning API quota
- Shows system transparency

### Cons
- The entry point (a separate "Plan" view) may confuse users vs just having "inspect before run" inside Command Center
- The report is text/JSON-heavy — needs good UI to make it readable

### Decision
Integrate Planning Report INTO Command Center as a pre-run modal/panel, not a separate route. User types their prompt → clicks "Analyze" → sees plan → clicks "Run" to execute. This is more natural than a separate route.

---

# PART 2: WHAT TO REMOVE / WHAT IS DUPLICATE

---

## REMOVE: `/legacy` route and all legacy views
✅ Already done.

## REMOVE: `styles.css`
✅ Already done.

## REMOVE: Dashboard `OrionDashboard` and `AppShell` (legacy)
These are in `dashboard/` and not imported anywhere now. Safe to delete the whole `dashboard/` folder.

## REMOVE: Old `views/` directory
`PlanView`, `BusinessView`, `WorkView`, `ActivityView`, `LoopsView` — these were the legacy generation UI views. They are still on disk but no longer imported. Delete them.

## REMOVE: Old `operating/` components (14 files)
`AnchorBoard`, `AnchorTrend`, `CompanySelector`, etc. — these were the legacy operating views. The new Platform UI has Operations views that should replace them. Delete after wiring Operations section.

## REMOVE from Topbar: Hardcoded date and hardcoded "Abhishek"
The date "Thu, 19 Sep 2026" is hardcoded in `Topbar.jsx`. The user name "Abhishek" is hardcoded. Both should come from the auth user object.

## REMOVE: Approval badge "5" and Notification badge "12" (hardcoded)
These should be dynamic counts from real data or removed until real counts exist.

## REMOVE: `/orion` route
It was redundant with `/*` — both pointed to `PlatformApp`. ✅ Already removed.

## DUPLICATE: `ViewOperations` (dept) vs `ViewOperationsOverview` (ops section)
There are two "Operations" concepts:
- `ViewOperations` — the "Operations" AI department (staffing, supply chain, etc.)
- `ViewOperationsOverview` — the Operations section in the sidebar (running company operations)

These are different things but share names. Rename the department one to `ViewDeptOperations` in the UI label to avoid confusion.

## DUPLICATE: `ViewFinanceDept` (dept) vs `ViewFinance` (ops)
Same issue. Finance as a generation department vs Finance as a running company operations view.

---

# PART 3: THE UNIFIED SYSTEM ARCHITECTURE

---

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                      (React 18 + Vite)                          │
│                                                                 │
│  Auth Flow          Platform App (PlatformApp.jsx)              │
│  ─────────          ─────────────────────────────               │
│  Landing Page  →    Sidebar Navigation                          │
│  Intro Splash       ├── Command Center  ──────────────┐         │
│  Sign Up / In       ├── Missions                      │         │
│                     ├── Approvals                     │         │
│                     ├── Notifications                 │         │
│                     ├── Departments ──────────────────┤         │
│                     ├── Agents                        │         │
│                     ├── Knowledge                     │         │
│                     ├── Tools                         │         │
│                     ├── Operations ──────────────────┤         │
│                     ├── Observability                 │         │
│                     └── Settings                      │         │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTP / WebSocket
                    (localhost:8080)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND                        │
│                                                                 │
│  Auth Layer          Generation Layer    Operating Layer        │
│  ──────────          ────────────────    ───────────────        │
│  /auth/signup        /intent             /operating/anchors     │
│  /auth/login         /planning/reports   /operating/ledger      │
│  /auth/refresh       /generate           /operating/decisions   │
│  /auth/logout        /ws/generate        /operating/findings    │
│  /auth/me            /sessions           /operating/memory      │
│                      /sections           /operating/loops       │
│                      /health             /operating/tick        │
│                                                                 │
│  Intelligence Layer                                             │
│  ──────────────────                                             │
│  Intent Classifier (1 LLM call)                                 │
│  21-Agent Orchestrator (LangGraph DAG)                          │
│     Stage 1: Market Research + Competitive + Location           │
│     Stage 2: Business Planning + Risk Analysis                  │
│     Stage 3: Finance (Revenue + Cost + Funding + P&L)           │
│     Stage 3: Branding (Naming + Identity + Voice + Visual)      │
│     Stage 3: Marketing (Digital + Persona + Campaign + SEO)     │
│     Stage 4: Operations (Supply + Staffing + Tech + Process)    │
│                                                                 │
│  LLM Fallback Chain: Groq → Gemini → Ollama                     │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
       SQLite              ChromaDB         MongoDB Atlas
    (sessions,           (vector cache,      (user accounts,
    planning_reports,     episodic           auth tokens,
    operating data)       memory)            API key store)
```

---

# PART 4: USE CASES

---

## USE CASE 1: First-Time User — Generate a Business Plan

**Actor**: Someone with a business idea, no business background

**Flow**:
1. Visits the app → Intro splash plays (3s)
2. Sees Landing Page → clicks "Get Started"
3. Signs up (email + password) → JWT issued, refresh cookie set
4. Enters platform → Command Center loads
5. Types: "I want to open a chai tapri near Dadar station with ₹2L budget"
6. Clicks "Analyze" → Planning Report builds (1 LLM call)
7. Sees: 17 agents will run (digital business), estimated 23,400 tokens, Serper missing (warning)
8. Clicks "Run" → 21 agents stream results live (60–90s)
9. Progress panel shows: Strategy → Finance (parallel with Branding, Marketing) → Operations
10. Plan appears: market research, competitor analysis, revenue model, brand name, marketing campaign, staffing plan
11. Mission saved → appears in Missions list
12. User can download HTML report or PDF

**What this touches**: Auth, Landing, Intro, Command Center, Planning Report, WebSocket generation, Sessions, Output

---

## USE CASE 2: Returning User — Review and Act on a Plan

**Actor**: User who generated a plan last week

**Flow**:
1. Refresh cookie restores session → goes straight to Platform (no login prompt)
2. Clicks Missions → sees their "Chai tapri" mission, status Completed
3. Clicks the mission → sees Mission Details: execution graph, all 17 agents, their status
4. Clicks "Finance" tab → sees P&L forecast, revenue model, cost structure
5. Wants to share → clicks "Download PDF" → gets the PDF report
6. Notices Operations agents suggested 2 staff → goes to Operations → HR view → sees staffing plan
7. Approves the hiring → creates an Approval decision → marks it approved

**What this touches**: Session restore, Missions, Mission Details, Output (PDF), Operations, Approvals

---

## USE CASE 3: Operating a Business (Day-to-Day)

**Actor**: User who wants AI to help run their business, not just plan it

**Flow**:
1. User runs the autonomy demo or `/operating/tick` to advance the company state
2. Goes to Operations → Overview → sees current KPIs (revenue, customers, burn rate)
3. Finance tab shows ledger entries (in paise, divided by 100 for display)
4. Gets notification: "Marketing Agent recommends increasing ad spend"
5. Goes to Approvals → Marketing Budget Approval request from the Marketing Operating Agent
6. Reviews the proposal, ROI estimate, supporting evidence
7. Approves → agent executes the decision → ledger entry created
8. Goes to Observability → sees the agent run that was triggered, its token usage, latency

**What this touches**: Operating layer, Operations views, Approvals, Notifications (future), Observability

---

## USE CASE 4: Developer / Power User — Monitoring Agents

**Actor**: Technical user who wants visibility into what AI is doing

**Flow**:
1. Goes to Observability → Dashboard → sees success rate 98.2%, avg latency 842ms
2. Notices an error spike → clicks Errors & Failures → sees "Finance Agent failed: JSON parse error on retry 2"
3. Clicks into the run → Trace view → sees every LLM call, input tokens, output tokens, latency, the raw prompt
4. Goes to LLM Usage → sees Groq is handling 85% of calls, Gemini 10%, Ollama 5%
5. Wants to understand costs → sees token totals per provider, maps to free tier limits
6. Goes to Agents → Performance → sees which agents have lowest success rates

**What this touches**: Observability (all sub-views), Agents → Performance

---

## USE CASE 5: Knowledge-Enhanced Plan

**Actor**: User who has existing business documents (financial history, market reports)

**Flow**:
1. Goes to Knowledge → Upload Sources
2. Uploads their last 2 years of financial data (PDF) and a competitor report (PDF)
3. Documents are chunked, embedded, stored in ChromaDB
4. Returns to Command Center → types a new business prompt
5. The agents now retrieve relevant chunks from ChromaDB when doing market research and financial modeling
6. Plan is significantly more grounded than a cold-start plan

**What this touches**: Knowledge Upload, ChromaDB ingestion pipeline, Agent context injection

---

# PART 5: WHAT IS THE RIGHT SYSTEM STRUCTURE

---

## The Two Products in One App

Orion is actually two products that share infrastructure:

**Product A: Business Plan Generator**
- Input: one sentence
- Output: structured business plan (JSON + HTML + PDF)
- Users: entrepreneurs, students, consultants
- Core: Intent → 21 Agents → Plan
- UI section: Command Center + Missions

**Product B: AI Business Operating System**
- Input: an approved business plan
- Output: day-by-day AI management of the company
- Users: business owners who want AI to help run operations
- Core: Operating layer (ledger + anchors + governance + agents)
- UI section: Operations + Approvals + Departments

Both products need: Auth, Knowledge, Tools, Observability, Settings.

**You need to decide: Are you building both, or just Product A for now?**

Recommendation: **Build Product A completely first. Product B is built in the backend but has no real business users yet. Product A is the hook that gets users in.**

---

# PART 6: BUILD ROADMAP

---

## Phase 1: Make the Core Flow Work (2–3 weeks)

Goal: A user can sign up, generate a business plan, and see it.

| Task | What to do | Files |
|------|-----------|-------|
| Wire Command Center to backend | Call `/ws/generate` from `ViewCommandCenter`, stream events, display progress and result | `ViewCommandCenter.jsx`, `api.js` |
| Planning Report pre-run | Show planning report modal before running (call `POST /planning/reports`, display agent roster, confirm) | `ViewCommandCenter.jsx`, `api.js` |
| Wire Missions to `/sessions` | Replace mock data with real sessions from `GET /sessions` | `ViewMissions.jsx` |
| Wire Mission Details to session | Load real agent trace data for a session | `ViewMissionDetails.jsx` |
| Fix Topbar user name | Read from auth user object | `Topbar.jsx` |
| Fix Topbar date | Use real date | `Topbar.jsx` |
| Delete dead code | Remove `dashboard/`, old `views/`, old `operating/` components | File deletion |

---

## Phase 2: Wire Approvals and Operations (1–2 weeks)

Goal: The operating layer is visible and actionable.

| Task | What to do | Files |
|------|-----------|-------|
| Wire Approvals | Call `/operating/decisions` for list, wire Approve/Reject/Return buttons | `ViewApprovals.jsx` |
| Wire Operations Overview | Call `/operating/anchors` + `/operating/runs` | `ViewOperationsOverview.jsx` |
| Wire Operations Finance | Call `/operating/ledger` | `ViewFinance.jsx` (ops) |
| Wire Observability Dashboard | Add `GET /observability/runs` endpoint, wire to `ViewObsDashboard` | New backend endpoint + `ViewObsDashboard.jsx` |

---

## Phase 3: Profile, Settings, Knowledge Memory (1 week)

Goal: User profile works, API keys manageable, memory visible.

| Task | What to do | Files |
|------|-----------|-------|
| Wire Profile | Call `/auth/me`, display user info, save changes | `ViewSettingsProfile.jsx` |
| API Access | Store user's LLM API keys in MongoDB, use them in agents | `ViewApiAccess.jsx` + new backend endpoint |
| Wire Memory | Call `/operating/memory` for memory entries | `ViewMemoryOverview.jsx` |
| Fix notification badges | Make "Approvals" badge count real, remove fake "12" from notifications | `Sidebar.jsx`, `navigation.js` |

---

## Phase 4: Agents Observability and Performance (1 week)

Goal: Technical users can see what agents are doing.

| Task | What to do | Files |
|------|-----------|-------|
| Wire Agents Overview | Show real 21 agents from registry | `ViewAgents.jsx` |
| Wire Agents Performance | Aggregate AgentTrace from sessions | `ViewAgentPerformance.jsx` + new endpoint |
| Wire Observability Runs | Show real session runs with agent details | `ViewObsRuns.jsx` |
| Wire Observability LLM | Show real token/provider data | `ViewObsLLM.jsx` |

---

## Phase 5: Knowledge Upload (2 weeks)

Goal: Users can upload documents that agents use.

| Task | What to do | Files |
|------|-----------|-------|
| Document ingestion endpoint | `POST /knowledge/documents` — parse PDF/URL, chunk, embed, store in ChromaDB | New backend module |
| Wire Upload Sources | Call the upload endpoint, show progress | `ViewUploadSources.jsx` |
| Agent context injection | Pass relevant chunks to agents during generation | `app/agents/base.py` modifications |

---

## Phase 6: Defer / Do Not Build Now

| Feature | Why to defer |
|---------|-------------|
| Agent Builder / Create Agent | Requires new backend (dynamic agent runtime, prompt templates) — weeks of work |
| Custom Tools / MCP | Requires tool execution framework |
| Slack/Notion/Drive integrations | Requires OAuth flows per provider |
| Billing | Requires payment processor |
| Workspace / Team settings | Requires multi-user architecture changes |
| Notifications system | Requires event bus and notification store |
| Real-time collaboration | Not in scope |

---

# PART 7: WHAT THE SIDEBAR SHOULD ACTUALLY REPRESENT

---

Current sidebar structure is aspirational. Here is what each item ACTUALLY maps to today:

| Sidebar Item | Backend Reality | Wire Priority |
|-------------|----------------|---------------|
| Dashboard | Static welcome + KPIs from `/sessions` aggregate | Phase 1 |
| Command Center | `/ws/generate` — CORE FEATURE | Phase 1 (highest) |
| Missions | `/sessions` list + detail | Phase 1 |
| Approvals | `/operating/decisions` — FULLY BUILT | Phase 2 |
| Notifications | Nothing built yet | Phase 6 |
| Departments | Mixed (generation + operating) | Phase 2-3 |
| Agents | `/agents/registry` (read only) | Phase 4 |
| Knowledge | `/operating/memory` + future upload | Phase 3 |
| Tools | Only API Keys are real today | Phase 3 |
| Operations | `/operating/*` — FULLY BUILT | Phase 2 |
| Observability | AgentTrace data in sessions, needs new endpoints | Phase 4 |
| Settings | `/auth/me` for profile, rest deferred | Phase 3 |

---

# PART 8: THE SINGLE MOST IMPORTANT THING

---

**Everything else in the system exists to support this one flow:**

```
User types a sentence
         ↓
Orion analyzes it (1 LLM call, shows the plan)
         ↓
User confirms (free)
         ↓
21 AI agents run in parallel and in sequence (60-90 seconds)
         ↓
Complete business plan appears:
- Market research with real competitor data
- Financial model with projections
- Brand name + identity + voice
- Marketing campaign + SEO plan
- Operations playbook + staffing plan
         ↓
User downloads it as PDF
```

**This flow is 100% working in the backend right now.**
**The frontend (Command Center) is not wired to it.**

That is the single most impactful thing you can build. Everything else — departments, agents, operations, observability — adds value on top of this. But without this working, the app does nothing.

---

# PART 9: THE 5 THINGS THAT MAKE ORION UNIQUE

---

These are your moat. Protect them in every design decision:

1. **One sentence in → complete business plan out** — no other tool does this with 21 specialized agents in 60-90s
2. **Free tier only** — Groq + Gemini + Ollama fallback, zero cost to users (within free tier limits)
3. **Grounded output** — competitors from real Google Places/OpenStreetMap data, market research from real Serper web search — not hallucinated
4. **Plan → Operate continuity** — the same platform that generates your plan also runs your company (operating layer)
5. **Transparent AI** — Planning Report shows exactly what will run, Observability shows what ran, Audit logs show every decision

---

# SUMMARY TABLE

| Feature | Status | Build? | Priority |
|---------|--------|--------|----------|
| Command Center → backend wire | Not wired | YES | 1 (highest) |
| Planning Report in Command Center | Backend done, UI removed | YES | 1 |
| Missions → /sessions | Not wired | YES | 1 |
| Approvals → /operating/decisions | Not wired | YES | 2 |
| Operations → /operating/* | Not wired | YES | 2 |
| Profile → /auth/me | Not wired | YES | 3 |
| API Keys management | Not built | YES | 3 |
| Knowledge Memory view | Not wired | YES | 3 |
| Agents Overview (real data) | Not wired | YES | 4 |
| Observability (real data) | Needs new endpoint | YES | 4 |
| Knowledge Upload | Not built | YES | 5 |
| Notification badges (real count) | Not built | Partial | 3 |
| Agent Builder / Create | Not in backend | NO (defer) | — |
| Custom Tools / MCP | Not in backend | NO (defer) | — |
| Slack/Notion integrations | Not in backend | NO (defer) | — |
| Billing | Not in backend | NO (defer) | — |
| Workspace/Team settings | Not in backend | NO (defer) | — |
| Notifications system | Not in backend | NO (defer) | — |
| Delete legacy code (dashboard/, old views/, old operating/) | On disk unused | YES | 1 |
| Fix hardcoded user name/date in Topbar | Hardcoded | YES | 1 |
