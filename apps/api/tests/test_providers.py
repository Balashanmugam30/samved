import pytest
from app.providers.base import (
    LLMProvider,
    SpeechToTextProvider,
    TelephonyProvider,
    TextToSpeechProvider,
)
from app.providers.mocks import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTelephonyProvider,
    MockTextToSpeechProvider,
)


@pytest.mark.asyncio
async def test_mock_telephony_provider():
    provider = MockTelephonyProvider()
    assert isinstance(provider, TelephonyProvider)

    call_id = await provider.initiate_call("+91-9876543210", "+91-14566", {"mode": "test"})
    assert call_id.startswith("mock-call-")

    health = await provider.health_check()
    assert health["status"] == "healthy"
    assert health["active_calls_count"] == 1

    ended = await provider.terminate_call(call_id)
    assert ended is True


@pytest.mark.asyncio
async def test_mock_stt_provider():
    provider = MockSpeechToTextProvider()
    assert isinstance(provider, SpeechToTextProvider)

    started = await provider.start_stream("sess-test-stt", "hi-IN")
    assert started is True

    await provider.send_audio_chunk("sess-test-stt", b"\x00\x01\x02")

    transcripts = []
    async for item in provider.receive_transcripts("sess-test-stt"):
        transcripts.append(item)

    assert len(transcripts) == 2
    assert transcripts[0]["is_final"] is False
    assert transcripts[1]["is_final"] is True
    assert "Namaste" in transcripts[1]["text"]


@pytest.mark.asyncio
async def test_mock_tts_provider():
    provider = MockTextToSpeechProvider()
    assert isinstance(provider, TextToSpeechProvider)

    audio_bytes = await provider.synthesize("Namaste, main aapki sahayata kar sakta hoon.", "hi-IN")
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 0


@pytest.mark.asyncio
async def test_mock_llm_provider():
    provider = MockLLMProvider()
    assert isinstance(provider, LLMProvider)

    resp = await provider.generate_response(
        system_prompt="You are a helpful helpline assistant.",
        messages=[{"role": "user", "content": "Mujhe de-addiction center chahiye."}],
    )
    assert "Mock response acknowledging" in resp

    structured = await provider.generate_structured_output(
        system_prompt="Extract entities",
        messages=[{"role": "user", "content": "Jaipur me alcohol addiction center"}],
        schema_model=None,
    )
    assert structured["intent"] == "INQUIRY_DE_ADDICTION"
    assert structured["entities"]["location"] == "Jaipur"
