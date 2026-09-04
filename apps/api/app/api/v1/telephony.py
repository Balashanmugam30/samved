import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.telephony_state import CallState
from app.providers.exotel import ExotelTelephonyProvider
from app.providers.mocks import MockTelephonyProvider
from app.realtime.connection_manager import manager as ws_event_manager
from app.realtime.session_manager import telephony_session_manager
from app.schemas.events import EventEnvelope, EventType
from app.schemas.telephony import (
    ExotelInboundPayload,
    ExotelStatusPayload,
    SimulationCallRequest,
    TelephonySessionInfo,
)

logger = logging.getLogger("samved.api.telephony")
telephony_router = APIRouter(prefix="/telephony", tags=["Telephony Operations"])

settings = get_settings()
exotel_provider = ExotelTelephonyProvider()
mock_provider = MockTelephonyProvider()


@telephony_router.post("/exotel/inbound", status_code=status.HTTP_200_OK)
async def exotel_inbound_webhook(request: Request):
    """Inbound call webhook from Exotel telephony cloud.

    Provisions a call record, initializes a realtime session, and returns the streaming instruction.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    # 1. Provider signature validation (if enabled)
    if not exotel_provider.validate_webhook(headers, raw_body):
        logger.warning("Rejected Exotel webhook: invalid HMAC signature.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid provider webhook signature.",
        )

    # 2. Extract payload (handle JSON or form-encoded POST from Exotel)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form_data = await request.form()
        data = dict(form_data)

    call_sid = data.get("CallSid") or data.get("call_sid")
    from_number = data.get("From") or data.get("from") or "anonymous"
    to_number = data.get("To") or data.get("to") or "14566"

    if not call_sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required CallSid parameter.",
        )

    # 3. Idempotency check: reuse existing session if this webhook was retried
    existing_session = await telephony_session_manager.get_by_provider_call_id(call_sid)
    if existing_session:
        logger.info(f"Duplicate inbound webhook for CallSid {call_sid}; returning existing stream.")
        ws_url = f"{settings.PUBLIC_WS_BASE_URL}/ws/telephony/exotel/{existing_session.session_id}"
        return exotel_provider.create_streaming_instruction(existing_session.session_id, ws_url)

    # 4. Provision fresh Call and Realtime Session
    call_id = f"CALL-{uuid.uuid4().hex[:8]}"
    session_id = f"SESS-{uuid.uuid4().hex[:8]}"

    session = await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id=call_sid,
        caller_number=from_number,
        provider="exotel",
    )

    # Transition state to RINGING then CONNECTING
    if session.state_machine.can_transition_to(CallState.RINGING):
        session.state_machine.transition_to(CallState.RINGING, reason="inbound_webhook_received")
    if session.state_machine.can_transition_to(CallState.CONNECTING):
        session.state_machine.transition_to(CallState.CONNECTING, reason="stream_instruction_issued")

    # 5. Emit canonical CALL_STARTED domain event
    start_envelope = EventEnvelope(
        event_type=EventType.CALL_STARTED,
        session_id=session_id,
        call_id=call_id,
        payload={
            "telephony_provider": "exotel",
            "provider_call_id": call_sid,
            "caller_masked_number": session.masked_caller_number,
            "destination_number": to_number,
            "mode": settings.APP_MODE,
        },
    )
    await ws_event_manager.broadcast_to_session(session_id, start_envelope)

    ws_stream_url = f"{settings.PUBLIC_WS_BASE_URL}/ws/telephony/exotel/{session_id}"
    logger.info(f"Handled inbound call {call_sid} -> session {session_id}, stream: {ws_stream_url}")

    # Return Exotel Streaming Applet instruction
    return exotel_provider.create_streaming_instruction(session_id, ws_stream_url)


@telephony_router.post("/exotel/status", status_code=status.HTTP_200_OK)
async def exotel_status_callback(request: Request):
    """Post-call status callback from Exotel passthru applet."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form_data = await request.form()
        data = dict(form_data)

    call_sid = data.get("CallSid") or data.get("call_sid")
    status_str = data.get("Status", "completed")
    duration = data.get("DialCallDuration")

    logger.info(f"Received status callback for Exotel call {call_sid}: status={status_str}, duration={duration}s")

    if call_sid:
        session = await telephony_session_manager.get_by_provider_call_id(call_sid)
        if session:
            await telephony_session_manager.end_session(session.session_id, reason=f"exotel_status_{status_str}")

    return {"status": "acknowledged"}


@telephony_router.get("/doctor", status_code=status.HTTP_200_OK)
async def telephony_doctor() -> Dict[str, Any]:
    """Safe diagnostic mechanism inspecting telephony readiness without leaking secrets."""
    is_live = settings.is_live()
    has_creds = settings.has_exotel_credentials()
    is_enabled = settings.EXOTEL_ENABLED
    is_public = not ("localhost" in settings.PUBLIC_BASE_URL or "127.0.0.1" in settings.PUBLIC_BASE_URL)

    return {
        "app_mode": settings.APP_MODE,
        "telephony_provider": "Exotel",
        "exotel_credentials_present": has_creds,
        "exotel_enabled": is_enabled,
        "live_mode_safe_to_start": is_live and has_creds and is_enabled and is_public,
        "public_webhook_base_url": settings.PUBLIC_BASE_URL,
        "public_ws_base_url": settings.PUBLIC_WS_BASE_URL,
        "public_url_configured": is_public,
        "signature_verification_enabled": settings.EXOTEL_VERIFY_SIGNATURE,
        "active_calls_count": telephony_session_manager.active_calls_count,
        "note": "Exotel webhooks require public HTTPS/WSS reachable endpoints during LIVE calls."
    }


@telephony_router.get("/sessions", response_model=List[TelephonySessionInfo])
async def list_active_telephony_sessions():
    """Lists active telephony calls and real-time streaming metrics."""
    return telephony_session_manager.list_active_sessions()


@telephony_router.post("/simulate", status_code=status.HTTP_201_CREATED)
async def start_simulated_call(payload: SimulationCallRequest):
    """Triggers an end-to-end backend synthetic call simulation for technical diagnostics and testing."""
    call_id = f"SIM-{uuid.uuid4().hex[:8]}"
    session_id = f"SESS-{uuid.uuid4().hex[:8]}"
    provider_call_id = f"MOCK-EXO-{uuid.uuid4().hex[:8]}"

    session = await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id=provider_call_id,
        caller_number=payload.caller_phone,
        provider="mock",
    )

    # Lifecycle progression
    session.state_machine.transition_to(CallState.RINGING, reason="simulated_inbound")
    session.state_machine.transition_to(CallState.CONNECTING, reason="simulated_handshake")
    session.state_machine.transition_to(CallState.CONNECTED, reason="simulated_connect")
    session.state_machine.transition_to(CallState.STREAMING, reason="simulated_stream_active")

    # Generate synthetic frames
    frames = mock_provider.generate_synthetic_frames(
        session_id=session_id,
        call_id=call_id,
        count=payload.duration_frames,
        simulate_gap=payload.simulate_gap,
    )

    # Ingest frames asynchronously
    async def run_simulation():
        try:
            for raw_msg in frames:
                await asyncio.sleep(payload.frame_interval_ms / 1000.0)
                audio_frame = exotel_provider.normalize_media_event(
                    raw_msg=raw_msg,
                    session_id=session_id,
                    call_id=call_id,
                    sequence_number=raw_msg["sequenceNumber"],
                )
                if audio_frame:
                    session.ingest_inbound_frame(audio_frame)
            await asyncio.sleep(0.1)
        finally:
            await telephony_session_manager.end_session(session_id, reason="simulation_completed")

    asyncio.create_task(run_simulation())

    return {
        "status": "simulation_started",
        "call_id": call_id,
        "session_id": session_id,
        "masked_caller_number": session.masked_caller_number,
        "frames_scheduled": payload.duration_frames,
        "state": session.state_machine.current_state.value,
    }
