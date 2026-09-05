"""Test suite for Case Intelligence domain models and schemas (Phase 11)."""

import pytest
from app.cases.models import (
    CaseCandidate,
    CaseEntity,
    CaseEvent,
    CaseEvidenceLink,
    CaseGraph,
    CaseRecord,
    CaseRelationship,
)
from app.schemas.events import (
    CaseStatus,
    ClaimStatus,
    EntityType,
    PersonRole,
    RelationshipType,
)


def test_case_evidence_link_defaults():
    link = CaseEvidenceLink(
        source_id="call-001",
        verbatim_excerpt="I am staying in Chennai.",
    )
    assert link.link_id is not None
    assert link.source_type == "CALL_TRANSCRIPT"
    assert link.confidence == 1.0
    assert link.created_at is not None


def test_case_entity_creation():
    entity = CaseEntity(
        case_id="case-101",
        type=EntityType.PERSON,
        role=PersonRole.CALLER,
        label="Sunita",
        claim_status=ClaimStatus.REPORTED,
    )
    assert entity.entity_id.startswith("ent-")
    assert entity.label == "Sunita"
    assert entity.role == PersonRole.CALLER
    assert entity.claim_status == ClaimStatus.REPORTED


def test_case_relationship_creation():
    edge = CaseRelationship(
        case_id="case-101",
        source_entity="ent-001",
        relationship_type=RelationshipType.CONNECTED_TO,
        target_entity="ent-002",
        claim_status=ClaimStatus.REPORTED,
    )
    assert edge.edge_id.startswith("edge-")
    assert edge.source_entity == "ent-001"
    assert edge.target_entity == "ent-002"
    assert edge.superseded_at is None


def test_case_candidate_defaults():
    cand = CaseCandidate(
        case_id="case-101",
        source_entity="ent-001",
        source_label="Caller",
        relationship_type=RelationshipType.SUPPORTS,
        target_entity="ent-002",
        target_label="Aunt",
        evidence_excerpt="My aunt helps me.",
    )
    assert cand.candidate_id.startswith("cand-")
    assert cand.status == "PENDING"
    assert cand.confirmed_by is None


def test_case_record_defaults():
    case = CaseRecord(
        case_number="CAS-2026-000001",
    )
    assert case.case_id.startswith("case-")
    assert case.status == CaseStatus.OPEN
    assert case.consent_recorded is False
    assert len(case.linked_calls) == 0


def test_case_graph_aggregation():
    graph = CaseGraph(
        case_id="case-101",
        nodes=[],
        edges=[],
        candidates=[],
    )
    assert graph.total_nodes == 0
    assert graph.total_edges == 0
