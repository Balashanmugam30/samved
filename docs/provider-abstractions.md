# SAMVED — Provider Abstractions & Adapter Architecture

## 1. Architectural Motivation
Vendor lock-in is a critical risk for government-grade systems. SAMVED isolates all external telephony, speech, and AI provider mechanics behind strict Python Protocols and abstract interfaces.

### Core Benefits
1. **Replaceability**: The system can switch between Exotel and Twilio, Sarvam and alternative speech engines, or Google Gemini and OpenAI without altering core business rules or safety logic.
2. **Cost & Credit Conservation**: During local development and automated CI testing, deterministic mock providers simulate real audio streams without incurring API costs.
3. **Resilience & Fallback**: Runtime fallback mechanisms can route to secondary providers if a primary provider experiences downtime.

---

## 2. Core Provider Interfaces

### 1. `TelephonyProvider` (`app/providers/base.py`)
```python
class TelephonyProvider(Protocol):
    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str: ...
    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool: ...
    async def health_check(self) -> Dict[str, Any]: ...
```
- **Phase 1 Status**: `ExotelTelephonyProvider` (`app/providers/exotel.py`) implemented with REST client, webhook signature verification, and 8kHz PCM streaming normalizer. `MockTelephonyProvider` provides deterministic synthetic audio frame simulation.
- **Secondary Provider**: Twilio Media Streams (conforms to same `TelephonyProvider` Protocol).

---

### 2. `SpeechToTextProvider` (`app/providers/base.py`)
```python
class SpeechToTextProvider(Protocol):
    async def start_stream(self, session_id: str, language_code: str) -> bool: ...
    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None: ...
    async def receive_transcripts(self, session_id: str) -> AsyncIterator[Dict[str, Any]]: ...
    async def close_stream(self, session_id: str) -> None: ...
```
- **Phase 2 Status**: `SarvamSTTProvider` (`app/providers/sarvam_stt.py`) implemented with realtime WebSocket client (`saaras:v3`), token streaming, and partial/final event extraction. `MockSpeechToTextProvider` provides deterministic multi-turn simulation across Tamil, Hindi, and English.
- **Target LIVE Provider**: Sarvam AI Indian-Language Streaming STT (`saaras:v3`).

---

### 3. `TextToSpeechProvider` (`app/providers/base.py`)
```python
class TextToSpeechProvider(Protocol):
    async def synthesize(self, text: str, language_code: str, voice_id: Optional[str] = None) -> bytes: ...
    async def synthesize_stream(self, text_iterator: AsyncIterator[str], language_code: str) -> AsyncIterator[bytes]: ...
```
- **Phase 2 Status**: `SarvamTTSProvider` (`app/providers/sarvam_tts.py`) implemented with `bulbul:v3` REST synthesis, 8000Hz PCM mode, and 44-byte WAV header stripping. `MockTextToSpeechProvider` generates canonical 320-byte 8kHz PCM audio frames.
- **Target LIVE Provider**: Sarvam AI Multilingual Bulbul TTS (`bulbul:v3`).

---

### 4. `LLMProvider` (`app/providers/base.py`)
```python
class LLMProvider(Protocol):
    async def generate_response(self, system_prompt: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str: ...
    async def generate_structured_output(self, system_prompt: str, messages: List[Dict[str, str]], schema_model: Any) -> Dict[str, Any]: ...
```
- **Phase 2 Status**: `GeminiLLMProvider` (`app/providers/gemini.py`) implemented with `gemini-2.5-flash`, structured JSON schema enforcement, voice response sanitization, and fallback recovery. `MockLLMProvider` provides deterministic multi-turn responses and safety triggers.
- **Target LIVE Provider**: Google Gemini 2.5 Flash via Google AI Studio / Vertex AI.
- **Alternative Providers**: OpenRouter, OpenAI GPT-4o.
