# 09 — APPROVALS & HUMAN-IN-THE-LOOP PLAN

---

## What It Is and Why It Exists in the System

Agents are powerful. Some actions should never happen automatically — spending money, sending messages externally, making irreversible changes, hiring, posting publicly.

The Approvals system is the **safety gate**. When an agent wants to take a high-stakes action, it stops and creates a Decision. The mission pauses. The user reviews the full context — what the agent wants to do, why, what the expected impact is. The user approves or rejects. The agent then continues or cancels that action.

Without Approvals: agents could post to Slack, spend budget, send emails, or make bookings entirely without human review. The system would be uncontrollable.

With Approvals: the user is always the final authority on consequential actions. Agents handle the research and analysis autonomously. Humans handle the decisions that matter.

**Role in the whole system:** Approvals sits inside the Mission Engine's execution loop. It is triggered by the Executor when an agent calls `request_approval`. It pauses the Mission Engine, waits for the user, then resumes or cancels. It also writes to Observability's audit log for immutable record-keeping.

---

## When Approvals Trigger

Approval triggering is configured per agent in the `permissions` field (Agents Plan):

```json
{
  "can_send_external": false,
  "spend_limit_usd": 50.0,
  "requires_approval_for": ["post_message", "send_email", "make_booking", "create_contract"]
}
```

**Trigger conditions:**
- `can_send_external: false` → any attempt to call Slack, email, webhook requires approval
- `spend_limit_usd: 50` → any financial action above $50 requires approval
- `requires_approval_for: ["post_message"]` → specific action types always need approval

**How the agent signals it:**
The agent calls a virtual tool `request_approval` in its LLM response:
```json
{
  "tool": "request_approval",
  "input": {
    "title": "Post Q4 strategy to Slack",
    "description": "I want to post the completed Q4 marketing strategy to the #marketing channel",
    "proposed_action": { "channel": "#marketing", "content": "..." },
    "expected_impact": "Team will be informed of the strategy and can begin execution",
    "priority": "medium"
  }
}
```

**Executor intercepts this:**
1. Creates a `decisions` row with status `pending`
2. Pauses the task (status = `waiting_approval`)
3. Emits `{ event: "approval_required", decision_id, title, priority }` over WebSocket
4. Mission Engine waits — other parallel tasks continue, this task is paused

---

## The UI — Two-Column Layout

### Left Column: Decision Queue
- List of all pending approval requests
- Each card shows: icon, title, requesting agent name, description (truncated), priority badge (High/Medium/Low with colors), time ago
- Active/selected card highlighted
- Tabs: Pending (5) / Approved (12) / Rejected (2) / All (19)
- Search bar to find specific requests

### Right Column: Approval Detail Panel
Full context for the selected decision:

**Header:** Icon + title + priority badge + time ago + requesting agent

**Business Context:** What situation led the agent to request this? (Free text from the agent)

**Proposed Action:** Structured breakdown of exactly what will happen. For a budget request: table with line items (Digital Ads ₹1L, Print ₹75K, etc.) and total.

**Expected Impact:** Bullet list of what the agent expects to happen if approved.

**Supporting Evidence:** Files and data the agent collected to justify the request. Click to view.

**Action Buttons (footer):**
- **Reject** (rose) → `POST /decisions/{id}/reject { by, reason }`
- **Request Changes** (outline) → `POST /decisions/{id}/return { by, reason }` → task gets the reason and can revise its request
- **Approve** (indigo) → `POST /decisions/{id}/approve { by }` → task resumes immediately

---

## Inline Approvals in Command Center

When an approval is triggered mid-mission, the user does not need to navigate away:

```
WS emits: { event: "approval_required", decision_id, title, priority }
Command Center injects inline card into the chat:

┌────────────────────────────────────────────────────┐
│ ⚠️  Approval Required                    [Medium]   │
│ Marketing Agent wants to post to Slack              │
│ "Post Q4 strategy to #marketing channel"            │
│                                                     │
│            [Reject]    [Request Changes]  [Approve] │
└────────────────────────────────────────────────────┘

User clicks Approve → POST /decisions/{id}/approve
WS emits: { event: "task_resumed", task_id }
Agent card in chat resumes its progress animation
```

The Approvals section in the sidebar is for managing the **full queue** of all decisions across all missions over time. The inline card in Command Center is for **immediate decisions** during active missions.

---

## Sidebar Badge

The "5" badge on Approvals in the sidebar must show the real count:
```
GET /decisions?status=pending → count field
Polled every 30 seconds
Badge = count (hidden if 0)
```
Replace the currently hardcoded `{ text: "5", color: "rose" }` in `navigation.js`.

---

## Database Table

```sql
CREATE TABLE decisions (
    id              TEXT PRIMARY KEY,
    mission_id      TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    priority        TEXT DEFAULT 'medium',   -- high | medium | low
    proposed_action TEXT,                    -- json: structured action data
    expected_impact TEXT,
    evidence        TEXT DEFAULT '[]',       -- json: list of {name, type, url}
    status          TEXT DEFAULT 'pending',  -- pending | approved | rejected | returned
    created_at      TEXT NOT NULL,
    resolved_at     TEXT,
    resolved_by     TEXT,                    -- user_id
    resolution_reason TEXT
);

CREATE TABLE audit_logs (
    id          TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    action      TEXT NOT NULL,   -- approved | rejected | returned
    by          TEXT NOT NULL,   -- user_id
    reason      TEXT,
    created_at  TEXT NOT NULL
);
-- audit_logs is append-only. Never update or delete rows.
```

---

## API Endpoints

```
GET    /decisions
  query:   status=pending|approved|rejected|all, mission_id?, agent_id?, limit, offset
  returns: list of decisions with summary fields

GET    /decisions/{id}
  returns: full decision detail including proposed_action, evidence, history

GET    /decisions/count
  query:   status=pending
  returns: { count: 5 }   ← used for sidebar badge

POST   /decisions/{id}/approve
  body:    { by: user_id }
  returns: updated decision
  effect:  decision status → approved, task resumes, audit_log row created

POST   /decisions/{id}/reject
  body:    { by: user_id, reason: string }
  returns: updated decision
  effect:  decision status → rejected, task cancelled, audit_log row created

POST   /decisions/{id}/return
  body:    { by: user_id, reason: string }
  returns: updated decision
  effect:  decision status → returned, task gets reason as context, can revise request
```

---

## How Approvals Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Mission Engine | Executor calls `request_approval` → creates decision → pauses task. On resolve → task resumes or cancels. |
| Agents | `agent.permissions` determines WHEN approvals trigger. Different agents have different autonomy levels. |
| Command Center | `approval_required` WS event → inline approval card in chat. Approve/reject without leaving the screen. |
| Observability | Every resolve action → `audit_logs` row. Audit Logs sub-tab reads this for immutable history. |
| Notifications | `approval_required` event → notification created so user is alerted even if not watching Command Center. |
| Operations | Approved budget/spend decisions → become ledger entries tracked in Operations/Finance. |

---

## Build Order

**Phase 5:**
1. `decisions` + `audit_logs` DB tables
2. `request_approval` virtual tool in Executor (intercepted, not dispatched to tool registry)
3. Task pause/resume mechanism in Executor (status = `waiting_approval`)
4. WS events: `approval_required`, `task_resumed`, `task_cancelled`
5. REST endpoints (`GET /decisions`, approve/reject/return)
6. Wire `ViewApprovals` list and detail panel
7. Wire inline approval cards in Command Center chat
8. Replace hardcoded sidebar badge with real `GET /decisions/count` poll
