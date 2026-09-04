import pytest
from app.providers.mocks import MockTextToSpeechProvider
from app.providers.sarvam_tts import SarvamTTSProvider, strip_wav_header_if_present
from app.realtime.audio_adapter import AudioStreamAdapter


def test_strip_wav_header():
    # 44 bytes dummy RIFF header + 10 bytes PCM
    dummy_wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 32 + b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10"
    pcm = strip_wav_header_if_present(dummy_wav)
    assert len(pcm) == 10
    assert pcm == b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10"

    raw_pcm = b"\x00\x01\x02\x03"
    assert strip_wav_header_if_present(raw_pcm) == raw_pcm


@pytest.mark.asyncio
async def test_mock_tts_provider():
    tts = MockTextToSpeechProvider()
    pcm = await tts.synthesize("Hello caller, how can I help you?", language_code="en-IN")
    assert len(pcm) > 0
    # Must be multiple of 320 bytes (20ms frames)
    assert len(pcm) % 320 == 0

    frames = AudioStreamAdapter.slice_pcm_to_frames(pcm)
    assert len(frames) == 10
    assert len(frames[0]) == 320


def test_sarvam_tts_unconfigured():
    tts = SarvamTTSProvider(api_key=None)
    assert tts.is_configured is False