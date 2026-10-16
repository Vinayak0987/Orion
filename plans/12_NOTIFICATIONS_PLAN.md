# 12 — NOTIFICATIONS SYSTEM PLAN

---

## What It Is and Why It Exists in the System

Notifications tell the user when something important happened anywhere in the system — without requiring them to manually check every section.

Without Notifications: a mission could complete, an approval could be pending, an agent could be failing — and the user would have no idea unless they happened to be looking at the right screen at the right time.

With Notifications: important events surface automatically. The user sees a badge on the bell icon. They know when to act. The system feels alive and responsive.

**Role in the whole system:** Notifications is a **consumer of events from all other plans**. It does not create business logic. It does not write to operational tables. It reads events that other plans emit and surfaces them to the user. It is the last plan to build because it depends on everything else being in place first.

---

## The Events That Generate Notifications

Each event comes from a specific plan:

### From Mission Engine
| Event | Title | When |
|-------|-------|------|
| `mission_completed` | "Mission completed" | All tasks done successfully |
| `mission_failed` | "Mission failed" | Unrecoverable error |
| `mission_waiting_approval` | "Approval required" | Any task hits approval gate |

### From Approvals
| Event | Title | When |
|-------|-------|------|
| `approval_required` | "Action requires your approval" | Agent creates decision (HIGHEST PRIORITY — badge turns red) |
| `approval_resolved` | "Decision resolved" | Another user approved/rejected (multi-user future) |

### From Agents
| Event | Title | When |
|-------|-------|------|
| `agent_error_recovered` | "Agent recovered from error" | Auto-retry succeeded |
| `agent_repeatedly_failing` | "Agent needs attention" | 3+ consecutive failures |

### From System
| Event | Title | When |
|-------|-------|------|
| `llm_provider_degraded` | "LLM provider issue" | Groq/Gemini unavailable |
| `api_key_quota_warning` | "API quota warning" | Near rate limit |

---

## The UI

### Notification Feed (Left Column)
- Scrollable list of all notifications, newest first
- Each row: colored icon (by type), title, description (truncated), time ago
- Unread items: blue left border
- Active/selected item: highlighted background
- Tabs: All (20) / Missions (8) / Approvals (5) / Agents (4) / System (3)
- "Mark all as read" button → `POST /notifications/read-all`

### Notification Detail (Right Column)
For the selected notification:
- Full title and description
- Related entity: mission name (link), agent name (link), decision title (link)
- Metadata: triggered by, at what time, which department
- Action button: "View Mission" → navigates to that mission | "View Approval" → Approvals section
- "Mark as unread" toggle

---

## Sidebar Badge

**Notifications bell badge (currently hardcoded "12"):**
```javascript
// Replace hardcoded { text: "12", color: "indigo" } in navigation.js with:
// Dynamic count from GET /notifications/count?unread=true
// Poll every 30 seconds
// Show badge only if count > 0
// Hide if 0 (no badge)
```

**Approvals badge (currently hardcoded "5"):**
```javascript
// Replace with GET /decisions/count?status=pending
// Poll every 30 seconds
// Show only if > 0
```

Both badges implemented in `Sidebar.jsx` using `usePolling` hook (already exists in the codebase).

---

## Implementation — Simple Polling (No WebSocket Needed)

No need for a dedicated notification WebSocket. Use simple polling:

```javascript
// In Sidebar.jsx — badge counts
const { data: notifCount } = usePolling(() => api.notifications.count(), 30000);
const { data: approvalCount } = usePolling(() => api.decisions.count(), 30000);
```

Notification events are **generated at the source** (Mission Engine, Approvals) by calling a `create_notification(user_id, type, title, description, entity_type, entity_id)` function. This writes a row to the `notifications` table. The frontend polls for new rows.

---

## Database Table

```sql
CREATE TABLE notifications (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    type        TEXT NOT NULL,         -- mission_completed | mission_failed | approval_required |
                                       --   agent_error | system_alert
    title       TEXT NOT NULL,
    description TEXT,
    entity_type TEXT,                  -- mission | decision | agent
    entity_id   TEXT,                  -- the id of the related entity
    priority    TEXT DEFAULT 'normal', -- high | normal | low
    read        INTEGER DEFAULT 0,     -- 0 = unread, 1 = read
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_notif_user ON notifications(user_id, read, created_at DESC);
```

---

## API Endpoints

```
GET /notifications
  query:   limit=50, offset, type, unread=true|false
  returns: list of notification objects

GET /notifications/count
  query:   unread=true
  returns: { count: 7 }  ← used for sidebar badge

POST /notifications/{id}/read
  marks one notification as read
  returns: { updated: true }

POST /notifications/read-all
  marks all as read for this user
  returns: { updated: 12 }

DELETE /notifications/{id}
  removes one notification
```

---

## How Notifications Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Mission Engine | Calls `create_notification` on `mission_completed` and `mission_failed` events |
| Approvals | Calls `create_notification` on `approval_required` (priority=high) and approval resolved |
| Agents | Calls `create_notification` on `agent_repeatedly_failing` |
| Command Center | `approval_required` notifications have a direct action button → navigates inline |
| All other plans | They are **event sources**. They call `create_notification()`. Notifications only displays. |

**The `create_notification` function:**
```python
async def create_notification(
    user_id: str,
    type: str,
    title: str,
    description: str,
    entity_type: str = None,
    entity_id: str = None,
    priority: str = "normal"
):
    await db.insert("notifications", {
        "id": new_id(),
        "user_id": user_id,
        "type": type,
        "title": title,
        "description": description,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "priority": priority,
        "read": 0,
        "created_at": now()
    })
```

This function is called by Mission Engine and Approvals at their event points. No complex pub/sub system needed.

---

## Build Order

**Phase 6 (last — after all other plans are working):**
1. `notifications` table
2. `create_notification()` utility function
3. Add `create_notification` calls to Mission Engine (`mission_completed`, `mission_failed`)
4. Add `create_notification` calls to Approvals (`approval_required`)
5. `GET /notifications` + `GET /notifications/count` endpoints
6. Wire `ViewNotifications` list and detail
7. Replace hardcoded "12" badge in `Sidebar.jsx` with real `usePolling` on count
8. Replace hardcoded "5" Approvals badge with real `GET /decisions/count`
9. Mark as read / read all
10. Add `create_notification` for agent failures (Phase 6 polish)
