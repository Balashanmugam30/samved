import json
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.realtime.connection_manager import manager
from app.realtime.session_manager import telephony_session_manager
from app.schemas.events import EventEnvelope, EventType

logger = logging.getLogger("samved.realtime.operator")

operator_ws_router = APIRouter(tags=["Operator WebSocket"])


@operator_ws_router.websocket("/ws/operator")
async def operator_websocket_endpoint(
    websocket: WebSocket,
    call_id: Optional[str] = Query(default=None),
):
    """Dedicated real-time WebSocket endpoint for human operators and supervisor consoles.

    Sends domain, conversation, transcript, and latency events without raw audio frames.
    """
    await websocket.accept()
    manager.register_operator(websocket, call_id=call_id)
    settings = get_settings()

    logger.info(
        f"Operator connected to /ws/operator (initial filter: {call_id or 'ALL'}). Total operators: {manager.total_operators}"
    )

    try:
        # 1. Immediate Initial Snapshot
        calls_data = telephony_session_manager.list_calls()
        snapshot_envelope = EventEnvelope(
            event_type=EventType.OPERATOR_SNAPSHOT,
            session_id="operator-session",
            call_id=call_id or "global",
            payload={
                "system_mode": settings.APP_MODE,
                "active_calls": calls_data["active_calls"],
                "recent_calls": calls_data["recent_calls"],
                "total_active": calls_data["total_active"],
                "total_recent": calls_data["total_recent"],
                "total_operators": manager.total_operators,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await websocket.send_text(snapshot_envelope.model_dump_json())

        # 2. Inbound Operator Action Loop
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Malformed JSON from operator client: {raw_data[:100]}")
                err_env = EventEnvelope(
                    event_type=EventType.STT_ERROR,
                    session_id="operator-session",
                    call_id=call_id or "global",
                    payload={"error": "MALFORMED_JSON", "message": "Expected valid JSON payload"},
                )
                await websocket.send_text(err_env.model_dump_json())
                continue

            action = data.get("action") or data.get("event_type")

            if action in ("SUBSCRIBE_CALL", "subscribe_call"):
                target_cid = data.get("call_id")
                manager.subscribe_operator(websocket, target_cid)
                call_summary = await telephony_session_manager.get_call_summary(target_cid) if target_cid else None
                transcript = await telephony_session_manager.get_call_transcript(target_cid) if target_cid else []
                ack = EventEnvelope(
                    event_type=EventType.OPERATOR_SNAPSHOT,
                    session_id="operator-session",
                    call_id=target_cid or "global",
                    payload={
                        "action_ack": "SUBSCRIBE_CALL",
                        "subscribed_call_id": target_cid,
                        "call_summary": call_summary,
                        "transcript": transcript or [],
                    },
                )
                await websocket.send_text(ack.model_dump_json())

            elif action in ("SUBSCRIBE_ALL", "subscribe_all"):
                manager.subscribe_operator(websocket, None)
                current_data = telephony_session_manager.list_calls()
                ack = EventEnvelope(
                    event_type=EventType.OPERATOR_SNAPSHOT,
                    session_id="operator-session",
                    call_id="global",
                    payload={
                        "action_ack": "SUBSCRIBE_ALL",
                        "active_calls": current_data["active_calls"],
                        "recent_calls": current_data["recent_calls"],
                    },
                )
                await websocket.send_text(ack.model_dump_json())

            elif action in ("PING", "HEARTBEAT_PING"):
                pong = EventEnvelope(
                    event_type=EventType.HEARTBEAT_PONG,
                    session_id="operator-session",
                    call_id="global",
                    payload={
                        "status": "alive",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                await websocket.send_text(pong.model_dump_json())

            else:
                logger.debug(f"Unhandled operator action: {action}")

    except WebSocketDisconnect:
        logger.info("Operator client disconnected cleanly")
    except Exception as e:
        logger.error(f"Error in operator WebSocket connection: {e}")
    finally:
        manager.unregister_operator(websocket)
