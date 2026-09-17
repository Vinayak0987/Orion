"""Operations schema additions (Phase 1) - frozen-safe field checks.

Proves the new compliance/feasibility fields are additive: every existing
OperationsOutput field is untouched and defaults as before, and the new fields
default empty/None so a baseline run (synthesis off) produces an identical
section. Fully offline - pure Pydantic.
"""

from __future__ import annotations

from app.models.departments import (
    EvidenceItem,
    Licence,
    OperationsOutput,
    ProcessStep,
    Role,
    ToolRecommendation,
    Vendor,
)


def test_existing_operations_fields_unchanged() -> None:
    o = OperationsOutput()
    assert o.inventory_requirements == []
    assert o.vendors == []
    assert o.inventory_approach is None
    assert o.roles == []
    assert o.total_headcount_y1 is None
    assert o.total_monthly_payroll_inr is None
    assert o.tools == []
    assert o.total_tool_cost_monthly_inr is None
    assert o.daily_workflow == []
    assert o.key_processes == []
    assert o.quality_checkpoints == []


def test_new_synthesis_fields_default_empty() -> None:
    o = OperationsOutput()
    assert o.licences == []
    assert o.compliance_notes is None
    assert o.feasibility_score is None
    assert o.feasibility_warnings == []
    assert o.operations_summary is None
    assert o.operations_evidence == []


def test_licence_model_defaults() -> None:
    lic = Licence(name="FSSAI Food Licence", authority="FSSAI")
    assert lic.evidence_kind == "assumption"
    assert lic.est_cost_inr is None
    assert lic.when_required == ""


def test_feasibility_score_bounds() -> None:
    import pytest
    from pydantic import ValidationError

    OperationsOutput(feasibility_score=0)
    OperationsOutput(feasibility_score=100)
    with pytest.raises(ValidationError):
        OperationsOutput(feasibility_score=101)
    with pytest.raises(ValidationError):
        OperationsOutput(feasibility_score=-1)


def test_operations_output_roundtrips_with_new_fields() -> None:
    o = OperationsOutput(
        roles=[Role(title="Manager", headcount=1)],
        tools=[ToolRecommendation(name="Khatabook", purpose="accounting")],
        vendors=[Vendor(category="dairy")],
        daily_workflow=[ProcessStep(order=1, name="Open", owner_role="Manager")],
        licences=[Licence(name="GST Registration", authority="GST Dept", evidence_kind="fact")],
        compliance_notes="Verify all licences locally.",
        feasibility_score=75,
        feasibility_warnings=["tech stack thin"],
        operations_summary="Staffing fits budget; process well owned.",
        operations_evidence=[EvidenceItem(claim="payroll within budget", kind="inference", confidence=0.6)],
    )
    restored = OperationsOutput.model_validate_json(o.model_dump_json())
    assert restored == o
    assert restored.licences[0].evidence_kind == "fact"
    assert restored.feasibility_score == 75
    assert restored.operations_evidence[0].kind == "inference"
