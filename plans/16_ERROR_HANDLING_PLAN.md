# 16 — ERROR HANDLING PLAN

---

## What It Is and Why It Exists in the System

Every other plan describes the happy path — what happens when everything works. This plan describes **what happens when things fail**.

Failures in Orion happen at multiple layers: the LLM provider can be down, a tool can return a 429, the WebSocket can drop, the database can be unreachable, the user's API key can be invalid, the planner can return malformed JSON.

Without a clear error handling strategy:
- Missions silently fail and users have no idea why
- Agents get stuck in infinite loops retrying a broken tool
- Users lose work when their browser tab closes mid-run
- Errors in one task cascade and kill the whole mission unnecessarily

With error handling:
- Every failure is **categorized** (recoverable vs fatal)
- Every failure is **surfaced** to the user in plain language
- Every failure is **logged** for debugging
- Recoverable failures are **retried automatically**
- Fatal failures **fail gracefully** with a clear message and partial results preserved

**Role in the whole system:** Error handling is not a section in the sidebar — it is a cross-cutting concern that every plan relies on. This plan defines the rules that govern failure at each layer.

---

## Layer 1 — LLM Provider Failures

### What can fail
- HTTP 429: Rate limited
- HTTP 401/403: Invalid API key
- HTTP 503: Provider temporarily down
- Timeout: Provider took >30 seconds to respond
- JSON parse error: LLM returned malformed JSON

### Recovery strategy
```
LLM call fails with 429 or 503
    → Mark provider as temporarily unavailable (backoff: 60s)
    → Try next provider in chain (Groq → Gemini → Ollama)
    → If all providers fail → AllProvidersFailedError

LLM returns malformed JSON (for structured calls)
    → Attempt 1: extract from markdown code block
    → Attempt 2: retry with repair prompt (fast tier, same provider)
    → Attempt 3: try next provider
    → All fail → JSONParseError → task fails with clear message

LLM response empty or too short
    → Retry once with temperature 0 (more deterministic)
    → If still bad → task fails
```

### What the user sees
- Single provider down → **nothing** (failover is invisible)
- All providers down → "⚠️ Cannot reach any AI provider. Check your API keys in Settings or start Ollama locally."
- Rate limited → "⚠️ AI quota reached for today. Runs will resume tomorrow, or add your own API key in Settings."
- Invalid key → "⚠️ API key rejected. Update your {provider} key in Settings → API Keys."

### What is logged
Every failure → `execution_traces` row: `success=0`, `error_message="{provider}: HTTP 429 rate limited"`, `latency_ms=measured`

---

## Layer 2 — Tool Failures

### What can fail
- `web_search`: Serper API down, 429, invalid key, network error
- `maps_api`: Google Places 403 (billing), 429, OpenStreetMap timeout
- `document_rag`: ChromaDB connection error, empty collection
- `http_request` (custom tool): User's custom endpoint down, timeout, bad response
- `request_approval`: Database write fails

### Recovery strategy
```
Tool call fails with HTTP 4xx/5xx or timeout
    → Retry: up to 2 retries with exponential backoff (1s, 3s)
    → After 2 retries still failing:
        - web_search → continue WITHOUT search results, agent uses LLM knowledge only
          (degraded mode — agent is told: "Web search unavailable. Use your training data.")
        - maps_api → fall back to OpenStreetMap, then to LLM-inferred data
        - document_rag → continue without retrieved docs (no crash, just no context)
        - http_request (custom) → FAIL the task (no fallback for user-defined tools)
        - request_approval → retry DB write 3x then fail hard

Tool returns empty/useless result
    → Agent receives empty result and can decide to retry or proceed
    → Maximum 1 LLM-triggered retry per tool per task
```

### What the user sees
- Tool degraded but recoverable → nothing visible (agent notes it internally)
- Custom tool repeatedly failing → task fails with: "Tool '{tool_name}' is unreachable. Check the endpoint URL in Tools → Custom Tools."
- All search tools failed → result delivered but with banner: "⚠️ Web search was unavailable during this run. Results may be less current."

### What is logged
Every tool retry → `execution_traces` row with `success=0`, `error_message`
Final tool result (success or failure) → another `execution_traces` row

---

## Layer 3 — Task Failures

### What can fail
- Agent prompt exceeds context window (too much context from previous tasks)
- Agent in infinite tool-call loop (keeps calling tools without finishing)
- Task timeout (single task running > 120s by default)
- Approval rejected → task explicitly cancelled
- Sub-agent failure → parent agent cannot continue

### Recovery strategy
```
Agent in tool-call loop (>10 tool calls in one task)
    → Inject message: "You have made 10 tool calls. Provide your final answer now."
    → If still looping after 2 more calls → force-terminate task, return partial result

Task timeout (>120s)
    → Log timeout error
    → Return whatever result was accumulated so far (partial)
    → Continue other tasks (timeout is task-level, not mission-level)

Context window exceeded
    → Truncate oldest task results from context (keep most recent 3)
    → Retry with truncated context
    → Log warning: "Context truncated for task {title}"

Approval rejected
    → Task status → "cancelled"
    → Mission continues (only this task and tasks that depend on it are skipped)
    → WS emits: { event: "task_cancelled", task_id, reason: "approval_rejected" }

Sub-agent failure
    → Parent agent receives error message as the sub-agent result
    → Parent agent decides whether to continue or fail
    → Logged in execution_traces
```

### What the user sees
- Task timeout → task card shows ⏱️ "Timed out" badge, result shows partial output
- Approval rejected → task card shows "Cancelled — approval rejected"
- Sub-agent fail → task card shows "Partial result — sub-agent failed"

---

## Layer 4 — Mission Failures

### What can fail
- Planner returns invalid JSON / empty task list
- All tasks fail
- Mission timeout (total mission > 600s by default)
- User closes the tab / WebSocket drops

### Recovery strategy
```
Planner JSON parse fails (after all repair attempts)
    → Mission status → "failed"
    → WS emits: { event: "mission_failed", error: "Could not parse the execution plan. Try rephrasing your goal." }
    → Mission saved with status=failed (partial or empty result)

All tasks fail
    → Mission status → "failed"
    → Partial results from any completed tasks are preserved in mission_tasks
    → User can still download whatever was completed

Mission timeout (>600s)
    → All running tasks are cancelled
    → Mission status → "partial"
    → WS emits: { event: "mission_failed", error: "Mission timed out after 10 minutes." }
    → All completed task results preserved

WebSocket drops mid-mission
    → Mission CONTINUES running on the server (WebSocket is just a viewer)
    → When user reconnects or opens Mission Details → sees current state
    → Frontend can reconnect to WS /ws/missions/{id} and resume receiving events
    → If user never reconnects → mission completes, result saved, notification created
```

### What the user sees
- Planner failure → inline error in Command Center chat: "Could not create a plan for this goal. Try being more specific."
- Mission timeout → Command Center shows: "Mission timed out. Partial results saved."
- WebSocket drop → Command Center shows: "Connection lost. Your mission is still running. Reconnect or check Missions."
- Partial results → Mission Details shows completed tasks with results, failed tasks with error messages

---

## Layer 5 — Network / Infrastructure Failures

### What can fail
- Database (SQLite) unreachable
- ChromaDB connection refused
- MongoDB Atlas unreachable (Auth/Settings)
- Backend server down

### Recovery strategy
```
SQLite error mid-mission
    → Log error
    → Attempt 3 retries on the specific write operation (WAL mode handles concurrent reads)
    → If still failing → mission status set to "failed" in-memory, emitted via WS
    → On next startup: check for missions stuck in "running" state → mark as "failed"

ChromaDB unreachable
    → document_rag tool returns empty result (degraded mode, see Layer 2)
    → Memory reads: skip (agents work without memory context)
    → Memory writes: queue in memory, retry on next request
    → Log warning

MongoDB Atlas unreachable (at startup)
    → Auth endpoints return 503: "User service temporarily unavailable"
    → Mission/agent operations still work (those use SQLite, not MongoDB)
    → Retry MongoDB connection every 30s

Backend server down (user tries to use app)
    → Frontend shows "Cannot reach the backend. Check that the server is running."
    → Command Center shows HealthBanner with error
```

### Stuck Mission Recovery (startup cleanup)

On every app startup, the lifespan handler runs:
```python
async def lifespan():
    # ... existing init ...
    
    # Find missions stuck in 'running' state from a previous crash
    stuck = await db.query(
        "SELECT id FROM missions WHERE status = 'running' AND created_at < ?",
        [two_hours_ago()]
    )
    for mission_id in stuck:
        await db.execute(
            "UPDATE missions SET status = 'failed' WHERE id = ?", [mission_id]
        )
        await create_notification(
            user_id=mission.created_by,
            type="mission_failed",
            title="Mission failed (server restarted)",
            description=f"Mission '{mission.title}' was running when the server restarted."
        )
```

---

## Layer 6 — Frontend / User Errors

### What can fail
- User submits empty prompt
- User submits very short prompt (<10 chars)
- User submits a prompt with no clear goal
- User uploads unsupported file type
- User tries to approve an expired decision

### Recovery strategy
```
Empty / too short prompt
    → Frontend validation before API call
    → Inline error: "Please describe your goal in at least 10 characters."

Prompt with no clear goal (detected by planner)
    → Planner returns task list with 0 tasks OR single task "Clarify the goal"
    → Mission fails at planning stage
    → WS emits: { event: "mission_failed", error: "Goal too vague. Example: 'Research my top 5 competitors in Pune'" }

Unsupported file type for Knowledge upload
    → Frontend file type check (accept: .pdf, .docx, .txt, .csv, .md)
    → If bypassed: backend returns 422 "Unsupported file type. Accepted: PDF, Word, TXT, CSV"

Expired decision approval attempt
    → POST /decisions/{id}/approve → 409: "This approval request has expired."
    → Frontend: show inline error on the approval card
```

---

## Error States in the Frontend

Every view must have three states, not just the happy path:

### 1. Loading State
Show skeleton loaders (not spinning indicators) while data is being fetched.

### 2. Empty State
Show a helpful message when there is no data yet:
- Missions: "No missions yet. Go to Command Center to start your first mission."
- Agents: "No agents yet. Go to Agents → Templates to start from a pre-built agent."
- Approvals: "No pending approvals. Agents will request your input here when needed."

### 3. Error State
Show a clear error with a retry option:
```jsx
// Pattern for all views:
if (error) return (
  <ErrorCard
    title="Could not load missions"
    message={error.message}
    onRetry={refetch}
  />
);
```

---

## Error Codes and Messages Reference

| Error | HTTP Code | User-Facing Message |
|-------|-----------|---------------------|
| Empty prompt | 422 | "Please describe your goal." |
| Prompt too short | 422 | "Your goal needs more detail (minimum 10 characters)." |
| All LLM providers down | 503 | "No AI providers are available. Check Settings → API Keys." |
| Mission timeout | 408 | "Mission timed out. Partial results saved in Missions." |
| Agent loop | 500 | "An agent ran into trouble. Partial results saved." |
| Database error | 500 | "A system error occurred. Please try again." |
| Auth expired | 401 | Silently refresh token. If fails → redirect to /login. |
| Resource not found | 404 | "Not found. It may have been deleted." |
| Decision expired | 409 | "This approval has expired and can no longer be actioned." |
| Invalid API key | 401 | "{Provider} rejected your API key. Update it in Settings → API Keys." |

---

## What is Logged vs What the User Sees

| Event | Logged (execution_traces) | Shown to User |
|-------|--------------------------|----------------|
| Provider 429 | ✅ yes | ❌ no (invisible fallback) |
| Provider 503 | ✅ yes | ❌ no (invisible fallback) |
| All providers fail | ✅ yes | ✅ yes — error message |
| Tool 429 with retry | ✅ yes (retry rows) | ❌ no (transparent) |
| Tool repeated failure | ✅ yes | ✅ yes — degraded banner |
| Task timeout | ✅ yes | ✅ yes — task card badge |
| Mission timeout | ✅ yes | ✅ yes — chat error card |
| WS disconnect | ❌ no (client-side) | ✅ yes — reconnect message |
| JSON repair succeeded | ✅ yes | ❌ no |
| JSON repair failed | ✅ yes | ✅ yes — task error |

**Rule:** Log everything, surface only what the user can act on.

---

## How Error Handling Connects to Every Other Plan

| Plan | Errors it can produce → handled by this plan |
|------|----------------------------------------------|
| LLM Provider | Rate limit, timeout, invalid key, JSON parse failure |
| Mission Engine | Planner failure, task loop, mission timeout, stuck missions on restart |
| Tools | Tool 4xx/5xx, timeout, empty result |
| Agents | Context overflow, sub-agent failure |
| Approvals | Decision expired, DB write fail |
| Auth | Token expired → silent refresh. Repeated failure → /login |
| Knowledge | ChromaDB down → document_rag degrades gracefully |
| Observability | Errors tab reads from execution_traces WHERE success=0 |
| Notifications | Mission failed → create_notification called |
| Command Center | WS error events → rendered as error cards in chat |

---

## Build Order

Error handling is not a phase — it is built **alongside** every other plan:

**Phase 1:** LLM provider fallback chain, JSON repair, mission failure WS event, HealthBanner in frontend
**Phase 2:** Task loop detection (10-call limit), task timeout, partial results preservation
**Phase 3:** Tool retry logic (2 retries + exponential backoff), degraded mode banners
**Phase 4:** ChromaDB graceful degradation, stuck mission cleanup on startup
**Phase 5:** Approval expired handling, frontend error states (loading/empty/error) for all views
**Phase 6:** Comprehensive error messages, user-facing error codes, all views have proper empty states
