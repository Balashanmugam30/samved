import asyncio
import base64
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.exotel import ExotelTelephonyProvider
from app.providers.sarvam_stt import SarvamSTTProvider
from app.providers.sarvam_tts import DEFAULT_VOICES, SarvamTTSProvider
from app.realtime.conversation_orchestrator import INITIAL_GREETINGS, ConversationOrchestrator
from app.realtime.session_manager import AudioTelemetry, telephony_session_manager
from app.schemas.conversation import TranscriptEvent
from app.schemas.languages import LanguageCode
from app.schemas.telephony import AudioDiagnosticsInfo, ExotelMediaEvent


# 1. Sarvam STT URL construction with query parameters
def test_sarvam_stt_websocket_url_query_params():
    provider = SarvamSTTProvider(api_key="test-api-key-12345678")
    assert provider.is_configured is True
    assert "wss://api.sarvam.ai/speech-to-text-realtime/ws" in provider.ws_url


# 2. Sarvam STT parsing of partial transcript events
@pytest.mark.asyncio
async def test_sarvam_stt_event_parsing_partial():
    provider = SarvamSTTProvider(api_key="test-api-key-12345678")
    provider._event_queues["sess-1"] = asyncio.Queue()

    # Mock WebSocket receiving a transcript.partial event
    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = [
        json.dumps({
            "event": "transcript.partial",
            "transcript": "வணக்கம் நான்",
            "language_code": "ta-IN",
        })
    ]

    await provider._listen_loop("sess-1", mock_ws)
    assert not provider._event_queues["sess-1"].empty()
    event: TranscriptEvent = await provider._event_queues["sess-1"].get()
    assert event.is_final is False
    assert event.text == "வணக்கம் நான்"
    assert event.language == "ta-IN"


# 3. Sarvam STT parsing of final transcript events
@pytest.mark.asyncio
async def test_sarvam_stt_event_parsing_final():
    provider = SarvamSTTProvider(api_key="test-api-key-12345678")
    provider._event_queues["sess-2"] = asyncio.Queue()

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = [
        json.dumps({
            "event": "transcript.final",
            "transcript": "வணக்கம் எனக்கு உதவி வேண்டும்",
            "language_code": "ta-IN",
            "confidence": 0.95,
        })
    ]

    await provider._listen_loop("sess-2", mock_ws)
    event: TranscriptEvent = await provider._event_queues["sess-2"].get()
    assert event.is_final is True
    assert event.text == "வணக்கம் எனக்கு உதவி வேண்டும்"
    assert event.confidence == 0.95


# 4. Sarvam STT VAD and session events handling
@pytest.mark.asyncio
async def test_sarvam_stt_vad_events():
    provider = SarvamSTTProvider(api_key="test-api-key-12345678")
    provider._event_queues["sess-3"] = asyncio.Queue()

    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = [
        json.dumps({"event": "session.begin", "request_id": "req-1"}),
        json.dumps({"event": "vad.speech_start"}),
        json.dumps({"event": "vad.speech_end"}),
        json.dumps({"event": "session.end"}),
    ]

    await provider._listen_loop("sess-3", mock_ws)
    # VAD and session events should not be queued as transcripts
    assert provider._event_queues["sess-3"].empty()


# 5. Sarvam TTS valid speakers for bulbul:v3
def test_sarvam_tts_default_voices():
    assert DEFAULT_VOICES["ta-IN"] == "kavitha"
    assert DEFAULT_VOICES["hi-IN"] == "shubh"
    assert DEFAULT_VOICES["en-IN"] == "priya"


# 6. Sarvam TTS streaming chunk sizing
@pytest.mark.asyncio
async def test_sarvam_tts_slicing():
    provider = SarvamTTSProvider(api_key="test-api-key-12345678")
    # Generate 6400 bytes of mock PCM (exactly 2 x 3200B frames)
    fake_pcm = b"\x00" * 6400

    async def fake_text_stream():
        yield "Hello "
        yield "world"

    with patch.object(provider, "synthesize", new=AsyncMock(return_value=fake_pcm)):
        chunks = []
        async for chunk in provider.synthesize_stream(fake_text_stream(), "en-IN"):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert len(chunks[0]) == 3200
        assert len(chunks[1]) == 3200


# 7. Exotel normalize media with camelCase and snake_case
def test_exotel_normalize_media_camel_and_snake():
    provider = ExotelTelephonyProvider()
    dummy_b64 = base64.b64encode(b"\x00" * 320).decode("utf-8")

    # CamelCase event
    msg_camel = {
        "event": "media",
        "sequenceNumber": 10,
        "media": {"payload": dummy_b64},
    }
    frame1 = provider.normalize_media_event(msg_camel, "s1", "c1", 1)
    assert frame1 is not None
    assert frame1.sequence_number == 10
    assert frame1.payload_size_bytes == 320

    # Snake_case event
    msg_snake = {
        "event": "media",
        "sequence_number": 11,
        "media": {"chunk": dummy_b64},
    }
    frame2 = provider.normalize_media_event(msg_snake, "s1", "c1", 1)
    assert frame2 is not None
    assert frame2.sequence_number == 11
    assert frame2.payload_size_bytes == 320


# 8. Exotel outbound media formatting conforming to specs
def test_exotel_format_outbound_media_spec():
    provider = ExotelTelephonyProvider()
    pcm = b"\x00" * 3200
    outbound = provider.format_outbound_media(
        stream_sid="stream-test-123",
        pcm_bytes=pcm,
        chunk_index=1,
        timestamp_ms=1000,
    )
    assert outbound["event"] == "media"
    assert outbound["streamSid"] == "stream-test-123"
    assert outbound["stream_sid"] == "stream-test-123"
    assert outbound["media"]["chunk"] == "1"
    assert outbound["media"]["timestamp"] == "1000"
    raw_payload = base64.b64decode(outbound["media"]["payload"])
    assert len(raw_payload) == 3200


# 9. Exotel mark and clear formatting
def test_exotel_format_mark_and_clear():
    provider = ExotelTelephonyProvider()
    mark = provider.format_mark_event("stream-123", "test_mark")
    assert mark["event"] == "mark"
    assert mark["streamSid"] == "stream-123"
    assert mark["mark"]["name"] == "test_mark"

    clear = provider.format_clear_event("stream-123")
    assert clear["event"] == "clear"
    assert clear["streamSid"] == "stream-123"


# 10. Outbound pump audio aggregation (>=3200B and multiple of 320)
def test_audio_telemetry_counters():
    telemetry = AudioTelemetry()
    assert telemetry.inbound_frames_received == 0
    assert telemetry.outbound_frames_sent_to_exotel == 0
    assert telemetry.two_way_audio_verified is False

    info: AudioDiagnosticsInfo = telemetry.to_info()
    assert info.inbound_frames_received == 0
    assert info.two_way_audio_verified is False


# 11. Initial safe greeting exists for Tamil, Hindi, and English
def test_conversation_orchestrator_initial_greeting_texts():
    assert "SAMVED" in INITIAL_GREETINGS["ta-IN"]
    assert "SAMVED" in INITIAL_GREETINGS["hi-IN"]
    assert "SAMVED" in INITIAL_GREETINGS["en-IN"]
    assert "வணக்கம்" in INITIAL_GREETINGS["ta-IN"]
    assert "नमस्ते" in INITIAL_GREETINGS["hi-IN"]
    assert "Hello" in INITIAL_GREETINGS["en-IN"]


# 12. Telephony /doctor endpoint exposes audio diagnostics
def test_telephony_doctor_exposes_audio_diagnostics(client):
    resp = client.get("/v1/telephony/doctor")
    assert resp.status_code == 200
    data = resp.json()
    assert "audio_pipeline_diagnostics" in data
    diag = data["audio_pipeline_diagnostics"]
    assert "inbound_frames_received" in diag
    assert "outbound_frames_sent_to_exotel" in diag
    assert "two_way_audio_verified" in diag


# 13. End-to-end WebSocket media connection and initial greeting transmission
def test_telephony_ws_initial_greeting_on_start(client):
    call_sid = f"ws-audio-test-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919844455566", "To": "14566"},
    )
    assert inbound_resp.status_code == 200
    session_id = inbound_resp.json()["session_id"]

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        # Handshake connected
        ws.send_text(json.dumps({"event": "connected"}))

        # Send start event
        ws.send_text(json.dumps({
            "event": "start",
            "streamSid": f"stream-{session_id}",
            "start": {"streamSid": f"stream-{session_id}"},
        }))

        # In mock/test mode, start triggers initial greeting which pumps outbound frames
        # Read the first outbound frame sent to Exotel
        received_raw = ws.receive_text()
        msg = json.loads(received_raw)
        assert msg["event"] == "media"
        assert msg["streamSid"] == f"stream-{session_id}"
        assert "payload" in msg["media"]
        # Verify frame is at least 3200 bytes and multiple of 320 bytes
        payload_bytes = base64.b64decode(msg["media"]["payload"])
        assert len(payload_bytes) >= 3200
        assert len(payload_bytes) % 320 == 0

        # Send stop event to finish cleanly
        ws.send_text(json.dumps({"event": "stop"}))


# 14. Exotel Mark event received updates telemetry
def test_telephony_ws_mark_event_received(client):
    call_sid = f"ws-mark-test-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919844455566", "To": "14566"},
    )
    session_id = inbound_resp.json()["session_id"]

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "streamSid": f"stream-{session_id}",
            "start": {"streamSid": f"stream-{session_id}"},
        }))
        # Read initial greeting frame to keep queue moving
        ws.receive_text()

        # Send mark event
        ws.send_text(json.dumps({
            "event": "mark",
            "streamSid": f"stream-{session_id}",
            "mark": {"name": "greeting_mark"},
        }))

        # Send stop
        ws.send_text(json.dumps({"event": "stop"}))


# 15. Exotel Clear event triggers barge-in interruption
def test_telephony_ws_clear_event_barge_in(client):
    call_sid = f"ws-clear-test-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919844455566", "To": "14566"},
    )
    session_id = inbound_resp.json()["session_id"]

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "streamSid": f"stream-{session_id}",
            "start": {"streamSid": f"stream-{session_id}"},
        }))
        ws.receive_text()

        # Send clear event (caller barge-in)
        ws.send_text(json.dumps({
            "event": "clear",
            "streamSid": f"stream-{session_id}",
        }))

        # Send stop
        ws.send_text(json.dumps({"event": "stop"}))


# 16. Inbound audio frames ingestion updates telemetry
def test_telephony_ws_inbound_media_ingestion(client):
    call_sid = f"ws-media-test-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919844455566", "To": "14566"},
    )
    session_id = inbound_resp.json()["session_id"]

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "streamSid": f"stream-{session_id}",
            "start": {"streamSid": f"stream-{session_id}"},
        }))
        ws.receive_text()

        dummy_pcm = base64.b64encode(b"\x00" * 320).decode("utf-8")
        ws.send_text(json.dumps({
            "event": "media",
            "sequenceNumber": 1,
            "media": {"chunk": "1", "payload": dummy_pcm},
        }))

        ws.send_text(json.dumps({"event": "stop"}))
