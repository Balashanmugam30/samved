import asyncio
import math
import struct
import pytest
from app.services.acoustic_engine import AcousticEngine, acoustic_engine


def generate_pcm_frame(amplitude: int = 1200, freq: float = 220.0) -> bytes:
    samples = [int(amplitude * math.sin(2 * math.pi * freq * (i / 8000.0))) for i in range(160)]
    return struct.pack("<160h", *samples)


@pytest.mark.asyncio
async def test_concurrency_50_sessions():
    """Verifies that 50 concurrent telephony sessions process frames without state leakage or race conditions."""
    engine = AcousticEngine()
    num_sessions = 50
    frames_per_session = 30  # 600ms per session

    async def run_session(idx: int):
        session_id = f"concurr-sess-{idx}"
        call_id = f"concurr-call-{idx}"
        freq = 150.0 + (idx * 2)  # distinct frequency per session
        frame = generate_pcm_frame(amplitude=1000 + (idx * 10), freq=freq)

        for _ in range(frames_per_session):
            engine.ingest_frame(session_id, call_id, frame)
            await asyncio.sleep(0.001)

        if idx % 3 == 0:
            engine.record_interruption(session_id)
            engine.record_interruption(session_id)

        assessment = engine.evaluate_window(call_id, session_id)
        assert assessment.session_id == session_id
        assert assessment.call_id == call_id
        assert assessment.turn_metrics.turn_duration_ms == frames_per_session * 20
        if idx % 3 == 0:
            assert assessment.interruption_metrics.interruption_count == 2
        else:
            assert assessment.interruption_metrics.interruption_count == 0
        return assessment

    tasks = [run_session(i) for i in range(num_sessions)]
    results = await asyncio.gather(*tasks)

    assert len(results) == num_sessions
    # Verify each result retained its independent identity
    session_ids = {r.session_id for r in results}
    assert len(session_ids) == num_sessions
