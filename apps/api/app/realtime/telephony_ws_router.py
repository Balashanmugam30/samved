import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.telephony_state import CallState
from app.providers.exotel import ExotelTelephonyProvider
from app.realtime.session_manager import telephony_session_manager
from app.schemas.telephony import ExotelMediaEvent

logger = logging.getLogger("samved.realtime.telephony_ws")
telephony_ws_router = APIRouter()
exotel_provider = ExotelTelephonyProvider()


@telephony_ws_router.websocket("/ws/telephony/exotel/{session_id}")
async def exotel_telephony_websocket(websocket: WebSocket, session_id: str):
    """Realtime bidirectional audio streaming WebSocket endpoint for Exotel media streams."""
    await websocket.accept()

    session = await telephony_session_manager.get_session(session_id)
    if not session:
        logger.warning(f"Rejecting telephony WebSocket connection: unknown session_id {session_id}")
        await websocket.close(code=4004, reason="Session not found")
        return

    await telephony_session_manager.attach_websocket(session_id, websocket)
    logger.info(f"Exotel media stream connected for session {session_id} (Call: {session.call_id})")

    stream_sid: Optional[str] = None
    sequence_counter = 0

    # Background task to stream outbound audio back to Exotel
    async def outbound_pump():
        try:
            while True:
                pcm_chunk = await session.outbound_queue.get()
                if stream_sid and session.websocket:
                    outbound_msg = exotel_provider.format_outbound_media(stream_sid, pcm_chunk)
                    await websocket.send_text(json.dumps(outbound_msg))
                session.outbound_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in outbound audio pump for session {session_id}: {e}")

    pump_task = asyncio.create_task(outbound_pump())

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON in telephony stream for session {session_id}")
                continue

            event_type = msg.get("event")

            if event_type == ExotelMediaEvent.CONNECTED.value:
                logger.info(f"Handshake acknowledged by Exotel for session {session_id}")

            elif event_type == ExotelMediaEvent.START.value:
                start_data = msg.get("start", {})
                stream_sid = (
                    msg.get("streamSid")
                    or start_data.get("streamSid")
                    or start_data.get("stream_sid")
                    or f"stream-{session_id}"
                )
                if session.state_machine.can_transition_to(CallState.STREAMING):
                    session.state_machine.transition_to(
                        CallState.STREAMING, reason="media_stream_started"
                    )
                logger.info(
                    f"Telephony media stream started for session {session_id} (StreamSid: {stream_sid})"
                )

            elif event_type == ExotelMediaEvent.MEDIA.value:
                sequence_counter += 1
                if not session.state_machine.is_streaming and session.state_machine.can_transition_to(
                    CallState.STREAMING
                ):
                    session.state_machine.transition_to(
                        CallState.STREAMING, reason="first_audio_frame"
                    )

                audio_frame = exotel_provider.normalize_media_event(
                    raw_msg=msg,
                    session_id=session_id,
                    call_id=session.call_id,
                    sequence_number=sequence_counter,
                )
                if audio_frame:
                    session.ingest_inbound_frame(audio_frame)

            elif event_type == ExotelMediaEvent.CLEAR.value:
                # Barge-in / interruption: drain outbound queue
                logger.info(f"Barge-in / clear event received for session {session_id}")
                while not session.outbound_queue.empty():
                    try:
                        session.outbound_queue.get_nowait()
                        session.outbound_queue.task_done()
                    except (asyncio.QueueEmpty, ValueError):
                        break

            elif event_type == ExotelMediaEvent.STOP.value:
                logger.info(f"Stop event received from Exotel for session {session_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"Exotel WebSocket disconnected cleanly for session {session_id}")
    except Exception as exc:
        logger.error(f"Unexpected error in telephony stream for session {session_id}: {exc}")
    finally:
        pump_task.cancel()
        await telephony_session_manager.end_session(session_id, reason="stream_ended")
