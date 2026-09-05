"""Test suite for Case Intelligence relationships and historical superseding (Phase 11)."""

import pytest
from app.cases.service import CaseService
from app.schemas.events import ClaimStatus, EntityType, PersonRole, RelationshipType


@pytest.mark.asyncio
async def test_create_and_query_relationship():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-REL-001")

    e1 = await svc.add_entity(case.case_id, EntityType.PERSON, "Meera", PersonRole.CALLER)
    e2 = await svc.add_entity(case.case_id, EntityType.LOCATION, "Coimbatore Center")

    rel = await svc.add_relationship(
        case_id=case.case_id,
        source_entity=e1.entity_id,
        relationship_type=RelationshipType.LOCATED_AT,
        target_entity=e2.entity_id,
        claim_status=ClaimStatus.REPORTED,
    )

    assert rel.edge_id.startswith("edge-")
    assert rel.source_entity == e1.entity_id
    assert rel.target_entity == e2.entity_id
    assert rel.superseded_at is None


@pytest.mark.asyncio
async def test_relationship_invalid_endpoints_rejected():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-REL-002")

    e1 = await svc.add_entity(case.case_id, EntityType.PERSON, "Meera", PersonRole.CALLER)

    with pytest.raises(ValueError, match="Target entity.*not found"):
        await svc.add_relationship(
            case_id=case.case_id,
            source_entity=e1.entity_id,
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity="ent-nonexistent",
        )


@pytest.mark.asyncio
async def test_supersede_relationship_preserves_history():
    svc = CaseService(auto_seed=False)
    case = await svc.create_case(case_number="CAS-REL-003")

    e1 = await svc.add_entity(case.case_id, EntityType.PERSON, "Meera", PersonRole.CALLER)
    loc1 = await svc.add_entity(case.case_id, EntityType.LOCATION, "Temporary Shelter")
    loc2 = await svc.add_entity(case.case_id, EntityType.LOCATION, "Permanent Safe Home")

    edge1 = await svc.add_relationship(
        case_id=case.case_id,
        source_entity=e1.entity_id,
        relationship_type=RelationshipType.LOCATED_AT,
        target_entity=loc1.entity_id,
    )

    edge2 = await svc.add_relationship(
        case_id=case.case_id,
        source_entity=e1.entity_id,
        relationship_type=RelationshipType.LOCATED_AT,
        target_entity=loc2.entity_id,
    )

    # Supersede edge1 by edge2
    superseded = await svc.supersede_relationship(
        case_id=case.case_id,
        old_edge_id=edge1.edge_id,
        new_edge_id=edge2.edge_id,
        operator_id="counselor_42",
    )

    assert superseded is not None
    assert superseded.superseded_by == edge2.edge_id
    assert superseded.superseded_at is not None
    assert superseded.valid_to is not None
