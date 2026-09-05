"""Case Intelligence & Knowledge Graph Subsystem (Phase 11)."""

from app.cases.audit import CaseAuditEntry, CaseAuditLogger, get_audit_logger
from app.cases.extraction import (
    extract_entities_and_relationships_from_text,
    sanitize_transcript_for_extraction,
)
from app.cases.graph import extract_subgraph, get_entity_neighbors, verify_integrity
from app.cases.models import (
    CandidateActionRequest,
    CaseCandidate,
    CaseEntity,
    CaseEvent,
    CaseEvidenceLink,
    CaseGraph,
    CaseRecord,
    CaseRelationship,
    CreateCaseRequest,
    CreateEntityRequest,
    CreateRelationshipRequest,
    LinkCallRequest,
)
from app.cases.provenance import (
    compute_evidence_hash,
    create_evidence_link,
    validate_evidence_anchors,
    verify_excerpt_substring,
)
from app.cases.service import CaseService, case_service, get_case_service
from app.cases.temporal import (
    is_edge_active_at,
    parse_iso_datetime,
    sort_events_chronologically,
    supersede_edge,
)

__all__ = [
    "CaseService",
    "case_service",
    "get_case_service",
    "CaseRecord",
    "CaseEntity",
    "CaseRelationship",
    "CaseCandidate",
    "CaseEvent",
    "CaseEvidenceLink",
    "CaseGraph",
    "CreateCaseRequest",
    "CreateEntityRequest",
    "CreateRelationshipRequest",
    "LinkCallRequest",
    "CandidateActionRequest",
    "compute_evidence_hash",
    "create_evidence_link",
    "validate_evidence_anchors",
    "verify_excerpt_substring",
    "is_edge_active_at",
    "parse_iso_datetime",
    "supersede_edge",
    "sort_events_chronologically",
    "extract_subgraph",
    "get_entity_neighbors",
    "verify_integrity",
    "extract_entities_and_relationships_from_text",
    "sanitize_transcript_for_extraction",
    "CaseAuditEntry",
    "CaseAuditLogger",
    "get_audit_logger",
]
