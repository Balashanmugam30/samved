import base64
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AudioDirection(str, Enum):
    INBOUND = "INBOUND"    # Caller audio -> SAMVED Gateway -> (Future STT)
    OUTBOUND = "OUTBOUND"  # (Future TTS) -> SAMVED Gateway -> Caller audio


class AudioFormat(BaseModel):
    codec: str = "pcm_s16le"
    sample_rate_hz: int = 8000
    channels: int = 1
    sample_width_bytes: int = 2
    encoding: str = "base64"
    frame_duration_ms: int = 20  # standard 20ms frame = 160 samples = 320 bytes at 8kHz


class AudioFrame(BaseModel):
    """Canonical internal audio frame model."""
    frame_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    call_id: str
    sequence_number: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    direction: AudioDirection = AudioDirection.INBOUND
    codec: str = "pcm_s16le"
    sample_rate_hz: int = 8000
    channels: int = 1
    payload_base64: str
    payload_size_bytes: int

    def get_raw_bytes(self) -> bytes:
        return base64.b64decode(self.payload_base64)


# Exotel Inbound Webhook Payload (HTTP Form or JSON)
class ExotelInboundPayload(BaseModel):
    CallSid: str
    From: str
    To: str
    Direction: Optional[str] = "inbound"
    CallType: Optional[str] = "trans"
    Created: Optional[str] = None
    DialWhomNumber: Optional[str] = None


# Exotel Status Callback Payload
class ExotelStatusPayload(BaseModel):
    CallSid: str
    Status: str
    DialCallDuration: Optional[int] = None
    RecordingUrl: Optional[str] = None
    EventType: Optional[str] = None


# Exotel Realtime WebSocket Message Schemas
class ExotelMediaEvent(str, Enum):
    CONNECTED = "connected"
    START = "start"
    MEDIA = "media"
    MARK = "mark"
    CLEAR = "clear"
    STOP = "stop"


class ExotelStartData(BaseModel):
    streamSid: Optional[str] = None
    stream_sid: Optional[str] = None
    accountSid: Optional[str] = None
    callSid: Optional[str] = None
    call_sid: Optional[str] = None
    tracks: Optional[List[str]] = Field(default_factory=lambda: ["inbound"])
    mediaFormat: Optional[Dict[str, Any]] = None
    customParameters: Optional[Dict[str, Any]] = None


class ExotelMediaData(BaseModel):
    track: Optional[str] = "inbound"
    chunk: Optional[str] = None
    timestamp: Optional[str] = None
    payload: Optional[str] = None  # Base64 encoded audio bytes


class ExotelWebSocketMessage(BaseModel):
    event: ExotelMediaEvent
    sequenceNumber: Optional[int] = None
    streamSid: Optional[str] = None
    stream_sid: Optional[str] = None
    start: Optional[ExotelStartData] = None
    media: Optional[ExotelMediaData] = None
    stop: Optional[Dict[str, Any]] = None


class ExotelOutboundMediaMessage(BaseModel):
    event: str = "media"
    streamSid: str
    media: Dict[str, str]  # {"payload": base64_encoded_pcm}


# Diagnostics & Telephony Session Summaries
class TelephonySessionInfo(BaseModel):
    session_id: str
    call_id: str
    provider_call_id: str
    provider: str
    caller_masked_number: str
    state: str
    connected_at: Optional[str] = None
    last_activity_at: str
    audio_format: AudioFormat
    inbound_frames_count: int = 0
    inbound_bytes_count: int = 0
    sequence_gaps_count: int = 0
    dropped_frames_count: int = 0
    conversation_state: Optional[str] = None
    current_language: Optional[str] = None
    utterances_count: int = 0
    is_active: bool = True


class SimulationCallRequest(BaseModel):
    caller_phone: str = "+919876543210"
    duration_frames: int = 15  # Number of synthetic 20ms audio frames to stream
    frame_interval_ms: int = 50
    simulate_gap: bool = False
