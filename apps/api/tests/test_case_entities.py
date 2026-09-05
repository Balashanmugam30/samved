"""Test suite for Case Intelligence entity creation and epistemic safety (Phase 11)."""

import pytest
from app.cases.models import CaseEntity
from app.cases.service import CaseService
from app.schemas.events import ClaimStatus, EntityType, PersonRole


@pytest.mark.asyncio
async def test_entity_creation_via_service():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-TEST-001")

    entity = await svc.add_entity(
        case_id=case.case_id,
        entity_type=EntityType.PERSON,
        label="Ravi",
        role=PersonRole.SUPPORT_PERSON,
        claim_status=ClaimStatus.REPORTED,
        metadata={"relation": "cousin"},
    )
    assert entity.entity_id.startswith("ent-")
    assert entity.label == "Ravi"
    assert entity.role == PersonRole.SUPPORT_PERSON
    assert entity.claim_status == ClaimStatus.REPORTED


@pytest.mark.asyncio
async def test_epistemic_safety_filters_prohibited_guilt_roles():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-TEST-002")

    # Prohibited roles like OFFENDER or GUILTY must be normalized to REPORTED_ACTOR
    entity = await svc.add_entity(
        case_id=case.case_id,
        entity_type=EntityType.PERSON,
        label="Unknown Individual",
        role="OFFENDER",
        claim_status=ClaimStatus.REPORTED,
    )
    assert entity.role == PersonRole.REPORTED_ACTOR


@pytest.mark.asyncio
async def test_update_entity_attributes():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-TEST-003")

    entity = await svc.add_entity(
        case_id=case.case_id,
        entity_type=EntityType.LOCATION,
        label="Old Shelter",
        claim_status=ClaimStatus.REPORTED,
    )

    updated = await svc.update_entity(
        case_id=case.case_id,
        entity_id=entity.entity_id,
        updates={"label": "New Women Shelter", "claim_status": ClaimStatus.VERIFIED},
    )
    assert updated is not None
    assert updated.label == "New Women Shelter"
    assert updated.claim_status == ClaimStatus.VERIFIED


@pytest.mark.asyncio
async def test_add_entity_to_nonexistent_case_fails():
    svc = CaseService(auto_seed=False)
    with pytest.raises(ValueError, match="not found"):
        await svc.add_entity(
            case_id="case-nonexistent",
            entity_type=EntityType.PERSON,
            label="Ghost",
        )
