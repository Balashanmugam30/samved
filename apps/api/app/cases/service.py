"""CaseService: Central Domain Service for Case Intelligence & Knowledge Graph (Phase 11)."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from app.cases.audit import get_audit_logger
from app.cases.graph import extract_subgraph, verify_integrity
from app.cases.models import (
    CaseCandidate,
    CaseEntity,
    CaseEvent,
    CaseEvidenceLink,
    CaseGraph,
    CaseRecord,
    CaseRelationship,
)
from app.cases.provenance import create_evidence_link, validate_evidence_anchors
from app.cases.temporal import supersede_edge
from app.realtime.connection_manager import manager
from app.schemas.events import (
    CaseStatus,
    ClaimStatus,
    EntityType,
    EventEnvelope,
    EventType,
    PersonRole,
    RelationshipType,
)

logger = logging.getLogger("samved.cases.service")


class CaseService:
    """Thread-safe domain service governing cases, graph entities, relationships, candidates, and events."""

    def __init__(self, auto_seed: bool = True):
        self._cases: Dict[str, CaseRecord] = {}
        self._entities: Dict[str, Dict[str, CaseEntity]] = {}  # case_id -> {entity_id: CaseEntity}
        self._edges: Dict[str, Dict[str, CaseRelationship]] = {}  # case_id -> {edge_id: CaseRelationship}
        self._events: Dict[str, List[CaseEvent]] = {}  # case_id -> List[CaseEvent]
        self._candidates: Dict[str, Dict[str, CaseCandidate]] = {}  # case_id -> {cand_id: CaseCandidate}
        self._call_to_case: Dict[str, str] = {}  # call_id -> case_id
        self._lock = asyncio.Lock()
        self._audit_logger = get_audit_logger()
        self._case_counter = 1000

        if auto_seed:
            self._seed_default_fixtures()

    def _seed_default_fixtures(self) -> None:
        """Seeds standard test cases for immediate operator console and E2E verification."""
        case_id = "case-1001"
        case_number = "CAS-2026-001001"
        call_id = "call-fixture-01"

        case = CaseRecord(
            case_id=case_id,
            case_number=case_number,
            status=CaseStatus.ACTIVE,
            primary_language="en-IN",
            svi_score=42,
            svi_band="ELEVATED",
            safety_state="SAFE",
            assigned_operator_id="operator",
            consent_recorded=True,
            notes_summary="Caller reported family relocation and shelter inquiry.",
            linked_calls=[call_id],
        )
        self._cases[case_id] = case
        self._call_to_case[call_id] = case_id

        # Entities
        e1 = CaseEntity(
            entity_id="ent-1001",
            case_id=case_id,
            type=EntityType.PERSON,
            role=PersonRole.CALLER,
            label="Priya",
            claim_status=ClaimStatus.REPORTED,
            source_refs=[f"call:{call_id}:turn:1"],
            evidence=[
                create_evidence_link(
                    source_type="CALL_TRANSCRIPT",
                    source_id=call_id,
                    turn_index=1,
                    verbatim_excerpt="My name is Priya and I need guidance.",
                )
            ],
            metadata={"caller": True},
        )
        e2 = CaseEntity(
            entity_id="ent-1002",
            case_id=case_id,
            type=EntityType.PERSON,
            role=PersonRole.SUPPORT_PERSON,
            label="Ananya",
            claim_status=ClaimStatus.REPORTED,
            source_refs=[f"call:{call_id}:turn:2"],
            evidence=[
                create_evidence_link(
                    source_type="CALL_TRANSCRIPT",
                    source_id=call_id,
                    turn_index=2,
                    verbatim_excerpt="My sister Ananya called me earlier.",
                )
            ],
            metadata={"relation": "sister"},
        )
        e3 = CaseEntity(
            entity_id="ent-1003",
            case_id=case_id,
            type=EntityType.ORGANIZATION,
            label="Delhi Safe Home",
            claim_status=ClaimStatus.VERIFIED,
            source_refs=["org:delhi_safe_home"],
            metadata={"type": "shelter"},
        )
        e4 = CaseEntity(
            entity_id="ent-1004",
            case_id=case_id,
            type=EntityType.DOCUMENT,
            label="SOP-14566-V3",
            claim_status=ClaimStatus.VERIFIED,
            source_refs=["doc:central_policy_en"],
            metadata={"citation": "NHAA-14566"},
        )

        self._entities[case_id] = {
            e1.entity_id: e1,
            e2.entity_id: e2,
            e3.entity_id: e3,
            e4.entity_id: e4,
        }

        # Relationships
        rel1 = CaseRelationship(
            edge_id="edge-1001",
            case_id=case_id,
            source_entity=e1.entity_id,
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity=e2.entity_id,
            claim_status=ClaimStatus.REPORTED,
            source_refs=[f"call:{call_id}:turn:2"],
            evidence=[
                create_evidence_link(
                    source_type="CALL_TRANSCRIPT",
                    source_id=call_id,
                    turn_index=2,
                    verbatim_excerpt="My sister Ananya called me earlier.",
                )
            ],
        )
        rel2 = CaseRelationship(
            edge_id="edge-1002",
            case_id=case_id,
            source_entity=e1.entity_id,
            relationship_type=RelationshipType.LOCATED_AT,
            target_entity=e3.entity_id,
            claim_status=ClaimStatus.REPORTED,
            source_refs=[f"call:{call_id}:turn:3"],
        )
        self._edges[case_id] = {
            rel1.edge_id: rel1,
            rel2.edge_id: rel2,
        }

        # Candidate
        cand1 = CaseCandidate(
            candidate_id="cand-1001",
            case_id=case_id,
            source_entity=e1.entity_id,
            source_label="Priya",
            relationship_type=RelationshipType.CONNECTED_TO,
            target_entity=e2.entity_id,
            target_label="Ananya",
            evidence_excerpt="My sister Ananya called me earlier.",
            source_turn=f"call:{call_id}:turn:2",
            status="PENDING",
        )
        self._candidates[case_id] = {
            cand1.candidate_id: cand1,
        }

        # Events
        ev1 = CaseEvent(
            event_id="ev-1001",
            case_id=case_id,
            event_type="CASE_CREATED",
            title="Case Record Initialized",
            summary="Case created from intake call.",
            source_type="SYSTEM",
        )
        ev2 = CaseEvent(
            event_id="ev-1002",
            case_id=case_id,
            event_type="SAFETY_SIGNAL",
            title="Safety Assessment: SAFE",
            summary="Deterministic Safety Engine evaluated Level 0 (SAFE).",
            severity="LOW",
            source_type="SAFETY",
            claim_status=ClaimStatus.VERIFIED,
        )
        ev3 = CaseEvent(
            event_id="ev-1003",
            case_id=case_id,
            event_type="SVI_SIGNAL",
            title="SVI Assessment: ELEVATED",
            summary="SVI Score 42 (ELEVATED), key factor: relocation distress.",
            severity="MEDIUM",
            source_type="SVI",
            claim_status=ClaimStatus.VERIFIED,
        )
        self._events[case_id] = [ev1, ev2, ev3]

    async def _emit_event(
        self,
        event_type: EventType,
        call_id: Optional[str],
        payload: Dict[str, Any],
    ) -> None:
        """Broadcasts a case event envelope to active operator console WebSockets."""
        envelope = EventEnvelope(
            event_id=str(uuid.uuid4()),
            session_id=call_id or "system",
            call_id=call_id or "system",
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
        try:
            await manager.broadcast_to_operators(envelope)
        except Exception as e:
            logger.debug(f"Event broadcast exception: {e}")

    async def create_case(
        self,
        call_id: Optional[str] = None,
        case_number: Optional[str] = None,
        primary_language: str = "en-IN",
        operator_id: str = "operator",
        initial_notes: Optional[str] = None,
    ) -> CaseRecord:
        """Creates a new case record and optionally links an initial call."""
        async with self._lock:
            self._case_counter += 1
            generated_number = case_number or f"CAS-2026-{self._case_counter:06d}"
            case_id = f"case-{uuid.uuid4().hex[:10]}"

            linked_calls = [call_id] if call_id else []

            case = CaseRecord(
                case_id=case_id,
                case_number=generated_number,
                status=CaseStatus.ACTIVE if call_id else CaseStatus.OPEN,
                primary_language=primary_language,
                assigned_operator_id=operator_id,
                notes_summary=initial_notes,
                linked_calls=linked_calls,
            )

            self._cases[case_id] = case
            self._entities[case_id] = {}
            self._edges[case_id] = {}
            self._events[case_id] = []
            self._candidates[case_id] = {}

            if call_id:
                self._call_to_case[call_id] = case_id

            # Initial creation event
            ev = CaseEvent(
                case_id=case_id,
                event_type="CASE_CREATED",
                title="Case Initialized",
                summary=f"Case {generated_number} created by {operator_id}.",
                source_type="OPERATOR" if operator_id != "system" else "SYSTEM",
            )
            self._events[case_id].append(ev)

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_CREATED",
                actor_id=operator_id,
                details={"case_number": generated_number, "call_id": call_id},
            )

        await self._emit_event(
            EventType.CASE_CREATED,
            call_id,
            {"case_id": case_id, "case_number": generated_number, "status": case.status.value},
        )
        return case

    async def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """Retrieves a case record by case_id."""
        async with self._lock:
            return self._cases.get(case_id)

    async def get_case_by_call(self, call_id: str) -> Optional[CaseRecord]:
        """Retrieves the case record associated with a given call_id."""
        async with self._lock:
            case_id = self._call_to_case.get(call_id)
            if case_id:
                return self._cases.get(case_id)
            return None

    async def list_cases(self, limit: int = 50) -> List[CaseRecord]:
        """Lists active case records."""
        async with self._lock:
            return list(self._cases.values())[:limit]

    async def link_call(
        self,
        case_id: str,
        call_id: str,
        operator_id: str = "operator",
        is_primary: bool = False,
    ) -> CaseRecord:
        """Links an incoming or ongoing call to an existing case."""
        async with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise ValueError(f"Case '{case_id}' not found")

            if call_id not in case.linked_calls:
                if is_primary:
                    case.linked_calls.insert(0, call_id)
                else:
                    case.linked_calls.append(call_id)
                case.updated_at = datetime.now(timezone.utc).isoformat()

            self._call_to_case[call_id] = case_id

            ev = CaseEvent(
                case_id=case_id,
                event_type="CASE_CALL_LINKED",
                title="Call Linked to Case",
                summary=f"Call {call_id} linked to case {case.case_number}.",
                actor_id=operator_id,
                source_type="OPERATOR",
            )
            self._events.setdefault(case_id, []).append(ev)

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_CALL_LINKED",
                actor_id=operator_id,
                details={"call_id": call_id, "is_primary": is_primary},
            )

        await self._emit_event(
            EventType.CASE_CALL_LINKED,
            call_id,
            {"case_id": case_id, "call_id": call_id},
        )
        return case

    async def unlink_call(
        self,
        case_id: str,
        call_id: str,
        operator_id: str = "operator",
    ) -> CaseRecord:
        """Unlinks a call from a case."""
        async with self._lock:
            case = self._cases.get(case_id)
            if not case:
                raise ValueError(f"Case '{case_id}' not found")

            if call_id in case.linked_calls:
                case.linked_calls.remove(call_id)
                case.updated_at = datetime.now(timezone.utc).isoformat()

            if self._call_to_case.get(call_id) == case_id:
                del self._call_to_case[call_id]

            ev = CaseEvent(
                case_id=case_id,
                event_type="CASE_CALL_UNLINKED",
                title="Call Unlinked from Case",
                summary=f"Call {call_id} unlinked from case {case.case_number}.",
                actor_id=operator_id,
                source_type="OPERATOR",
            )
            self._events.setdefault(case_id, []).append(ev)

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_CALL_UNLINKED",
                actor_id=operator_id,
                details={"call_id": call_id},
            )

        await self._emit_event(
            EventType.CASE_CALL_UNLINKED,
            call_id,
            {"case_id": case_id, "call_id": call_id},
        )
        return case

    async def add_entity(
        self,
        case_id: str,
        entity_type: EntityType,
        label: str,
        role: Optional[Union[PersonRole, str]] = None,
        claim_status: ClaimStatus = ClaimStatus.REPORTED,
        confidence: float = 1.0,
        source_refs: Optional[List[str]] = None,
        evidence: Optional[List[CaseEvidenceLink]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        operator_id: str = "operator",
    ) -> CaseEntity:
        """Adds a graph node entity to the case boundary."""
        async with self._lock:
            if case_id not in self._cases:
                raise ValueError(f"Case '{case_id}' not found")

            cleaned_role = role
            if isinstance(role, str) and role.upper() in ("OFFENDER", "GUILTY", "PERPETRATOR"):
                cleaned_role = PersonRole.REPORTED_ACTOR

            entity = CaseEntity(
                case_id=case_id,
                type=entity_type,
                role=cleaned_role,
                label=label.strip(),
                claim_status=claim_status,
                confidence=confidence,
                source_refs=source_refs or [],
                evidence=evidence or [],
                metadata=metadata or {},
            )

            self._entities.setdefault(case_id, {})[entity.entity_id] = entity

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_ENTITY_CREATED",
                actor_id=operator_id,
                details={"entity_id": entity.entity_id, "label": entity.label, "type": entity.type.value},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_ENTITY_CREATED,
            call_id,
            {"case_id": case_id, "entity": entity.model_dump()},
        )
        return entity

    async def update_entity(
        self,
        case_id: str,
        entity_id: str,
        updates: Dict[str, Any],
        operator_id: str = "operator",
    ) -> Optional[CaseEntity]:
        """Updates attributes of an existing entity node."""
        async with self._lock:
            case_entities = self._entities.get(case_id, {})
            entity = case_entities.get(entity_id)
            if not entity:
                return None

            for k, v in updates.items():
                if hasattr(entity, k) and k not in ("entity_id", "case_id", "created_at"):
                    setattr(entity, k, v)
            entity.updated_at = datetime.now(timezone.utc).isoformat()

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_ENTITY_UPDATED",
                actor_id=operator_id,
                details={"entity_id": entity_id, "updates": list(updates.keys())},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_ENTITY_UPDATED,
            call_id,
            {"case_id": case_id, "entity": entity.model_dump()},
        )
        return entity

    async def add_relationship(
        self,
        case_id: str,
        source_entity: str,
        relationship_type: RelationshipType,
        target_entity: str,
        claim_status: ClaimStatus = ClaimStatus.REPORTED,
        confidence: float = 1.0,
        source_refs: Optional[List[str]] = None,
        evidence: Optional[List[CaseEvidenceLink]] = None,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        operator_id: str = "operator",
    ) -> CaseRelationship:
        """Creates a directed relationship edge between two entities within a case."""
        async with self._lock:
            if case_id not in self._cases:
                raise ValueError(f"Case '{case_id}' not found")

            case_entities = self._entities.get(case_id, {})
            if source_entity not in case_entities:
                raise ValueError(f"Source entity '{source_entity}' not found in case '{case_id}'")
            if target_entity not in case_entities:
                raise ValueError(f"Target entity '{target_entity}' not found in case '{case_id}'")

            edge = CaseRelationship(
                case_id=case_id,
                source_entity=source_entity,
                relationship_type=relationship_type,
                target_entity=target_entity,
                claim_status=claim_status,
                confidence=confidence,
                source_refs=source_refs or [],
                evidence=evidence or [],
                valid_from=valid_from or datetime.now(timezone.utc).isoformat(),
                valid_to=valid_to,
            )

            self._edges.setdefault(case_id, {})[edge.edge_id] = edge

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_RELATIONSHIP_CREATED",
                actor_id=operator_id,
                details={
                    "edge_id": edge.edge_id,
                    "type": edge.relationship_type.value,
                    "source": edge.source_entity,
                    "target": edge.target_entity,
                },
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_RELATIONSHIP_CREATED,
            call_id,
            {"case_id": case_id, "relationship": edge.model_dump()},
        )
        return edge

    async def supersede_relationship(
        self,
        case_id: str,
        old_edge_id: str,
        new_edge_id: str,
        operator_id: str = "operator",
    ) -> Optional[CaseRelationship]:
        """Marks an edge as superseded by a new edge, preserving historical truth."""
        async with self._lock:
            case_edges = self._edges.get(case_id, {})
            old_edge = case_edges.get(old_edge_id)
            if not old_edge:
                return None

            supersede_edge(old_edge, new_edge_id)

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_RELATIONSHIP_SUPERSEDED",
                actor_id=operator_id,
                details={"old_edge_id": old_edge_id, "new_edge_id": new_edge_id},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_RELATIONSHIP_SUPERSEDED,
            call_id,
            {"case_id": case_id, "old_edge_id": old_edge_id, "new_edge_id": new_edge_id},
        )
        return old_edge

    async def add_candidate(
        self,
        case_id: str,
        source_entity: str,
        source_label: str,
        relationship_type: RelationshipType,
        target_entity: str,
        target_label: str,
        evidence_excerpt: str,
        source_turn: Optional[str] = None,
        confidence: float = 1.0,
    ) -> CaseCandidate:
        """Stores a candidate relationship proposed by extraction layer requiring human confirmation."""
        async with self._lock:
            if case_id not in self._cases:
                raise ValueError(f"Case '{case_id}' not found")

            cand = CaseCandidate(
                case_id=case_id,
                source_entity=source_entity,
                source_label=source_label,
                relationship_type=relationship_type,
                target_entity=target_entity,
                target_label=target_label,
                evidence_excerpt=evidence_excerpt,
                source_turn=source_turn,
                confidence=confidence,
                status="PENDING",
            )
            self._candidates.setdefault(case_id, {})[cand.candidate_id] = cand

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_ENTITY_CANDIDATE_CREATED",
                actor_id="extraction_worker",
                details={"candidate_id": cand.candidate_id, "type": cand.relationship_type.value},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_ENTITY_CANDIDATE_CREATED,
            call_id,
            {"case_id": case_id, "candidate": cand.model_dump()},
        )
        return cand

    async def confirm_candidate(
        self,
        case_id: str,
        candidate_id: str,
        operator_id: str = "operator",
    ) -> Optional[CaseRelationship]:
        """Tele-counselor confirms a candidate relationship, graduating it into an active graph edge."""
        async with self._lock:
            case_cands = self._candidates.get(case_id, {})
            cand = case_cands.get(candidate_id)
            if not cand or cand.status != "PENDING":
                return None

            cand.status = "CONFIRMED"
            cand.confirmed_by = operator_id
            cand.confirmed_at = datetime.now(timezone.utc).isoformat()

            case_entities = self._entities.setdefault(case_id, {})
            if cand.source_entity not in case_entities:
                case_entities[cand.source_entity] = CaseEntity(
                    entity_id=cand.source_entity,
                    case_id=case_id,
                    type=EntityType.PERSON,
                    label=cand.source_label,
                    claim_status=ClaimStatus.REPORTED,
                )
            if cand.target_entity not in case_entities:
                case_entities[cand.target_entity] = CaseEntity(
                    entity_id=cand.target_entity,
                    case_id=case_id,
                    type=EntityType.PERSON,
                    label=cand.target_label,
                    claim_status=ClaimStatus.REPORTED,
                )

            evidence_link = create_evidence_link(
                source_type="CALL_TRANSCRIPT",
                source_id=cand.source_turn or "transcript",
                verbatim_excerpt=cand.evidence_excerpt,
                confidence=cand.confidence,
            )

            edge = CaseRelationship(
                case_id=case_id,
                source_entity=cand.source_entity,
                relationship_type=cand.relationship_type,
                target_entity=cand.target_entity,
                claim_status=ClaimStatus.REPORTED,
                confidence=cand.confidence,
                source_refs=[cand.source_turn] if cand.source_turn else [],
                evidence=[evidence_link],
            )
            self._edges.setdefault(case_id, {})[edge.edge_id] = edge

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_RELATIONSHIP_CONFIRMED",
                actor_id=operator_id,
                details={"candidate_id": candidate_id, "edge_id": edge.edge_id},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_RELATIONSHIP_CONFIRMED,
            call_id,
            {"case_id": case_id, "candidate_id": candidate_id, "edge": edge.model_dump()},
        )
        return edge

    async def reject_candidate(
        self,
        case_id: str,
        candidate_id: str,
        operator_id: str = "operator",
        reason: Optional[str] = None,
    ) -> Optional[CaseCandidate]:
        """Tele-counselor explicitly rejects a proposed candidate relationship."""
        async with self._lock:
            case_cands = self._candidates.get(case_id, {})
            cand = case_cands.get(candidate_id)
            if not cand or cand.status != "PENDING":
                return None

            cand.status = "REJECTED"
            cand.confirmed_by = operator_id
            cand.confirmed_at = datetime.now(timezone.utc).isoformat()

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_RELATIONSHIP_REJECTED",
                actor_id=operator_id,
                details={"candidate_id": candidate_id, "reason": reason},
            )

        call_id = self._cases[case_id].linked_calls[0] if self._cases[case_id].linked_calls else None
        await self._emit_event(
            EventType.CASE_RELATIONSHIP_REJECTED,
            call_id,
            {"case_id": case_id, "candidate_id": candidate_id, "reason": reason},
        )
        return cand

    async def add_event(
        self,
        case_id: str,
        event_type: str,
        title: str,
        summary: str,
        severity: Optional[str] = None,
        actor_id: Optional[str] = None,
        source_type: str = "SYSTEM",
        evidence_refs: Optional[List[str]] = None,
        claim_status: ClaimStatus = ClaimStatus.REPORTED,
    ) -> CaseEvent:
        """Records an event node in the case chronological timeline."""
        async with self._lock:
            if case_id not in self._cases:
                raise ValueError(f"Case '{case_id}' not found")

            ev = CaseEvent(
                case_id=case_id,
                event_type=event_type,
                title=title,
                summary=summary,
                severity=severity,
                actor_id=actor_id,
                source_type=source_type,
                evidence_refs=evidence_refs or [],
                claim_status=claim_status,
            )
            self._events.setdefault(case_id, []).append(ev)

            self._audit_logger.log(
                case_id=case_id,
                action="CASE_EVENT_RECORDED",
                actor_id=actor_id or source_type,
                details={"event_id": ev.event_id, "type": event_type, "title": title},
            )
        return ev

    async def get_graph(
        self,
        case_id: str,
        focus_entity_ids: Optional[List[str]] = None,
        max_depth: int = 2,
        as_of: Optional[str] = None,
    ) -> Optional[CaseGraph]:
        """Returns the bounded knowledge graph representation for a case."""
        async with self._lock:
            if case_id not in self._cases:
                return None

            nodes = list(self._entities.get(case_id, {}).values())
            edges = list(self._edges.get(case_id, {}).values())
            candidates = list(self._candidates.get(case_id, {}).values())

            full_graph = CaseGraph(
                case_id=case_id,
                nodes=nodes,
                edges=edges,
                candidates=candidates,
                total_nodes=len(nodes),
                total_edges=len(edges),
            )

        return extract_subgraph(
            case_graph=full_graph,
            focus_entity_ids=focus_entity_ids,
            max_depth=max_depth,
            as_of=as_of,
        )

    async def get_timeline(self, case_id: str, limit: int = 50) -> List[CaseEvent]:
        """Retrieves chronological events for a case."""
        async with self._lock:
            events = self._events.get(case_id, [])
            return list(reversed(events))[:limit]

    async def record_safety_event(
        self,
        call_id: str,
        safety_rule: str,
        action: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[CaseEvent]:
        """Records a read-only safety evaluation event linking to the case."""
        case = await self.get_case_by_call(call_id)
        if not case:
            return None

        async with self._lock:
            case.safety_state = severity
            case.updated_at = datetime.now(timezone.utc).isoformat()

        return await self.add_event(
            case_id=case.case_id,
            event_type="SAFETY_SIGNAL",
            title=f"Safety Check: {safety_rule}",
            summary=f"Deterministic Safety action: {action}. Level: {severity}.",
            severity=severity,
            source_type="SAFETY",
            evidence_refs=[f"call:{call_id}"],
            claim_status=ClaimStatus.VERIFIED,
        )

    async def record_svi_event(
        self,
        call_id: str,
        svi_score: int,
        band: str,
        factors: Optional[List[str]] = None,
    ) -> Optional[CaseEvent]:
        """Records a read-only SVI assessment event linking to the case."""
        case = await self.get_case_by_call(call_id)
        if not case:
            return None

        async with self._lock:
            case.svi_score = svi_score
            case.svi_band = band
            case.updated_at = datetime.now(timezone.utc).isoformat()

        factors_text = ", ".join(factors) if factors else "composite signals"
        return await self.add_event(
            case_id=case.case_id,
            event_type="SVI_SIGNAL",
            title=f"SVI Assessment: {band} ({svi_score})",
            summary=f"Vulnerability score: {svi_score}/100. Factors: {factors_text}.",
            severity=band,
            source_type="SVI",
            evidence_refs=[f"call:{call_id}"],
            claim_status=ClaimStatus.VERIFIED,
        )

    async def record_acoustic_event(
        self,
        call_id: str,
        valence: float,
        arousal: float,
        distress: float,
        primary_emotion: str,
    ) -> Optional[CaseEvent]:
        """Records acoustic biomarkers as an unalterable chronological event."""
        case = await self.get_case_by_call(call_id)
        if not case:
            return None

        return await self.add_event(
            case_id=case.case_id,
            event_type="ACOUSTIC_SIGNAL",
            title=f"Acoustic Telemetry: {primary_emotion}",
            summary=f"Distress: {distress:.2f}, Valence: {valence:.2f}, Arousal: {arousal:.2f}.",
            source_type="ACOUSTIC",
            evidence_refs=[f"call:{call_id}"],
            claim_status=ClaimStatus.OBSERVED,
        )

    async def record_knowledge_citation(
        self,
        call_id: str,
        citation_ref: str,
        source_id: str,
        title: str,
        excerpt: str,
    ) -> Optional[CaseEvent]:
        """Links an authoritative knowledge citation consulted during the call to the case graph."""
        case = await self.get_case_by_call(call_id)
        if not case:
            return None

        async with self._lock:
            existing_docs = [
                e for e in self._entities.get(case.case_id, {}).values()
                if e.type == EntityType.DOCUMENT and e.label == title
            ]
            if not existing_docs:
                doc_entity = CaseEntity(
                    case_id=case.case_id,
                    type=EntityType.DOCUMENT,
                    label=title,
                    claim_status=ClaimStatus.VERIFIED,
                    source_refs=[f"citation:{citation_ref}"],
                    metadata={"source_id": source_id, "excerpt": excerpt[:200]},
                )
                self._entities.setdefault(case.case_id, {})[doc_entity.entity_id] = doc_entity

        return await self.add_event(
            case_id=case.case_id,
            event_type="KNOWLEDGE_CITATION",
            title=f"Citation: {title}",
            summary=f"Ref: {citation_ref}. Excerpt: {excerpt[:120]}...",
            source_type="KNOWLEDGE",
            evidence_refs=[f"citation:{citation_ref}"],
            claim_status=ClaimStatus.VERIFIED,
        )

    def check_integrity(self, case_id: str) -> Dict[str, Any]:
        """Audits graph integrity for the specified case."""
        if case_id not in self._cases:
            return {"valid": False, "error": f"Case '{case_id}' not found"}

        nodes = list(self._entities.get(case_id, {}).values())
        edges = list(self._edges.get(case_id, {}).values())
        candidates = list(self._candidates.get(case_id, {}).values())

        cg = CaseGraph(
            case_id=case_id,
            nodes=nodes,
            edges=edges,
            candidates=candidates,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )
        return verify_integrity(cg)


case_service = CaseService(auto_seed=True)


def get_case_service() -> CaseService:
    """Returns the singleton CaseService instance."""
    return case_service
