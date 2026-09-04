import asyncio
import base64
import uuid
import pytest
from app.realtime.session_manager import telephony_session_manager


@pytest.mark.asyncio
async def test_concurrent_telephony_sessions_isolation():
    """Simulates 5 concurrent calls streaming audio simultaneously.

    Verifies complete session isolation, zero audio crosstalk, and 100% clean termination.
    """
    session_count = 5
    sessions = []

    # 1. Provision 5 distinct concurrent sessions
    for i in range(session_count):
        sid = f"concur-sess-{i}-{uuid.uuid4().hex[:6]}"
        cid = f"concur-call-{i}-{uuid.uuid4().hex[:6]}"
        exo_sid = f"concur-exo-{i}-{uuid.uuid4().hex[:6]}"
        phone = f"+91980000000{i}"

        sess = await telephony_session_manager.create_session(
            session_id=sid,
            call_id=cid,
            provider_call_id=exo_sid,
            caller_number=phone,
            provider="mock",
        )
        sessions.append(sess)

    assert telephony_session_manager.active_calls_count >= session_count

    # 2. Concurrently stream distinct frames to each session
    async def stream_worker(session, worker_id: int):
        dummy_pcm = bytes([worker_id % 256]) * 160  # Unique byte payload per worker
        b64_payload = base64.b64encode(dummy_pcm).decode("utf-8")

        for seq in range(1, 11):
            from app.schemas.telephony import AudioDirection, AudioFrame
            frame = AudioFrame(
                session_id=session.session_id,
                call_id=session.call_id,
                sequence_number=seq,
                direction=AudioDirection.INBOUND,
                payload_base64=b64_payload,
                payload_size_bytes=len(dummy_pcm),
            )
            session.ingest_inbound_frame(frame)
            await asyncio.sleep(0.005)

    # Run streaming concurrently
    await asyncio.gather(*(stream_worker(sess, idx) for idx, sess in enumerate(sessions)))

    # 3. Assert strict isolation: each session received exactly 10 frames and its own unique payload
    for idx, sess in enumerate(sessions):
        assert sess.inbound_frames_count == 10
        assert len(sess.inbound_buffer) == 10

        # Check payload byte: must match this worker's unique ID, not any other worker's
        first_frame = sess.inbound_buffer[0]
        raw_bytes = first_frame.get_raw_bytes()
        expected_byte = idx % 256
        assert raw_bytes[0] == expected_byte, f"Crosstalk detected in session {sess.session_id}!"

    # 4. Clean up all concurrent sessions
    for sess in sessions:
        ended = await telephony_session_manager.end_session(sess.session_id, reason="concurrency_test_complete")
        assert ended is not None

    # Assert all test sessions cleaned up
    remaining = telephony_session_manager.list_active_sessions()
    test_remaining = [s for s in remaining if s.session_id.startswith("concur-sess-")]
    assert len(test_remaining) == 0
