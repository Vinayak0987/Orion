"""Operations department - 4 agents (F34-F37). Conditional department.

Stage 1 (parallel)    supply_chain ∥ staffing_plan ∥ tech_stack
Stage 2 (sequential)  process_flow

Process flow runs last because it assigns each workflow step to a role, and those
roles come from the staffing agent. Assigning owners to roles that do not exist is
exactly the kind of internal inconsistency this staging prevents.

This whole department is skipped for digital businesses (F10), which is the token
saving RQ2 quantifies.
"""

from __future__ import annotations

from pydantic import Field

from app.agents.base import (
    Agent,
    AgentOutput,
    AgentSpec,
    context_block,
    upstream_block,
)
from app.llm.base import ModelTier
from app.models.departments import ProcessStep, Role, ToolRecommendation, Vendor
from app.models.state import Department, SharedBusinessState

DEPT = Department.OPERATIONS


# =============================================================================
# F34 - Supply Chain Agent
# =============================================================================


class VendorOut(AgentOutput):
    category: str = ""
    supplies: str = ""
    sourcing_type: str = ""
    notes: str = ""


class SupplyChainOut(AgentOutput):
    inventory_requirements: list[str] = Field(default_factory=list)
    vendors: list[VendorOut] = Field(default_factory=list)
    inventory_approach: str = ""


_SOURCING_TYPES = {"local", "wholesale", "online", "direct_manufacturer"}


class SupplyChainAgent(Agent):
    spec = AgentSpec(
        agent_id="supply_chain",
        department=DEPT,
        feature="F34",
        schema=SupplyChainOut,
        tier=ModelTier.REASONING,
        max_tokens=1200,
    )
    system = (
        "You are a supply chain consultant for Indian SMEs. You reference real "
        "Indian wholesale markets and sourcing channels where relevant."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "costs")}

Design the supply chain and return JSON with these keys:
{{
  "inventory_requirements": ["6-8 inputs this business must stock, with rough monthly quantities"],
  "vendors": [{{"category": "what they supply", "supplies": "specific items", "sourcing_type": "local, wholesale, online or direct_manufacturer", "notes": "one line on selection criteria"}}],
  "inventory_approach": "3 sentences on reorder policy, safety stock and wastage control"
}}

Give 4 to 6 vendor categories."""

    def to_patch(self, parsed: SupplyChainOut, state: SharedBusinessState) -> dict:
        vendors = [
            Vendor(
                category=v.category.strip(),
                supplies=v.supplies.strip(),
                sourcing_type=v.sourcing_type.strip().lower().replace(" ", "_")
                if v.sourcing_type.strip().lower().replace(" ", "_") in _SOURCING_TYPES
                else "local",
                notes=v.notes.strip(),
            )
            for v in parsed.vendors
            if v.category and v.category.strip()
        ]
        return {
            "inventory_requirements": parsed.inventory_requirements,
            "vendors": vendors,
            "inventory_approach": parsed.inventory_approach,
        }


# =============================================================================
# F35 - Staffing Plan Agent
# =============================================================================


class RoleOut(AgentOutput):
    title: str = ""
    headcount: int = 1
    monthly_salary_inr: int | None = None
    hire_month: int | None = None
    responsibilities: list[str] = Field(default_factory=list)


class StaffingOut(AgentOutput):
    roles: list[RoleOut] = Field(default_factory=list)


class StaffingPlanAgent(Agent):
    spec = AgentSpec(
        agent_id="staffing_plan",
        department=DEPT,
        feature="F35",
        schema=StaffingOut,
        tier=ModelTier.REASONING,
        temperature=0.2,
        max_tokens=1300,
    )
    system = (
        "You are an HR consultant who knows current Mumbai and Indian metro salary "
        "bands for small business roles."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

{upstream_block(state, "costs")}

Plan year-1 staffing and return JSON with this key:
{{
  "roles": [
    {{
      "title": "role",
      "headcount": 2,
      "monthly_salary_inr": 22000,
      "hire_month": 1,
      "responsibilities": ["2-3 duties"]
    }}
  ]
}}

Give 3 to 6 roles. monthly_salary_inr is per person, at real market rates for
this city. hire_month is the month of year 1 when the role is filled."""

    def to_patch(self, parsed: StaffingOut, state: SharedBusinessState) -> dict:
        roles = [
            Role(
                title=r.title.strip(),
                headcount=max(1, int(r.headcount or 1)),
                monthly_salary_inr=r.monthly_salary_inr,
                hire_month=r.hire_month,
                responsibilities=r.responsibilities,
            )
            for r in parsed.roles
            if r.title and r.title.strip()
        ]
        # Totals computed in code, not generated.
        headcount = sum(r.headcount for r in roles)
        payroll = sum(
            (r.monthly_salary_inr or 0) * r.headcount for r in roles
        )
        return {
            "roles": roles,
            "total_headcount_y1": headcount or None,
            "total_monthly_payroll_inr": payroll or None,
        }


# =============================================================================
# F36 - Technology Stack Agent
# =============================================================================


class ToolOut(AgentOutput):
    name: str = ""
    purpose: str = ""
    cost: str = "free"
    monthly_cost_inr: int | None = None


class TechStackOut(AgentOutput):
    tools: list[ToolOut] = Field(default_factory=list)


_COST_KINDS = {"free", "freemium", "paid"}


class TechStackAgent(Agent):
    spec = AgentSpec(
        agent_id="tech_stack",
        department=DEPT,
        feature="F36",
        schema=TechStackOut,
        tier=ModelTier.FAST,
        max_tokens=1100,
    )
    system = (
        "You are an SME technology advisor. You strongly prefer free and freemium "
        "tools available in India, and you name real products."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

Recommend the operational tech stack and return JSON with this key:
{{
  "tools": [
    {{
      "name": "real product name",
      "purpose": "what it is used for here",
      "cost": "free, freemium or paid",
      "monthly_cost_inr": 0
    }}
  ]
}}

Give 6 to 9 tools covering billing/POS, accounting, staff communication,
inventory, customer messaging and online presence. Prefer free options; only
recommend paid tools where there is no workable free alternative."""

    def to_patch(self, parsed: TechStackOut, state: SharedBusinessState) -> dict:
        tools = [
            ToolRecommendation(
                name=t.name.strip(),
                purpose=t.purpose.strip(),
                cost=t.cost.strip().lower() if t.cost.strip().lower() in _COST_KINDS else "paid",
                monthly_cost_inr=t.monthly_cost_inr,
            )
            for t in parsed.tools
            if t.name and t.name.strip()
        ]
        total = sum(t.monthly_cost_inr or 0 for t in tools)
        return {"tools": tools, "total_tool_cost_monthly_inr": total or None}


# =============================================================================
# F37 - Process Flow Agent (stage 2 - reads staffing)
# =============================================================================


class ProcessStepOut(AgentOutput):
    order: int = 0
    name: str = ""
    description: str = ""
    owner_role: str = ""
    depends_on: list[str] = Field(default_factory=list)


class ProcessFlowOut(AgentOutput):
    daily_workflow: list[ProcessStepOut] = Field(default_factory=list)
    key_processes: list[str] = Field(default_factory=list)
    quality_checkpoints: list[str] = Field(default_factory=list)


class ProcessFlowAgent(Agent):
    spec = AgentSpec(
        agent_id="process_flow",
        department=DEPT,
        feature="F37",
        schema=ProcessFlowOut,
        tier=ModelTier.FAST,
        max_tokens=1300,
    )
    system = "You are an operations manager documenting standard operating procedures."

    def build_prompt(self, state: SharedBusinessState) -> str:
        return f"""{context_block(state)}

STAFFING FROM THIS RUN:
{upstream_block(state, "staffing") or "(not yet available)"}

Document the daily operation and return JSON with these keys:
{{
  "daily_workflow": [
    {{
      "order": 1,
      "name": "step name",
      "description": "what happens",
      "owner_role": "which role owns it",
      "depends_on": ["names of earlier steps"]
    }}
  ],
  "key_processes": ["4-6 core processes beyond the daily routine"],
  "quality_checkpoints": ["3-5 checks that protect quality"]
}}

Give 6 to 9 workflow steps from opening to closing.
owner_role MUST be one of the roles listed above where any are given."""

    def to_patch(self, parsed: ProcessFlowOut, state: SharedBusinessState) -> dict:
        steps = [
            ProcessStep(
                order=step.order if step.order > 0 else index + 1,
                name=step.name.strip(),
                description=step.description.strip(),
                owner_role=step.owner_role.strip(),
                depends_on=step.depends_on,
            )
            for index, step in enumerate(parsed.daily_workflow)
            if step.name and step.name.strip()
        ]
        steps.sort(key=lambda s: s.order)
        return {
            "daily_workflow": steps,
            "key_processes": parsed.key_processes,
            "quality_checkpoints": parsed.quality_checkpoints,
        }


# =============================================================================
# Stage layout
# =============================================================================

OPERATIONS_STAGES: tuple[tuple[Agent, ...], ...] = (
    (
        SupplyChainAgent(),
        StaffingPlanAgent(),
        TechStackAgent(),
    ),
    (ProcessFlowAgent(),),
)
