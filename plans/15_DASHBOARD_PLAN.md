# 15 — DASHBOARD PLAN

---

## What It Is and Why It Exists in the System

The Dashboard is the **home screen** — the first thing a user sees after logging in. It is a single-page summary of everything happening across the entire system: missions, agents, approvals, insights, and recent activity.

The Dashboard does not do anything — it has no forms, no actions that are unique to it. But it connects to every other section. It is the **pulse monitor** of the whole system.

**Role in the whole system:** The Dashboard aggregates data from every other plan and presents it in one glance. A user opening the app should immediately know: how many missions are running, how many agents are active, what needs their attention (pending approvals), is the system healthy, and what happened recently.

Without Dashboard: every time the user opens the app, they land on Command Center with no context. They have to manually visit each section to understand the system state.

With Dashboard: one screen tells the full story.

---

## What the Screen Shows (4 Areas)

### Area 1 — Welcome Banner (full width)
- **Content:** Personalized greeting ("Welcome back, {user.full_name}!"), subtitle ("Plan, execute, and grow with your AI workforce"), motivational quote
- **Background:** Decorative circuit pattern image (`welcome-circuit.png`)
- **Data:** User's name from `GET /auth/me` (not hardcoded)
- **No interaction** — purely informational

### Area 2 — 4 KPI Metric Cards

| Card | Metric | Data Source | Trend |
|------|--------|-------------|-------|
| Active Missions | Count of missions with status = running | `GET /missions?status=running&count=true` | vs last 7 days |
| Agents Online | Count of agents with status = active | `GET /agents?status=active&count=true` | vs last 7 days |
| Pending Approvals | Count of decisions with status = pending | `GET /decisions/count?status=pending` | vs last 7 days |
| System Health | "All systems operational" / degraded count | `GET /health` → derive status | no trend |

Each card has:
- Colored icon (violet, teal, rose, indigo)
- Large metric value
- Metric label
- Trend indicator (green arrow up + %, or red arrow down + %)
- ChevronRight → navigates to that section

### Area 3 — Middle Row (3 columns)

**Left (2/3 width): Live Agent Network**
- SVG elliptical layout showing all agents as nodes around a center "Orion AI" hub
- Agents colored by department (blue=research, green=hr, purple=marketing, etc.)
- Agent name shown on each tile
- Clicking a tile → navigates to that agent's detail in Agents section
- Data source: `GET /agents` → render each agent as a node on the ellipse
- Static layout: positions calculated from agent count
- Currently: animated with CSS pulse for "active" agents

**Right (1/3 width): Recent Activity Feed**
- Last 5 system events across all sections
- Each entry: colored icon, event title, description, time ago
- Examples: "Market research completed", "Approval requested", "Agent deployed", "Mission completed"
- Data source: `GET /notifications?limit=5&unread=false` (all recent, read or unread)
- "View all" link → Notifications section

### Area 4 — Bottom Row (2 columns)

**Left: Key Insights**
- 2–3 AI-generated insights about the user's business based on recent mission outputs
- Each insight: lightbulb/rocket icon, insight text, source (e.g., "Based on last 3 missions"), time ago
- Examples:
  - "Thane shows 35% lower rent compared to Mumbai average"
  - "Competitor analysis reveals 3 untapped customer segments"
- Data source: `GET /missions/{id}` → extract key findings from completed task results
- **How insights are generated:** After each mission completes, the post-processor (Operations Plan) already classifies outputs. The Dashboard reads the 2 most recent `operations_data` rows with type = `research_output` and displays their `data.summary` field.

**Right: Pending Approvals**
- Top 3 pending approvals from the queue
- Each row: icon, title, description, priority badge (High/Medium/Low)
- "View all" link → Approvals section
- Clicking an item → Approvals section with that decision pre-selected
- Data source: `GET /decisions?status=pending&limit=3`

---

## Data Sources Summary

```
Welcome banner:  GET /auth/me                              → user.full_name
Active Missions: GET /missions?status=running              → count
Agents Online:   GET /agents?status=active                 → count
Pending Approvals: GET /decisions/count?status=pending     → count
System Health:   GET /health                               → derive status string
Live Agent Net:  GET /agents                               → all agents for ellipse
Recent Activity: GET /notifications?limit=5                → activity feed
Key Insights:    GET /operations/feed?limit=3&type=research_output → summaries
Pending Approvals widget: GET /decisions?status=pending&limit=3  → top 3
```

All fetched on mount. Refreshed every 60 seconds (Dashboard is ambient — doesn't need sub-second updates).

---

## The Navigation Role

Every element on the Dashboard that shows data from another section is also a **navigation shortcut**:

| Element | Click action |
|---------|-------------|
| Active Missions KPI card | → Missions section |
| Agents Online KPI card | → Agents → Overview |
| Pending Approvals KPI card | → Approvals section |
| System Health KPI card | → Observability → Dashboard |
| Agent tile in Live Agent Network | → Agents → that agent's settings |
| "View all" in Recent Activity | → Notifications section |
| Approval row in bottom-right | → Approvals, that decision selected |
| "View all" in Pending Approvals | → Approvals section |

---

## System Health Derivation

The Dashboard shows one of three states in the System Health card:

```
GET /health response:
  any_llm_available = false   → "System Degraded — No LLM providers available"
  database = "error"          → "System Degraded — Database error"
  llm_providers all slow      → "System Degraded — High latency"
  everything ok               → "All systems operational (98%)"

The 98% is calculated:
  total_components = 4 (Groq, Gemini, Ollama, DB)
  available = count(available) + (1 if DB ok)
  health_pct = (available / total_components) * 100
```

---

## Database

No new tables. All data read-only from:
- `missions` (status counts)
- `agents` (active count)
- `decisions` (pending count)
- `notifications` (recent activity)
- `operations_data` (insights)

---

## API Endpoints

No new endpoints needed. All data comes from existing endpoints across other plans.

One optional optimization — a single aggregation endpoint to avoid 7 parallel requests on page load:

```
GET /dashboard/summary
  returns: {
    user: { full_name, ... },
    metrics: { active_missions, agents_online, pending_approvals, system_health },
    recent_activity: [...5 notifications],
    insights: [...3 research outputs],
    pending_approvals_preview: [...3 decisions],
    health: { status, providers }
  }
```

This is a single backend call instead of 7. Build this in Phase 6 for performance.

---

## How Dashboard Connects to Every Other Plan

| Plan | What Dashboard shows from it |
|------|------------------------------|
| Auth | User name in welcome banner |
| Mission Engine | Active missions count, recent activity |
| Agents | Active agents count, Live Agent Network tiles |
| Approvals | Pending approvals count, top 3 approvals widget |
| Notifications | Recent activity feed |
| Operations | Key insights from research_output entries |
| Observability | System health card derives from `/health` |
| Settings | (none — but user name comes from auth which settings also uses) |
| All plans | Dashboard is the aggregator — it shows one metric from almost every plan |

---

## Build Order

**Phase 6 (polish — after all other sections have real data):**
1. Replace hardcoded "Welcome back, Abhishek!" with real `GET /auth/me`
2. Replace hardcoded metric cards with real API calls
3. Replace hardcoded Recent Activity with `GET /notifications?limit=5`
4. Replace hardcoded Pending Approvals with `GET /decisions?status=pending&limit=3`
5. Replace hardcoded Key Insights with `GET /operations/feed?type=research_output&limit=3`
6. Wire Live Agent Network tiles to real `GET /agents` list
7. System Health card from `GET /health`
8. All KPI card click handlers → navigation to correct sections
9. Optional: `GET /dashboard/summary` aggregation endpoint for performance

**Why Phase 6?** The Dashboard only makes sense when there is real data to show. Building it in Phase 1 would display empty/zero states for everything. Build it after missions are running and data exists.
