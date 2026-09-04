import asyncio
import pytest
from app.providers.mocks import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from app.realtime.conversation_orchestrator import ConversationOrchestrator
from app.schemas.conversation import ConversationState, TranscriptEvent
from app.schemas.telephony import AudioDirection, AudioFrame


@pytest.mark.asyncio
async def test_barge_in_cancels_ai_speech_and_drains_queue():
    outbound_q = asyncio.Queue()
    interrupted_events = []

    def mock_broadcast(ev_type: str, payload: dict):
        if ev_type == "SPEECH_INTERRUPTED":
            interrupted_events.append(payload)

    orchestrator = ConversationOrchestrator(
        session_id="sess-interrupt-01",
        call_id="call-interrupt-01",
        stt_provider=MockSpeechToTextProvider(),
        llm_provider=MockLLMProvider(),
        tts_provider=MockTextToSpeechProvider(),
        outbound_queue=outbound_q,
        event_broadcaster=mock_broadcast,
    )

    await orchestrator.start()

    # Pre-populate outbound queue with pending TTS speech
    for _ in range(5):
        await outbound_q.put(b"\x00\x02" * 160)

    # Force agent state to SPEAKING to simulate active playback
    orchestrator.state = ConversationState.SPEAKING
    assert outbound_q.qsize() == 5

    # Trigger interruption via caller voice activity
    loud_frame = AudioFrame(
        session_id="sess-interrupt-01",
        call_id="call-interrupt-01",
        sequence_number=1,
        direction=AudioDirection.INBOUND,
        payload_base64="/////w==",  # high energy sample
        payload_size_bytes=320,
    )

    # Calling interrupt directly
    orchestrator.interrupt(reason="test_barge_in")

    # Verify outbound queue was drained
    assert outbound_q.empty()
    assert len(interrupted_events) == 1
    assert interrupted_events[0]["reason"] == "test_barge_in"
    # Verify state returned to LISTENING for caller
    assert orchestrator.state == ConversationState.LISTENING

    await orchestrator.stop()