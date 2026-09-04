import asyncio
import base64
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from app.providers.base import (
    LLMProvider,
    SpeechToTextProvider,
    TelephonyProvider,
    TextToSpeechProvider,
)
from app.schemas.conversation import ConversationalResponse, TranscriptEvent


class MockTelephonyProvider:
    """Deterministic mock telephony provider for testing and DEV mode."""

    def __init__(self, configured: bool = True):
        self.configured = configured
        self.active_calls: Dict[str, Dict[str, Any]] = {}

    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str:
        call_id = f"mock-call-{uuid.uuid4().hex[:8]}"
        self.active_calls[call_id] = {
            "to": to_number,
            "from": from_number,
            "status": "connected",
            "metadata": metadata,
        }
        return call_id

    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id]["status"] = "terminated"
            self.active_calls[call_id]["reason"] = reason
            return True
        return False

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "MockTelephony",
            "status": "healthy" if self.configured else "unconfigured",
            "active_calls_count": len(self.active_calls),
        }

    def validate_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        return True

    def create_streaming_instruction(self, session_id: str, ws_stream_url: str) -> Dict[str, Any]:
        return {
            "action": "stream",
            "stream_url": ws_stream_url,
            "session_id": session_id,
            "format": "pcm_8000_16bit_mono",
        }

    def format_outbound_media(self, stream_sid: str, pcm_bytes: bytes) -> Dict[str, Any]:
        return {
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": base64.b64encode(pcm_bytes).decode("utf-8")},
        }

    def generate_synthetic_frames(
        self, session_id: str, call_id: str, count: int = 10, simulate_gap: bool = False
    ) -> List[Dict[str, Any]]:
        frames = []
        seq = 1
        dummy_pcm = b"\x00\x01" * 160  # 320 bytes = 20ms of 8kHz 16-bit mono PCM
        b64_pcm = base64.b64encode(dummy_pcm).decode("utf-8")

        for i in range(count):
            if simulate_gap and i == 3:
                seq += 2  # Introduce an intentional gap (skip sequence 4)
            frames.append({
                "event": "media",
                "sequenceNumber": seq,
                "streamSid": f"stream-{session_id}",
                "media": {
                    "track": "inbound",
                    "chunk": str(seq),
                    "timestamp": str(seq * 20),
                    "payload": b64_pcm,
                },
            })
            seq += 1
        return frames


class MockSpeechToTextProvider:
    """Deterministic mock STT provider supporting multilingual transcripts and scenarios."""

    def __init__(self):
        self.sessions: Dict[str, List[bytes]] = {}
        self.session_languages: Dict[str, str] = {}
        self.scripted_turns: Dict[str, List[Dict[str, Any]]] = {}

    def set_scripted_turns(self, session_id: str, turns: List[Dict[str, Any]]) -> None:
        self.scripted_turns[session_id] = turns

    async def start_stream(self, session_id: str, language_code: str = "unknown") -> bool:
        self.sessions[session_id] = []
        self.session_languages[session_id] = language_code
        return True

    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].append(chunk_bytes)

    async def receive_transcripts(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        # If predefined script exists for this session, yield it
        if session_id in self.scripted_turns:
            for item in self.scripted_turns[session_id]:
                yield TranscriptEvent(
                    session_id=session_id,
                    call_id=session_id,
                    speaker=item.get("speaker", "caller"),
                    text=item["text"],
                    confidence=item.get("confidence", 0.95),
                    is_final=item.get("is_final", True),
                    language=item.get("language", "en-IN"),
                )
                await asyncio.sleep(0.01)
            return

        lang = self.session_languages.get(session_id, "ta-IN")
        if lang == "hi-IN":
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Namaste, main...",
                confidence=0.88,
                is_final=False,
                language="hi-IN",
            )
            await asyncio.sleep(0.01)
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Namaste, mujhe sahayata chahiye.",
                confidence=0.97,
                is_final=True,
                language="hi-IN",
            )
        elif lang == "en-IN":
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Hello, I need...",
                confidence=0.88,
                is_final=False,
                language="en-IN",
            )
            await asyncio.sleep(0.01)
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Hello, I need urgent assistance.",
                confidence=0.97,
                is_final=True,
                language="en-IN",
            )
        else:
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Vanakkam, enakku romba bayama...",
                confidence=0.88,
                is_final=False,
                language="ta-IN",
            )
            await asyncio.sleep(0.01)
            yield TranscriptEvent(
                session_id=session_id,
                call_id=session_id,
                speaker="caller",
                text="Vanakkam, enakku romba bayama irukku.",
                confidence=0.97,
                is_final=True,
                language="ta-IN",
            )

    async def close_stream(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
        self.session_languages.pop(session_id, None)
        self.scripted_turns.pop(session_id, None)


class MockTextToSpeechProvider:
    """Deterministic mock TTS provider generating canonical 320-byte 8000Hz PCM frames."""

    async def synthesize(
        self, text: str, language_code: str = "en-IN", voice_id: Optional[str] = None
    ) -> bytes:
        # Generate 10 frames of 320-byte 8kHz PCM = 3200 bytes (~200ms audio)
        frame = b"\x00\x02" * 160
        return frame * 10

    async def synthesize_stream(
        self, text_iterator: AsyncIterator[str], language_code: str
    ) -> AsyncIterator[bytes]:
        async for chunk in text_iterator:
            # 320 bytes per frame
            yield b"\x00\x02" * 160


class MockLLMProvider:
    """Deterministic mock LLM provider generating structured responses across languages."""

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        last_text = messages[-1]["content"] if messages else ""
        if "de-addiction" in last_text.lower():
            return f"Mock response acknowledging: {last_text}"
        resp = await self.generate_conversational_response(messages)
        return resp.response_text

    async def generate_conversational_response(
        self,
        messages: List[Dict[str, str]],
        language: str = "en-IN",
    ) -> ConversationalResponse:
        last_text = messages[-1]["content"].lower() if messages else ""

        # Check for safety / threat indicators
        is_threat = any(k in last_text for k in ["threat", "danger", "kill", "outside", "gun", "weapon", "bayama", "attack"])

        # Determine language matching
        is_tamil = (
            language.startswith("ta")
            or any(w in last_text for w in ["vanakkam", "enakku", "irukku", "tamil", "amma", "வணக்கம்", "உதவி"])
            or any("\u0b80" <= ch <= "\u0bff" for ch in last_text)
        )
        is_hindi = (
            language.startswith("hi")
            or any(w in last_text for w in ["namaste", "madad", "sahayata", "chahiye", "hindi", "bachao", "नमस्ते", "सहायता"])
            or any("\u0900" <= ch <= "\u097f" for ch in last_text)
        )

        if is_tamil:
            lang = "ta-IN"
            if is_threat:
                reply = "அமைதியாக இருங்கள். நீங்கள் இப்போது பாதுகாப்பான இடத்தில் இருக்கிறீர்களா?"
                intent = "IMMEDIATE_SAFETY_CHECK"
            else:
                reply = "வணக்கம். நான் உங்கள் குரலைக் கேட்கிறேன். உங்களுக்கு எப்படி உதவ முடியும்?"
                intent = "GREETING_ACK"
        elif is_hindi:
            lang = "hi-IN"
            if is_threat:
                reply = "शांत रहें। क्या आप इस समय किसी सुरक्षित स्थान पर हैं?"
                intent = "IMMEDIATE_SAFETY_CHECK"
            else:
                reply = "नमस्ते। मैं आपकी सहायता के लिए उपस्थित हूँ। क्या हुआ है?"
                intent = "GREETING_ACK"
        else:
            lang = "en-IN"
            if is_threat:
                reply = "Please stay calm. Are you in a safe room or location right now?"
                intent = "IMMEDIATE_SAFETY_CHECK"
            else:
                reply = "Hello, I am listening to you. Can you tell me what happened?"
                intent = "GREETING_ACK"

        return ConversationalResponse(
            response_text=reply,
            detected_intent=intent,
            conversation_state="EMERGENCY_SUPPORT" if is_threat else "ENGAGED",
            next_action="SAFETY_HOOK" if is_threat else "CONTINUE",
            language=lang,
            confidence=0.96,
            safety_flag=is_threat,
        )

    async def generate_structured_output(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        schema_model: Any,
    ) -> Dict[str, Any]:
        last_text = messages[-1]["content"] if messages else ""
        if "extract entities" in system_prompt.lower() or "alcohol addiction" in last_text.lower():
            return {
                "intent": "INQUIRY_DE_ADDICTION",
                "entities": {"location": "Jaipur", "category": "alcohol"},
            }
        resp = await self.generate_conversational_response(messages)
        return resp.model_dump()