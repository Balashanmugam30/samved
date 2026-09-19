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
        # Cross-instance fallback: attempt hydration from Redis
        session = await telephony_session_manager.hydrate_session_from_redis(session_id)

    if not session:
        logger.warning(f"Rejecting telephony WebSocket connection: unknown session_id {session_id}")
        await websocket.close(code=4004, reason="Session not found")
        return

    await telephony_session_manager.attach_websocket(session_id, websocket)
    logger.info(f"Exotel media stream connected for session {session_id} (Call: {session.call_id})")

    stream_sid: Optional[str] = None
    sequence_counter = 0
    chunk_counter = 0
    buffer = bytearray()

    # Background task to stream outbound audio back to Exotel
    # Exotel VoiceBot requirements: minimum 3200 bytes (100ms at 8kHz 16-bit mono), multiple of 320 bytes, max 100KB
    TARGET_CHUNK_SIZE = 3200

    async def outbound_pump():
        nonlocal chunk_counter
        try:
            while True:
                pcm_chunk = await session.outbound_queue.get()
                buffer.extend(pcm_chunk)
                session.outbound_queue.task_done()

                # Drain any additional chunks ready in queue without blocking
                while not session.outbound_queue.empty():
                    try:
                        extra = session.outbound_queue.get_nowait()
                        buffer.extend(extra)
                        session.outbound_queue.task_done()
                    except (asyncio.QueueEmpty, ValueError):
                        break

                # Send all complete TARGET_CHUNK_SIZE blocks
                while len(buffer) >= TARGET_CHUNK_SIZE:
                    to_send = bytes(buffer[:TARGET_CHUNK_SIZE])
                    del buffer[:TARGET_CHUNK_SIZE]
                    if stream_sid and session.websocket:
                        chunk_counter += 1
                        outbound_msg = exotel_provider.format_outbound_media(
                            stream_sid=stream_sid,
                            pcm_bytes=to_send,
                            chunk_index=chunk_counter,
                        )
                        await websocket.send_text(json.dumps(outbound_msg))
                        session.audio_telemetry.outbound_frames_sent_to_exotel += 1
                        session.audio_telemetry.outbound_pcm_bytes_sent += len(to_send)
                        session.audio_telemetry.real_outbound_media_sent = True
                        session.audio_telemetry.update_two_way_verification()
                        logger.info(
                            f"MEDIA_SENT_TO_EXOTEL: session={session_id}, bytes={len(to_send)}, chunk={chunk_counter}"
                        )
                        await asyncio.sleep(0.100)

                # If queue is now empty and residual buffer remains:
                # Pad to multiple of 320 bytes and minimum 3200 bytes so Exotel accepts it
                if session.outbound_queue.empty() and len(buffer) > 0:
                    remainder = len(buffer) % 320
                    if remainder > 0:
                        buffer.extend(b"\x00" * (320 - remainder))
                    if len(buffer) < TARGET_CHUNK_SIZE:
                        buffer.extend(b"\x00" * (TARGET_CHUNK_SIZE - len(buffer)))
                    to_send = bytes(buffer[:TARGET_CHUNK_SIZE])
                    del buffer[:TARGET_CHUNK_SIZE]
                    if stream_sid and session.websocket:
                        chunk_counter += 1
                        outbound_msg = exotel_provider.format_outbound_media(
                            stream_sid=stream_sid,
                            pcm_bytes=to_send,
                            chunk_index=chunk_counter,
                        )
                        await websocket.send_text(json.dumps(outbound_msg))
                        session.audio_telemetry.outbound_frames_sent_to_exotel += 1
                        session.audio_telemetry.outbound_pcm_bytes_sent += len(to_send)
                        session.audio_telemetry.real_outbound_media_sent = True
                        session.audio_telemetry.update_two_way_verification()
                        logger.info(
                            f"MEDIA_SENT_TO_EXOTEL: session={session_id}, bytes={len(to_send)}, chunk={chunk_counter} (flushed/padded)"
                        )
                        await asyncio.sleep(0.100)

                # Send mark event when turn audio queue finishes
                if session.outbound_queue.empty() and len(buffer) == 0 and stream_sid and chunk_counter > 0:
                    mark_name = f"turn_{chunk_counter}"
                    mark_msg = exotel_provider.format_mark_event(stream_sid, mark_name=mark_name)
                    await websocket.send_text(json.dumps(mark_msg))
                    session.audio_telemetry.marks_sent += 1
                    logger.info(f"MARK_SENT: session={session_id}, mark={mark_name}")

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
                    or msg.get("stream_sid")
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

                # Trigger initial safe greeting immediately upon stream start
                if session.orchestrator:
                    session.audio_telemetry.initial_greeting_sent = True
                    asyncio.create_task(session.orchestrator.trigger_initial_greeting())

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
                    logger.info(
                        f"MEDIA_RECEIVED: session={session_id}, seq={audio_frame.sequence_number}, bytes={audio_frame.payload_size_bytes}"
                    )

            elif event_type == ExotelMediaEvent.MARK.value:
                session.audio_telemetry.marks_received += 1
                session.audio_telemetry.real_mark_received = True
                logger.info(f"MARK_RECEIVED: session={session_id}, mark={msg.get('mark', {})}")


            elif event_type == ExotelMediaEvent.CLEAR.value:
                session.audio_telemetry.barge_in_clears_received += 1
                logger.info(f"Barge-in / clear event received from Exotel for session {session_id}")
                buffer.clear()
                if session.orchestrator:
                    session.orchestrator.interrupt(reason="exotel_clear_barge_in")
                else:
                    while not session.outbound_queue.empty():
                        try:
                            session.outbound_queue.get_nowait()
                            session.outbound_queue.task_done()
                        except (asyncio.QueueEmpty, ValueError):
                            break

            elif event_type == ExotelMediaEvent.STOP.value:
                logger.info(f"CALL_STOPPED: Stop event received from Exotel for session {session_id}")
                break

    except WebSocketDisconnect:
        logger.info(f"Exotel WebSocket disconnected cleanly for session {session_id}")
    except Exception as exc:
        logger.error(f"Unexpected error in telephony stream for session {session_id}: {exc}")
    finally:
        pump_task.cancel()
        await telephony_session_manager.end_session(session_id, reason="stream_ended")
