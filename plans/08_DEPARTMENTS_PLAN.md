# 08 — DEPARTMENTS PLAN
# Orion AI Business Operating System

**Plan Series:** 08 of 12
**Phase:** Phase 3 (after Agents, before Knowledge)
**Status:** NOT YET BUILT
**Depends On:** 01_AUTH, 04_MISSION_ENGINE, 05_AGENTS

---

## TABLE OF CONTENTS

1. What Departments Are in the System
2. The Default 6 Departments and Their Agents
3. Create Department — How It Works
4. The Sub-Sections for Each Department (4 Tabs)
5. Database Table
6. API Endpoints
7. How Departments Connect to Every Other Plan
8. Build Order

---

## 1. WHAT DEPARTMENTS ARE IN THE SYSTEM

A Department is the organizational layer that turns a pile of AI agents into a structured company.

### The Problem Without Departments

Imagine building out Orion without departments. You have 40 agents:
- Content Writer, SEO Agent, Campaign Manager, Email Agent
- Revenue Analyst, Budget Agent, Forecasting Agent
- Process Agent, Compliance Agent, Workflow Manager
- Recruiter, Onboarding Agent, Policy Agent
- Outreach Agent, Pipeline Agent, CRM Agent

All 40 agents sit in a flat list. When a mission comes in — "Analyze our Q4 marketing performance and propose improvements" — the Router has to figure out which agents are relevant. Nothing in the system tells it "these 7 agents are the Marketing team." It has to guess from agent names or tags.

Activity is a jumble. Every task from every agent appears in one undifferentiated feed. You cannot ask "what did my Finance team do this week?" You cannot give the Marketing team access to their own documents without giving them access to everyone's documents.

### The Solution With Departments

A Department is a named grouping of agents with:
- A defined purpose (what this team does)
- A set of member agents (who does the work)
- Its own document collection in ChromaDB (team-specific knowledge)
- A dedicated Activity feed (what this team has done)

When a mission is tagged with `department_id = marketing`, the Task Router queries `agents WHERE department_id = 'marketing'` first. The relevant agents surface immediately.

### The Structural Role of Departments

Departments are not just a UI label. They are active participants in the system's logic:

1. **Task Routing:** `mission.department_id` → Router's first filter when selecting agents
2. **Knowledge Scoping:** `document.department_id` → controls which ChromaDB collection document_rag searches
3. **Operations Structure:** Each department has its own tab in the Operations section — departments define the shape of the Operations page
4. **Activity Isolation:** Each department's Activity feed shows only that department's agent runs
5. **Access Control (future):** Department-level permissions will let you restrict which human users can view or manage each department

### Custom vs. Default Departments

Orion ships with 6 default departments, pre-seeded with agent templates. Users can create additional custom departments for any business function they need: Customer Success, Legal, IT, Product, Data Science, etc. Users can also rename or repurpose the default departments.

---

## 2. THE DEFAULT 6 DEPARTMENTS AND THEIR AGENTS

These are seeded automatically when the system is set up. Each agent listed is a template reference, not a fully instantiated agent — the user creates the actual agents in the Agents section.

---

### MARKETING DEPARTMENT
**Purpose:** Generate demand, build brand awareness, and drive customer acquisition.
**Icon:** 📣 | **Color:** #7C3AED (purple)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Content Agent | Writes blog posts, landing pages, email sequences | web_search, document_rag |
| SEO Agent | Keyword research, on-page optimization, competitor analysis | web_search, document_rag |
| Social Agent | Creates social media posts, schedules content | web_search, document_rag |
| Campaign Agent | Plans and coordinates marketing campaigns | document_rag, http_request |
| Analytics Agent | Analyzes traffic, conversion data, campaign performance | document_rag, http_request |
| Creative Agent | Generates ad copy, headlines, creative briefs | web_search, document_rag |
| Growth Agent | Identifies growth opportunities, A/B testing ideas | web_search, document_rag |

**Marketing Orchestrator:** Campaign Agent acts as orchestrator, calling Content Agent, SEO Agent, and Analytics Agent for comprehensive campaign planning.

---

### FINANCE DEPARTMENT
**Purpose:** Track revenue, control costs, model forecasts, and produce financial reports.
**Icon:** 💰 | **Color:** #059669 (emerald)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Revenue Analyst | Tracks ARR, MRR, churn, expansion | document_rag, http_request |
| Cost Tracker | Monitors expenses by category, flags overruns | document_rag, http_request |
| Forecasting Agent | Models revenue and expense projections | document_rag, web_search |
| Reporting Agent | Generates weekly/monthly financial reports | document_rag, http_request |
| Budget Agent | Manages budget allocations and variances | document_rag, http_request |

**Finance Orchestrator:** Reporting Agent acts as orchestrator, pulling data from Revenue Analyst, Cost Tracker, and Forecasting Agent to produce the monthly board report.

---

### OPERATIONS DEPARTMENT
**Purpose:** Manage processes, inventory, suppliers, and compliance to keep the business running.
**Icon:** ⚙️ | **Color:** #D97706 (amber)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Process Agent | Documents and optimizes business processes | document_rag, http_request |
| Inventory Agent | Monitors stock levels, triggers reorders | http_request, document_rag |
| Supplier Agent | Manages supplier relationships, tracks deliveries | web_search, http_request |
| Workflow Agent | Automates approval workflows, routing rules | http_request, document_rag |
| Compliance Agent | Monitors regulatory requirements, flags risks | web_search, document_rag |
| Efficiency Agent | Identifies process bottlenecks, proposes improvements | document_rag, web_search |

---

### SALES DEPARTMENT
**Purpose:** Generate and convert leads, manage pipeline, and drive revenue.
**Icon:** 📈 | **Color:** #DC2626 (red)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Outreach Agent | Writes personalized outreach emails and sequences | web_search, document_rag |
| Pipeline Agent | Tracks deal stages, forecasts close dates | document_rag, http_request |
| Conversion Agent | Optimizes proposals, handles objections | document_rag, web_search |
| CRM Agent | Updates CRM records, logs activities | http_request, document_rag |
| Prospecting Agent | Researches and qualifies leads | web_search, maps_api |

**Sales Orchestrator:** Pipeline Agent orchestrates Prospecting Agent (find leads), Outreach Agent (contact them), and CRM Agent (record everything).

---

### HR DEPARTMENT
**Purpose:** Recruit talent, onboard employees, manage performance, and maintain policies.
**Icon:** 👥 | **Color:** #0891B2 (cyan)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Recruiting Agent | Writes job postings, screens candidates | web_search, document_rag |
| Onboarding Agent | Creates onboarding plans, answers new hire questions | document_rag |
| Performance Agent | Tracks performance metrics, suggests review templates | document_rag |
| Policy Agent | Maintains HR policies, answers policy questions | document_rag |

---

### RESEARCH DEPARTMENT
**Purpose:** Produce market intelligence, competitive analysis, and data-driven insights.
**Icon:** 🔬 | **Color:** #7C3AED (indigo)

**Agent Roster:**

| Agent | Role | Primary Tools |
|---|---|---|
| Market Research Agent | Studies market size, segments, trends | web_search, document_rag |
| Competitor Agent | Monitors competitor products, pricing, positioning | web_search, document_rag |
| Trend Analyst | Identifies emerging trends relevant to the business | web_search, document_rag |
| Data Agent | Processes and analyzes structured data | document_rag, http_request |
| Insight Agent | Synthesizes research into executive-ready insights | document_rag, web_search |

**Research Orchestrator:** Insight Agent is the natural orchestrator: it calls Market Research Agent, Competitor Agent, and Trend Analyst, then synthesizes their outputs into a unified brief.

---

## 3. CREATE DEPARTMENT — HOW IT WORKS

### The AI-Chat Creation Flow

Users create departments through a conversational interface, not a form. This mirrors how you would describe a new team to a colleague:

**Step 1 — User describes the department in chat:**
The Create Department view has a large textarea:
```
"I need a customer success team. They should handle onboarding new customers, 
track product adoption, run quarterly business reviews, identify at-risk accounts 
before they churn, and manage the renewal pipeline."
```

**Step 2 — System proposes the department:**
Frontend calls `POST /departments/propose` with `{prompt: "I need a customer success team..."}`.

Backend calls LLM with this system prompt:
```
You are an organizational design expert for AI-powered business teams.
The user wants to create a new department. Based on their description, propose:
{
  "name": "short department name",
  "purpose": "one sentence mission statement",
  "responsibilities": ["list", "of", "key", "responsibilities"],
  "suggested_agent_types": [
    {
      "name": "Agent Name",
      "role": "What this agent does",
      "primary_tools": ["tool1", "tool2"]
    }
  ],
  "icon": "single emoji",
  "color": "hex color code"
}
Return only valid JSON.
```

**Step 3 — Proposal appears in right panel:**
```
Proposed Department: Customer Success
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Purpose: Drive product adoption, retention, and customer lifetime value

Responsibilities:
• Customer onboarding and activation
• Adoption monitoring and health scoring  
• Churn risk identification and intervention
• QBR preparation and execution
• Renewal pipeline management

Suggested Agents:
[Onboarding Manager] — Guides new customers through setup
[Adoption Agent]     — Monitors usage, flags low engagement
[Churn Predictor]   — Identifies at-risk accounts, triggers alerts
[QBR Agent]         — Prepares quarterly business review decks
[Renewal Agent]     — Tracks renewal dates, manages pipeline

Icon: 🤝  Color: ████ (#0EA5E9 - sky blue)
```

**Step 4 — User refines via follow-up messages:**
User types: "Add a technical onboarding agent for complex integrations"
System updates the proposal: adds "Integration Specialist" to the agent list.

User types: "Change the color to green"
System updates: `color: "#10B981"`.

**Step 5 — User confirms:**
User clicks "Create Department" → `POST /departments` with the final proposal data.
Department saved to DB.

**Step 6 — User goes to Agents section:**
The department is created with no actual agents yet — just the proposal for which agents to create. A banner in the new department's Overview tab prompts: "This department has no agents yet. Go to Agents → Create to add agents and assign them here."

### Why Chat Instead of Form

Forms ask users to think in terms of database fields: name, purpose, icon, color, agents. Most users don't think that way when imagining a new business team.

A description like "I need a customer success team for retention" naturally contains all the information needed to propose a good department structure. The LLM translates the user's intent into the structured data the system needs.

---

## 4. THE SUB-SECTIONS FOR EACH DEPARTMENT (4 TABS)

When a user clicks on a department (from the Departments list), they see the department detail view. It has 4 tabs.

---

### TAB 1: OVERVIEW

**Purpose:** At-a-glance status of the department's health and activity.

**Stats strip (4 cards across the top):**

| Card | Value | Source |
|---|---|---|
| Agents | 7 active | COUNT(agents WHERE dept_id=this AND status='active') |
| Active Missions | 3 running | COUNT(missions WHERE dept_id=this AND status='running') |
| Knowledge Items | 142 docs | COUNT(documents WHERE dept_id=this) |
| Success Rate | 94.2% | from execution_traces for this dept's agents |

**Visual Agent Grid:**
Agent cards arranged in rows. Each card shows:
- Agent name + icon
- Status indicator: Active (green pulse) / Idle (gray) / Running (yellow pulse) / Error (red)
- Current task (if running): truncated task description
- Quick actions: View in Agents, Send Message (opens Command Center with this agent pre-selected)

Cards are grouped if some agents are orchestrators with sub-agents (orchestrator card spans wider, with sub-agent cards nested below it).

**Active Missions List:**
Shows missions currently running that involve this department's agents:
- Mission name
- Progress bar (tasks_completed / tasks_total)
- Running time
- "View" link → goes to Mission Detail

**Knowledge Graph:**
A small visualization (word cloud or tag cloud) showing the most frequently searched terms in recent `document_rag` calls by this department's agents. Shows what topics the agents are drawing on most from the Knowledge base.

---

### TAB 2: ACTIVITY

**Purpose:** Complete timestamped history of everything this department's agents have done.

This is the department's audit trail. Every action by any agent in this department appears here.

**Activity Feed Layout:**
Reverse-chronological list of events:
```
●  Oct 14, 10:23 AM — Content Agent
   Task Completed: "Write Q4 enterprise blog post"
   Mission: Q4 Marketing Campaign Planning | Duration: 3m 42s | ✓ Success

●  Oct 14, 10:19 AM — SEO Agent  
   Tool Called: web_search("enterprise software Q4 trends 2025")
   Mission: Q4 Marketing Campaign Planning | Result: 8 results returned

●  Oct 14, 10:15 AM — Campaign Agent
   Mission Started: Q4 Marketing Campaign Planning
   Tasks: 5 planned | Agents: Campaign, Content, SEO, Analytics | Estimated: 12 min

●  Oct 14, 09:44 AM — Analytics Agent
   Approval Requested: Spend $45 on competitor analysis report
   Mission: Competitor Benchmarking | Status: ⌛ Awaiting approval

●  Oct 13, 4:30 PM — Content Agent
   Task Failed: "Write product launch email sequence"
   Mission: Product Launch #12 | Error: web_search rate limit exceeded | ✗ Failed
```

**Event types shown:**
- Mission Started / Completed / Failed
- Task Started / Completed / Failed
- Tool Called (with tool name and brief input preview)
- Approval Requested / Approved / Rejected
- Agent Error (with error type)
- Document Uploaded to dept knowledge
- Memory Stored (if significant)

**Filters:**
- Date range picker (today / last 7 days / last 30 days / custom)
- Agent filter: dropdown of dept members
- Event type filter: all / missions / tools / approvals / errors
- Search: full-text search on event descriptions

**Data source:** Aggregates `execution_traces` WHERE agent.department_id = this.id, ordered by created_at DESC.

---

### TAB 3: MEMBERS

**Purpose:** Manage which agents belong to this department.

**Agent Cards Layout:**
Grid of agent member cards:
```
┌─────────────────────────────────┐
│  🤖  Content Agent              │
│  Role: Content Strategist        │
│  Status: ● Active               │
│  Missions: 47 | Success: 95.7%  │
│  Last Active: 2 hours ago        │
│  ─────────────────────────────  │
│  [View Agent]  [Remove]          │
└─────────────────────────────────┘
```

Clicking "View Agent" → navigates to that agent's detail page in the Agents section.

Clicking "Remove" → `DELETE /departments/{id}/agents/{agent_id}` with confirmation. This does NOT delete the agent — it just removes the `department_id` association. The agent becomes unassigned.

**"Add Agent" button:**
Opens a modal. Shows all agents that are:
- Not already in this department
- Not deleted
Search box + list. Clicking an agent → `POST /departments/{id}/agents {agent_id}`.

**Department Roles (optional, future feature):**
In a future iteration, each member can be assigned a role within the department (Lead, Specialist, Support). For now, roles are implicit from the agent's own purpose field.

---

### TAB 4: SETTINGS

**Purpose:** Configure the department itself.

**Basic Info:**
- Department Name (text)
- Purpose / Mission Statement (textarea)
- Icon (emoji picker)
- Color (color picker — used in the UI for the department's visual identity)
Save → `PUT /departments/{id}`

**Department Defaults:**
- Default Model: dropdown. Agents in this dept default to this model when created. Override at agent level.
- Default Memory TTL: dropdown (30/60/90/365 days). Agents in this dept default to this TTL.
- Autonomy Level Default: Supervised / Semi-Autonomous / Fully Autonomous

These defaults are applied when new agents are created with this department assigned. They don't change existing agents.

**Knowledge Collection:**
Shows the ChromaDB collection linked to this department.
- Collection ID (read-only)
- Document count in collection
- Collection size
- "View Documents" link → Knowledge → Knowledge Base filtered by this dept
- "Upload Document to this Dept" shortcut → Knowledge → Upload with dept pre-selected

**Archive / Delete:**
Separate section with red border:
- **Archive Department:** Sets `status = 'archived'`. Department disappears from the main nav sidebar. All its agents are unassigned (department_id set to null). Missions history is preserved. Can be unarchived.
- **Delete Department:** Hard delete. Requires typing department name to confirm. Deletes department record. Does NOT delete agents (they become unassigned). Does NOT delete knowledge documents — user must delete those manually.

---

## 5. DATABASE TABLE

### departments table (SQLite)

```sql
CREATE TABLE departments (
    id                     TEXT PRIMARY KEY,   -- UUID
    name                   TEXT NOT NULL,
    purpose                TEXT NOT NULL,
    icon                   TEXT DEFAULT '🏢', -- emoji
    color                  TEXT DEFAULT '#6B7280', -- hex color
    knowledge_collection_id TEXT NOT NULL,     -- ChromaDB collection name for this dept
    created_by             TEXT NOT NULL,      -- FK → users._id (MongoDB)
    created_at             TEXT NOT NULL,      -- ISO 8601
    updated_at             TEXT NOT NULL,      -- ISO 8601
    status                 TEXT NOT NULL DEFAULT 'active' -- active|archived|deleted
);

CREATE INDEX idx_departments_created_by ON departments(created_by);
CREATE INDEX idx_departments_status ON departments(status);
```

**Note on agent_ids:** Agents reference departments via `agents.department_id` (FK on the agents table). There is no `agent_ids` array on the department record — the relationship is maintained on the agents side. This avoids duplication and is more normalized. The department's member list is always: `SELECT * FROM agents WHERE department_id = dept_id`.

**Note on knowledge_collection_id:** This is the ChromaDB collection name for this department's documents, e.g., `dept_marketing_uuid`. Created automatically when the department is created. Format: `dept_{dept_id}`.

---

## 6. API ENDPOINTS

All endpoints require Authorization header (JWT).

```
POST /departments/propose
```
AI-powered department proposal. Body: `{prompt: "I need a team that handles X, Y, Z"}`. Calls LLM with organizational design prompt. Returns proposed department structure:
```json
{
  "proposal_id": "temp-uuid",
  "name": "Customer Success",
  "purpose": "Drive product adoption and customer retention",
  "responsibilities": ["Onboarding", "Adoption monitoring", "Churn prevention"],
  "suggested_agent_types": [
    {"name": "Onboarding Manager", "role": "...", "primary_tools": ["document_rag"]}
  ],
  "icon": "🤝",
  "color": "#0EA5E9"
}
```
This proposal is not saved to DB until user confirms via POST /departments.

```
POST /departments
```
Create a department. Body: `{name, purpose, icon?, color?, agent_ids?}`. Side effects:
1. Insert department record in SQLite
2. Create ChromaDB collection: `dept_{dept_id}`
3. If `agent_ids` provided: update each agent's `department_id` field
Returns: full department object.

```
GET /departments
```
List all departments for the authenticated user. Returns: array of department objects with computed fields: agent_count, active_missions, success_rate.

```
GET /departments/{id}
```
Department detail. Returns: department object + members list (from agents table) + active missions list.

```
PUT /departments/{id}
```
Update department config. Body: any updatable fields (name, purpose, icon, color). Returns: updated department object.

```
DELETE /departments/{id}
```
Archive or delete department. Query param: `?mode=archive|delete`. Default: archive.
- Archive: sets `status='archived'`, unassigns all agents (sets their department_id to null)
- Delete: hard delete of department record. Does NOT cascade-delete agents or knowledge documents.
Returns: `{status: 'archived'|'deleted'}`.

```
GET /departments/{id}/activity
```
Activity feed for a department. Query params: `?days=7|30`, `?agent_id=`, `?event_type=`, `?search=`. Returns: array of execution_trace events from agents in this department, sorted by created_at DESC.

Implementation:
```sql
SELECT et.*, a.name as agent_name, m.name as mission_name
FROM execution_traces et
JOIN agents a ON et.agent_id = a.id
JOIN missions m ON et.mission_id = m.id
WHERE a.department_id = :dept_id
  AND et.created_at > :since
ORDER BY et.created_at DESC
LIMIT 100
```

```
POST /departments/{id}/agents
```
Add an agent to this department. Body: `{agent_id}`. Side effect: `UPDATE agents SET department_id = :dept_id WHERE id = :agent_id`. Returns: `{success: true, agent: {...}}`.

```
DELETE /departments/{id}/agents/{agent_id}
```
Remove agent from department. Side effect: `UPDATE agents SET department_id = NULL WHERE id = :agent_id`. The agent is not deleted — just unassigned. Returns: `{success: true}`.

---

## 7. HOW DEPARTMENTS CONNECT TO EVERY OTHER PLAN

**→ Mission Engine (Plan 04)**
Missions have an optional `department_id` field. When set, the Task Router uses it as the primary filter:
```python
# Task Router - agent selection priority
if task.department_id:
    dept_agents = db.query("SELECT * FROM agents WHERE department_id=? AND status='active'", dept_id)
    if dept_agents:
        candidates = dept_agents  # prefer dept agents
    else:
        candidates = all_active_agents  # fallback if dept has no agents
```

This is how "assign this mission to Marketing" works. Users set department in the Command Center before submitting.

**→ Agents (Plan 05)**
Each agent has a `department_id` field. This is the source of truth for membership. The Departments Members tab reads from `agents WHERE department_id = dept_id`. Adding/removing agents updates `agents.department_id`.

New agents created in the Agents section can specify a department. New agents created from the department's Members tab auto-fill the department.

**→ Knowledge (Plan 07)**
Each department has its own ChromaDB collection (`dept_{dept_id}`). Documents uploaded with a `department_id` go into that collection. When a mission runs with that department's agents, `document_rag` searches the department's collection by default:
```python
# In document_rag tool
collection = f"dept_{mission.department_id}" if mission.department_id else f"user_{user_id}"
```
This scoping means Marketing agents see marketing documents, and Finance agents see finance documents. Agents don't get confused by each other's documents.

**→ Operations (future Plan)**
The Operations section is structured around departments. Each department has a corresponding tab in Operations showing that department's outputs and deliverables. Marketing Dept → Operations/Marketing → shows all marketing deliverables (blog posts produced, campaigns run, reports generated). Finance Dept → Operations/Finance → shows financial reports, forecasts produced.

This is why departments are a structural dependency for Operations. The Operations tabs are dynamically generated from the departments list.

**→ Observability (future Plan)**
Execution traces can be filtered by `agent.department_id`. Department-level analytics show:
- Total missions by department
- Success rates per department
- Token usage and cost per department
- Most active agents per department

This lets users see which departments are using Orion the most, and which are producing the best results.

**→ Missions (future Plan)**
The Missions list view has a department filter dropdown. Users can browse all missions that ran for a specific department. Missions show their department badge.

**→ Command Center (Plan 03)**
The Command Center's mission submission flow has an optional "Department" dropdown above the submit button. When selected, it sets `mission.department_id` → the Router preferentially assigns agents from that department.

The Live Agent Tree in the Command Center right panel groups agents by department. Each department is a collapsible section with its agents underneath.

---

## 8. BUILD ORDER

**Phase 3 — After Agents (Phase 2) is working**

Departments are built in Phase 3 because they need agents to assign to them. Building departments before agents would mean creating empty shells.

```
Step 1: Database setup
  - Create departments table (SQLite migration)
  - Seed 6 default departments (one per default dept, no agents assigned yet)
  - For each department: create ChromaDB collection (dept_{dept_id})
  - Note: seeded departments have empty agent_ids until user assigns agents

Step 2: POST /departments/propose (AI chat creation)
  - Implement the LLM call with organizational design prompt
  - Return structured proposal JSON
  - Frontend: render proposal in right panel
  - Frontend: follow-up message refinement loop
  - This is the most important UX interaction for this feature — get it right

Step 3: POST /departments (create confirmed dept)
  - Accept proposal data → create DB record
  - Create ChromaDB collection for new dept
  - If agent_ids provided → update agents.department_id
  - Return created department

Step 4: Core CRUD endpoints
  - GET /departments (with agent_count, active_missions computed)
  - GET /departments/{id} (with members and active missions)
  - PUT /departments/{id} (edit name, purpose, icon, color)
  - DELETE /departments/{id} (archive mode by default)

Step 5: Wire Departments list view
  - Left sidebar shows list of department names with icons
  - Main panel shows all departments as cards or list
  - Each card: name, purpose, agent count, active missions, success rate
  - Click card → department detail view

Step 6: Wire Department detail (Overview, Activity, Members tabs)
  - Overview tab: stats cards + agent grid + active missions
  - Activity tab: GET /departments/{id}/activity → feed
  - Members tab: agents list + Add Agent + Remove Agent
  - Wire POST /departments/{id}/agents and DELETE equivalent

Step 7: Wire Create Department chat flow
  - Create Department button → full-screen chat interface
  - Chat input → POST /departments/propose → proposal panel
  - Follow-up refinement (update proposal in-place)
  - Confirm button → POST /departments → redirect to new dept Overview

Step 8: Wire Settings tab
  - Edit form → PUT /departments/{id}
  - Department defaults configuration (saved to dept record)
  - Archive/Delete with confirmation
```

**What is NOT in Phase 3:**
- Department-level analytics dashboard (needs Observability plan)
- Knowledge collection management UI (needs Knowledge plan, Phase 4)
- Per-department access control for human users (future auth feature)
- Department-level billing/cost breakdown (future)

---

## APPENDIX: HOW THE 6 DEFAULTS ARE SEEDED

This is the seed data for the initial `departments` table insert. Run this once during database initialization.

```python
DEFAULT_DEPARTMENTS = [
    {
        "id": "dept_marketing",
        "name": "Marketing",
        "purpose": "Generate demand, build brand awareness, and drive customer acquisition",
        "icon": "📣",
        "color": "#7C3AED",
        "knowledge_collection_id": "dept_dept_marketing"
    },
    {
        "id": "dept_finance",
        "name": "Finance",
        "purpose": "Track revenue, control costs, model forecasts, and produce financial reports",
        "icon": "💰",
        "color": "#059669",
        "knowledge_collection_id": "dept_dept_finance"
    },
    {
        "id": "dept_operations",
        "name": "Operations",
        "purpose": "Manage processes, inventory, suppliers, and compliance",
        "icon": "⚙️",
        "color": "#D97706",
        "knowledge_collection_id": "dept_dept_operations"
    },
    {
        "id": "dept_sales",
        "name": "Sales",
        "purpose": "Generate and convert leads, manage pipeline, and drive revenue",
        "icon": "📈",
        "color": "#DC2626",
        "knowledge_collection_id": "dept_dept_sales"
    },
    {
        "id": "dept_hr",
        "name": "HR",
        "purpose": "Recruit talent, onboard employees, manage performance, and maintain policies",
        "icon": "👥",
        "color": "#0891B2",
        "knowledge_collection_id": "dept_dept_hr"
    },
    {
        "id": "dept_research",
        "name": "Research",
        "purpose": "Produce market intelligence, competitive analysis, and data-driven insights",
        "icon": "🔬",
        "color": "#4F46E5",
        "knowledge_collection_id": "dept_dept_research"
    }
]
```

When the database initializer runs, it:
1. Inserts these 6 records into the `departments` table
2. Creates the corresponding ChromaDB collections for each
3. Does NOT create agents (user does that in Phase 2 via Agents section)

---

*End of 08_DEPARTMENTS_PLAN.md*
