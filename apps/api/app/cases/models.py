"""Pydantic models for Case Intelligence & Knowledge Graph subsystem (Phase 11)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field

from app.schemas.events import (
    CaseStatus,
    ClaimStatus,
    EntityType,
    PersonRole,
    RelationshipType,
)


class CaseEvidenceLink(BaseModel):
    """Cryptographic and turn references anchoring nodes and edges to evidence."""

    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "CALL_TRANSCRIPT"  # CALL_TRANSCRIPT, KNOWLEDGE_CITATION, OPERATOR_NOTE, SAFETY_SIGNAL, SYSTEM_EVENT
    source_id: str
    turn_index: Optional[int] = None
    verbatim_excerpt: Optional[str] = None
    citation_ref: Optional[str] = None
    content_hash: Optional[str] = None
    confidence: float = 1.0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseEntity(BaseModel):
    """Graph node representing an individual, location, service, organization, or document."""

    entity_id: str = Field(default_factory=lambda: f"ent-{uuid.uuid4().hex[:12]}")
    case_id: str
    type: EntityType
    role: Optional[Union[PersonRole, str]] = None
    label: str
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    evidence: List[CaseEvidenceLink] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    first_seen: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseRelationship(BaseModel):
    """Directed graph edge representing a connection between two case entities."""

    edge_id: str = Field(default_factory=lambda: f"edge-{uuid.uuid4().hex[:12]}")
    case_id: str
    source_entity: str
    relationship_type: RelationshipType
    target_entity: str
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    evidence: List[CaseEvidenceLink] = Field(default_factory=list)
    valid_from: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    valid_to: Optional[str] = None
    observed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    superseded_at: Optional[str] = None
    superseded_by: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseEvent(BaseModel):
    """Event node representing an explicit occurrence or system assessment in a case."""

    event_id: str = Field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:12]}")
    case_id: str
    event_type: str
    title: str
    summary: str
    severity: Optional[str] = None
    actor_id: Optional[str] = None
    source_type: str = "SYSTEM"  # SYSTEM, OPERATOR, CALLER, SAFETY, SVI, ACOUSTIC, ADAPTIVE, KNOWLEDGE
    evidence_refs: List[str] = Field(default_factory=list)
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseCandidate(BaseModel):
    """Candidate relationship proposed by extraction layer requiring human confirmation."""

    candidate_id: str = Field(default_factory=lambda: f"cand-{uuid.uuid4().hex[:12]}")
    case_id: str
    source_entity: str
    source_label: str
    relationship_type: RelationshipType
    target_entity: str
    target_label: str
    confidence: float = 1.0
    evidence_excerpt: str
    source_turn: Optional[str] = None
    status: str = "PENDING"  # PENDING, CONFIRMED, REJECTED
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseRecord(BaseModel):
    """Aggregate case domain model."""

    case_id: str = Field(default_factory=lambda: f"case-{uuid.uuid4().hex[:10]}")
    case_number: str
    status: CaseStatus = CaseStatus.OPEN
    primary_language: str = "en-IN"
    svi_score: Optional[int] = None
    svi_band: Optional[str] = None
    safety_state: Optional[str] = None
    assigned_operator_id: Optional[str] = None
    consent_recorded: bool = False
    notes_summary: Optional[str] = None
    linked_calls: List[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseGraph(BaseModel):
    """Bounded representation of a case graph for querying and UI rendering."""

    case_id: str
    nodes: List[CaseEntity] = Field(default_factory=list)
    edges: List[CaseRelationship] = Field(default_factory=list)
    candidates: List[CaseCandidate] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    statistics: Dict[str, Any] = Field(default_factory=dict)


# Request & Response API models
class CreateCaseRequest(BaseModel):
    call_id: Optional[str] = None
    case_number: Optional[str] = None
    primary_language: str = "en-IN"
    operator_id: str = "operator"
    initial_notes: Optional[str] = None


class CreateEntityRequest(BaseModel):
    type: EntityType
    label: str
    role: Optional[Union[PersonRole, str]] = None
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateRelationshipRequest(BaseModel):
    source_entity: str
    relationship_type: RelationshipType
    target_entity: str
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class LinkCallRequest(BaseModel):
    call_id: str
    operator_id: str = "operator"
    is_primary: bool = False


class CandidateActionRequest(BaseModel):
    operator_id: str = "operator"
    reason: Optional[str] = None
