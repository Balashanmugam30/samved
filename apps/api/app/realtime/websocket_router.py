import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.realtime.connection_manager import manager
from app.schemas.events import EventEnvelope, EventType

logger = logging.getLogger("samved.realtime")
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
):
    actual_session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    await manager.connect(websocket, actual_session_id)

    # Emit initial connection handshake event
    welcome_envelope = EventEnvelope(
        event_type=EventType.CALL_CONNECTED,
        session_id=actual_session_id,
        call_id=f"call-{uuid.uuid4().hex[:8]}",
        payload={
            "status": "connected",
            "message": "SAMVED Realtime Gateway session established.",
            "server_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    await manager.send_personal_envelope(websocket, welcome_envelope)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                err_envelope = EventEnvelope(
                    event_type=EventType.HUMAN_ALERT,
                    session_id=actual_session_id,
                    call_id="unknown",
                    payload={"error": "MALFORMED_JSON", "message": "Expected valid JSON envelope."},
                )
                await manager.send_personal_envelope(websocket, err_envelope)
                continue

            try:
                incoming_envelope = EventEnvelope.model_validate(data)
            except ValidationError as ve:
                err_envelope = EventEnvelope(
                    event_type=EventType.HUMAN_ALERT,
                    session_id=actual_session_id,
                    call_id=data.get("call_id", "unknown"),
                    payload={"error": "INVALID_SCHEMA", "details": ve.errors()},
                )
                await manager.send_personal_envelope(websocket, err_envelope)
                continue

            # Heartbeat ping/pong handling
            if incoming_envelope.event_type == EventType.HEARTBEAT_PING:
                pong_envelope = EventEnvelope(
                    event_type=EventType.HEARTBEAT_PONG,
                    session_id=actual_session_id,
                    call_id=incoming_envelope.call_id,
                    payload={"reply_to": incoming_envelope.event_id},
                )
                await manager.send_personal_envelope(websocket, pong_envelope)
                continue

            # In Phase 0, echo or route validated events within the session
            logger.info(
                f"Processed event {incoming_envelope.event_type} for session {actual_session_id}"
            )
            # Acknowledge or broadcast event back to subscriber
            await manager.broadcast_to_session(actual_session_id, incoming_envelope)

    except WebSocketDisconnect:
        manager.disconnect(websocket, actual_session_id)
        logger.info(f"WebSocket client gracefully disconnected for session {actual_session_id}")
    except Exception as exc:
        manager.disconnect(websocket, actual_session_id)
        logger.error(f"Unexpected WebSocket error in session {actual_session_id}: {str(exc)}")
