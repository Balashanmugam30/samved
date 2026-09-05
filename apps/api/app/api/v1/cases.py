"""REST API Router for SAMVED Phase 11 Case Intelligence & Knowledge Graph."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.cases.audit import get_audit_logger
from app.cases.graph import get_entity_neighbors
from app.cases.models import (
    CandidateActionRequest,
    CaseCandidate,
    CaseEntity,
    CaseEvent,
    CaseGraph,
    CaseRecord,
    CaseRelationship,
    CreateCaseRequest,
    CreateEntityRequest,
    CreateRelationshipRequest,
    LinkCallRequest,
)
from app.cases.service import case_service
from app.schemas.events import CaseStatus

router = APIRouter(prefix="/cases", tags=["Case Intelligence & Knowledge Graph"])
audit_logger = get_audit_logger()


class CaseStatusResponse(BaseModel):
    status: str
    total_cases: int
    active_cases: int
    default_case_id: Optional[str] = None
    epistemic_mode: str = "EVIDENCE_LINKED_HUMAN_SUPERVISED"
    safety_boundary: str = "ZERO_CRIMINAL_DETERMINATION_NO_AUTONOMOUS_DISPATCH"


class UnlinkCallRequest(BaseModel):
    call_id: str
    operator_id: str = "operator"


class SupersedeRelationshipRequest(BaseModel):
    new_edge_id: str
    operator_id: str = "operator"


@router.get("/status", response_model=CaseStatusResponse)
async def get_case_subsystem_status():
    """Returns operational health, aggregate case counts, and epistemic safety constraints."""
    cases = await case_service.list_cases(limit=1000)
    active_cases = [c for c in cases if c.status in (CaseStatus.ACTIVE, CaseStatus.OPEN)]
    default_case = cases[0].case_id if cases else None

    return CaseStatusResponse(
        status="READY",
        total_cases=len(cases),
        active_cases=len(active_cases),
        default_case_id=default_case,
    )


@router.post("", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
async def create_case_record(request: CreateCaseRequest):
    """Creates a new case record and optionally links an initial intake call."""
    case = await case_service.create_case(
        call_id=request.call_id,
        case_number=request.case_number,
        primary_language=request.primary_language,
        operator_id=request.operator_id,
        initial_notes=request.initial_notes,
    )
    return case


@router.get("", response_model=List[CaseRecord])
async def list_cases(
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
):
    """Lists recent case records with optional status filtering."""
    cases = await case_service.list_cases(limit=limit)
    if status_filter:
        cases = [c for c in cases if c.status.value.upper() == status_filter.upper()]
    return cases


@router.get("/by-call/{call_id}", response_model=CaseRecord)
async def get_case_by_call_id(call_id: str):
    """Retrieves the case record linked to an ongoing or historical call."""
    case = await case_service.get_case_by_call(call_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No case record found linked to call '{call_id}'",
        )
    return case


@router.get("/{case_id}", response_model=CaseRecord)
async def get_case_record(case_id: str):
    """Retrieves a single case record by case_id."""
    case = await case_service.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case record '{case_id}' not found",
        )
    return case


@router.post("/{case_id}/link-call", response_model=CaseRecord)
async def link_call_to_case(case_id: str, request: LinkCallRequest):
    """Links an incoming or ongoing call to an existing case boundary."""
    try:
        case = await case_service.link_call(
            case_id=case_id,
            call_id=request.call_id,
            operator_id=request.operator_id,
            is_primary=request.is_primary,
        )
        return case
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{case_id}/unlink-call", response_model=CaseRecord)
async def unlink_call_from_case(case_id: str, request: UnlinkCallRequest):
    """Unlinks a call from a case boundary."""
    try:
        case = await case_service.unlink_call(
            case_id=case_id,
            call_id=request.call_id,
            operator_id=request.operator_id,
        )
        return case
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{case_id}/graph", response_model=CaseGraph)
async def get_case_graph(
    case_id: str,
    focus: Optional[str] = Query(
        default=None, description="Comma-separated entity IDs to center subgraph on"
    ),
    depth: int = Query(
        default=2, ge=1, le=4, description="Maximum traversal depth (bounded 1-4)"
    ),
    as_of: Optional[str] = Query(
        default=None, description="Historical as-of timestamp (ISO 8601)"
    ),
):
    """Extracts a bounded knowledge graph for the case with optional focus entities and as-of time."""
    focus_entity_ids = [f.strip() for f in focus.split(",") if f.strip()] if focus else None
    graph = await case_service.get_graph(
        case_id=case_id,
        focus_entity_ids=focus_entity_ids,
        max_depth=depth,
        as_of=as_of,
    )
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found",
        )
    return graph


@router.get("/{case_id}/timeline", response_model=List[CaseEvent])
async def get_case_timeline(
    case_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Retrieves chronological case timeline events in reverse order."""
    case = await case_service.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found",
        )
    return await case_service.get_timeline(case_id=case_id, limit=limit)


@router.post("/{case_id}/entities", response_model=CaseEntity, status_code=status.HTTP_201_CREATED)
async def create_case_entity(case_id: str, request: CreateEntityRequest):
    """Creates a new entity node within the case boundary."""
    try:
        entity = await case_service.add_entity(
            case_id=case_id,
            entity_type=request.type,
            label=request.label,
            role=request.role,
            claim_status=request.claim_status,
            confidence=request.confidence,
            source_refs=request.source_refs,
            metadata=request.metadata,
        )
        return entity
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{case_id}/entities/{entity_id}", response_model=CaseEntity)
async def update_case_entity(case_id: str, entity_id: str, updates: Dict[str, Any]):
    """Updates attributes of an existing entity node."""
    entity = await case_service.update_entity(
        case_id=case_id,
        entity_id=entity_id,
        updates=updates,
    )
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in case '{case_id}'",
        )
    return entity


@router.get("/{case_id}/entities/{entity_id}/neighbors")
async def get_entity_neighbors_endpoint(
    case_id: str,
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=4),
    as_of: Optional[str] = Query(default=None),
):
    """Retrieves direct inbound and outbound relationships and connected entities for a node."""
    graph = await case_service.get_graph(case_id=case_id, as_of=as_of)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found",
        )
    return get_entity_neighbors(case_graph=graph, entity_id=entity_id, depth=depth, as_of=as_of)


@router.post("/{case_id}/relationships", response_model=CaseRelationship, status_code=status.HTTP_201_CREATED)
async def create_case_relationship(case_id: str, request: CreateRelationshipRequest):
    """Creates a directed relationship edge between two entities in the case."""
    try:
        edge = await case_service.add_relationship(
            case_id=case_id,
            source_entity=request.source_entity,
            relationship_type=request.relationship_type,
            target_entity=request.target_entity,
            claim_status=request.claim_status,
            confidence=request.confidence,
            source_refs=request.source_refs,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
        )
        return edge
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{case_id}/relationships/{edge_id}/supersede", response_model=CaseRelationship)
async def supersede_relationship_endpoint(
    case_id: str,
    edge_id: str,
    request: SupersedeRelationshipRequest,
):
    """Marks a historical edge as superseded by a newer edge without destroying historical records."""
    edge = await case_service.supersede_relationship(
        case_id=case_id,
        old_edge_id=edge_id,
        new_edge_id=request.new_edge_id,
        operator_id=request.operator_id,
    )
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge '{edge_id}' not found in case '{case_id}'",
        )
    return edge


@router.post("/{case_id}/candidates/{candidate_id}/confirm", response_model=CaseRelationship)
async def confirm_candidate_endpoint(
    case_id: str,
    candidate_id: str,
    request: CandidateActionRequest = CandidateActionRequest(),
):
    """Human counselor confirms a candidate relationship, graduating it to an active graph edge."""
    edge = await case_service.confirm_candidate(
        case_id=case_id,
        candidate_id=candidate_id,
        operator_id=request.operator_id,
    )
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending candidate '{candidate_id}' not found in case '{case_id}'",
        )
    return edge


@router.post("/{case_id}/candidates/{candidate_id}/reject", response_model=CaseCandidate)
async def reject_candidate_endpoint(
    case_id: str,
    candidate_id: str,
    request: CandidateActionRequest = CandidateActionRequest(),
):
    """Human counselor explicitly rejects a proposed candidate relationship."""
    candidate = await case_service.reject_candidate(
        case_id=case_id,
        candidate_id=candidate_id,
        operator_id=request.operator_id,
        reason=request.reason,
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending candidate '{candidate_id}' not found in case '{case_id}'",
        )
    return candidate


@router.get("/{case_id}/integrity")
async def check_case_integrity(case_id: str):
    """Audits graph integrity: dangling edges, temporal anomalies, and evidence hash verification."""
    report = case_service.check_integrity(case_id)
    if not report.get("valid") and "error" in report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=report["error"],
        )
    return report


@router.get("/{case_id}/audit")
async def get_case_audit_logs(
    case_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Retrieves immutable audit records of all mutations and confirmations within the case."""
    entries = audit_logger.get_logs_for_case(case_id=case_id, limit=limit)
    return [e.model_dump() for e in entries]
