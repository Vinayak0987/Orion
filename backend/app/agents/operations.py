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
from app.agents.operations_feasibility import fallback_summary, score_operations
from app.config import settings
from app.llm.base import ModelTier
from app.models.departments import (
    EvidenceItem,
    Licence,
    ProcessStep,
    Role,
    ToolRecommendation,
    Vendor,
)
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
  "inventory_requirements": ["6-8 inputs this business must stock, each with a rough MONTHLY quantity"],
  "vendors": [{{"category": "what they supply", "supplies": "specific items", "sourcing_type": "local, wholesale, online or direct_manufacturer", "notes": "one line on selection criteria"}}],
  "inventory_approach": "3 sentences on reorder policy, safety stock and wastage control"
}}

Think in SCOR terms - Source (who supplies), Make/store (how inputs are held),
Deliver (how output reaches the customer). Give 4 to 6 vendor categories. Note
any items that are perishable or need special storage."""

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
this city. hire_month is the month of year 1 when the role is filled (1-12).
Justify each headcount by the WORK it covers - operating hours, shifts, peak
demand and any legally required roles - not a round number."""

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
inventory, customer messaging and online presence. Choose each tool on fit for
THIS business - cost, security, ease of integration and the process it supports -
not because it is popular. Prefer free options; only recommend paid tools where
there is no workable free alternative."""

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

Give 6 to 9 workflow steps from opening to closing. Every step MUST name an
owner_role, and owner_role MUST be one of the roles listed above where any are
given. In quality_checkpoints, include the controls and exception-handling that
protect each critical step - not just a generic checklist."""

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
# F34a - Compliance & Licensing Agent (stage 3 - synthesis, opt-in)
# =============================================================================
#
# Static seed of obligatory Indian-SME licences by sector, so the obvious ones
# are never omitted even if the model forgets them. The LLM extends this list
# with business-specific licences. Seeded items are tagged `fact`; LLM additions
# `assumption`. Costs/applicability are jurisdiction- and time-sensitive, so
# every item's notes tell the operator to verify with the authority.

_LICENCE_GAZETTEER: dict[str, list[tuple[str, str, str]]] = {
    # sector: [(name, authority, when_required)]
    "food_and_beverage": [
        ("FSSAI Food Licence", "FSSAI", "any business handling food"),
        ("Shop & Establishment Registration", "State Labour Department", "any commercial premises"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
        ("Trade Licence", "Municipal Corporation", "operating within municipal limits"),
    ],
    "retail": [
        ("Shop & Establishment Registration", "State Labour Department", "any commercial premises"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
        ("Trade Licence", "Municipal Corporation", "operating within municipal limits"),
    ],
    "manufacturing": [
        ("Factory Licence", "State Factories Department", "manufacturing premises with workers"),
        ("Pollution Control Consent (NOC)", "State Pollution Control Board", "processes with effluent/emissions"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
        ("Shop & Establishment Registration", "State Labour Department", "commercial premises"),
    ],
    "healthcare": [
        ("Clinical Establishment Registration", "State Health Department", "any clinic or health facility"),
        ("Bio-medical Waste Authorisation", "State Pollution Control Board", "generates clinical waste"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
    ],
    "services": [
        ("Shop & Establishment Registration", "State Labour Department", "any commercial premises"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
    ],
    "education": [
        ("Shop & Establishment Registration", "State Labour Department", "any commercial premises"),
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
    ],
    "technology": [
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
        ("Shop & Establishment Registration", "State Labour Department", "if a physical office is maintained"),
    ],
    "creative": [
        ("GST Registration", "GST Department", "turnover above the registration threshold"),
        ("Shop & Establishment Registration", "State Labour Department", "if a physical studio is maintained"),
    ],
}

_VERIFY_NOTE = "verify current fee, applicability and process with the issuing authority"


class LicenceOut(AgentOutput):
    name: str = ""
    authority: str = ""
    when_required: str = ""
    est_cost_inr: int | None = None
    notes: str = ""


class ComplianceOut(AgentOutput):
    licences: list[LicenceOut] = Field(default_factory=list)
    compliance_notes: str = ""


class ComplianceLicensingAgent(Agent):
    """F34a. Produces the licence/permit checklist an Indian SME needs. The
    gazetteer guarantees the sector's obligatory licences are present (tagged
    `fact`); the LLM adds business-specific ones (tagged `assumption`). Never
    guarantees fees or approval - every item says 'verify locally'."""

    spec = AgentSpec(
        agent_id="compliance_licensing",
        department=DEPT,
        feature="F34a",
        schema=ComplianceOut,
        tier=ModelTier.REASONING,
        max_tokens=1200,
    )
    system = (
        "You are a compliance advisor for Indian SMEs. You list concrete licences "
        "and registrations, and you never guarantee current fees or approval - you "
        "always tell the operator to verify with the issuing authority."
    )

    def build_prompt(self, state: SharedBusinessState) -> str:
        intent = state.get("intent")
        sector = intent.sector.value if intent is not None else "unspecified"
        seeded = _LICENCE_GAZETTEER.get(sector, [])
        seeded_names = ", ".join(name for name, _, _ in seeded) or "(none seeded)"
        return f"""{context_block(state)}

The following licences are already known to apply to this sector and will be
included automatically: {seeded_names}.

List any ADDITIONAL licences, registrations or permits this specific business
needs beyond those, and return JSON with these keys:
{{
  "licences": [
    {{
      "name": "licence/permit name",
      "authority": "issuing body",
      "when_required": "the condition that triggers it",
      "est_cost_inr": rough official fee as a plain integer or null,
      "notes": "one line; state clearly if uncertain"
    }}
  ],
  "compliance_notes": "2-3 sentences on the overall compliance approach and sequencing"
}}

Only list licences you are reasonably confident apply. Do not repeat the ones
already listed above. Do not invent precise fees - use null if unsure."""

    def to_patch(self, parsed: ComplianceOut, state: SharedBusinessState) -> dict:
        intent = state.get("intent")
        sector = intent.sector.value if intent is not None else "unspecified"

        # 1. Seed the sector's obligatory licences as facts.
        licences: list[Licence] = [
            Licence(
                name=name,
                authority=authority,
                when_required=when,
                evidence_kind="fact",
                notes=_VERIFY_NOTE,
            )
            for (name, authority, when) in _LICENCE_GAZETTEER.get(sector, [])
        ]
        seen = {lic.name.strip().lower() for lic in licences}

        # 2. Add LLM-suggested licences as assumptions, deduped by name.
        for item in parsed.licences:
            name = item.name.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            note = item.notes.strip()
            if _VERIFY_NOTE not in note.lower():
                note = f"{note} ({_VERIFY_NOTE})".strip() if note else _VERIFY_NOTE.capitalize()
            licences.append(
                Licence(
                    name=name,
                    authority=item.authority.strip(),
                    when_required=item.when_required.strip(),
                    est_cost_inr=item.est_cost_inr,
                    evidence_kind="assumption",
                    notes=note,
                )
            )

        return {
            "licences": licences,
            "compliance_notes": parsed.compliance_notes.strip() or None,
        }


# =============================================================================
# F37a - Operations Feasibility / SOP Reviewer (stage 4 - reads all operations)
# =============================================================================


class EvidenceOut(AgentOutput):
    claim: str = ""
    kind: str = "assumption"
    confidence: float | None = None
    source: str = ""


class OpsFeasibilityOut(AgentOutput):
    operations_summary: str = ""
    evidence: list[EvidenceOut] = Field(default_factory=list)


_EVIDENCE_KINDS = {"fact", "assumption", "inference", "prediction", "unknown"}


class OperationsFeasibilityAgent(Agent):
    """F37a. Runs the deterministic feasibility scorer over the completed
    operations section (consistency, feasibility, completeness, tech coverage),
    then writes a short evidence-tagged summary explaining the result. Falls back
    to a deterministic summary if the LLM is unavailable. The SCORE is computed in
    Python, never asserted by the model."""

    spec = AgentSpec(
        agent_id="operations_feasibility",
        department=DEPT,
        feature="F37a",
        schema=OpsFeasibilityOut,
        tier=ModelTier.FAST,
        max_tokens=800,
    )
    system = (
        "You are an operations reviewer. You explain a computed feasibility result "
        "plainly and are explicit about what is assumed versus known."
    )

    def _score(self, state: SharedBusinessState) -> tuple[int | None, list[str]]:
        ops = state.get(DEPT.value)
        if ops is None:
            return None, []
        return score_operations(ops, state.get("intent"))

    def build_prompt(self, state: SharedBusinessState) -> str:
        score, warnings = self._score(state)
        warning_block = "\n".join(f"- {w}" for w in warnings) or "- (none)"
        return f"""{context_block(state)}

{upstream_block(state, "staffing")}

A deterministic check produced this operations feasibility result:
SCORE: {score if score is not None else "n/a"}/100
WARNINGS:
{warning_block}

Explain this result and return JSON with these keys:
{{
  "operations_summary": "2-3 sentences on the biggest operational risk and readiness, citing the score",
  "evidence": [
    {{"claim": "a key operational claim",
      "kind": "one of fact, assumption, inference, prediction, unknown",
      "confidence": 0.0 to 1.0,
      "source": "staffing / process / tech / budget / llm"}}
  ]
}}

Tag anything you did not verify as 'assumption' or 'unknown'."""

    def to_patch(self, parsed: OpsFeasibilityOut, state: SharedBusinessState) -> dict:
        score, warnings = self._score(state)
        evidence = [
            EvidenceItem(
                claim=e.claim.strip(),
                kind=e.kind.strip().lower()
                if e.kind.strip().lower() in _EVIDENCE_KINDS
                else "assumption",
                confidence=_clamp_confidence(e.confidence),
                source=e.source.strip()[:40],
            )
            for e in parsed.evidence
            if e.claim and e.claim.strip()
        ]
        summary = parsed.operations_summary.strip() or fallback_summary(score, warnings)
        return {
            "feasibility_score": score,
            "feasibility_warnings": warnings,
            "operations_summary": summary,
            "operations_evidence": evidence,
        }


def _clamp_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


# =============================================================================
# Stage layout
# =============================================================================
#
# Baseline is 4 agents across two stages (F34-F37). When
# `enable_operations_synthesis` is on, two more stages run: F34a Compliance
# (stage 3) then F37a Feasibility (stage 4). Feasibility runs last so it can
# score the whole section, including staffing, process and tech.


def build_operations_stages(*, synthesis: bool | None = None) -> tuple[tuple[Agent, ...], ...]:
    """Assemble the operations stage tuple, honouring the synthesis flag.

    `synthesis=None` reads `settings.enable_operations_synthesis`; tests pass an
    explicit bool to exercise both topologies.
    """
    if synthesis is None:
        synthesis = settings.enable_operations_synthesis

    stages: list[tuple[Agent, ...]] = [
        (
            SupplyChainAgent(),
            StaffingPlanAgent(),
            TechStackAgent(),
        ),
        (ProcessFlowAgent(),),
    ]
    if synthesis:
        stages.append((ComplianceLicensingAgent(),))
        stages.append((OperationsFeasibilityAgent(),))
    return tuple(stages)


OPERATIONS_STAGES: tuple[tuple[Agent, ...], ...] = build_operations_stages()
