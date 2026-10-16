# 03 — COMMAND CENTE+R PLAN

---

## What It Is and Why It Exists in the System

The Command Center is **the entry point of the entire system**. Every mission starts here. Nothing else in the sidebar matters without this working.

The user types a goal in natural language. The system does everything else. Command Center is the mouth through which all work enters Orion.

Without Command Center: the system has no input. Agents, Tools, Departments, Knowledge — all useless.

**Role in the whole system:** Command Center is the UI layer over the Mission Engine. It takes the user's goal, sends it to the Mission Engine via WebSocket, and displays every event that streams back — live, in real time.

---

## What the Screen Shows

### Left Panel (Chat Area)

- **Chat history** above: previous missions displayed as conversation entries (user prompt + brief result summary). Clicking one opens that mission in full.
- **Live response area**: when a mission is running, shows:
  1. Orion's plan (checklist of tasks it will run)
  2. Agent progress cards (agent name, current task, progress bar or "Queued" badge)
  3. Completion: result cards with outputs
- **Composer bar** at bottom: text input + file attach button + send button
- **Quick tags**: "Deep Research", "Create Plan", "Analyze Data", "Generate Strategy" — click to pre-fill a prompt template

### Right Panel

- **Live Agent Tree**: SVG tree that builds in real time as agents are assigned tasks. Structure: Orion Planner (root) → branch nodes (Research, Analysis, Execution) → leaf tasks. Each node appears the moment an agent picks up its task, then turns green on completion.
- **Tools Being Used**: chips showing tools currently being called (Web Search, Maps API, Document RAG, etc.). Appear on tool_call event, grey out on tool_result.

---

## How It Works Technically

### Step 1: User Submits Goal

```
User types: "Analyze my top 5 competitors and suggest pricing"
Presses send → frontend calls POST /missions { prompt, department_id? }
Server creates mission record, status = "planning"
Returns immediately: { mission_id } (202 Accepted, does not wait for completion)
```

### Step 2: WebSocket Connection

```
Frontend connects: WS /ws/missions/{mission_id}
Server streams events as they happen
```

### Step 3: Event Stream

```
{ event: "planning_started" }
{ event: "task_created", task: { id, title, agent_type, depends_on: [] } }
{ event: "task_created", task: { id, title, agent_type, depends_on: ["t1"] } }
... (one per task)
{ event: "planning_complete", task_count: 4 }
{ event: "task_started", task_id: "t1", agent_id, agent_name: "Research Agent" }
{ event: "tool_call", task_id: "t1", tool: "web_search", input: { query: "..." } }
{ event: "tool_result", task_id: "t1", tool: "web_search", success: true, latency_ms: 1200 }
{ event: "task_completed", task_id: "t1", result_summary: "Found 5 competitors..." }
{ event: "task_started", task_id: "t2", agent_id, agent_name: "Analysis Agent" }
...
{ event: "approval_required", decision_id, title: "Post to Slack?", priority: "medium" }
...resumed after approval...
{ event: "mission_completed", outputs: [...] }
```

### Step 4: Frontend Maps Events to UI

```
task_created      → add leaf node to Live Agent Tree (greyed out, not started)
task_started      → node pulses green, agent card appears in chat
tool_call         → chip appears in "Tools Being Used" panel
tool_result       → chip updates (success = green, fail = red)
task_completed    → node turns to checkmark, agent card shows result
approval_required → inline approval card injected into chat (see Approvals Plan)
mission_completed → result cards shown in chat, mission saved
mission_failed    → error card shown with retry option
```

---

## Chat History

Previous missions displayed as conversation thread above the composer:

- Each entry: user's prompt on the right (blue bubble), Orion's brief summary on the left
- Source: `GET /missions?limit=20&status=completed` on Command Center mount
- Clicking an entry → opens that mission in full inside Command Center (or navigates to Missions section)

---

## Inline Approvals

When an agent triggers an approval mid-mission:

1. WS sends `{ event: "approval_required", decision_id, title, description }`
2. Chat injects an approval card inline: `"Marketing Agent wants to post to Slack. Approve?"`
3. Card has two buttons: **Approve** and **Reject**
4. User clicks → frontend calls `POST /decisions/{decision_id}/approve` or `/reject`
5. WS receives `{ event: "task_resumed", task_id }` → agent card resumes animation
6. User never leaves Command Center for routine approvals

---

## Quick Tags


| Tag               | Pre-fills                                                        |
| ----------------- | ---------------------------------------------------------------- |
| Deep Research     | "Research [topic] thoroughly and give me a complete report"      |
| Create Plan       | "Create a detailed step-by-step plan for [goal]"                 |
| Analyze Data      | "Analyze [subject] and give me key insights and recommendations" |
| Generate Strategy | "Generate a complete strategy for [objective]"                   |


User fills in the brackets then sends.

---

## File Attach

File attach button in the composer:

- User selects file → `POST /knowledge/documents` (multipart upload)
- Document ingested into ChromaDB for this user
- Agents in this mission can call `document_rag` to search it
- File name shown as attachment chip in the composer

---

## How Command Center Connects to Every Other Plan


| Plan           | Connection                                                                                |
| -------------- | ----------------------------------------------------------------------------------------- |
| Mission Engine | Submit button → `POST /missions`. WS streams Mission Engine events.                       |
| Agents         | Live Agent Tree shows real agent names from agents DB. Agent cards show real agent types. |
| Tools          | "Tools Being Used" panel shows real tool calls from `tool_call` WS events.                |
| Knowledge      | File attach → `POST /knowledge/documents`. Agents search it via `document_rag`.           |
| Approvals      | `approval_required` event → inline approval card. Approve/reject calls Approvals API.     |
| Missions       | Completed missions appear in chat history. Click to navigate to Missions detail.          |
| Observability  | Every WS event is also logged to `execution_traces`. Command Center shows same data live. |
| Departments    | Optional department dropdown before submit → `department_id` on mission.                  |
| Notifications  | `mission_completed` / `mission_failed` → notification created (shown in Notifications).   |


---

## Build Order

**Phase 1 (first thing to build after Mission Engine):**

1. `POST /missions` endpoint
2. `WS /ws/missions/{id}` streaming
3. Wire submit button → `POST /missions` → connect WS
4. Stream `task_created` events → basic task list in chat
5. Stream `task_started` / `task_completed` → agent progress cards

**Phase 2:**
6. Live Agent Tree (SVG) building from `task_created` / `task_started` events
7. Tools Being Used panel from `tool_call` events

**Phase 3:**
8. Chat history from `GET /missions`
9. Inline approval cards from `approval_required` events

**Phase 4:**
10. File attach → knowledge upload
11. Quick tags pre-fill behavior