# ORION — HOW THE WHOLE SYSTEM WORKS AS ONE THING

---

## Read this first. One picture.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   USER SIGNS UP                                                             │
│       │                                                                     │
│       ▼                                                                     │
│   SETS UP THEIR WORKSPACE                                                   │
│   ├── Creates Agents      (who will do the work)                            │
│   ├── Connects Tools      (what agents can use)                             │
│   ├── Creates Departments (how agents are organized)                        │
│   └── Uploads Documents   (what agents can reference)                      │
│       │                                                                     │
│       ▼                                                                     │
│   GIVES A GOAL                                                              │
│   "Analyze my 5 competitors and suggest a pricing strategy"                │
│       │                                                                     │
│       ▼                                                                     │
│   SYSTEM BREAKS IT INTO TASKS                                               │
│   ├── Task 1: Find competitors        → Research Agent → Web Search tool   │
│   ├── Task 2: Get their pricing       → Research Agent → Web Search tool   │
│   ├── Task 3: Analyze pricing data    → Analysis Agent → Doc RAG tool      │
│   └── Task 4: Write strategy report  → Strategy Agent → no tool needed    │
│       │                                                                     │
│       ▼                                                                     │
│   AGENTS RUN (streamed live to the screen)                                  │
│   ├── Research Agent calls Web Search  →  gets real data                   │
│   ├── Analysis Agent reads results     →  finds patterns                   │
│   └── Strategy Agent writes report    →  final output                      │
│       │                                                                     │
│       ├── IF agent wants to take action (spend money, post externally)      │
│       │       └── APPROVAL GATE → user approves/rejects → agent continues  │
│       │                                                                     │
│       ▼                                                                     │
│   RESULT                                                                    │
│   ├── Saved as a Mission (findable later)                                  │
│   ├── Output stored in Knowledge Base (agents remember it)                 │
│   ├── Full trace logged (every step, every token, every cost)              │
│   └── Department Activity updated (if mission was under a dept)            │
│       │                                                                     │
│       ▼                                                                     │
│   USER COMES BACK NEXT TIME                                                 │
│   ├── Agents remember previous missions (Memory)                           │
│   ├── Knowledge Base has documents from past runs                          │
│   └── System gets better because agents learn what worked                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Now here is how EVERY part of the sidebar contributes to that flow above.

Each section has ONE JOB in the system. Not features. ONE JOB.

```
SIDEBAR SECTION        ONE JOB IN THE SYSTEM
──────────────────────────────────────────────────────────────────────────────

COMMAND CENTER    →    WHERE THE GOAL IS GIVEN AND THE WORK HAPPENS LIVE
                       This is the entry point. Every mission starts here.
                       Nothing else in the system matters without this.

MISSIONS          →    WHERE COMPLETED/RUNNING GOALS ARE STORED AND FOUND
                       After Command Center runs a mission, Missions keeps it.
                       User comes back days later → finds results here.

APPROVALS         →    WHERE THE SYSTEM PAUSES AND WAITS FOR HUMAN DECISION
                       When an agent tries to do something irreversible or
                       expensive, it stops here. User says yes or no.
                       Without this, agents could do dangerous things freely.

NOTIFICATIONS     →    WHERE THE SYSTEM TELLS THE USER SOMETHING HAPPENED
                       "Your mission completed." "Approval needed."
                       "Agent failed." Connects all other sections to the user.

DEPARTMENTS       →    WHERE AGENTS ARE ORGANIZED INTO TEAMS
                       Instead of loose agents, they belong to teams.
                       Marketing dept → all marketing missions go to its agents.
                       Finance dept → all finance missions go to its agents.
                       Creates order. Without departments, it is just a pile of agents.

AGENTS            →    WHERE THE WORKERS THEMSELVES ARE CONFIGURED
                       This is the most important setup section.
                       A mission with bad agents = bad results.
                       A mission with well-configured agents = great results.
                       Everything the agent knows, can do, and is allowed to do
                       is configured here. This feeds directly into the mission engine.

KNOWLEDGE         →    WHERE AGENTS GET THEIR LONG-TERM MEMORY AND CONTEXT
                       Uploaded documents = agents know YOUR specific business.
                       Memory entries = agents remember what worked before.
                       Without knowledge, agents only know generic LLM training data.
                       With knowledge, agents know your company, your market, your data.

TOOLS             →    WHERE AGENTS GET THEIR CAPABILITIES TO ACT IN THE WORLD
                       An agent without tools = just an LLM that generates text.
                       An agent with web_search = it can find real current information.
                       An agent with maps_api = it can find real businesses near you.
                       An agent with Notion = it can write to your actual workspace.
                       Tools are what make the system REAL instead of just a chatbot.

OPERATIONS        →    WHERE THE RESULTS OF EVERYTHING ACCUMULATE
                       Every mission agents complete produces data.
                       Finance missions → Finance tab fills with real numbers.
                       Marketing missions → Marketing tab fills with campaign data.
                       Operations is the OUTCOME section. You see the real-world
                       impact of all the missions your agents have run.

OBSERVABILITY     →    WHERE YOU SEE EXACTLY WHAT THE SYSTEM IS DOING INTERNALLY
                       Every LLM call, every tool call, every token, every error.
                       This is the X-ray of the system.
                       Without this, if something goes wrong you have no idea why.
                       With this, you see exactly which step failed and how to fix it.

SETTINGS          →    WHERE YOU CONFIGURE WHO YOU ARE AND HOW THE SYSTEM RUNS
                       Your identity (profile), your API keys (what LLMs/tools to use),
                       your security preferences. Foundation-level config.
                       This affects everything because your API keys determine
                       which LLM providers are available to your agents.
```

---

## Now read it as a story. One user, one day.

```
MORNING — User sets up the system (AGENTS + TOOLS + DEPARTMENTS + KNOWLEDGE)

  User goes to AGENTS → creates "Research Agent"
    - gives it instructions: "You research markets and competitors"
    - connects it to: web_search tool, document_rag tool
    - assigns it to: Research Department

  User goes to AGENTS → creates "Marketing Agent"
    - gives it instructions: "You create marketing strategies and campaigns"
    - connects it to: web_search tool, document_rag tool
    - assigns it to: Marketing Department

  User goes to KNOWLEDGE → uploads their business plan PDF
    - System chunks it, embeds it, stores in ChromaDB
    - Now agents can search this document during missions

  User goes to TOOLS → connects their Serper API key
    - web_search tool is now live with real search capability

  User goes to SETTINGS → stores their Groq API key
    - Agents will now use Groq (fast, free tier) for LLM calls


MIDDAY — User gives a goal (COMMAND CENTER)

  User types: "Create a marketing strategy for Q4"

  STEP 1: System calls Planner LLM
    → Returns: [
        { task: "Research current market trends", agent_type: "research" },
        { task: "Analyze competitor campaigns",   agent_type: "research" },
        { task: "Create marketing strategy",      agent_type: "marketing" },
        { task: "Write campaign brief",           agent_type: "marketing" }
      ]

  STEP 2: Task Router assigns agents
    → Task 1, 2 → Research Agent (found in agents DB, type=research)
    → Task 3, 4 → Marketing Agent (found in agents DB, type=marketing)

  STEP 3: Research Agent runs tasks 1 and 2 in parallel
    → calls web_search("Q4 marketing trends 2026")   [TOOL CALL]
    → calls web_search("competitor Q4 campaigns")     [TOOL CALL]
    → calls document_rag("our business plan goals")   [TOOL CALL → searches PDF user uploaded]
    → writes: market_trends.json, competitor_analysis.json

  STEP 4: Marketing Agent runs tasks 3 and 4
    → reads market_trends.json and competitor_analysis.json (context from previous tasks)
    → writes strategy and campaign brief as outputs

  STEP 5: Agent wants to post strategy to Slack
    → APPROVAL triggered (agent cannot send external messages without approval)
    → Mission pauses → notification goes to APPROVALS section

  User sees in APPROVALS:
    "Marketing Agent wants to post Q4 strategy to #marketing Slack channel"
    User clicks Approve → agent continues → posts to Slack

  Mission completes.


AFTERNOON — User reviews results (MISSIONS + OBSERVABILITY + OPERATIONS)

  User goes to MISSIONS
    → sees "Q4 Marketing Strategy" — Completed
    → clicks it → sees full execution graph: which agents ran, in what order
    → reads the strategy and campaign brief that were produced

  User goes to OBSERVABILITY
    → sees this mission used 4 LLM calls, 3 tool calls, 1847 tokens total, cost $0.02
    → one tool call took 4.2 seconds (Serper was slow)
    → no errors

  User goes to OPERATIONS → Marketing tab
    → the Q4 strategy is now logged here as a completed marketing output
    → over time, as more marketing missions run, this tab fills up with real data

  User notices their Research Agent took 3.2 seconds average
  User goes to AGENTS → Research Agent → Performance
    → sees success rate 94%, avg latency 3.1s, top tool used: web_search
    → decides to update the system prompt to make it faster


NEXT WEEK — System remembers (KNOWLEDGE + MEMORY)

  User runs a new mission: "Update our marketing strategy based on new competitor moves"

  Research Agent now:
    → searches ChromaDB → finds the Q4 strategy from last week (stored in knowledge)
    → finds memory entries from previous research runs
    → its output is MORE RELEVANT because it knows the context

  The system got smarter just by being used.
```

---

## The system in one diagram

```
                     ┌─────────────┐
                     │   SETTINGS  │  ← user identity + API keys
                     │  (foundation)│    (affects every LLM call)
                     └──────┬──────┘
                            │ provides API keys to
                            ▼
┌──────────┐    setup   ┌──────────────────────────────────────────┐
│  AGENTS  │ ─────────► │                                          │
│(who does │            │            MISSION ENGINE                │
│the work) │            │                                          │
└──────────┘            │  1. User gives goal (COMMAND CENTER)     │
                        │  2. Planner breaks into tasks            │
┌──────────┐    setup   │  3. Router assigns tasks to agents       │
│  TOOLS   │ ─────────► │  4. Agents run + call tools              │
│(what they│            │  5. Results produced                     │
│can use)  │            │                                          │
└──────────┘            └──────────────────┬───────────────────────┘
                                           │
┌──────────┐    setup                      │ outputs go to
│KNOWLEDGE │ ─────────►────────────────────┤
│(what they│  agents search during runs    │
│know)     │                               ▼
└──────────┘               ┌──────────────────────────────────────┐
                           │           RESULTS LAYER              │
┌──────────┐    organizes  │                                      │
│DEPARTMENTS│ ────────────►│  MISSIONS      → find past work      │
│(team     │  missions     │  OPERATIONS    → business outcomes   │
│structure)│  by dept      │  KNOWLEDGE     → docs from missions  │
└──────────┘               └──────────────────┬───────────────────┘
                                              │
                           ┌──────────────────┼───────────────────┐
                           │                  │                   │
                           ▼                  ▼                   ▼
                     ┌──────────┐      ┌──────────┐      ┌──────────────┐
                     │APPROVALS │      │OBSERV-   │      │NOTIFICATIONS │
                     │          │      │ABILITY   │      │              │
                     │ safety   │      │          │      │ alerts user  │
                     │ gate for │      │ full     │      │ when things  │
                     │ actions  │      │ x-ray of │      │ happen       │
                     │ agents   │      │ system   │      │              │
                     │ want to  │      │ internals│      │              │
                     │ take     │      │          │      │              │
                     └──────────┘      └──────────┘      └──────────────┘

The three bottom boxes NEVER block the mission.
They run alongside it — safety, visibility, awareness.
```

---

## The single sentence for each section

If you remove ANY of these, here is what breaks:

| Remove this | What breaks |
|-------------|-------------|
| Command Center | Nothing starts. No goals. No missions. System is dead. |
| Missions | Users lose all their previous work. No history. No results. |
| Agents | Nothing runs. No workers. Goals produce nothing. |
| Tools | Agents only generate text. No real data. No real actions. |
| Knowledge | Agents are generic. They know nothing about YOUR business. |
| Departments | All agents are a pile. No structure. No ownership. |
| Approvals | Agents act freely. Dangerous. Uncontrolled. |
| Observability | System is a black box. Can't debug. Can't improve. |
| Operations | You see missions but never the accumulated business impact. |
| Notifications | User has to constantly check every section manually. |
| Settings | No API keys. No LLM. Nothing works. |

**Nothing is optional. Every section has a specific job in the flow.**
**The question is not "is it needed" — it is "what order do you build it."**

---

## The build order based on what blocks what

```
MUST EXIST BEFORE ANYTHING ELSE:
  Auth (done) + Settings (API keys) + Tools (web_search at minimum)

MUST EXIST FOR THE SYSTEM TO DO ANYTHING:
  Command Center + Mission Engine + Agents (defaults)

MUST EXIST FOR THE SYSTEM TO BE USEFUL:
  Missions (history) + Knowledge (memory) + Approvals (safety)

MUST EXIST FOR THE SYSTEM TO BE ORGANIZED:
  Departments

MUST EXIST FOR THE SYSTEM TO BE TRUSTWORTHY:
  Observability

MUST EXIST FOR THE SYSTEM TO FEEL ALIVE:
  Operations + Notifications
```

Build in that order. Each layer is only possible because the layer above it exists.
