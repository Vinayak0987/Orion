# 10 — OBSERVABILITY PLAN

---

## What It Is and Why It Exists in the System

Observability is the **complete X-ray of everything the system has ever done**.

Every LLM call, every tool call, every token consumed, every millisecond of latency, every error, every cost — all recorded and queryable.

Without Observability: when something goes wrong, you have no idea why. When an agent is slow, you cannot see where the time goes. When costs spike, you cannot see which agent or tool is responsible. The system is a black box.

With Observability: you see exactly which step in which task in which mission caused the problem. You see which LLM provider handled the most requests. You see which tools are failing. You can debug, optimize, and improve with evidence.

**Role in the whole system:** Observability is a **pure reader**. It does not write to any operational table. It reads exclusively from `execution_traces` (written by the Mission Engine's Executor) and `audit_logs` (written by Approvals). This means: build the Mission Engine first, run some missions, and Observability data appears automatically — no extra instrumentation needed.

---

## Where All the Data Comes From

**One source: `execution_traces` table.**

The Mission Engine's Executor writes one row to this table for:
- Every LLM call: `trace_type=llm`, provider, model, input_tokens, output_tokens, cost_usd, latency_ms, success
- Every tool call: `trace_type=tool`, tool_name, tool_input, tool_output, latency_ms, success, error_message

That is the only writer. Every sub-section of Observability is a different aggregation query on this one table.

---

## The 9 Sub-Sections

### 1. Dashboard
The high-level health view.

**4 KPI Cards:**
```sql
Success Rate:  SELECT (SUM(success) * 100.0 / COUNT(*)) FROM execution_traces WHERE created_by = user_id
Avg Latency:   SELECT AVG(latency_ms) FROM execution_traces WHERE ...
Total Runs:    SELECT COUNT(DISTINCT mission_id) FROM execution_traces WHERE ...
Total Cost:    SELECT SUM(cost_usd) FROM execution_traces WHERE ...
```

**Bar Chart:** Run volume per hour over last 24h
```sql
SELECT strftime('%H', created_at) as hour, COUNT(*) as runs
FROM execution_traces WHERE created_at > (now - 24h) GROUP BY hour
```

**Line Chart:** Avg latency per hour over last 24h

**System Health Table:**
- Agents: success rate across all agent runs
- Tools: success rate across all tool calls
- LLM Providers: availability (Groq/Gemini/Ollama each available or not)

### 2. Runs / Sessions
Table of all missions with high-level trace summary.

Columns: Time, Mission Title (truncated prompt), Status, Agents Used (count), Duration (ms), Tokens, Cost ($)

```sql
SELECT m.id, m.title, m.status, m.created_at,
       COUNT(DISTINCT t.agent_id) as agent_count,
       SUM(t.input_tokens + t.output_tokens) as total_tokens,
       SUM(t.cost_usd) as total_cost,
       MAX(t.created_at) - MIN(t.created_at) as duration_ms
FROM missions m JOIN execution_traces t ON t.mission_id = m.id
GROUP BY m.id ORDER BY m.created_at DESC
```

Click row → navigates to Trace Details for that mission.

### 3. Trace Details
Step-by-step breakdown of one mission. The most detailed view.

**Timeline:** Each step shown as a card in order:
1. Initialize → agent loaded from DB
2. Retrieve Context → memory retrieval from ChromaDB
3. Plan → Planner LLM call (shows model, tokens, latency)
4. Execute Tools → each tool call (shows tool name, input, output, latency)
5. LLM Call → the main agent LLM call (shows model, tokens, latency)
6. Post Process → memory storage, result classification

Each card shows: step number, type (llm/tool), name, duration, ✅ success or ❌ fail.

**Right panel (Step Details):** When a step is selected:
- Input JSON (what was sent)
- Output JSON (what was returned)
- Duration, cost, provider
- Error message (if failed)

**"Re-run" button:** `POST /missions { prompt: mission.prompt, department_id: mission.department_id }` — creates a new mission with the same prompt.

### 4. Tool Usage
Which tools are being called most and how they are performing.

**Bar Chart:** Tool call counts by tool name

**Table:**
```
Tool Name      | Calls | Success Rate | Avg Latency | Failures
web_search     | 1,240 | 97.2%        | 1,340ms     | 34
maps_api       | 456   | 94.1%        | 2,100ms     | 27
document_rag   | 890   | 99.8%        | 340ms       | 2
```

```sql
SELECT tool_name,
       COUNT(*) as calls,
       (SUM(success) * 100.0 / COUNT(*)) as success_rate,
       AVG(latency_ms) as avg_latency,
       SUM(1 - success) as failures
FROM execution_traces WHERE trace_type = 'tool' GROUP BY tool_name
```

### 5. LLM Usage & Costs
Token and cost breakdown per provider.

**Provider cards:** Groq / Gemini / Ollama / OpenAI — each showing total calls, input tokens, output tokens, estimated cost

**Daily cost trend chart:** Line chart showing cost per day over last 30 days

**Usage table:**
```
Provider | Calls | Input Tokens | Output Tokens | Cost ($)
Groq     | 8,400 | 12.4M        | 3.2M          | $18.40
Gemini   | 1,200 | 1.8M         | 0.4M          | $4.20
Ollama   | 320   | 0.4M         | 0.1M          | $0.00
```

```sql
SELECT provider, COUNT(*) as calls,
       SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens,
       SUM(cost_usd) as total_cost
FROM execution_traces WHERE trace_type = 'llm' GROUP BY provider
```

### 6. Errors & Failures
Error log with trend chart.

**Error rate trend:** Line chart — percentage of failed calls per day

**Error log table:**
```
Time           | Agent           | Type  | Error Message                    | Mission
2m ago         | Research Agent  | tool  | Serper API 429: rate limited     | Competitor Analysis
15m ago        | Finance Agent   | llm   | JSON parse error on retry 2      | Q4 Forecast
1h ago         | Marketing Agent | tool  | HTTP 403: Slack token expired    | Campaign Launch
```

```sql
SELECT t.created_at, a.name as agent_name, t.trace_type, t.error_message, m.title
FROM execution_traces t
JOIN agents a ON t.agent_id = a.id
JOIN missions m ON t.mission_id = m.id
WHERE t.success = 0 ORDER BY t.created_at DESC
```

### 7. Evaluations
Quality scoring for mission outputs. **LOW PRIORITY — build last.**

Metrics: completeness (did the mission produce all expected sections?), accuracy (factual grounding score), task_completion_rate.

Not based on `execution_traces`. Needs a separate evaluation run after each mission using a judge LLM. Defer to after v1.

### 8. Audit Logs
Immutable record of every approval decision. Reads from `audit_logs` table (written by Approvals Plan).

**Table:**
```
Time        | Decision Title              | Action   | By       | Reason
2h ago      | Marketing Budget Approval   | Approved | Abhishek | —
1 day ago   | Post to Slack              | Rejected | Abhishek | Not ready yet
3 days ago  | Hire Data Analyst Agent    | Approved | Abhishek | —
```

This table is **append-only**. No deletes. This is the compliance trail.

### 9. Website
Frontend performance metrics (page load, JS errors, session count). **LOWEST PRIORITY.** Not core to the system. Build after everything else.

---

## Database

No new tables needed for Observability beyond what Mission Engine already creates.

**Reads from:**
- `execution_traces` (Mission Engine's Executor writes this)
- `audit_logs` (Approvals Plan writes this)
- `missions` (for join on mission title)
- `agents` (for join on agent name)

**Optional: `observability_snapshots`** for pre-computed aggregations if queries become slow:
```sql
CREATE TABLE observability_snapshots (
    id TEXT PRIMARY KEY,
    snapshot_type TEXT,  -- daily_summary | provider_usage | tool_usage
    period TEXT,         -- 2026-10-15
    data TEXT,           -- json aggregated data
    created_at TEXT
);
```
Pre-compute nightly for performance. Not needed initially.

---

## API Endpoints

```
GET /observability/summary
  query:   period=24h|7d|30d
  returns: { success_rate, avg_latency_ms, total_runs, total_cost_usd, system_health }

GET /observability/runs
  query:   limit, offset, status, agent_id, department_id, period
  returns: list of missions with aggregated trace stats

GET /observability/runs/{mission_id}/trace
  returns: ordered list of execution_traces for this mission with step structure

GET /observability/llm
  query:   period
  returns: per-provider breakdown (calls, tokens, cost) + daily trend

GET /observability/tools
  query:   period
  returns: per-tool stats (calls, success_rate, avg_latency, failures)

GET /observability/errors
  query:   period, agent_id, trace_type
  returns: error log + error rate trend

GET /observability/audit
  query:   limit, offset, period
  returns: audit_log rows with decision context
```

---

## How Observability Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Mission Engine | Executor writes every LLM/tool call to `execution_traces`. This is the ONLY data source for Observability. |
| Agents | `GET /agents/{id}/performance` uses the same aggregation queries, filtered by `agent_id`. |
| Approvals | Audit Logs sub-tab reads `audit_logs` table written by Approvals resolve actions. |
| Tools | Tool Usage sub-tab shows real tool performance from `execution_traces WHERE trace_type='tool'`. |
| All other plans | Observability is a **pure reader**. It influences nothing. It shows everything. |

---

## Build Order

**Phase 5 (after Mission Engine is running and traces are being written):**
1. `GET /observability/summary` → wire Dashboard KPIs
2. `GET /observability/runs` → wire Runs table
3. `GET /observability/runs/{id}/trace` → wire Trace Details
4. `GET /observability/llm` → wire LLM Usage & Costs
5. `GET /observability/tools` → wire Tool Usage
6. `GET /observability/errors` → wire Errors & Failures
7. `GET /observability/audit` → wire Audit Logs
8. Recharts charts wired to real data (Observability already uses recharts)
9. Defer: Evaluations, Website
