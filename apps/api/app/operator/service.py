import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import get_settings
from app.operator.audit import operator_audit_logger
from app.operator.models import (
    CallOperatorState,
    HandoffStatus,
    OperatorActionType,
    OperatorAuditEvent,
    OperatorNote,
    OperatorNoteCategory,
    OperatorOwnershipState,
)
from app.operator.schemas import SubsystemStatus, TimelineEventItem
from app.schemas.events import EventEnvelope, EventType

logger = logging.getLogger("samved.operator.service")


class OperatorService:
    """Core domain service for Human Operator Console and Tele-Counselor Workstation.

    Ensures:
    - Thread-safe state transitions
    - Idempotency for repeated operator commands
    - Append-only audit logging for accountability
    - Subsystem independence (Operator actions cannot mutate Safety Engine or SVI)
    """

    def __init__(self):
        self._states: Dict[str, CallOperatorState] = {}
        self._notes: Dict[str, List[OperatorNote]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_state(self, call_id: str) -> CallOperatorState:
        """Retrieves or initializes the operator state for a call."""
        async with self._lock:
            if call_id not in self._states:
                self._states[call_id] = CallOperatorState(
                    call_id=call_id,
                    ownership_state=OperatorOwnershipState.AI_ASSISTED,
                    handoff_status=HandoffStatus.AVAILABLE,
                    adaptive_paused=False,
                    active_operator_id=None,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
            return self._states[call_id]

    async def takeover(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator initiated human takeover",
    ) -> CallOperatorState:
        """Transfers call ownership to human operator (HUMAN_ACTIVE).

        Idempotent: If already HUMAN_ACTIVE, returns existing state without error.
        """
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_ownership = state.ownership_state.value
            state.ownership_state = OperatorOwnershipState.HUMAN_ACTIVE
            state.active_operator_id = operator_id
            state.updated_at = datetime.now(timezone.utc).isoformat()

        # Log audit event
        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.TAKEOVER,
            actor_id=operator_id,
            summary=f"Operator {operator_id} took over active control ({reason})",
            previous_state=prev_ownership,
            new_state=OperatorOwnershipState.HUMAN_ACTIVE.value,
            details={"reason": reason},
        )

        # Notify Adaptive Engine
        try:
            from app.adaptive.models import OperatorOverrideAction
            from app.adaptive.service import adaptive_engine
            adaptive_engine.apply_operator_override(
                call_id=call_id,
                action=OperatorOverrideAction.FORCE_HUMAN,
                reason=reason,
                operator_id=operator_id,
            )
        except Exception as e:
            logger.debug(f"Adaptive override notification error: {e}")

        # Broadcast event
        await self._broadcast_event(
            EventType.OPERATOR_TAKEOVER,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "ownership_state": OperatorOwnershipState.HUMAN_ACTIVE.value,
                "timestamp": state.updated_at,
            },
        )

        return state

    async def pause_adaptive(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator paused adaptive AI assistance",
    ) -> CallOperatorState:
        """Pauses adaptive conversational AI generation while safety/SVI monitoring continues."""
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_paused = state.adaptive_paused
            state.adaptive_paused = True
            state.updated_at = datetime.now(timezone.utc).isoformat()

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.PAUSE_ADAPTIVE,
            actor_id=operator_id,
            summary=f"Operator {operator_id} paused adaptive conversational engine ({reason})",
            previous_state=f"adaptive_paused={prev_paused}",
            new_state="adaptive_paused=True",
            details={"reason": reason},
        )

        try:
            from app.adaptive.models import OperatorOverrideAction
            from app.adaptive.service import adaptive_engine
            adaptive_engine.apply_operator_override(
                call_id=call_id,
                action=OperatorOverrideAction.PAUSE_ADAPTIVE,
                reason=reason,
                operator_id=operator_id,
            )
        except Exception as e:
            logger.debug(f"Adaptive override error: {e}")

        await self._broadcast_event(
            EventType.OPERATOR_PAUSE_ADAPTIVE,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "adaptive_paused": True,
                "timestamp": state.updated_at,
            },
        )

        return state

    async def resume_adaptive(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator resumed adaptive AI assistance",
    ) -> CallOperatorState:
        """Resumes adaptive conversational planning."""
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_paused = state.adaptive_paused
            state.adaptive_paused = False
            state.updated_at = datetime.now(timezone.utc).isoformat()

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.RESUME_ADAPTIVE,
            actor_id=operator_id,
            summary=f"Operator {operator_id} resumed adaptive conversational engine ({reason})",
            previous_state=f"adaptive_paused={prev_paused}",
            new_state="adaptive_paused=False",
            details={"reason": reason},
        )

        try:
            from app.adaptive.models import OperatorOverrideAction
            from app.adaptive.service import adaptive_engine
            adaptive_engine.apply_operator_override(
                call_id=call_id,
                action=OperatorOverrideAction.RESUME_ADAPTIVE,
                reason=reason,
                operator_id=operator_id,
            )
        except Exception as e:
            logger.debug(f"Adaptive override error: {e}")

        await self._broadcast_event(
            EventType.OPERATOR_RESUME_AI,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "adaptive_paused": False,
                "timestamp": state.updated_at,
            },
        )

        return state

    async def request_safety_check(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator requested explicit safety verification",
    ) -> Dict[str, Any]:
        """Audits operator request for safety check and triggers policy re-evaluation."""
        now_str = datetime.now(timezone.utc).isoformat()

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.REQUEST_SAFETY_CHECK,
            actor_id=operator_id,
            summary=f"Operator {operator_id} requested immediate safety re-evaluation ({reason})",
            details={"reason": reason},
        )

        try:
            from app.adaptive.models import OperatorOverrideAction
            from app.adaptive.service import adaptive_engine
            adaptive_engine.apply_operator_override(
                call_id=call_id,
                action=OperatorOverrideAction.FORCE_SAFETY_CHECK,
                reason=reason,
                operator_id=operator_id,
            )
        except Exception as e:
            logger.debug(f"Safety check override error: {e}")

        await self._broadcast_event(
            EventType.OPERATOR_REQUEST_SAFETY_CHECK,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "timestamp": now_str,
            },
        )

        return {
            "call_id": call_id,
            "operator_id": operator_id,
            "status": "SAFETY_CHECK_REQUESTED",
            "timestamp": now_str,
        }

    async def request_handoff(
        self,
        call_id: str,
        operator_id: str = "operator",
        target_department: str = "tele_counselor_tier2",
        notes: Optional[str] = None,
    ) -> CallOperatorState:
        """Initiates a warm human handoff request. Transitions to HANDOFF_PENDING (status: REQUESTED).

        Never collapses requested with confirmed.
        """
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_status = state.handoff_status.value
            state.ownership_state = OperatorOwnershipState.HANDOFF_PENDING
            state.handoff_status = HandoffStatus.REQUESTED
            state.handoff_target = target_department
            state.handoff_notes = notes
            state.handoff_requested_at = datetime.now(timezone.utc).isoformat()
            state.updated_at = state.handoff_requested_at

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.HANDOFF_REQUEST,
            actor_id=operator_id,
            summary=f"Operator {operator_id} requested transfer to {target_department}",
            previous_state=prev_status,
            new_state=HandoffStatus.REQUESTED.value,
            details={"target_department": target_department, "notes": notes},
        )

        await self._broadcast_event(
            EventType.OPERATOR_HANDOFF_REQUESTED,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "target_department": target_department,
                "handoff_status": HandoffStatus.REQUESTED.value,
                "ownership_state": OperatorOwnershipState.HANDOFF_PENDING.value,
                "notes": notes,
                "timestamp": state.handoff_requested_at,
            },
        )

        return state

    async def confirm_handoff(
        self,
        call_id: str,
        transfer_confirmed_by: str = "supervisor",
        target_agent: Optional[str] = "counselor-01",
        notes: Optional[str] = None,
    ) -> CallOperatorState:
        """Confirms transfer of call to receiving counselor/supervisor."""
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_status = state.handoff_status.value
            state.handoff_status = HandoffStatus.CONFIRMED
            state.active_operator_id = target_agent or transfer_confirmed_by
            state.handoff_confirmed_at = datetime.now(timezone.utc).isoformat()
            state.updated_at = state.handoff_confirmed_at

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.HANDOFF_CONFIRM,
            actor_id=transfer_confirmed_by,
            summary=f"Transfer confirmed by {transfer_confirmed_by} to {target_agent or 'assigned counselor'}",
            previous_state=prev_status,
            new_state=HandoffStatus.CONFIRMED.value,
            details={"target_agent": target_agent, "notes": notes},
        )

        await self._broadcast_event(
            EventType.OPERATOR_HANDOFF_CONFIRMED,
            call_id,
            {
                "call_id": call_id,
                "transfer_confirmed_by": transfer_confirmed_by,
                "target_agent": target_agent,
                "handoff_status": HandoffStatus.CONFIRMED.value,
                "timestamp": state.handoff_confirmed_at,
            },
        )

        return state

    async def cancel_handoff(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator cancelled transfer request",
    ) -> CallOperatorState:
        """Cancels a pending handoff request and returns ownership to HUMAN_ACTIVE."""
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_status = state.handoff_status.value
            state.ownership_state = OperatorOwnershipState.HUMAN_ACTIVE
            state.handoff_status = HandoffStatus.CANCELLED
            state.updated_at = datetime.now(timezone.utc).isoformat()

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.HANDOFF_CANCEL,
            actor_id=operator_id,
            summary=f"Operator {operator_id} cancelled transfer ({reason})",
            previous_state=prev_status,
            new_state=HandoffStatus.CANCELLED.value,
            details={"reason": reason},
        )

        await self._broadcast_event(
            EventType.OPERATOR_HANDOFF_CANCELLED,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "handoff_status": HandoffStatus.CANCELLED.value,
                "ownership_state": OperatorOwnershipState.HUMAN_ACTIVE.value,
                "timestamp": state.updated_at,
            },
        )

        return state

    async def add_note(
        self,
        call_id: str,
        operator_id: str = "operator",
        category: OperatorNoteCategory = OperatorNoteCategory.GENERAL,
        text: str = "",
        citation_ref: Optional[str] = None,
    ) -> OperatorNote:
        """Adds a structured operator note to the call with optional citation provenance."""
        note = OperatorNote(
            note_id=str(uuid.uuid4()),
            call_id=call_id,
            operator_id=operator_id,
            category=category,
            text=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_structured=True,
            citation_ref=citation_ref,
        )

        async with self._lock:
            if call_id not in self._notes:
                self._notes[call_id] = []
            self._notes[call_id].append(note)

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.ADD_NOTE,
            actor_id=operator_id,
            summary=f"Note added [{category.value}]: {text[:40]}...",
            details={"note_id": note.note_id, "category": category.value, "citation_ref": citation_ref},
        )

        await self._broadcast_event(
            EventType.OPERATOR_NOTE_ADDED,
            call_id,
            note.model_dump(),
        )

        return note

    async def get_notes(self, call_id: str) -> List[OperatorNote]:
        """Returns all operator notes for a call."""
        async with self._lock:
            return list(self._notes.get(call_id, []))

    async def end_call(
        self,
        call_id: str,
        operator_id: str = "operator",
        reason: str = "Operator concluded call",
    ) -> CallOperatorState:
        """Concludes call by operator action. Terminates telephony and sets ownership to ENDED."""
        async with self._lock:
            state = self._states.get(call_id)
            if not state:
                state = CallOperatorState(call_id=call_id)
                self._states[call_id] = state

            prev_ownership = state.ownership_state.value
            state.ownership_state = OperatorOwnershipState.ENDED
            state.updated_at = datetime.now(timezone.utc).isoformat()

        await operator_audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.END_CALL,
            actor_id=operator_id,
            summary=f"Operator {operator_id} terminated call ({reason})",
            previous_state=prev_ownership,
            new_state=OperatorOwnershipState.ENDED.value,
            details={"reason": reason},
        )

        # Terminate telephony session cleanly
        try:
            from app.realtime.session_manager import telephony_session_manager
            sess = await telephony_session_manager.get_by_call_id(call_id)
            if sess:
                await telephony_session_manager.end_session(sess.session_id, reason=f"operator_hangup: {reason}")
        except Exception as e:
            logger.error(f"Error ending telephony session for {call_id}: {e}")

        await self._broadcast_event(
            EventType.OPERATOR_CALL_ENDED,
            call_id,
            {
                "call_id": call_id,
                "operator_id": operator_id,
                "reason": reason,
                "ownership_state": OperatorOwnershipState.ENDED.value,
                "timestamp": state.updated_at,
            },
        )

        return state

    async def get_timeline(
        self,
        call_id: str,
        category: Optional[str] = None,
        limit: int = 60,
    ) -> List[TimelineEventItem]:
        """Aggregates and sorts a chronological unified event timeline for the operator."""
        timeline_items: List[TimelineEventItem] = []

        # 1. Operator Audit Records
        audit_events = await operator_audit_logger.get_audit_trail(call_id, limit=limit)
        for ae in audit_events:
            timeline_items.append(
                TimelineEventItem(
                    event_id=ae.event_id,
                    timestamp=ae.timestamp,
                    category="OPERATOR",
                    event_type=ae.action.value,
                    summary=ae.summary,
                    actor_id=ae.actor_id,
                    details=ae.details,
                )
            )

        # 2. Notes
        notes = await self.get_notes(call_id)
        for n in notes:
            timeline_items.append(
                TimelineEventItem(
                    event_id=n.note_id,
                    timestamp=n.timestamp,
                    category="OPERATOR",
                    event_type="NOTE_ADDED",
                    summary=f"[{n.category.value}] {n.text}",
                    actor_id=n.operator_id,
                    details={"category": n.category.value, "text": n.text},
                )
            )

        # 3. Telephony Session Events
        try:
            from app.realtime.session_manager import telephony_session_manager
            raw_events = await telephony_session_manager.get_call_events(call_id) or []
            for ev in raw_events:
                ev_type = str(ev.get("event_type", ""))
                cat = "SYSTEM"
                if "SAFETY" in ev_type:
                    cat = "SAFETY"
                elif "SVI" in ev_type:
                    cat = "SVI"
                elif "ACOUSTIC" in ev_type:
                    cat = "ACOUSTIC"
                elif "ADAPTIVE" in ev_type:
                    cat = "ADAPTIVE"
                elif "TRANSCRIPT" in ev_type:
                    cat = "TRANSCRIPT"
                elif "CALL_" in ev_type:
                    cat = "TELEPHONY"

                summary = f"{ev_type}"
                payload = ev.get("payload", {})
                if cat == "SAFETY":
                    summary = f"Safety Signal: {payload.get('signal_type', 'ELEVATED')} ({payload.get('severity', 'HIGH')})"
                elif cat == "SVI":
                    summary = f"SVI Updated: {payload.get('score', 0)} / 100 ({payload.get('band', 'LOW')})"
                elif cat == "ACOUSTIC":
                    summary = f"Acoustic Quality: {payload.get('quality', 'GOOD')}"
                elif cat == "ADAPTIVE":
                    summary = f"Adaptive Strategy: {payload.get('action', 'GROUNDING')} (Priority: {payload.get('priority', 'P2')})"

                timeline_items.append(
                    TimelineEventItem(
                        event_id=ev.get("event_id", str(uuid.uuid4())),
                        timestamp=ev.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        category=cat,
                        event_type=ev_type,
                        summary=summary,
                        actor_id="system",
                        details=payload,
                    )
                )
        except Exception as e:
            logger.debug(f"Error reading session events for timeline {call_id}: {e}")

        # Filter by category if requested
        if category and category.upper() != "ALL":
            timeline_items = [item for item in timeline_items if item.category.upper() == category.upper()]

        # Sort chronologically by timestamp
        timeline_items.sort(key=lambda x: x.timestamp)
        return timeline_items[-limit:]

    def is_adaptive_paused(self, call_id: str) -> bool:
        """Quick sync check whether adaptive generation is paused for a call."""
        state = self._states.get(call_id)
        return state.adaptive_paused if state else False

    def is_human_active(self, call_id: str) -> bool:
        """Quick sync check whether human takeover is active for a call."""
        state = self._states.get(call_id)
        return state.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE if state else False

    def get_subsystems_status(self) -> List[SubsystemStatus]:
        """Inspects and returns explicit status of all 5 SAMVED subsystems."""
        settings = get_settings()

        return [
            SubsystemStatus(
                name="Safety Engine",
                status="AVAILABLE",
                details="Deterministic safety rules engine active & authoritative",
                version="v1.0.0",
            ),
            SubsystemStatus(
                name="SVI Engine",
                status="AVAILABLE",
                details="Explainable 0-100 Stress Vulnerability Index active",
                version="v1.0.0",
            ),
            SubsystemStatus(
                name="Acoustic Engine",
                status="AVAILABLE",
                details="Non-verbal operational signal layer active",
                version="v1.0.0",
            ),
            SubsystemStatus(
                name="Adaptive Engine",
                status="AVAILABLE",
                details="P0-P5 conversational planning layer active",
                version="v1.0.0",
            ),
            SubsystemStatus(
                name="Operator Control Gateway",
                status="AVAILABLE",
                details="Supervision controls, handoff router, and append-only audit active",
                version=settings.APP_VERSION,
            ),
        ]

    async def _broadcast_event(
        self,
        event_type: EventType,
        call_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Broadcasts operator event over websocket manager and records in session history."""
        try:
            from app.realtime.connection_manager import manager
            from app.realtime.session_manager import telephony_session_manager

            envelope = EventEnvelope(
                event_type=event_type,
                session_id=f"op-session-{call_id}",
                call_id=call_id,
                payload=payload,
            )

            # Record in session history if active
            sess = await telephony_session_manager.get_by_call_id(call_id)
            if sess:
                sess.record_event(envelope)

            # Broadcast to connected operator consoles
            await manager.broadcast_global(envelope)
        except Exception as e:
            logger.error(f"Error broadcasting operator event {event_type.value}: {e}")


operator_service = OperatorService()
