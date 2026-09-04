import pytest
from app.providers.mocks import MockSpeechToTextProvider
from app.providers.sarvam_stt import SarvamSTTProvider
from app.schemas.conversation import TranscriptEvent


@pytest.mark.asyncio
async def test_mock_stt_provider_streaming():
    stt = MockSpeechToTextProvider()
    session_id = "test-session-stt-01"

    started = await stt.start_stream(session_id, language_code="ta-IN")
    assert started is True

    # Send dummy 8kHz audio chunk
    await stt.send_audio_chunk(session_id, b"\x00\x01" * 160)

    events = []
    async for event in stt.receive_transcripts(session_id):
        events.append(event)

    assert len(events) == 2
    assert events[0].is_final is False
    assert events[1].is_final is True
    assert events[1].language == "ta-IN"

    await stt.close_stream(session_id)
    assert session_id not in stt.sessions


def test_sarvam_stt_provider_unconfigured_behavior():
    stt = SarvamSTTProvider(api_key=None)
    assert stt.is_configured is False