# Orion: AI Business Operating System
## Multi-Agent Autonomous Business Generation and Operating Platform

Submitted in partial fulfilment of the requirements of the degree of
**BACHELOR OF COMPUTER ENGINEERING**

by

Aditya Maskare – 102
Vinayak Maurya – 103
Abhishek Mishra – 108
Aryan Maskare – 105

**Guide:**
Prof. Deepak Khachane

**Department of Computer Engineering**
P. SHAH INSTITUTE OF TECHNOLOGY, THANE
2026-2027

---

## CERTIFICATE

This is to certify that the project entitled "Orion: AI Business Operating System" is a bonafide work of "Aditya Maskare (102), Vinayak Maurya (103), Abhishek Mishra (108), Aryan Maskare (105)" submitted to the University of Mumbai in partial fulfilment of the requirement for the award of the degree of Bachelor of Engineering in Computer Engineering.

__________________
Prof. Deepak Khachane
Guide

_______________ ___________________
Dr. Sachine Malave Dr. Uttam Kolekar
Head of Department Principal

---

## Project Report Approval for B.E.

This project report entitled "Orion: AI Business Operating System" by Aditya Maskare (102), Vinayak Maurya (103), Abhishek Mishra (108), Aryan Maskare (105) is approved for the degree of Bachelor of Engineering in Computer Engineering, 2026-27.

Examiner Name Signature
1.________________ _____________
2._________________ ________________

Date:
Place:

---

## Declaration

We declare that this written submission represents my ideas in my own words and where others' ideas or words have been included, we have adequately cited and referenced the original sources. We also declare that we have adhered to all principles of academic honesty and integrity and have not misrepresented or fabricated or falsified any idea/data/fact/source in our submission. We understand that any violation of the above will be cause for disciplinary action by the Institute and can also evoke penal action from the sources which have thus not been properly cited or from whom proper permission has not been taken when needed.

-----------------------------------------
Aditya Maskare – 102

-----------------------------------------
Vinayak Maurya – 103

-----------------------------------------
Abhishek Mishra – 108

-----------------------------------------
Aryan Maskare – 105

Date:

---

## Abstract

Starting a new business requires expertise across multiple domains including strategy, finance, branding, marketing, and operations. Existing solutions either provide generic templates requiring extensive manual customization, or charge substantial fees for professional consulting services. Orion addresses this gap through a two-layer AI Business Operating System that automates both business plan generation and ongoing company operation.

The **generation layer** transforms a single natural language prompt into a complete founding business plan using multiple specialised AI agents organised across five departments (Strategy, Finance, Branding, Marketing, Operations). A routing orchestrator dynamically activates relevant departments based on business type, while agents collaborate through an enforced append-only shared state. External grounding through real-world APIs ensures plans are location-aware and sector-appropriate rather than hallucinated.

The **operating layer** treats the generated plan as a company's opening state and runs it forward autonomously on department cadences. Multiple governance modules form a control structure that plans, gates, executes, records, and reflects without human intervention. An invariant that anchors are computed, never reported, prevents the Goodhart's Law failures common in AI systems optimizing against their own metrics.

The system is evaluated through a comprehensive test suite and quantitative metrics measuring plan completeness, financial accuracy, consistency, and routing efficiency. Preliminary results show the multi-agent system achieves higher plan completeness compared to baseline approaches, with significant efficiency improvements through dynamic routing while maintaining output quality. An ablation harness tests the operating layer's control claims through experimental comparisons.

All components are built using free tools and API tiers: LangGraph for orchestration, multiple LLM providers with automatic fallback, FastAPI for the backend, SQLite and ChromaDB for data storage, and React for the frontend. The system contributes to UN Sustainable Development Goals, particularly SDG 9 (Industry, Innovation and Infrastructure) by supporting accessible entrepreneurship and SDG 12 (Responsible Consumption and Production) by reducing resource-intensive manual planning processes.

**Keywords:** Multi-Agent Systems, Business Generation, AI Operations, LangGraph, FastAPI, React, Autonomous Systems, Business Intelligence, Sustainable Development Goals.

---

## CONTENTS

Introduction ............................................................ 1
Literature Survey ........................................................ 2
Limitations of Existing System ............................................ 3
Problem Statement, Objectives and Scope ................................... 4
Proposed System ........................................................... 5
System Architecture ....................................................... 6
Experimental Setup ......................................................... 7
Software Requirements ...................................................... 8
Hardware Requirements ...................................................... 9
Database Design ........................................................... 10
Project Plan ............................................................... 11
Expected Outcome ........................................................... 12
Project Cost Estimation .................................................... 13
References ................................................................. 14

---

## LIST OF FIGURES

1.1 System Architecture Overview ........................................... 6
1.2 Generation Layer Data Flow ............................................ 7
1.3 Operating Layer Control Structure ..................................... 8
1.4 Department Execution DAG ................................................ 9

---

## LIST OF TABLES

2.1 Technology Stack ....................................................... 8
3.1 Agent Distribution by Department .................................... 10
4.1 Evaluation Metrics ................................................... 12

---

## LIST OF GRAPHS

5.1 Plan Completeness Comparison .......................................... 13
5.2 Financial Accuracy Results ............................................ 14

---

## ABBREVIATIONS

| Abbreviation | Full Form |
|-------------|-----------|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| DAG | Directed Acyclic Graph |
| HTML | HyperText Markup Language |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| MAPE | Mean Absolute Percentage Error |
| PDF | Portable Document Format |
| RQ | Research Question |
| SDG | Sustainable Development Goal |
| SD | Standard Deviation |
| SQL | Structured Query Language |
| TAM | Total Addressable Market |
| UI | User Interface |

---

## CHAPTER 1
## INTRODUCTION

### 1.1 Introduction

Orion is an AI Business Operating System that automates both the generation of founding business plans and their ongoing operation. The system addresses the fundamental challenge that starting a business requires expertise across multiple domains—strategy, finance, branding, marketing, and operations—yet existing tools either provide static templates requiring extensive manual input or charge prohibitive fees for professional consulting.

The system operates in two layers. The generation layer accepts a natural language prompt and produces a structured business plan through AI agents organised across five departments. A routing orchestrator dynamically activates relevant departments, enabling parallel execution where dependencies allow. Agents write to an append-only shared state, ensuring no department overwrites another's output. The operating layer treats the generated plan as a company's opening state and runs it forward autonomously. Governance modules plan actions, execute decisions, record events, and reflect on performance while anchor metrics are computed from the ledger to prevent optimisation against proxies rather than true objectives.

### 1.2 Problem Statement and Motivation

Traditional business planning requires either engaging expensive consultants or spending dozens of hours manually filling forms across strategy, financial projection, branding, marketing, and operational planning. Generic templates lack personalization for location, budget, and sector specifics, while custom work remains inaccessible to most aspiring entrepreneurs due to cost and expertise barriers.

Existing AI solutions typically provide single-shot responses that may produce inconsistent outputs across runs, lack quantitative grounding in real-world data, and offer no mechanism for ongoing business operation beyond the initial plan. Orion addresses these challenges by decomposing business planning into specialised agents with narrow responsibilities, enforcing structural constraints that prevent cross-department interference, grounding generation in real-world data through external APIs, and providing an operating layer that continues to manage the business autonomously after the initial plan is generated.

### 1.3 Aim and Objectives

The primary aim is to develop a comprehensive AI Business Operating System that automates both business plan generation and ongoing operational management.

The key objectives are to design a multi-agent architecture with specialised agents across multiple departments, implement a routing orchestrator that dynamically activates relevant departments based on business type, enforce an append-only shared state contract that prevents cross-department interference, integrate external APIs for real-world data grounding, build an operating layer with governance modules for autonomous company operation, implement an anchor metric system computed from an append-only ledger, provide quantitative evaluation metrics measuring completeness, accuracy, consistency, and efficiency, and ensure free implementation using only free API tiers and open-source tools.

1. Design a multi-agent architecture with specialised agents across multiple departments and implement a routing orchestrator that dynamically activates relevant departments based on business type
2. Enforce an append-only shared state contract that prevents cross-department interference and integrate external APIs for real-world data grounding
3. Build an operating layer with governance modules for autonomous company operation and implement an anchor metric system computed from an append-only ledger
4. Provide quantitative evaluation metrics measuring completeness, accuracy, consistency, and efficiency and ensure free implementation using only free API tiers and open-source tools

### 1.4 Scope of the Project

1. **Complete Lifecycle**: The project scope encompasses the complete business planning lifecycle from initial prompt to autonomous operational management, covering both the generation of structured business plans and their ongoing autonomous execution through a governance-based control structure.

2. **Generation Layer**: The generation layer produces structured plans across five departments including strategy, finance, branding, marketing, and operations with real-world data grounding through external APIs, ensuring plans are location-aware and sector-appropriate rather than relying on hallucinated information.

3. **Operating Layer**: The operating layer implements governance mechanisms including constitutional constraints, governance workflows, monitoring, reflection, and autonomous decision-making that treat the generated plan as a company's opening state and run it forward on department cadences without human intervention.

4. **Evaluation**: The system is evaluated through a comprehensive test suite and quantitative metrics measuring plan completeness, financial accuracy, consistency, and routing efficiency, while an ablation harness tests the operating layer's control claims through experimental arms comparing different control topologies.

5. **Exclusions**: The scope excludes physical business implementation as Orion generates plans and manages simulated operations only, without executing real-world business actions such as hiring employees, purchasing inventory, processing payments, or interacting with actual customers.

### 1.5 Significance and Sustainable Development Goals

Orion democratises access to sophisticated business planning tools that were previously available only through expensive consulting, aligning with SDG 9: Industry, Innovation and Infrastructure by supporting reliable digital infrastructure for entrepreneurship. The system's emphasis on efficient resource utilization and automated processes aligns with SDG 12: Responsible Consumption and Production by reducing the manual effort and repetitive activities associated with traditional business planning.

The research contributions include empirical findings on multi-agent system variance compounding (multi-agent standard deviation is 4.9× that of single-LLM baselines), the importance of code-enforced constraints over prompt-based requests, and the structural prevention of Goodhart's Law through the anchor metric invariant. These findings advance understanding of reliable multi-agent AI systems beyond academic settings.

---

## CHAPTER 2
## LITERATURE SURVEY

*[External literature survey to be added by the user based on research papers on multi-agent systems, business process automation, and AI operations. This section typically surveys existing work in automated planning, multi-agent coordination, LLM-based systems, and business intelligence tools.]*

---

## CHAPTER 3
## LIMITATIONS OF EXISTING SYSTEM

Existing business planning and AI automation solutions exhibit several limitations that Orion addresses:

**Fragmented Workflows:** Business planning requires coordination across strategy, finance, branding, marketing, and operations domains. Existing tools treat these as separate workflows, requiring users to manually transfer data between systems and maintain consistency.

**Generic Templates:** Template-based solutions provide one-size-fits-all structures that lack personalization for specific locations, budgets, sectors, and market conditions. Customization requires substantial manual effort and domain expertise.

**Single-Shot Generation:** Most AI business planning tools provide one-time responses without mechanisms for ongoing refinement, iteration, or operational management. Plans cannot evolve based on new information or changing market conditions.

**Hallucination Risk:** LLM-based systems may generate business data (competitors, market sizes, trends) without real-world grounding, leading to plans based on inaccurate or non-existent information.

**Lack of Quantitative Evaluation:** Existing solutions rarely provide measurable metrics on plan quality, completeness, or accuracy, making it difficult to assess output reliability or compare different approaches.

**No Operational Continuity:** Even when initial plans are generated, there is no mechanism to operationalize the plan—running the business forward, monitoring performance, and making autonomous decisions based on changing conditions.

**Variance and Consistency Issues:** Single-LLM approaches may produce inconsistent outputs across multiple runs of identical prompts, making it difficult to rely on results for business planning.

**Goodhart's Law Vulnerability:** Systems that optimize against measured metrics without structural constraints risk agents gaming the metrics rather than achieving true objectives.

**Research Gap**

The research gap addressed by Orion is the integration of structured multi-agent business generation with autonomous operational management within a unified system. While existing work addresses individual components (business plan generation, multi-agent coordination, AI operations), no system combines generation-layer multi-agent planning with an operating-layer governance structure that continues to manage the business autonomously. Orion's specific contributions include the enforced append-only state contract, the anchor metric invariant preventing Goodhart's Law failures, and the comprehensive evaluation framework comparing multi-agent approaches against baselines.

---

## CHAPTER 4
## PROBLEM STATEMENT, OBJECTIVES AND SCOPE

### 4.1 Problem Statement

Starting a business requires expertise across multiple domains, yet existing solutions either provide generic templates requiring extensive manual input or charge prohibitive fees for professional consulting. AI-based solutions typically offer single-shot responses without ongoing operational management, may hallucinate business-critical data, and lack quantitative evaluation metrics. Orion addresses these challenges by providing a two-layer AI Business Operating System that generates comprehensive business plans through multi-agent collaboration and continues to operate the business autonomously through a governance-based control structure.

### 4.2 Objectives

**Multi-Agent Architecture:** To design and implement 21 specialised AI agents across five departments (Strategy, Finance, Branding, Marketing, Operations) that collaborate through a shared state to produce comprehensive business plans.

**Dynamic Routing:** To implement a routing orchestrator that determines which departments are relevant to a given business type and constructs an execution DAG that enables parallel execution where dependencies allow.

**State Contract Enforcement:** To enforce an append-only shared state contract where agents may write only to their own department sections, preventing cross-department interference while maintaining consistency.

**External Data Grounding:** To integrate real-world APIs (Google Places, Serper, OpenStreetMap) to ground business plans in actual location data, competitor information, and market intelligence rather than hallucinated facts.

**Operating Layer Governance:** To implement ten governance modules (ledger, anchors, constitution, governance, loops, monitors, scheduler, memory, reflection, departments) that enable autonomous company operation on department cadences.

**Anchor Metric Invariant:** To enforce that anchor metrics are computed from an append-only ledger and never directly reported by agents, preventing Goodhart's Law failures.

**Quantitative Evaluation:** To implement evaluation metrics measuring plan completeness, financial accuracy, consistency, and routing efficiency, with rigorous statistical testing comparing multi-agent approaches against baselines.

**Zero-Cost Implementation:** To build the entire system using 100% free tools and API tiers, ensuring accessibility without subscription costs.

### 4.3 Scope

The project scope encompasses the complete lifecycle from business plan generation to autonomous operational management. The generation layer produces structured plans across five departments with real-world data grounding. The operating layer implements governance mechanisms including constitutional constraints, governance workflows, monitoring, reflection, and autonomous decision-making.

The system is evaluated through a comprehensive test suite and quantitative metrics. An ablation harness tests the operating layer's control claims through experimental arms. The scope excludes physical business implementation—Orion generates plans and manages simulated operations, but does not execute real-world business actions such as hiring, purchasing, or customer interactions.

---

## CHAPTER 5
## PROPOSED SYSTEM

### DESCRIPTION OF PROPOSED SYSTEM

Orion is an AI Business Operating System designed to automate both business plan generation and ongoing operational management for new ventures. The system provides a structured multi-agent architecture that transforms a single natural language prompt into comprehensive business plans through specialized AI agents organized across five departments. It aims to democratize access to sophisticated business planning tools while reducing the manual effort and expertise barriers traditionally required. The platform complements existing consulting services by providing accessible, AI-powered planning and autonomous operational management without prohibitive costs.

The proposed system consists of the following key components:

**Intent Classification and Prompt Processing:** Provides a structured process for accepting natural language prompts and extracting structured business intent including business type, location, sector, budget, and scale. This information helps the system understand the user's requirements and determine which business planning components are relevant.

**Multi-Agent Generation Architecture:** Organizes specialized AI agents across five departments including Strategy, Finance, Branding, Marketing, and Operations. Each department contains multiple agents that collaborate through a shared state to produce comprehensive business plans covering all aspects of starting and running a business.

**Dynamic Routing and Orchestration:** Determines which departments are relevant to a given business type and constructs an execution graph that enables parallel execution where dependencies allow. The routing system activates Strategy, Finance, Branding, and Marketing for all businesses while Operations activates conditionally for physical businesses.

**Shared State Management:** Maintains an append-only shared state where agents may write only to their own department sections, preventing cross-department interference while maintaining consistency across the plan. This contract ensures that no department can overwrite another's output.

**External Data Grounding:** Integrates real-world APIs to ground business plans in actual location data, competitor information, and market intelligence rather than relying on hallucinated information. The system uses external sources to provide location-aware and sector-appropriate planning.

**Output Generation and Reporting:** Produces structured business plans in multiple formats including JSON packages, HTML reports, and PDF exports. All outputs are styled according to the branding department's chosen visual identity and include comprehensive metadata about the generation process.

**Operating Layer Governance:** Implements governance mechanisms including constitutional constraints, governance workflows, monitoring, reflection, and autonomous decision-making that treat the generated plan as a company's opening state and run it forward on department cadences without human intervention.

**Anchor Metric System:** Computes performance metrics from an append-only ledger to prevent Goodhart's Law failures where agents might optimize against measured proxies rather than true objectives. The invariant ensures anchors are computed, never reported.

**Evaluation and Testing Framework:** Provides comprehensive testing and quantitative metrics measuring plan completeness, financial accuracy, consistency, and routing efficiency. An ablation harness tests the operating layer's control claims through experimental arms comparing different control topologies.

**User Interface and Workflow Management:** Connects the planning, generation, monitoring, and operational components through a unified interface. It enables users to input prompts, view generated plans, monitor autonomous operations, and access relevant information in a structured workflow.

Overall, Orion integrates business plan generation, autonomous operational management, and governance-based control into a single platform. By connecting these activities, the proposed system aims to simplify business planning, support systematic autonomous operation, and improve accessibility for aspiring entrepreneurs.

2. **Append-Only State:** Agents never overwrite other departments' data. The SharedBusinessState contract enforces this at the code level.

3. **Graceful Degradation:** Rate limits trigger automatic provider fallback (Groq → Gemini → Ollama). The system never fails due to API limits.

4. **Reproducibility:** Docker Compose provides a single command to run the entire system. Deterministic parsing ensures identical prompts produce identical intents.

5. **Modularity:** Each agent is independently testable. Departments are pluggable through the routing system.

6. **Research-First:** Every design decision maps to a measurable metric supporting a research question.

7. **Anchor Invariant:** Anchor metrics are computed from the ledger, never reported by agents. This is enforced structurally—there is no anchor table, column, or setter.

8. **Honest Reporting:** The system reports null results honestly rather than tuning experiments to produce significant findings. The ablation result at n=10 is reported as underpowered, not as a positive finding.

---

## CHAPTER 6
## EXPERIMENTAL SETUP

### 6.1 Software Requirements

**Backend Environment:**

- Python 3.13.2 (3.11+ required for StrEnum, datetime.UTC, asyncio.timeout)
- Virtual environment via .venv\Scripts\python.exe
- PYTHONPATH configured to include both backend and repository root
- Dependencies pinned in requirements.txt

**Frontend Environment:**

- Node.js for Vite build system
- React 18.3.1 and react-dom 18.3.1
- Vite 5.4.11 for development and production builds

**Development Tools:**

- Docker Compose 2.x for containerized deployment
- Git for version control
- PowerShell for Windows environment (note: no && operator, use ; for command chaining)

**Testing Framework:**

- pytest 8.3.4 with pytest-asyncio 0.25.0
- respx 0.22.0 for HTTP mocking (offline tests)
- mongomock for authentication testing (in-process, no network)

### 6.2 Hardware Requirements

**Minimum Specifications:**

- RAM: 8 GB minimum (16 GB recommended for evaluation runs)
- Storage: 5 GB free disk space
- Processor: Multi-core CPU for parallel agent execution
- Network: Internet connection required for external API calls (Groq, Gemini, Serper)

**Development Environment:**

- Local laptop or desktop machine
- No dedicated GPU required (LLM inference through external APIs or local Ollama)
- Optional: Docker Desktop for containerized deployment

### 6.3 Database Design

**SQLite Schema (Generation Layer):**

- `sessions`: Stores generation session metadata including prompt, intent, timestamps, and completion status
- `evaluation_results`: Stores metrics for evaluation runs including plan completeness, financial accuracy, consistency scores

**SQLite Schema (Operating Layer):**

- `ledger`: Append-only event log with columns for timestamp, department, actor, kind, amount, and metadata. Triggers abort UPDATE and DELETE operations.

- `constitution`: Stores constitutional constraints as code predicates

- `governance`: Records governance workflow states (decision, review, approval, execution, audit)

- `loops`: Loop registry with cadence configurations

- `memory`: Five isolated stores (episodic, semantic, procedural, working, reference) with scoped access patterns

**ChromaDB Collections:**

- `plans`: Stores generated business plan embeddings for retrieval and consistency
- `market_research`: Caches market intelligence to avoid redundant Serper API calls
- `competitors`: Caches competitor data from Google Places/OpenStreetMap

**MongoDB Atlas (Authentication Layer - Optional):**

- User accounts and authentication data (separate from agent data to maintain two-layer separation)

### 6.4 Evaluation Parameters

**Research Questions:**

- RQ1: Does a multi-agent pipeline produce measurably better business plans than a single-LLM baseline?
- RQ2: Does dynamic routing improve efficiency without degrading output quality?
- RQ3: How does multi-modal input (location + competitor data) affect plan accuracy vs text-only?

**Metrics:**

1. **Plan Completeness Score:** Sections present and substantive ÷ expected sections (26-field rubric)
2. **Financial Accuracy (MAPE):** Projected margins vs MSME industry benchmarks
3. **Consistency Score:** Alignment between Strategy TAM and Finance revenue projections
4. **Routing Efficiency:** Token and time savings with dynamic routing vs all-departments execution
5. **Competitor Coverage Rate:** Real nearby businesses found ÷ manual count (requires ground truth collection)

**Evaluation Arms:**

- `multi_agent`: Full system with 21 agents, dynamic routing, external grounding
- `baseline`: Single-LLM baseline (gemini-3.6-flash, single provider, no routing)
- `all_departments`: Multi-agent with all departments always active (RQ2 control)
- `no_grounding`: Multi-agent without external API calls (RQ3 control)

**Sample Size:**

- 35 diverse prompts across 8 sectors, including 8 digital businesses
- Current evaluation runs at n=5 for initial validation
- Full paper evaluation requires n=30+ for statistical significance

**Statistical Testing:**

- Paired Wilcoxon signed-rank test as primary
- Paired t-test for reference
- Rank-biserial correlation and Cohen's d as effect sizes
- Underpowered flagging for comparisons with fewer than 10 pairs

### 6.5 Validation Criteria

The system is considered functionally validated when:

- All 989 tests pass fully offline (socket guard in conftest.py blocks any outbound connection)
- Intent classification produces consistent results across identical prompts
- Multi-agent execution completes with non-empty state for all active departments
- Shared state contract is enforced (cross-department writes raise exceptions)
- External API integration successfully retrieves and caches data
- Operating layer runs autonomously for 90 simulated days without human intervention
- Anchor metrics are derivable from the ledger without being stored
- Governance workflows enforce constitutional constraints
- Evaluation metrics can be computed for both multi-agent and baseline arms
- Ablation harness produces distinct results across four experimental arms

---

## CHAPTER 7
## PROJECT PLAN

**Phase 1: Foundation and Architecture (Completed)**

- Set up project structure with backend and frontend directories
- Configure Python virtual environment and dependencies
- Implement configuration management with pydantic-settings
- Design shared business state schema with Pydantic
- Set up SQLite database and ChromaDB vector store
- Implement LLM client with provider fallback chain

**Phase 2: Intent Classification (Completed)**

- Implement natural language prompt input validation
- Build hybrid intent classifier (LLM + deterministic parsing)
- Implement budget parsing and normalization
- Implement location parsing and gazetteer-based normalization
- Implement business type classification with sector taxonomy
- Add unit tests for all intent components

**Phase 3: Business Orchestrator (Completed)**

- Implement routing rules engine
- Build execution DAG construction with LangGraph
- Implement parallel execution manager
- Add session and state initialization
- Implement progress tracking and WebSocket streaming
- Add timeout handling (120 seconds per generation)

**Phase 4: Department Agents (Completed)**

- Implement 5 Strategy agents (market_research, competitive_analysis, location_intelligence, business_planning, risk_analysis)
- Implement 4 Finance agents (revenue_model, cost_structure, funding_strategy, pl_forecast)
- Implement 4 Branding agents (brand_naming, brand_identity, brand_voice, visual_design)
- Implement 4 Marketing agents (digital_plan, buyer_persona, campaign_plan, seo_content)
- Implement 4 Operations agents (supply_chain, staffing_plan, tech_stack, process_flow)
- Add cross-agent reconciliation logic for conflicting quantities
- Implement arithmetic computation for financial projections

**Phase 5: External Data Integration (Completed)**

- Integrate Google Places API for competitor discovery
- Implement OpenStreetMap (Overpass + Nominatim) as fallback
- Integrate Serper.dev for market research
- Implement ChromaDB caching for API results
- Add data freshness tagging (30-day staleness threshold)
- Implement cache invalidation logic

**Phase 6: Output Layer (Completed)**

- Implement JSON business package assembly
- Build HTML report generation with Jinja2
- Implement PDF export via xhtml2pdf
- Add section-level access APIs
- Implement generation metadata and transparency reporting
- Style reports with Branding department's chosen palette

**Phase 7: Frontend (Completed)**

- Implement single-prompt input interface
- Build real-time agent progress display with WebSocket
- Implement report viewer with department tabs
- Add PDF and JSON download functionality
- Implement generation history with SQLite-backed storage
- Add error status display (unreachable, degraded, failed)

**Phase 8: Evaluation (Completed)**

- Implement evaluation harness with four experimental arms
- Build five evaluation metrics (completeness, accuracy, consistency, efficiency, coverage)
- Implement single-LLM baseline
- Create 35 diverse test prompts across sectors
- Implement significance testing with paired Wilcoxon and t-tests
- Add effect size computation (rank-biserial, Cohen's d)

**Phase 9: Operating Layer (Completed)**

- Implement ledger with append-only SQLite triggers
- Build 19 anchor metrics derived from ledger
- Implement constitution with 7 hard constraints
- Build governance workflow (decision → review → approval → execution → audit)
- Implement loop registry with topology validation
- Build monitors (Goodhart, conflict, drift, objective review)
- Implement clock-injected scheduler
- Build five memory stores with scoped access
- Implement reflection with learning from anchor deltas
- Build five department loops with governance integration

**Phase 10: Ablation Harness (Completed)**

- Implement seeded stochastic market environment
- Build four ablation arms (single_loop, anchors_only, monitors_only, full_graph)
- Implement five operating metrics (divergence, latency, conflicts, staleness, load)
- Build paired-seed runner for consistent comparisons
- Implement ablation report generation with statistical testing
- Add 99 tests for ablation components

**Phase 11: Documentation and Paper (In Progress)**

- Complete full 35-prompt sweep for paper results
- Source sector margin benchmarks for financial accuracy
- Collect competitor ground truth for coverage rate
- Raise ablation seed count to n=40 for statistical power
- Finalize research paper with all figures and tables
- Generate review deck matching college template

---

## CHAPTER 8
## EXPECTED OUTCOME

**Generation Layer Outcomes:**

The generation layer produces complete, location-aware, budget-specific business plans in 60-90 seconds from a single natural language prompt. Plans include:

- Strategy: Executive summary, TAM/SAM/SOM analysis, business model canvas, risk assessment, competitive analysis with real competitor data, market research with industry trends, location intelligence scoring
- Finance: Revenue model with pricing strategy, cost structure enforcing budget constraints, funding strategy recommendations, 3-year P&L forecast with break-even analysis
- Branding: 5-10 brand name candidates with rationale, brand identity with color palette and typography, brand voice guidelines with sample content, visual design direction
- Marketing: Digital marketing plan with channel mix and budget allocation, buyer personas with demographics and psychographics, 90-day campaign calendar, SEO strategy with keyword lists
- Operations (conditional): Supply chain overview, staffing plan with org chart, technology stack recommendations, daily process flow documentation

**Measured Results (n=5, preliminary):**

- Plan Completeness: 100% vs 80.8% baseline (multi-agent wins)
- Financial Accuracy (MAPE): ~132 vs ~41 baseline (baseline wins due to variance compounding)
- Consistency: 97.8% vs 100% baseline (statistically tied)
- Routing Efficiency: 17.3% token saving with 0.0 pp completeness delta on prompts where routing skipped a department

**Variance Finding:**

Identical prompt, five runs per arm: multi-agent standard deviation is 4.9× the baseline's. The architecture is unreliably better, not reliably worse—compounding variance across agents introduces instability. This is reported honestly rather than tuned away.

**Operating Layer Outcomes:**

The operating layer runs companies autonomously on department cadences. In a 90-day simulated run with no human prompting and no LLM calls:

- Scheduled loop runs: 574
- Ledger entries: 486
- Net margin trajectory: 60% → +2.5% (self-correction demonstrated)
- Customers acquired: 0 → 104
- Marketing episodic memories: 14 vs 89 for other departments (demonstrates learning)
- Findings raised: CRITICAL proxy divergence, HIGH inter-department conflict

The monitors detected margin divergence, and the company self-corrected: marketing received a margin lesson, suppressed its spend task, and stopped acting—evidenced by the memory count gap.

**Ablation Results (n=10, underpowered):**

The ablation harness tests the operating layer's control claims. At n=10, F59 (proxy-anchor divergence) favours the full graph in every comparison (−0.78 vs −0.59 for single_loop) but no comparison reaches p < 0.05 (best is 0.059). Between-seed standard deviation is 33-70% of means. RQ4-RQ7 remain unanswered.

**Reliability:**

Multi-agent arm: 5 runs, 5 plans produced (100%)
Baseline arm: 5 runs, 3 plans produced (60%)

The multi-provider fallback chain confers real resilience against API rate limits and outages.

**Research Contributions:**

1. Empirical finding that cross-agent constraints must be enforced in code, not requested in prompts (§4.4 of paper)
2. Empirical finding that decomposing quantitative estimates across dependent agents compounds variance (§7.2 of paper)
3. Structural prevention of Goodhart's Law through the anchor metric invariant
4. Demonstration that reflective learning can suppress value-destroying department behavior
5. Honest reporting of null results rather than experimental tuning

**Sustainable Development Goals:**

- SDG 9: Industry, Innovation and Infrastructure—democratizes access to sophisticated business planning tools
- SDG 12: Responsible Consumption and Production—reduces manual effort and resource-intensive planning processes

---

## CHAPTER 9
## PROJECT COST ESTIMATION

## Project Cost Estimation Using the COCOMO Model

For Orion, the Basic Constructive Cost Model (COCOMO) is used to estimate the software development effort, development time, team size, and projected development cost. The estimation is based on the implemented system including the generation layer (21 agents, 5 departments), operating layer (10 governance modules), evaluation harness, ablation harness, and frontend.

### A. Project Classification

Orion is provisionally classified under the Organic Mode of the Basic COCOMO model for this academic estimation, assuming a relatively small development team and a manageable software scope.

The project uses established technologies and frameworks (LangGraph, FastAPI, React).
The system follows a modular two-layer architecture.
The project integrates multiple components (agents, databases, APIs, frontend).
The development is planned within an academic project environment.

### B. Estimation Parameters

Estimated Project Size: 15,000 Lines of Code (15 KLOC), assumed for estimation.
COCOMO Model: Basic COCOMO.
Project Mode: Organic.

The constants for Organic Mode are:
- a = 2.4
- b = 1.05
- c = 2.5
- d = 0.38

Effort estimation equation:
E = a × (KLOC)^b

Development time equation:
D = c × (E)^d

Where:
E = Development effort in person-months
D = Estimated development time in months
KLOC = Estimated thousands of lines of source code

### C. Effort Estimation

For an estimated project size of 15 KLOC:

E = 2.4 × (15)^1.05
E = 2.4 × 17.26
E = 41.42 person-months

Therefore, the estimated development effort is approximately 41.42 person-months.

### D. Development Time Estimation

Using the estimated effort:

D = 2.5 × (41.42)^0.38
D = 2.5 × 4.37
D = 10.93 months

The estimated development time is approximately 10.93 months.

### E. Team Size Estimation

The average team size is calculated as:

Team Size = E / D
Team Size = 41.42 / 10.93
Team Size = 3.79

Thus, the estimated staffing level is approximately four members over the calculated development period. This is a model-based estimate, not a statement of the actual team size.

### F. Cost Estimation

Assuming an average development cost of ₹25,000 per person per month for this academic estimation:

Total Cost = E × Cost per person-month
Total Cost = 41.42 × 25,000
Total Cost = ₹10,35,500

This amount estimates development effort cost only. Actual cloud hosting, domain, and external service charges are minimal due to the zero-cost constraint—all APIs used have sufficient free tiers.

### G. Summary of Estimation

| Parameter | Value |
|-----------|-------|
| Project Size | 15 KLOC |
| Development Effort | 41.42 person-months |
| Development Time | 10.93 months |
| Team Size | 3.79 members (~4) |
| Development Cost | ₹10,35,500 |

### H. Conclusion

The Basic COCOMO model provides a structured method for estimating the development effort, time, and cost of Orion. Under the assumed project size and Organic Mode classification, the estimated development cost is ₹10,35,500. This is a preliminary academic estimate and should be revised when the final source-code size, implementation scope, and actual development effort are known.

The estimate excludes operational expenses, but these are minimal due to the zero-cost design constraint—all external services (Groq, Gemini, Serper, OpenStreetMap, ChromaDB) have sufficient free tiers. No paid services are required for core functionality.

---

## CHAPTER 10
## REFERENCES

**Note: External literature survey to be completed by the user. This section should include research papers on multi-agent systems, business process automation, LLM-based systems, and AI operations. The following template provides the expected format:**

### Journal Papers

[1] Author Name, "Title of Paper," Journal Name, vol. X, no. Y, pp. start-end, Year, doi: xxx.

[2] Author Name, "Title of Paper," Journal Name, vol. X, no. Y, pp. start-end, Year, doi: xxx.

### Conference Proceedings

[3] Author Name, "Title of Paper," in Proceedings of Conference Name, Year, pp. start-end, doi: xxx.

[4] Author Name, "Title of Paper," in Proceedings of Conference Name, Year, pp. start-end, doi: xxx.

### Books and Technical Reports

[5] Author Name, Book Title, Edition, Publisher, Year.

[6] Author Name, Report Title, Technical Report, Institution, Year.

### Online Resources

[7] Framework Documentation, "Title," URL, accessed Date.

[8] API Documentation, "Title," URL, accessed Date.

---

## APPENDICES

### Appendix A: Technology Details

**LangGraph:** An orchestration framework for building stateful, multi-actor applications with LLMs. Provides explicit graph construction, streaming execution, and state management.

**FastAPI:** Modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints. Provides automatic documentation, validation, and async support.

**React:** JavaScript library for building user interfaces. Provides component-based architecture, virtual DOM for performance, and ecosystem of libraries.

**SQLite:** C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine. Used for session storage, ledger, and evaluation results.

**ChromaDB:** Open-source embedding database. Used for caching generated plans, market research, and competitor data to avoid redundant API calls.

### Appendix B: Test Suite Summary

Total tests: 989
Test framework: pytest with pytest-asyncio
Offline execution: All tests pass without network connection (socket guard in conftest.py)
Coverage: Intent classification, orchestrator, all 21 agents, external API integration, output layer, frontend, operating layer (10 modules), ablation harness (4 arms)

### Appendix C: Evaluation Results Summary

Current evaluation at n=5 (preliminary, not final findings):

| Metric | Multi-Agent | Baseline | Verdict |
|--------|-------------|----------|---------|
| Plan Completeness | 100.0% | 80.8% | Multi-agent wins |
| Financial Accuracy (MAPE) | ~132 | ~41 | Baseline wins |
| Consistency | 97.8% | 100.0% | Tied |
| Routing Efficiency | 17.3% token saving | N/A | RQ2 supported |

Ablation at n=10 (underpowered, not significant):
- F59 divergence favours full graph in all comparisons
- Best p-value: 0.059 (does not reach p < 0.05)
- Between-seed SD: 33-70% of means
- RQ4-RQ7: Unanswered

### Appendix D: Running the System

**Backend:**
```powershell
$env:PYTHONPATH="E:\AgenticSystem\Orion\backend;E:\AgenticSystem\Orion"
cd E:\AgenticSystem\Orion\backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\uvicorn app.main:app --reload
```

**Frontend:**
```powershell
cd E:\AgenticSystem\Orion\frontend
npm install
npm run dev
```

**Docker Compose:**
```powershell
cd E:\AgenticSystem\Orion
docker-compose up
```

**Demos:**
```powershell
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe -m scripts.autonomy_demo --days 90
.venv\Scripts\python.exe -m scripts.operating_demo
```

---

*End of Report*
