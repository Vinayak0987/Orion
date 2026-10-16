# 11 — OPERATIONS PLAN

---

## What It Is and Why It Exists in the System

Operations is the **business outcomes dashboard**. It shows the real-world results that have accumulated from everything the agents have done.

It is **not a control panel**. You do not enter data here. You do not configure anything here. You read what the agents produced.

As departments run missions and agents produce outputs, Operations fills up naturally:
- Finance agents complete financial projections → Finance tab shows those numbers
- Marketing agents complete campaign strategies → Marketing tab shows those campaigns
- Sales agents track pipeline → Sales tab shows deals and conversion rates

Without Operations: users see missions (what the agents did) but not the business impact (what it means for the company). Operations is the "so what" of the system.

**Role in the whole system:** Operations is a **pure reader** of mission outputs. The Mission Engine's post-completion processor classifies mission task results and writes them to `operations_data`. Operations reads that table. This means: run missions → Operations fills itself automatically.

---

## How Operations Gets Its Data

This is the key to understanding Operations:

```
Mission task completes
    │
    ▼
Task result stored in mission_tasks.result as JSON
    │
    ▼
Post-mission processor runs (after mission_completed event)
    │
    ▼
LLM classifier call (fast model):
"Classify this task result. Return JSON: { type: string, department: string, data: object }
 Types: financial_projection | campaign_result | sales_data | inventory_update |
        hr_data | research_output | supplier_data | crm_data | ops_workflow
 Task result: {task.title} → {task.result}"
    │
    ▼
Classified output stored in operations_data table
    │
    ▼
Operations tabs read operations_data filtered by type
```

**Example:**
Finance Agent completes task "Project Q4 revenue":
```json
{
  "type": "financial_projection",
  "department": "finance",
  "data": {
    "period": "Q4 2026",
    "revenue": 500000,
    "costs": 320000,
    "profit": 180000,
    "currency": "INR",
    "confidence": "medium"
  }
}
```
→ Stored in `operations_data`
→ Operations/Finance tab queries: `SELECT * FROM operations_data WHERE type = 'financial_projection'`
→ Displays as a financial metrics card

---

## The 10 Sub-Sections

### Overview
**Stats:** Total Operations (count all ops_data rows), Active Workflows (running missions count), Tasks Completed (sum completed mission_tasks), Success Rate (completed / total missions)

**Area Chart:** Operations volume over time (ops_data rows created per day, using recharts)

**Recent Operations Feed:** Last 10 `operations_data` rows across all types, showing: icon (by type), title, source department, time ago

**Quick Actions:** "Run Workflow" (→ Command Center), "View All Operations", "Create Operation" (→ Command Center with pre-filled prompt), "Operation Settings"

### Finance
Financial outputs from Finance agent missions.
- Revenue projections, cost breakdowns, P&L forecasts, budget allocations
- Metric cards: Revenue, Costs, Profit, Cash Position
- Trend chart: revenue/cost over time (recharts)
- Table: all financial_projection entries with period, revenue, cost, profit

### Sales
Pipeline and revenue data from Sales agent missions.
- Deals tracked, conversion rates, pipeline value, revenue targets
- Table: sales_data entries with deal name, value, stage, probability

### Inventory
Stock and supply data from Operations agent missions.
- Item list with quantity, reorder point, status (In Stock / Low / Out)
- inventory_update entries from Operations agents

### Marketing
Campaign data from Marketing agent missions.
- Active campaigns with name, spend, reach, conversion rate
- campaign_result entries from Marketing agents

### Customers / CRM
Customer data from CRM/Sales agent missions.
- Customer count, segments, acquisition rate, lifetime value
- crm_data entries from relevant agents

### Employees / HR
Headcount and hiring data from HR agent missions.
- Headcount by department, open roles, recent hires
- hr_data entries from HR agents

### Research
Research outputs from Research agent missions.
- Completed studies, key findings, sources, confidence level
- research_output entries from Research agents

### Suppliers
Supplier data from Operations agent missions.
- Supplier list with name, status, lead time, contract expiry
- supplier_data entries from Operations agents

### Website
Web analytics (page views, sessions, bounce rate). **LOWEST PRIORITY.** Not core. Static placeholder for now.

---

## Database Table

```sql
CREATE TABLE operations_data (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,       -- financial_projection | campaign_result | sales_data |
                                         --   inventory_update | hr_data | research_output |
                                         --   supplier_data | crm_data | ops_workflow
    department      TEXT,                -- finance | marketing | sales | operations | hr | research
    title           TEXT,                -- generated summary title
    data            TEXT NOT NULL,       -- json: the actual classified data
    source_mission_id TEXT NOT NULL,
    source_task_id  TEXT NOT NULL,
    created_by      TEXT NOT NULL,       -- user_id
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_ops_type ON operations_data(type, created_by, created_at DESC);
CREATE INDEX idx_ops_dept ON operations_data(department, created_by, created_at DESC);
```

---

## API Endpoints

```
GET /operations/summary
  returns: { total_operations, active_workflows, tasks_completed, success_rate, recent_feed[] }

GET /operations/feed
  query:   limit=20, offset
  returns: recent operations_data rows across all types (unified timeline)

GET /operations/{category}
  where category: finance | sales | inventory | marketing | crm | hr | research | suppliers
  query:   limit, offset, period
  returns: paginated operations_data rows for that category

GET /operations/finance
  returns: financial_projection rows + computed totals

GET /operations/marketing
  returns: campaign_result rows

GET /operations/sales
  returns: sales_data rows

...etc for each category
```

---

## How Operations Connects to Every Other Plan

| Plan | Connection |
|------|-----------|
| Mission Engine | After `mission_completed` event → post-processor classifies outputs → writes to `operations_data`. Mission Engine is the **only writer** to this table. |
| Departments | Marketing dept missions → `operations_data.department = 'marketing'` → Operations/Marketing tab. Finance dept missions → Finance tab. Each department's work flows to its corresponding Operations sub-tab. |
| Agents | The quality of Operations data depends on agent output quality. Well-prompted Finance agents produce structured financial data. Poorly prompted ones produce unstructured text that fails classification. |
| Approvals | Approved budget/spend decisions from Approvals → financial actions → become financial_projection entries in Operations/Finance. |
| Observability | Observability shows HOW the system ran (technical). Operations shows WHAT it produced (business). Together = complete picture. |
| Knowledge | Research outputs stored in `operations_data` also get stored as documents in Knowledge for future agent reference. |

---

## Build Order

**Phase 6 (polish phase):**
1. `operations_data` table
2. Post-mission classifier (LLM call after mission_completed)
3. `GET /operations/summary` + wire Overview
4. `GET /operations/finance` + wire Finance tab
5. `GET /operations/marketing` + wire Marketing tab
6. `GET /operations/feed` + wire activity timeline
7. Remaining tabs: Sales, Inventory, HR, Research, Suppliers, CRM

**Note:** Operations is last because it depends on missions being run and producing real data. Building it before real missions run would show empty views anyway. Build it after Phase 1 is running and users can generate real mission outputs.
