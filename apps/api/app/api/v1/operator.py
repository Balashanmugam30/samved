from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.operator.models import OperatorNoteCategory
from app.operator.schemas import (
    AddNoteRequest,
    CallOperatorState,
    EndCallRequest,
    HandoffCancelRequest,
    HandoffConfirmRequest,
    HandoffRequest,
    OperatorActionResponse,
    OperatorNotesListResponse,
    OperatorStatusResponse,
    OperatorTimelineResponse,
    PauseRequest,
    ResumeRequest,
    SafetyCheckRequest,
    TakeoverRequest,
)
from app.operator.service import operator_service
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.operator")

router = APIRouter(prefix="/operator", tags=["Operator Workstation"])


@router.get("/status", response_model=OperatorStatusResponse)
async def get_operator_workstation_status():
    """Returns workstation health, app mode, and explicit status of all 5 SAMVED engines."""
    settings = get_settings()
    subsystems = operator_service.get_subsystems_status()
    total_active = telephony_session_manager.active_calls_count

    return OperatorStatusResponse(
        status="healthy",
        app_mode=settings.APP_MODE,
        subsystems=subsystems,
        active_operators_count=1,
        total_active_calls=total_active,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/calls")
async def list_operator_calls(
    filter_by: Optional[str] = Query(default=None, description="Optional filter: active, critical, elevated, takeover"),
):
    """Returns call list enriched with operator ownership, safety, SVI, acoustic, and adaptive state."""
    data = telephony_session_manager.list_calls()
    active_calls = data["active_calls"]

    enriched_active = []
    for c in active_calls:
        cid = c["call_id"]
        op_state = await operator_service.get_or_create_state(cid)
        notes = await operator_service.get_notes(cid)
        enriched = dict(c)
        enriched["ownership_state"] = op_state.ownership_state.value
        enriched["handoff_status"] = op_state.handoff_status.value
        enriched["adaptive_paused"] = op_state.adaptive_paused
        enriched["active_operator_id"] = op_state.active_operator_id
        enriched["notes_count"] = len(notes)
        enriched_active.append(enriched)

    # Filter if requested
    if filter_by:
        f = filter_by.lower()
        if f == "critical":
            enriched_active = [c for c in enriched_active if c.get("safety_state") == "CRITICAL"]
        elif f == "elevated":
            enriched_active = [c for c in enriched_active if c.get("safety_state") in ("CRITICAL", "HIGH", "ELEVATED")]
        elif f == "takeover":
            enriched_active = [c for c in enriched_active if c.get("ownership_state") == "HUMAN_ACTIVE"]

    return {
        "active_calls": enriched_active,
        "recent_calls": data["recent_calls"],
        "total_active": len(enriched_active),
        "total_recent": data["total_recent"],
    }


@router.get("/calls/{call_id}", response_model=CallOperatorState)
async def get_call_operator_state(call_id: str):
    """Retrieves current operator supervision state for a specific call."""
    summary = await telephony_session_manager.get_call_summary(call_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )
    return await operator_service.get_or_create_state(call_id)


@router.get("/calls/{call_id}/timeline", response_model=OperatorTimelineResponse)
async def get_call_timeline(
    call_id: str,
    category: Optional[str] = Query(default=None, description="Filter: ALL, OPERATOR, SAFETY, SVI, ACOUSTIC, ADAPTIVE"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Retrieves bounded, chronologically sorted event timeline for a call."""
    events = await operator_service.get_timeline(call_id=call_id, category=category, limit=limit)
    return OperatorTimelineResponse(
        call_id=call_id,
        events=events,
        total_events=len(events),
    )


@router.get("/calls/{call_id}/notes", response_model=OperatorNotesListResponse)
async def get_call_notes(call_id: str):
    """Retrieves all structured operator notes for a call."""
    notes = await operator_service.get_notes(call_id)
    return OperatorNotesListResponse(
        call_id=call_id,
        notes=notes,
        total_notes=len(notes),
    )


@router.post("/calls/{call_id}/takeover", response_model=OperatorActionResponse)
async def takeover_call(call_id: str, req: TakeoverRequest):
    """Transfers control of call to human operator. Suppresses autonomous AI speech.

    Idempotent: Re-calling when already HUMAN_ACTIVE is safe.
    """
    state = await operator_service.takeover(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return OperatorActionResponse(
        action="TAKEOVER",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message=f"Call ownership successfully transferred to human operator {req.operator_id}",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/pause", response_model=OperatorActionResponse)
async def pause_adaptive_ai(call_id: str, req: PauseRequest):
    """Pauses adaptive conversational AI planning for the call."""
    state = await operator_service.pause_adaptive(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return OperatorActionResponse(
        action="PAUSE_ADAPTIVE",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message="Adaptive conversational engine successfully paused",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/resume", response_model=OperatorActionResponse)
async def resume_adaptive_ai(call_id: str, req: ResumeRequest):
    """Resumes adaptive conversational AI planning for the call."""
    state = await operator_service.resume_adaptive(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return OperatorActionResponse(
        action="RESUME_ADAPTIVE",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message="Adaptive conversational engine successfully resumed",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/safety-check")
async def request_safety_check(call_id: str, req: SafetyCheckRequest):
    """Requests immediate deterministic safety re-evaluation by the Safety Engine."""
    result = await operator_service.request_safety_check(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return result


@router.post("/calls/{call_id}/handoff", response_model=OperatorActionResponse)
async def request_call_handoff(call_id: str, req: HandoffRequest):
    """Initiates a warm handoff request. State becomes HANDOFF_PENDING (status: REQUESTED).

    Never collapses requested with confirmed.
    """
    state = await operator_service.request_handoff(
        call_id=call_id,
        operator_id=req.operator_id,
        target_department=req.target_department,
        notes=req.notes,
    )
    return OperatorActionResponse(
        action="HANDOFF_REQUEST",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message=f"Handoff requested to {req.target_department}. Operator remains in control until confirmed.",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/handoff/confirm", response_model=OperatorActionResponse)
async def confirm_call_handoff(call_id: str, req: HandoffConfirmRequest):
    """Confirms transfer of call to receiving counselor/supervisor."""
    state = await operator_service.confirm_handoff(
        call_id=call_id,
        transfer_confirmed_by=req.transfer_confirmed_by,
        target_agent=req.target_agent,
        notes=req.notes,
    )
    return OperatorActionResponse(
        action="HANDOFF_CONFIRM",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message=f"Handoff confirmed to {req.target_agent or 'assigned counselor'}",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/handoff/cancel", response_model=OperatorActionResponse)
async def cancel_call_handoff(call_id: str, req: HandoffCancelRequest):
    """Cancels a pending handoff request and reverts ownership to HUMAN_ACTIVE."""
    state = await operator_service.cancel_handoff(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return OperatorActionResponse(
        action="HANDOFF_CANCEL",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message="Handoff request cancelled. Operator remains in active control.",
        timestamp=state.updated_at,
    )


@router.post("/calls/{call_id}/notes")
async def add_call_note(call_id: str, req: AddNoteRequest):
    """Appends an immutable structured operator note to the call."""
    note = await operator_service.add_note(
        call_id=call_id,
        operator_id=req.operator_id,
        category=req.category,
        text=req.text,
    )
    return note


@router.post("/calls/{call_id}/end", response_model=OperatorActionResponse)
async def end_call(call_id: str, req: EndCallRequest):
    """Concludes call and terminates telephony session cleanly."""
    state = await operator_service.end_call(
        call_id=call_id,
        operator_id=req.operator_id,
        reason=req.reason,
    )
    return OperatorActionResponse(
        action="END_CALL",
        call_id=call_id,
        ownership_state=state.ownership_state.value,
        handoff_status=state.handoff_status.value,
        message=f"Call successfully ended ({req.reason})",
        timestamp=state.updated_at,
    )
