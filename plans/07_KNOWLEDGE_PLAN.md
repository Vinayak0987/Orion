# 07 — KNOWLEDGE BASE & MEMORY PLAN
# Orion AI Business Operating System

**Plan Series:** 07 of 12
**Phase:** Phase 4 (Tools & Knowledge phase)
**Status:** NOT YET BUILT
**Depends On:** 01_AUTH, 04_MISSION_ENGINE, 05_AGENTS, 06_TOOLS (document_rag must be seeded)

---

## TABLE OF CONTENTS

1. What Knowledge Is in the System
2. The 5 Sub-Sections in the Sidebar
3. How the Document Pipeline Works
4. How Memory Works
5. Database Tables
6. API Endpoints
7. How Knowledge Connects to Every Other Plan
8. Build Order

---

## 1. WHAT KNOWLEDGE IS IN THE SYSTEM

Knowledge is what agents know beyond the boundary of their LLM training data.

### The Problem Without Knowledge

Every LLM has a training cutoff. As of writing, most models know nothing after early 2024. More importantly, no LLM was trained on YOUR business:

- Your company's internal strategy documents
- Your pricing tiers and contract terms
- Your Q3 performance data
- Your product specifications
- Your customer support playbooks
- Your supplier agreements
- Decisions made in last week's board meeting

Without the Knowledge system, when an agent is asked "What is our standard pricing for enterprise clients?", it either halluccinates an answer or admits it does not know. Neither is useful.

With the Knowledge system, the agent calls `document_rag("standard pricing enterprise clients")` → retrieves the relevant section from your pricing PDF → gives a specific, accurate answer grounded in your actual document.

### Two Types of Knowledge

**Type 1: Documents**
Files and URLs that the user explicitly uploads. These become the searchable knowledge base for agents. Think of it as giving agents access to a company's entire document library.

Supported sources: PDF, DOCX, TXT, CSV, URLs, Excel (future), Notion pages (future), Google Drive (future).

Processing pipeline: Upload → Parse text → Split into chunks → Embed chunks → Store in ChromaDB → Available for `document_rag` queries.

**Type 2: Memory**
Episodic memory that agents build automatically through their own work. After every task, the Executor extracts key facts and stores them in ChromaDB keyed to the agent. Before every task, relevant memories are retrieved and added to the agent's prompt.

Think of it as: the first time a Customer Support agent handles a ticket about a specific integration bug, it learns what the resolution was. The next time a similar ticket comes in, it already knows the resolution without being told.

### The Impact

Without Knowledge:
> "Based on general business best practices, Q4 marketing strategies typically involve..."
> (Generic. Could be from any LLM response for any company.)

With Knowledge:
> "According to your Q4_Strategy.pdf, your primary goal is growing the enterprise segment by 30%. The ICP_Definition.docx specifies your target is mid-market SaaS companies with 50–200 employees. In my previous run analyzing Q3 results, I noted that LinkedIn campaigns outperformed Google Ads by 2.3x for this segment."
> (Specific. Grounded in the company's actual documents and past work.)

---

## 2. THE 5 SUB-SECTIONS IN THE SIDEBAR

---

### 2.1 KNOWLEDGE BASE

**Purpose:** The main document library. See everything that has been uploaded.

**Layout:**
- Top bar: Search by document name + Department filter dropdown + Type filter (PDF/DOC/XLS/URL/All) + View toggle (List/Grid) + "Add Document" button
- Status summary strip: "142 documents | 89,430 chunks | 4 departments | Last updated 2h ago"

**Document Table (List view):**

| Column | Description |
|---|---|
| Name | File name or URL title. Clicking opens DocumentViewer |
| Type | Icon + badge: PDF, DOCX, TXT, CSV, URL, XLS |
| Department | Which dept collection it belongs to (or "All Departments") |
| Size | File size in KB/MB |
| Chunks | Number of text chunks stored in ChromaDB |
| Status | Active (green) / Processing (yellow spinner) / Error (red) / Review (orange) |
| Last Updated | When it was uploaded or re-ingested |
| Actions | Preview, Re-index, Delete |

**Grid view:** Each document as a card with type icon, name, status badge, chunk count.

**DocumentViewer (right panel, opened on click):**
- Top: document name, type, upload date, chunk count
- Tabs:
  - **Preview tab:** Rendered document content (PDF preview via iframe or extracted text)
  - **Chunk Inspector tab:** Table of all chunks from this document, each showing: chunk index, text content (first 200 chars), embedding similarity to a test query (user can type a query and see which chunks it would match)
  - **Usage tab:** Recent `document_rag` calls that returned chunks from this document (from execution_traces)

**Data source:** `GET /knowledge/documents`

---

### 2.2 UPLOAD SOURCES

**Purpose:** The interface for adding new documents to the knowledge base.

**Layout:**

**Primary upload area — Drag and drop zone:**
Large dashed rectangle: "Drop files here, or click to browse"
- Accepts: .pdf, .docx, .txt, .csv, .xlsx
- Multi-file upload supported
- Shows file list with progress bars as files upload and process

**Secondary inputs — URL ingestion:**
Text input: "Paste a URL to ingest"
Examples shown: web page, Google Doc link (view-only), Notion page link
Submit → starts URL parsing pipeline

**Configuration options (expandable section):**
- Department assignment: dropdown (assign to specific dept or All Departments)
- Processing settings:
  - Chunk size: 200 / 500 / 1000 tokens (default: 500)
  - Chunk overlap: 0 / 50 / 100 tokens (default: 50)
  - Embedding model: sentence-transformers/all-MiniLM-L6-v2 (default) or user's OpenAI embedding model if key is set

**Processing status:**
After upload, a live status panel shows each file progressing through stages:
```
Q4_Strategy.pdf
  ✓ Uploaded (0.3s)
  ✓ Parsed — 42 pages, 18,400 words
  ✓ Chunked — 87 chunks created
  ⟳ Embedding — 45/87 chunks embedded...
  ○ Storing in ChromaDB
  ○ Done
```

**Supported formats and parsers:**

| Format | Parser | Notes |
|---|---|---|
| PDF | pdfminer.six | Extracts text + basic structure. Tables may need special handling. |
| DOCX | python-docx (docx2txt) | Preserves headings, paragraphs. |
| TXT | Direct read | UTF-8 assumed. |
| CSV | pandas | Each row becomes a chunk. Headers included in each chunk. |
| XLSX | openpyxl | Sheet by sheet, row by row. |
| URL | requests + BeautifulSoup | Fetches page, strips HTML, extracts main content. |

**Future (Coming Soon) — shown as grayed-out tiles:**
- Notion Pages (OAuth integration required)
- Google Drive (OAuth integration required)
- Dropbox (OAuth integration required)
- Confluence (API key integration)

---

### 2.3 MEMORY OVERVIEW

**Purpose:** See what all agents have learned from their past runs.

The Memory Overview is a read-only window into the episodic memory store across all agents. It answers: "What do my agents know from their past work?"

**Layout:**
- Filters: Agent dropdown | Department dropdown | Date range | Search by content
- Summary stats: Total memory entries | Active (not expired) | Expiring this week | By agent breakdown

**Memory entries displayed as cards or table rows:**

| Column | Description |
|---|---|
| Agent | Name of the agent that generated this memory |
| Content | First 200 chars of the memory text |
| Source Mission | Mission name/ID where this memory was created (clickable link) |
| Created | When this memory was stored |
| Expires | When TTL expires. Color: green (>30 days), orange (7-30 days), red (<7 days) |
| Similarity | Most recent similarity score when this memory was retrieved (0.0–1.0) |
| Actions | View Full, Delete |

**Example memory entries:**

```
Agent: SEO Agent
Content: "The target keyword cluster for Q4 is 'enterprise project management' and its variations. 
         Volume: 22,000/mo. Difficulty: 67. Top competitor: Asana..."
Source: Mission #847 — "Q4 SEO Strategy"
Created: Oct 12, 2025
Expires: Jan 10, 2026 (90 days)
```

```
Agent: Customer Support Agent  
Content: "The integration error 'ERR_WEBHOOK_TIMEOUT' is caused by the user's firewall blocking 
         outbound port 443 to webhooks.orion.ai. Resolution: whitelist the IP range..."
Source: Mission #831 — "Handle ticket #12094"
Created: Oct 8, 2025
Expires: Jan 6, 2026 (90 days)
```

**Data source:** `GET /knowledge/memory?agent_id=&dept_id=`

---

### 2.4 MEMORY DETAILS

**Purpose:** Inspect a single memory entry in full detail.

Accessed by clicking a memory entry from the Memory Overview.

**Layout:**
- Full memory content (no truncation)
- Metadata panel: agent_id, mission_id, created_at, expires_at, chroma_id
- Source section: Link to the source mission's execution trace
- **Similarity Panel:** Shows the most recent queries that retrieved this memory and their cosine similarity scores:
  ```
  Query: "what keywords should we target this quarter" → score: 0.91
  Query: "SEO priorities for Q4" → score: 0.87
  Query: "keyword research competitor analysis" → score: 0.83
  ```
  This tells the user "this memory is being found by relevant queries — it's working."
- Delete button → `DELETE /knowledge/memory/{id}`

---

### 2.5 MEMORY SETTINGS

**Purpose:** Configure how memory works, per agent or globally.

**Global settings (top section):**
- **Memory Enabled (global toggle):** Master switch. Turns off all memory extraction and retrieval system-wide. Warning: disabling means no agent will learn from past runs. Default: ON.
- **Default TTL:** Dropdown: 30 / 60 / 90 / 180 / 365 days. Applied to all new memory entries unless overridden per agent. Default: 90 days.
- **Max Global Memory Entries:** If total entries across all agents exceeds this limit, oldest entries are deleted first. Default: 10,000. (Prevents ChromaDB from growing unbounded.)
- **Memory Extraction Model:** Which LLM to use for the memory extraction step. Default: same as user's primary model. Cheaper models (e.g., llama-3.1-8b-instant) work well here since it's a simple extraction task.

**Per-Agent settings (expandable list of agents):**
Each agent row shows:
- Agent name + department
- Memory enabled toggle (overrides global)
- TTL override (or "Use global")
- Max entries for this agent
- Current entry count
- "Clear Memory" button → `DELETE /knowledge/memory/agent/{id}` with confirmation dialog

**Bulk actions:**
- "Clear All Memory" → wipes entire memory store for all agents. Requires typing "CLEAR ALL" to confirm.
- "Export Memory" → downloads all memory entries as JSON (for backup)
- "Purge Expired" → manually runs the expiry cleanup (normally runs automatically on schedule)

**Data source:** `PUT /knowledge/memory/settings`

---

## 3. HOW THE DOCUMENT PIPELINE WORKS

This is the full end-to-end flow from user uploading a file to an agent using it.

### Step-by-Step Pipeline

```
1. USER UPLOADS FILE
   POST /knowledge/documents (multipart/form-data)
   Body: file binary, department_id (optional)
   
2. BACKEND — SAVE FILE
   - Generate unique ID (UUID)
   - Save file to disk: /data/documents/{user_id}/{doc_id}.{ext}
   - Or: upload to S3 bucket (production)
   - Insert document record in SQLite: {id, name, type, file_path, size_bytes, status='processing', ...}
   - Return document_id to frontend (frontend shows processing state)

3. BACKEND — PARSE CONTENT (async background task)
   Run in background using FastAPI BackgroundTasks:
   
   if type == 'pdf':
       from pdfminer.high_level import extract_text
       text = extract_text(file_path)
       
   elif type == 'docx':
       import docx2txt
       text = docx2txt.process(file_path)
       
   elif type == 'txt':
       text = open(file_path).read()
       
   elif type == 'csv':
       import pandas as pd
       df = pd.read_csv(file_path)
       # Each row: "Column1: value | Column2: value | ..."
       text = "\n".join(df.apply(lambda row: " | ".join(f"{k}: {v}" for k,v in row.items()), axis=1))
       
   elif type == 'url':
       import requests
       from bs4 import BeautifulSoup
       html = requests.get(url).text
       soup = BeautifulSoup(html, 'html.parser')
       # Remove nav, footer, script, style
       for tag in soup(['nav', 'footer', 'script', 'style', 'header']):
           tag.decompose()
       text = soup.get_text(separator="\n", strip=True)

4. BACKEND — CHUNK TEXT
   Using a sliding window approach:
   
   chunk_size = 500     # tokens
   overlap = 50         # tokens
   
   # Tokenize (approximate: 1 token ≈ 4 chars)
   # Split at paragraph boundaries first, then by size if needed
   chunks = text_splitter.split(text, chunk_size=chunk_size, overlap=overlap)
   # chunks = ["paragraph 1 text...", "paragraph 1 tail... paragraph 2 text...", ...]
   
   # Each chunk also gets metadata:
   chunk_metadata = {
       "doc_id": document.id,
       "doc_name": document.name,
       "doc_type": document.type,
       "department_id": document.department_id,
       "chunk_index": i,
       "user_id": user_id
   }

5. BACKEND — EMBED CHUNKS
   Using sentence-transformers (local, no API key needed):
   
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
   embeddings = model.encode(chunks)  # returns numpy array of shape (n_chunks, 384)
   
   Or, if user has OpenAI key set:
   # Use text-embedding-3-small for better quality
   embeddings = openai_client.embeddings.create(input=chunks, model='text-embedding-3-small')

6. BACKEND — STORE IN CHROMADB
   collection_name = f"user_{user_id}"
   # Or: f"dept_{department_id}" if department-scoped
   
   collection = chroma_client.get_or_create_collection(collection_name)
   collection.add(
       documents=chunks,           # raw text
       embeddings=embeddings,       # vectors
       metadatas=chunk_metadata_list,  # metadata for filtering
       ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
   )

7. BACKEND — UPDATE STATUS
   db.update_document(doc_id, {
       status: 'active',
       chunks_count: len(chunks),
       chroma_collection_id: collection_name
   })
   
   # Optionally: emit WebSocket event to notify frontend
   emit('document_ready', {doc_id, name, chunks_count})
```

### How document_rag Uses This Data

```python
async def document_rag(query: str, collection: str = None, user_id: str = None, top_k: int = 5):
    # Embed the query
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([query])
    
    # Determine which collection to search
    if collection:
        collection_name = collection
    elif mission.department_id:
        collection_name = f"dept_{mission.department_id}"
    else:
        collection_name = f"user_{user_id}"
    
    # Search ChromaDB
    chroma_collection = chroma_client.get_collection(collection_name)
    results = chroma_collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=['documents', 'metadatas', 'distances']
    )
    
    # Format results
    passages = []
    for i, doc in enumerate(results['documents'][0]):
        passages.append({
            "content": doc,
            "source": results['metadatas'][0][i]['doc_name'],
            "score": 1 - results['distances'][0][i],  # convert distance to similarity
            "chunk_index": results['metadatas'][0][i]['chunk_index']
        })
    
    return passages
```

The top 5 passages are then formatted and injected into the agent's LLM prompt:
```
Relevant documents found:
[Source: Q4_Strategy.pdf, Score: 0.92]
"Our Q4 ICP is mid-market SaaS companies with 50-200 employees experiencing rapid growth..."

[Source: ICP_Definition.docx, Score: 0.87]
"Target segment characteristics: ARR between $1M-$10M, technical founding team..."
```

---

## 4. HOW MEMORY WORKS

Memory is automatic. The Executor handles it transparently around every task.

### Memory Retrieval (Before Task)

```python
async def retrieve_memory(agent_id: str, task_description: str, top_k: int = 5) -> list[str]:
    if not agent.memory_enabled:
        return []
    
    # Embed the task description
    query_embedding = embedding_model.encode([task_description])
    
    # Search the memory collection for this agent
    memory_collection = chroma_client.get_collection(f"memory_{agent_id}")
    
    # Filter by expiry: only retrieve memories that haven't expired
    results = memory_collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"expires_at": {"$gt": datetime.utcnow().isoformat()}}
    )
    
    return [doc for doc in results['documents'][0]]
```

When memories are retrieved, they are prepended to the agent's system prompt:

```
[ORIGINAL SYSTEM PROMPT]
You are a senior content strategist...

[MEMORY INJECTION — added by Executor]
What you remember from past work:
- For Q4 campaigns targeting enterprise, LinkedIn ads had 2.3x better CTR than Google Ads
- The phrase "scale without complexity" resonated strongly with mid-market SaaS buyers in Sept emails
- Content about integration capabilities drove 40% more demo requests than feature-focused content

[TASK]
Write a Q4 campaign brief for the enterprise segment.
```

The agent now has context it built itself from its own past experience — not from training data, but from its actual work history in this Orion workspace.

### Memory Extraction (After Task)

```python
async def extract_and_store_memory(agent_id: str, mission_id: str, task_result: str, agent: Agent):
    if not agent.memory_enabled:
        return
    
    # Ask LLM to extract key facts worth remembering
    extraction_prompt = f"""
    Review this completed task and extract facts that would be useful to remember for future tasks.
    Focus on: specific data points, what worked/didn't work, discovered patterns, key decisions made.
    Ignore: generic advice, task instructions, boilerplate text.
    Return as a JSON array of strings. Maximum 5 items. Each item should be one clear fact.
    
    Task result:
    {task_result[:3000]}  # truncate to avoid token overflow
    
    Return only JSON: ["fact 1", "fact 2", ...]
    """
    
    extracted = await llm.complete(extraction_prompt)
    facts = json.loads(extracted)  # ["Q4 target is 30% growth...", "LinkedIn outperformed...", ...]
    
    for fact in facts:
        # Embed the fact
        embedding = embedding_model.encode([fact])
        
        # Store in ChromaDB memory collection
        memory_id = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(days=agent.memory_ttl_days)
        
        memory_collection.add(
            documents=[fact],
            embeddings=embedding,
            metadatas=[{
                "agent_id": agent_id,
                "mission_id": mission_id,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat()
            }],
            ids=[memory_id]
        )
        
        # Also record in SQLite for the UI (Memory Overview)
        db.insert_memory_entry({
            id: memory_id,
            agent_id: agent_id,
            content: fact,
            chroma_id: memory_id,
            source_mission_id: mission_id,
            created_at: datetime.utcnow(),
            expires_at: expires_at
        })
```

### Memory Expiry

TTL-based expiry. Two mechanisms:
1. **Query-time filtering:** The ChromaDB query includes `where: {expires_at: {$gt: now}}` — expired memories are simply not returned even if they exist.
2. **Background cleanup job:** A scheduled task (cron or APScheduler) runs daily and deletes entries where `expires_at < now` from both ChromaDB and the SQLite memory_entries table.

### Why Episodic Memory Matters

Without memory, every agent run starts from zero. The agent does not remember what it learned last week. With memory, agents compound their effectiveness over time — each run teaches them something new that makes future runs better.

This is the mechanism that makes Orion more valuable the longer it is used.

---

## 5. DATABASE TABLES

### documents table (SQLite)

```sql
CREATE TABLE documents (
    id                   TEXT PRIMARY KEY,     -- UUID
    name                 TEXT NOT NULL,         -- original file name or URL title
    type                 TEXT NOT NULL,         -- pdf|docx|txt|csv|xlsx|url
    file_path            TEXT,                  -- local path or S3 URI
    source_url           TEXT,                  -- original URL (for type=url)
    size_bytes           INTEGER,
    chunks_count         INTEGER DEFAULT 0,     -- populated after processing
    status               TEXT NOT NULL DEFAULT 'processing', -- processing|active|error|review
    department_id        TEXT,                  -- FK → departments.id (nullable = all depts)
    chroma_collection_id TEXT NOT NULL,         -- which ChromaDB collection was used
    processing_error     TEXT,                  -- error message if status='error'
    uploaded_by          TEXT NOT NULL,         -- FK → users._id (MongoDB)
    uploaded_at          TEXT NOT NULL          -- ISO 8601
);

CREATE INDEX idx_documents_dept ON documents(department_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
```

### memory_entries table (SQLite)

```sql
CREATE TABLE memory_entries (
    id               TEXT PRIMARY KEY,   -- UUID (same as ChromaDB ID for this entry)
    agent_id         TEXT NOT NULL,       -- FK → agents.id
    department_id    TEXT,               -- denormalized from agent for easy filtering
    content          TEXT NOT NULL,       -- the fact/memory text
    chroma_id        TEXT NOT NULL,       -- ChromaDB document ID (for deletion)
    source_mission_id TEXT NOT NULL,      -- FK → missions.id (which run created this)
    created_at       TEXT NOT NULL,
    expires_at       TEXT NOT NULL        -- ISO 8601, computed from created_at + memory_ttl_days
);

CREATE INDEX idx_memory_agent ON memory_entries(agent_id);
CREATE INDEX idx_memory_expires ON memory_entries(expires_at);
CREATE INDEX idx_memory_dept ON memory_entries(department_id);
```

---

## 6. API ENDPOINTS

All endpoints require Authorization header (JWT).

```
POST /knowledge/documents
```
Upload a document. Content-Type: multipart/form-data. Form fields: `file` (binary), `department_id` (optional), `chunk_size` (optional, default 500), `chunk_overlap` (optional, default 50). Returns: `{document_id, status: 'processing'}` immediately. Processing runs async in background.

```
POST /knowledge/documents/url
```
Ingest from URL. Body: `{url, department_id?, name?}`. Returns: `{document_id, status: 'processing'}`. Processing (fetch + parse + chunk + embed) runs async.

```
GET /knowledge/documents
```
List all documents. Query params: `?dept_id=`, `?type=`, `?status=`, `?search=`. Returns: array of document objects with all fields.

```
GET /knowledge/documents/{id}
```
Document detail. Returns: full document object. For Chunk Inspector: also returns `chunks` array (fetched from ChromaDB collection).

```
DELETE /knowledge/documents/{id}
```
Delete document. Side effects:
1. Deletes file from disk/S3
2. Removes all chunks from ChromaDB: `collection.delete(where={"doc_id": id})`
3. Deletes document record from SQLite
Returns: `{deleted: true, chunks_removed: 87}`.

```
POST /knowledge/documents/{id}/reindex
```
Re-process a document (useful if document was updated or embedding model changed). Re-runs the full parse → chunk → embed → store pipeline. Replaces existing chunks in ChromaDB. Returns: `{status: 'reprocessing'}`.

```
POST /knowledge/search
```
Search across documents directly (for testing, not for agent use). Body:
```json
{
  "query": "what is our Q4 target revenue",
  "collection": "user_uuid",  // optional
  "dept_id": "dept_uuid",     // optional, filters by dept collection
  "limit": 5
}
```
Returns: array of passages with content, source, score. This is the same call `document_rag` makes internally — useful for testing what chunks would be returned before running a real agent.

```
GET /knowledge/memory
```
List memory entries. Query params: `?agent_id=`, `?dept_id=`, `?expired=false` (default excludes expired). Returns: array of memory_entry objects.

```
DELETE /knowledge/memory/{id}
```
Delete a single memory entry. Side effects: removes from ChromaDB + SQLite. Returns: `{deleted: true}`.

```
DELETE /knowledge/memory/agent/{agent_id}
```
Clear ALL memory for a specific agent. Side effects: removes all ChromaDB entries for this agent + all SQLite records. Requires confirmation token in body: `{confirm: "CLEAR"}`. Returns: `{deleted: true, entries_removed: 142}`.

```
PUT /knowledge/memory/settings
```
Update memory configuration. Body:
```json
{
  "global_enabled": true,
  "default_ttl_days": 90,
  "max_global_entries": 10000,
  "per_agent": {
    "agent_id_1": {"enabled": true, "ttl_days": 30, "max_entries": 200},
    "agent_id_2": {"enabled": false}
  }
}
```
Returns: updated settings object. Settings stored in MongoDB user document under `settings.memory`.

---

## 7. HOW KNOWLEDGE CONNECTS TO EVERY OTHER PLAN

**→ Tools (Plan 06) — Primary Connection**
`document_rag` is the interface. The Knowledge plan builds the data (uploads documents → stores in ChromaDB). The Tools plan provides the mechanism agents use to access that data (document_rag tool). These two plans are the two halves of the same feature. Without the Knowledge pipeline, document_rag queries return empty results. Without the document_rag tool, uploaded documents are never used by agents.

**→ Mission Engine (Plan 04)**
The Executor runs two memory hooks around every task:
- **Pre-task hook:** `await retrieve_memory(agent_id, task_description)` → result prepended to prompt
- **Post-task hook:** `await extract_and_store_memory(agent_id, mission_id, task_result, agent)` → facts stored

These hooks run transparently. The Mission Engine plan does not need to know about ChromaDB or embeddings — it just calls these two functions from the Knowledge service.

**→ Agents (Plan 05)**
Two agent fields control memory behavior:
- `agent.memory_enabled` — if False, both memory hooks are skipped for that agent
- `agent.memory_ttl_days` — used in `extract_and_store_memory` to set `expires_at`

The Memory Settings page in the Knowledge section is the UI for configuring these per-agent settings.

**→ Departments (Plan 08)**
Documents can be scoped to a department by setting `document.department_id`. When scoped, they are stored in a department-specific ChromaDB collection: `f"dept_{dept_id}"`. The `document_rag` tool automatically searches the department collection when the executing mission has a `department_id` set. This means Marketing agents naturally find marketing documents, and Finance agents find finance documents, without manual configuration.

**→ Operations (future Plan)**
Mission outputs (the final reports, analyses, documents agents produce) should optionally be saved as Knowledge documents. This creates a feedback loop: agents produce output → output becomes new knowledge → future agents find that output in document_rag searches. Example: Agent generates Q3 Analysis Report → auto-saved to Knowledge → future agent preparing Q4 strategy searches Knowledge and finds Q3 Analysis Report.

**→ Command Center (Plan 03)**
File attachment in the Command Center composer. When a user drags a file into the chat before submitting a mission, the file is:
1. Uploaded to Knowledge: `POST /knowledge/documents` with a temporary scope
2. The resulting document_id is attached to the mission
3. When the mission's agents call `document_rag`, the query includes a filter for this document_id, ensuring the attached file is searched

This is how "attach a file to your question" works in the Command Center.

**→ Observability (future Plan)**
Every `document_rag` call is traced in `execution_traces`:
```json
{
  "event_type": "tool_call",
  "tool_name": "document_rag",
  "input": {"query": "Q4 target revenue"},
  "output": "[3 passages returned]",
  "latency_ms": 145,
  "chunks_returned": 3,
  "top_score": 0.91
}
```
The Document Detail view's Usage tab reads these traces (filtered by `tool_name=document_rag` AND metadata matching `doc_id`).

---

## 8. BUILD ORDER

**Phase 4 — After Agents (Phase 2) and Departments (Phase 3) are built**

The dependency is: document_rag tool was seeded in Phase 1 (Tools), but ChromaDB was empty. Phase 4 builds the upload pipeline that fills ChromaDB.

```
Step 1: Database setup
  - Create documents table (SQLite migration)
  - Create memory_entries table (SQLite migration)
  - Initialize ChromaDB client and default collections
  - Verify ChromaDB is running and accessible

Step 2: Document parsing infrastructure
  - Install: pdfminer.six, docx2txt, beautifulsoup4, requests, pandas, openpyxl
  - Implement parse_document(file_path, type) → returns plain text string
  - Implement parse_url(url) → requests + BeautifulSoup → returns text
  - Unit test: verify each parser produces clean text output

Step 3: Chunking + Embedding pipeline
  - Implement text_splitter(text, chunk_size=500, overlap=50) → returns list of chunk strings
  - Install: sentence-transformers
  - Implement embed_chunks(chunks) → returns list of embedding vectors
  - Implement store_chunks_in_chroma(chunks, embeddings, metadatas, collection) → ChromaDB add
  - Integration test: upload a small PDF, verify chunks appear in ChromaDB

Step 4: POST /knowledge/documents endpoint
  - Accept multipart file upload
  - Save to disk
  - Insert 'processing' record in SQLite
  - Kick off background task: parse → chunk → embed → store
  - Return {document_id, status: 'processing'}
  - Wire status updates (polling GET /knowledge/documents/{id} or WebSocket event)

Step 5: Wire Upload Sources view
  - Drag-and-drop upload zone (react-dropzone)
  - Progress bars per file
  - Processing status stages display
  - POST /knowledge/documents/url for URL ingestion

Step 6: GET /knowledge/documents → Wire Knowledge Base view
  - Document table with all columns
  - Search and filter
  - DocumentViewer: Preview tab (text render), Chunk Inspector tab

Step 7: Memory hooks in Mission Engine Executor
  - Implement retrieve_memory(agent_id, task_description)
  - Implement extract_and_store_memory(agent_id, mission_id, task_result, agent)
  - Wire both into task_executor.py before/after LLM call
  - Test: run a mission with an agent that has memory_enabled=true → verify memory entries created
  - Test: run second mission → verify memories appear in prompt

Step 8: GET /knowledge/memory → Wire Memory Overview
  - Memory entries table with all columns
  - Filters by agent and department
  - Memory Details drill-down view

Step 9: Memory Settings endpoint + view
  - PUT /knowledge/memory/settings
  - Memory Settings UI: global toggle, default TTL, per-agent overrides
  - DELETE /knowledge/memory/agent/{id} (clear all for one agent)
  - Background cleanup job for expired entries (APScheduler or cron)
```

**What is NOT in Phase 4:**
- OAuth sources (Notion, Google Drive) — separate phase
- Full-text search on raw document content (uses ChromaDB vector search only)
- Document version tracking (if you upload v2 of a doc, v1 is replaced)
- Fine-tuning or long-term model training from knowledge — not planned

---

*End of 07_KNOWLEDGE_PLAN.md*
