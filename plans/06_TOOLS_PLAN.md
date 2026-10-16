# 06 — TOOLS PLAN
# Orion AI Business Operating System

**Plan Series:** 06 of 12
**Phase:** Phase 1 (built-in tools with Mission Engine) + Phase 4 (full tools phase)
**Status:** NOT YET BUILT (Phase 1 partially addressed in Mission Engine)
**Depends On:** 01_AUTH, 02_SETTINGS, 04_MISSION_ENGINE, 05_AGENTS

---

## TABLE OF CONTENTS

1. What Tools Are in the System
2. The 5 Types of Tools
3. The 5 Sub-Sections in the Sidebar
4. Database Table
5. API Endpoints
6. How Tools Connect to Every Other Plan
7. Build Order

---

## 1. WHAT TOOLS ARE IN THE SYSTEM

A Tool is something an agent can call to interact with the real world or the system's own data.

### Why Tools Are the Difference Between Useful and Useless

Without tools, an agent is a closed system. It can only generate text based on its LLM training data. That training data has a cutoff date (typically 2023). It knows nothing about the user's business, their customers, their inventory, their competitors' current pricing, or anything that happened last week.

Tools break that limitation:

- **web_search** → Agent finds real, current information from the internet right now.
- **maps_api** → Agent finds real businesses, addresses, and locations.
- **document_rag** → Agent reads the user's own documents. It knows YOUR company's strategy, YOUR product specs, YOUR internal policies.
- **http_request** → Agent calls ANY external API. It can check inventory systems, CRMs, databases, anything with an HTTP endpoint.
- **call_agent** → Agent coordinates with other specialized agents.

Without tools: "Based on general knowledge, here's a generic marketing strategy."
With tools: "I searched your Q3 report, checked competitors' current pricing on their websites, and found 3 vendors near your Chicago office. Here's a specific strategy."

Tools are what make Orion's output grounded in reality rather than hallucinated.

### How Tools Work at Runtime

1. Agent's LLM generates a response that includes a tool call in its output (OpenAI function-calling format or similar structured format).
2. The Executor detects the tool call in the LLM response.
3. The Executor checks: is this tool in `agent.tools[]`? If not → blocked with error.
4. The Executor calls the tool's implementation with the agent's provided arguments.
5. The tool runs (HTTP call, DB query, etc.) and returns a result.
6. The Executor injects the result back into the conversation as a "tool result" message.
7. The LLM generates its next response, now informed by the tool's output.
8. This loop continues until the LLM produces a final response with no more tool calls.

### Tools Are Registered

Every tool that can be used in Orion is registered in the `tools` table. When an agent is assigned tools, the agent's `tools[]` field contains the IDs from this table. The Executor's tool dispatcher reads from this table to know how to call each tool.

---

## 2. THE 5 TYPES OF TOOLS

### TYPE 1 — BUILT-IN TOOLS

Always available. No external configuration needed beyond the API keys in Settings. These ship with Orion.

---

**`web_search(query: str) → SearchResults`**

Implementation: Calls the Serper API (Google search results in JSON format).

Input schema:
```json
{"query": {"type": "string", "description": "The search query"}}
```

Output: List of results, each with title, url, snippet, date.

API key required: `SERPER_API_KEY` (from Settings → API Keys)

Example agent call:
```
web_search("Salesforce CRM pricing 2025 enterprise")
→ Returns: [{title: "Salesforce Pricing...", url: "...", snippet: "Enterprise plan starts at $300/user/month..."}]
```

Execution path:
```python
import httpx

async def web_search(query: str, api_key: str) -> list[dict]:
    response = await httpx.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key},
        json={"q": query, "num": 8}
    )
    return response.json().get("organic", [])
```

---

**`maps_api(query: str, location: str) → PlaceResults`**

Implementation: Calls Google Places API (primary) or OpenStreetMap Nominatim (fallback, no key required).

Input schema:
```json
{
  "query": {"type": "string", "description": "What to search for (e.g., 'coffee shops', 'coworking spaces')"},
  "location": {"type": "string", "description": "Where to search (e.g., 'Chicago, IL', '123 Main St')"}
}
```

Output: List of places with name, address, rating, phone, website, coordinates.

API key required: `GOOGLE_PLACES_API_KEY` (from Settings → API Keys). Falls back to OpenStreetMap if key not set.

Example agent call:
```
maps_api("logistics warehouses", "Chicago, IL")
→ Returns: [{name: "XYZ Logistics", address: "...", rating: 4.2, phone: "..."}]
```

---

**`document_rag(query: str, collection?: str) → Passages`**

Implementation: Embeds the query using sentence-transformers → queries ChromaDB → returns top-k most similar document chunks.

Input schema:
```json
{
  "query": {"type": "string", "description": "What you want to find in the documents"},
  "collection": {"type": "string", "description": "ChromaDB collection to search. Optional — defaults to user's main collection or dept collection."}
}
```

Output: List of passages with content, source document name, similarity score, page number.

API key required: None (uses local sentence-transformers model or user's embedding API).

Example agent call:
```
document_rag("what is our target customer segment for Q4")
→ Returns: [
    {content: "Our Q4 ICP is mid-market SaaS companies with 50-200 employees...", source: "Q4_Strategy.pdf", score: 0.92},
    {content: "Target segment: companies experiencing rapid growth...", source: "ICP_Definition.docx", score: 0.87}
  ]
```

This tool is the bridge between the Knowledge system and the Agent execution system. Every document uploaded to Knowledge becomes searchable via this tool.

---

**`http_request(url: str, method: str, headers?: dict, body?: dict) → Response`**

Implementation: Generic HTTP client. Makes any HTTP request and returns the response.

Input schema:
```json
{
  "url": {"type": "string"},
  "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
  "headers": {"type": "object", "description": "Optional HTTP headers"},
  "body": {"type": "object", "description": "Optional request body (for POST/PUT)"},
  "timeout_seconds": {"type": "number", "default": 30}
}
```

Output: `{status_code, headers, body}` — the raw HTTP response.

API key required: None (keys can be passed in headers by the agent).

Security note: This tool has significant power. Only assign it to agents that need it. Consider restricting allowed URLs in future (allowlist config).

Example agent call:
```
http_request("https://api.mycompany.com/inventory/sku-123", "GET", {"Authorization": "Bearer xyz"})
→ Returns: {status_code: 200, body: {sku: "123", stock: 45, warehouse: "Chicago"}}
```

---

### TYPE 2 — MCP TOOLS

MCP (Model Context Protocol) is an open standard for connecting AI agents to external tool servers.

**How It Works:**
1. An admin or user registers an MCP server by providing its URL.
2. Orion sends a discovery request to the MCP server (`tools/list` endpoint from MCP spec).
3. The MCP server returns a list of its available tools with names, descriptions, and input schemas.
4. Orion registers each discovered tool in its `tools` table with `type='mcp'` and stores the MCP server URL in the `config` field.
5. These tools appear in the Toolbox and can be assigned to agents.

**Execution:**
When an agent calls an MCP tool, the Executor:
1. Looks up the tool in the DB → gets MCP server URL from `config.server_url`
2. Sends a `tools/call` request to the MCP server with the tool name and agent's input
3. MCP server executes the tool and returns the result
4. Executor returns result to the LLM

**Example MCP Servers:**
- **Filesystem MCP:** read_file, write_file, list_directory — lets agents read/write local files
- **Notion MCP:** search_pages, create_page, update_page — full Notion workspace access
- **Brave Search MCP:** brave_search — alternative to Serper for web search
- **GitHub MCP:** list_repos, read_file, create_issue — GitHub access
- **Postgres MCP:** query, insert, update — direct database access

**MCP Registration Request:**
```json
POST /tools/mcp
{
  "server_url": "http://localhost:8765",
  "name": "Filesystem MCP",
  "description": "Read and write local files"
}
```

**Discovery Response (from MCP server):**
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read the contents of a file",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "File path to read"}
        },
        "required": ["path"]
      }
    }
  ]
}
```

---

### TYPE 3 — CUSTOM TOOLS

Any HTTP API can become a tool. No code required.

**How It Works:**
User fills out a form in the Custom Tools section:
- Name: `inventory_lookup`
- Description: "Query the company inventory system for stock levels by SKU"
- Endpoint URL: `https://api.mycompany.com/inventory`
- HTTP Method: `GET`
- Input Schema (JSON):
  ```json
  {
    "sku": {"type": "string", "description": "Product SKU to look up"},
    "warehouse": {"type": "string", "description": "Optional warehouse code"}
  }
  ```

Orion registers this as a tool with `type='custom'`. The endpoint URL is stored in `config.endpoint`.

**Execution:**
When an agent calls `inventory_lookup({"sku": "ABC-123"})`, the Executor:
1. Looks up the tool → gets endpoint URL and method from `config`
2. Calls `GET https://api.mycompany.com/inventory?sku=ABC-123`
3. Returns the HTTP response body to the agent's LLM

**Use Cases:**
- Internal CRM system → agent can look up customer records
- Internal ERP → agent can check inventory, orders, invoices
- Internal analytics API → agent can pull current metrics
- Any SaaS product with an API → weather, news, stock prices, shipping rates
- IoT sensor APIs → agent can read real-time sensor data

Custom tools are the most powerful extensibility mechanism. They turn Orion into a connective layer over the user's entire software stack.

---

### TYPE 4 — INTEGRATION TOOLS (DEFERRED)

OAuth-based integrations with major SaaS platforms.

**Status: DEFERRED — show as "Coming Soon" in UI.**

Why deferred: Each OAuth integration requires:
- A registered app with the provider (Slack app, Google OAuth client, etc.)
- Per-user OAuth token storage and refresh logic
- Provider-specific API client implementation

This is significant work per provider and is not needed for the core Orion value proposition.

**Planned integrations:**
- **Slack:** send_message, list_channels, post_to_channel
- **Google Drive:** list_files, read_file, create_doc, update_doc
- **Notion:** search, create_page, update_database
- **Stripe:** list_customers, create_invoice, check_payment_status
- **Twilio:** send_sms, make_call

**Implementation plan when undeferred:**
1. Register OAuth app with provider
2. Add OAuth flow endpoint: `GET /integrations/{provider}/oauth/start` → redirect
3. Add OAuth callback: `GET /integrations/{provider}/oauth/callback` → store token in Settings
4. Implement tool functions using provider's SDK
5. Register tools in tools table with `type='integration'`

---

### TYPE 5 — AGENT-CALLING (VIRTUAL TOOL)

`call_agent(agent_id: str, message: str)` — runs a sub-agent.

This is NOT a registered tool in the tools table. It is hardcoded into the Executor.

When the Executor injects tool definitions into the LLM's context, it always includes `call_agent` for any agent that has `sub_agents[]` non-empty. The agent can call it to delegate work to a specialist.

See the Sub-Agent Mechanism section in Plan 05 (Agents) for the full execution flow.

The Builder in the Agents section visually represents which agents can be called by other agents via this virtual tool.

---

## 3. THE 5 SUB-SECTIONS IN THE SIDEBAR

---

### 3.1 ALL TOOLS (Toolbox)

**Purpose:** See and manage every tool available in the system.

**Layout:**
- Top bar: Search input + Type filter (All/Built-in/MCP/Custom/Integration) + Category filter + "Add Custom Tool" button
- Tool cards / table rows with:
  - Icon (type-specific: wrench for built-in, plug for MCP, gear for custom)
  - Name
  - Type badge (Built-in/MCP/Custom/Integration)
  - Category badge (Search/Maps/Knowledge/Communication/Data)
  - Status toggle (Active/Inactive) — click to enable/disable
  - Last Used timestamp (from execution_traces)
  - Action buttons: Configure, Test, View Usage

**Active/Inactive Toggle:**
Setting a tool to Inactive means it will be blocked even if an agent has it in their `tools[]` array. Use this to temporarily disable a broken tool without reconfiguring all agents.

**Test Button:**
Opens a modal with a JSON input form. Calls `POST /tools/execute` with `{tool_id, input}`. Shows the tool's raw output. Useful for debugging tool configurations.

**Data source:** `GET /tools` (returns all tools with last_used computed from execution_traces)

---

### 3.2 MCP SERVERS

**Purpose:** Connect and manage MCP tool servers.

**Layout:**
- "Connect Server" button (top right)
- Cards for each connected MCP server:
  - Server name and description
  - URL (masked: shows host only)
  - Tool count (e.g., "6 tools")
  - Status: Connected (green) / Disconnected (red) / Error (yellow)
  - Last Active timestamp
  - Expand button → shows list of all tools from this server
  - Refresh button → re-runs tool discovery
  - Disconnect button

**Connect Server Flow:**
1. User clicks "Connect Server"
2. Modal appears with fields: Server URL, Name (optional), Description (optional)
3. User submits → `POST /tools/mcp` with `{server_url}`
4. Backend sends MCP discovery request to the URL
5. If successful: lists discovered tools in modal for user to review
6. User confirms → tools registered in DB, server appears in list
7. If failed: shows error (connection refused, invalid MCP response, etc.)

**Data source:** `GET /tools/mcp`

---

### 3.3 INTEGRATIONS

**Purpose:** Show available OAuth-based integrations.

**Layout:**
Grid of integration cards. Each shows:
- Provider logo + name
- Short description of what it enables
- Status: Connected (green badge) / Coming Soon (gray badge)
- For connected: shows connected account name + "Disconnect" button
- For coming soon: grayed out, "Coming Soon" badge, no action button

**Available integrations:**
| Integration | Status | Enabled by |
|---|---|---|
| Slack | Coming Soon | — |
| Google Drive | Coming Soon | — |
| Notion | Coming Soon | — |
| Stripe | Coming Soon | — |
| Twilio | Coming Soon | — |
| GitHub | Coming Soon | — |
| HubSpot | Coming Soon | — |

No API calls yet — this section is mostly static display until integrations are implemented. When an integration is implemented, its card gets a real "Connect" button that starts the OAuth flow.

---

### 3.4 CUSTOM TOOLS

**Purpose:** Register HTTP APIs as tools without writing code.

**Layout:**
Two-part screen:

**Left/Top — Registration Form:**
- Name (text, snake_case, unique)
- Display Name (text)
- Description (textarea — important: this is what the LLM reads to decide when to call this tool. Write it clearly.)
- Category (dropdown: search/maps/knowledge/communication/data/custom)
- Endpoint URL (text)
- HTTP Method (radio: GET/POST/PUT/DELETE/PATCH)
- Input Schema (JSON editor with validation)
  ```json
  {
    "property_name": {
      "type": "string|number|boolean|object|array",
      "description": "What this field means",
      "required": true
    }
  }
  ```
- Authentication (optional): None / Bearer Token / API Key Header / Basic Auth
  - If Bearer Token: text input for header name (default: Authorization) + field to enter the token value (stored encrypted)
- Test Endpoint (button) → sends a test request with dummy values → shows response
- Save → `POST /tools/custom`

**Right/Bottom — Custom Tools Table:**
Columns: Name | Endpoint | Method | Category | Status | Last Used | Actions (Edit, Test, Delete)

**The Description Field Is Critical:**
When the Executor presents tool definitions to the LLM, it includes the tool's name + description + input schema. The LLM uses this description to decide whether to call this tool for a given task. A vague description means the LLM won't know when to use it. A clear description means the LLM will call it at the right times.

Good: "Query the internal inventory management system for current stock levels by product SKU. Use this when you need to know how many units of a product are in stock."

Bad: "Inventory API"

---

### 3.5 API KEYS

**This is the most important sub-section in the Tools sidebar.**

**Purpose:** Store the API keys that agents use when making LLM calls and tool calls.

This is different from the Orion platform API keys in Settings (Plan 02). Those are for accessing Orion's API. These keys in the Tools section are the keys that power the actual agent execution:

| Key | Used For | Where It Goes |
|---|---|---|
| Groq API Key | LLM calls (llama-3.1 models) | Passed to GroqClient when agent model = groq:* |
| Gemini API Key | LLM fallback (gemini-pro models) | Passed to Gemini SDK |
| OpenAI API Key | LLM calls (gpt-4o models) | Passed to OpenAI SDK |
| Anthropic API Key | LLM calls (claude models) | Passed to Anthropic SDK |
| Google Places API Key | maps_api tool | Passed to Google Places API calls |
| Serper API Key | web_search tool | Passed to Serper API calls |

**Layout:**
- Header: "These keys are encrypted and used only by your agents. Never shared."
- Cards for each provider:
  - Provider logo + name
  - Status: Configured (green dot) / Not Set (gray)
  - Masked key display: `gsk-••••••••••••••••••••••••••••1a3b` (only last 4 chars visible)
  - "Update" button → inline text input to enter new key → Save
  - "Remove" button → clears the key

**Security rules:**
- Keys are never returned from the API in full. Ever.
- On save: encrypt with Fernet (same as Settings plan) → store in MongoDB
- On display: backend returns only `{provider, last_four, is_set: true}` — never the full value
- On Executor use: backend decrypts in memory at request time, passes to SDK, never logs the value

**Data flow:**
```
User enters Groq key → PUT /settings/api-keys {provider: 'groq', key: 'gsk-...'} 
→ Fernet encrypt → store in MongoDB settings.api_keys.groq
→ Agent task starts → Executor: settings_service.get_api_key(user_id, 'groq') → decrypt → pass to GroqClient
→ LLM call succeeds
```

**Wire to:** `PUT /settings/api-keys` (same endpoint as in Settings plan — this is just a second entry point to the same data)

---

## 4. DATABASE TABLE

### tools table (SQLite)

```sql
CREATE TABLE tools (
    id          TEXT PRIMARY KEY,   -- UUID
    name        TEXT NOT NULL UNIQUE, -- snake_case identifier used in agent.tools[]
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,       -- CRITICAL: read by LLM to decide when to call this tool
    type        TEXT NOT NULL,       -- builtin|mcp|custom|integration
    category    TEXT NOT NULL,       -- search|maps|knowledge|communication|data|custom
    input_schema TEXT NOT NULL DEFAULT '{}', -- JSON schema for inputs
    config      TEXT NOT NULL DEFAULT '{}',  -- JSON: {server_url} for MCP, {endpoint, method, auth} for custom
    enabled     INTEGER NOT NULL DEFAULT 1,  -- 0/1 bool
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_tools_type ON tools(type);
CREATE INDEX idx_tools_enabled ON tools(enabled);
```

**config JSON shape by type:**

For `type='mcp'`:
```json
{
  "server_url": "http://localhost:8765",
  "mcp_server_id": "uuid-of-mcp-server-record"
}
```

For `type='custom'`:
```json
{
  "endpoint": "https://api.example.com/inventory",
  "method": "GET",
  "auth_type": "bearer",
  "auth_header": "Authorization",
  "auth_value_encrypted": "..."
}
```

For `type='builtin'`: config is `{}`

### mcp_servers table (SQLite)

Tracks connected MCP servers separately from individual tools.

```sql
CREATE TABLE mcp_servers (
    id          TEXT PRIMARY KEY,   -- UUID
    name        TEXT NOT NULL,
    description TEXT,
    server_url  TEXT NOT NULL UNIQUE,
    status      TEXT NOT NULL DEFAULT 'connected', -- connected|disconnected|error
    tool_count  INTEGER DEFAULT 0,
    last_active TEXT,
    created_at  TEXT NOT NULL
);
```

---

## 5. API ENDPOINTS

All endpoints require Authorization header (JWT).

```
GET /tools
```
List all tools. Query params: `?type=builtin|mcp|custom|integration`, `?enabled=true|false`, `?category=`. Returns: array of tool objects with computed `last_used` (from execution_traces).

```
POST /tools/custom
```
Register a custom HTTP tool. Body:
```json
{
  "name": "inventory_lookup",
  "display_name": "Inventory Lookup",
  "description": "Query internal inventory for stock levels by SKU...",
  "category": "data",
  "endpoint": "https://api.company.com/inventory",
  "method": "GET",
  "input_schema": {...},
  "auth_type": "bearer",
  "auth_value": "secret-key-here"
}
```
Returns: created tool object (auth_value not returned — only confirmation it was stored).

```
PUT /tools/{id}
```
Update tool configuration. Same body shape as POST. Returns: updated tool.

```
DELETE /tools/{id}
```
Remove tool from registry. Side effect: if any agents have this tool_id in their `tools[]` array, it is silently removed. Returns: `{deleted: true}`.

```
POST /tools/execute
```
Test a tool directly without running through an agent. Body:
```json
{
  "tool_id": "web_search_id",
  "input": {"query": "Salesforce pricing 2025"}
}
```
Returns: raw tool output. For built-in tools: calls the actual API (uses user's API key). For custom tools: calls the registered endpoint. For MCP tools: calls the MCP server.

```
GET /tools/mcp
```
List all connected MCP servers. Returns: array of mcp_server objects with their tool lists.

```
POST /tools/mcp
```
Connect a new MCP server. Body: `{server_url, name?, description?}`. Side effects:
1. Sends MCP `tools/list` discovery request to server_url
2. Registers each discovered tool in tools table with type='mcp'
3. Creates mcp_servers record
Returns: `{server: {...}, tools_discovered: [...]}` or error if connection failed.

```
DELETE /tools/mcp/{id}
```
Disconnect MCP server. Side effects:
1. Deletes all tools from tools table that belong to this MCP server (type='mcp' AND config.mcp_server_id = id)
2. Deletes mcp_servers record
Returns: `{deleted: true, tools_removed: 6}`.

---

## 6. HOW TOOLS CONNECT TO EVERY OTHER PLAN

**→ Mission Engine (Plan 04) — Primary Consumer**
The Executor is where all tool calls actually happen. Flow:
```python
# In Executor._run_tool_call()
async def _run_tool_call(self, agent: Agent, tool_name: str, tool_input: dict):
    # 1. Verify authorization
    tool = db.get_tool_by_name(tool_name)
    if tool.id not in agent.tools:
        raise ToolNotAuthorizedError(f"{agent.name} cannot use {tool_name}")
    
    # 2. Check tool is enabled
    if not tool.enabled:
        raise ToolDisabledError(f"{tool_name} is currently disabled")
    
    # 3. Dispatch to correct implementation
    if tool.type == 'builtin':
        result = await builtin_dispatcher.call(tool.name, tool_input, user_api_keys)
    elif tool.type == 'mcp':
        result = await mcp_client.call(tool.config['server_url'], tool.name, tool_input)
    elif tool.type == 'custom':
        result = await http_client.call(tool.config['endpoint'], tool.config['method'], tool_input)
    
    # 4. Write to execution_traces
    trace_service.record_tool_call(tool.name, tool_input, result, latency_ms)
    
    return result
```

**→ Agents (Plan 05)**
The agent's `tools[]` field (array of tool_ids) is the authorization list. The Builder UI shows each tool as a tool node connected to the agent. Adding or removing a tool in Builder updates this array. The Executor enforces it.

**→ Knowledge (Plan 07)**
`document_rag` is the most important built-in tool for the knowledge system. It IS the connection between agent execution and the Knowledge document store. When the Knowledge plan uploads and embeds documents into ChromaDB, `document_rag` is how agents access those documents at runtime. Without `document_rag` tool, the Knowledge system would have data but no way to use it.

**→ Settings (Plan 02) / API Keys (this plan, section 3.5)**
Built-in tools need user API keys:
- `web_search` needs `SERPER_API_KEY`
- `maps_api` needs `GOOGLE_PLACES_API_KEY`
- LLM calls need `GROQ_API_KEY`, `GEMINI_API_KEY`, etc.

The Executor fetches these keys from the Settings service before calling any tool or LLM. If a key is missing, the tool returns a configuration error (not a crash).

**→ Observability (future Plan)**
Every tool call is recorded in `execution_traces`:
```json
{
  "event_type": "tool_call",
  "tool_name": "web_search",
  "tool_id": "uuid",
  "input": {"query": "..."},
  "output": "[search results]",
  "latency_ms": 1240,
  "success": true,
  "error": null
}
```
The Tools Toolbox shows `last_used` computed from this data. The Agents Performance view shows Tool Usage bars from this data.

**→ Command Center (Plan 03)**
The "Tools Being Used" panel in the Command Center right sidebar reads real-time WebSocket events from the Executor:
```json
{
  "event": "tool_called",
  "tool_name": "web_search",
  "agent_name": "Research Agent",
  "input_preview": "Salesforce pricing 2025...",
  "timestamp": "2025-..."
}
```
These events are emitted by the Executor and consumed by the Command Center's WS connection.

**→ Departments (Plan 08)**
Tool usage can be filtered by department in the Observability views. Department-scoped document_rag calls filter by `collection = dept.knowledge_collection_id`.

---

## 7. BUILD ORDER

### Phase 1 — With Mission Engine (Required for any agent to work)

These must be built before the Mission Engine can run any agent:

```
Step 1: Tool registry table
  - Create tools table migration
  - Seed 4 built-in tools (web_search, maps_api, document_rag, http_request)
  - Each seeded with correct name, description, input_schema, type='builtin'

Step 2: web_search implementation
  - Install httpx
  - Implement web_search() function using Serper API
  - Read SERPER_API_KEY from user settings
  - Register in Executor's builtin_dispatcher
  - Test: POST /tools/execute {tool_id: web_search_id, input: {query: "test"}}

Step 3: document_rag implementation
  - Install chromadb, sentence-transformers
  - Implement document_rag() function: embed query → ChromaDB similarity search → return chunks
  - Register in Executor's builtin_dispatcher
  - Note: At this phase, ChromaDB may be empty — that's OK. Tool works, returns empty results.
```

### Phase 4 — Full Tools & Knowledge Phase

After Agents (Phase 2) and Departments (Phase 3) are built:

```
Step 4: maps_api implementation
  - Implement maps_api() with Google Places primary + OpenStreetMap fallback
  - Read GOOGLE_PLACES_API_KEY from user settings
  - Register in builtin_dispatcher

Step 5: http_request tool implementation
  - Implement generic HTTP client function
  - Add timeout handling, error handling
  - Register in builtin_dispatcher
  - Security: Log all URLs called for audit purposes

Step 6: MCP client implementation
  - Install mcp Python SDK or implement raw HTTP client to MCP protocol
  - POST /tools/mcp endpoint (connect server + discover tools)
  - DELETE /tools/mcp/{id} endpoint
  - GET /tools/mcp endpoint
  - Wire discovery: send tools/list → parse → insert into tools table
  - Wire call: tools/call → proxy to MCP server

Step 7: Custom tool registration
  - POST /tools/custom endpoint
  - GET /tools?type=custom endpoint
  - Implement custom tool executor in builtin_dispatcher:
    if tool.type == 'custom': http_client.call(tool.config.endpoint, ...)

Step 8: Wire Toolbox view (ALL TOOLS section)
  - GET /tools → render table
  - Enable/disable toggles → PUT /tools/{id}
  - Test button → POST /tools/execute → show result modal

Step 9: Wire MCP Servers view
  - GET /tools/mcp → render server cards
  - Connect Server form → POST /tools/mcp
  - Disconnect → DELETE /tools/mcp/{id}

Step 10: Wire Custom Tools view
  - Custom tool form → POST /tools/custom
  - GET /tools?type=custom → render table
  - Edit/Delete existing custom tools
  
Step 11: Wire API Keys view
  - This is an alias to the Settings API Keys section
  - Wire to same PUT /settings/api-keys endpoint
  - Masked display: only show last 4 chars
```

### What Is NOT in Phase 4

- OAuth integrations (Slack, Google Drive, Notion) — these are a separate phase entirely
- Tool usage analytics dashboard — that's Observability plan
- Per-user tool permissions (admin assigns which users can use which tools) — future feature

---

*End of 06_TOOLS_PLAN.md*
