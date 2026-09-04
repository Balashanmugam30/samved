import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.calls")

router = APIRouter(tags=["Calls"])


class CallSummaryResponse(BaseModel):
    session_id: str
    call_id: str
    provider_call_id: str
    provider: str
    caller_masked_number: str
    state: str
    created_at: str
    connected_at: Optional[str] = None
    ended_at: Optional[str] = None
    last_activity_at: str
    duration_seconds: float = 0.0
    conversation_state: str = "IDLE"
    current_language: str = "unknown"
    utterances_count: int = 0
    events_count: int = 0
    is_active: bool = False


class CallsListResponse(BaseModel):
    active_calls: List[Dict[str, Any]]
    recent_calls: List[Dict[str, Any]]
    total_active: int
    total_recent: int


class TranscriptResponse(BaseModel):
    call_id: str
    utterances: List[Dict[str, Any]]
    total_utterances: int


class EventsResponse(BaseModel):
    call_id: str
    events: List[Dict[str, Any]]
    total_events: int


@router.get("", response_model=CallsListResponse)
async def list_calls():
    """Returns active and recently completed calls with duration, masked numbers, and state."""
    data = telephony_session_manager.list_calls()
    return CallsListResponse(
        active_calls=data["active_calls"],
        recent_calls=data["recent_calls"],
        total_active=data["total_active"],
        total_recent=data["total_recent"],
    )


@router.get("/{call_id}")
async def get_call(call_id: str):
    """Retrieves call summary and metadata by call_id."""
    call = await telephony_session_manager.get_call_summary(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )
    return call


@router.get("/{call_id}/transcript", response_model=TranscriptResponse)
async def get_call_transcript(call_id: str):
    """Retrieves complete chronological transcript utterances for a call."""
    transcript = await telephony_session_manager.get_call_transcript(call_id)
    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )
    return TranscriptResponse(
        call_id=call_id,
        utterances=transcript,
        total_utterances=len(transcript),
    )


@router.get("/{call_id}/events", response_model=EventsResponse)
async def get_call_events(call_id: str):
    """Retrieves bounded domain and telephony event history for a call."""
    events = await telephony_session_manager.get_call_events(call_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )
    return EventsResponse(
        call_id=call_id,
        events=events,
        total_events=len(events),
    )
