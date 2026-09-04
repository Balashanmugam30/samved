# Sarvam AI Realtime Speech Integration (STT & TTS)

## 1. Overview
SAMVED utilizes **Sarvam AI** for low-latency Indian multilingual speech processing:
- **Speech-to-Text (STT)**: `saaras:v3-realtime` streaming bidirectional WebSocket.
- **Text-to-Speech (TTS)**: `bulbul:v3` REST synthesis configured for native 8000Hz sampling rate.

Target Helplines (NHAA 14566) require robust handling of Indian regional languages and accents, beginning with **Tamil (`ta-IN`)**, **Hindi (`hi-IN`)**, and **Indian English (`en-IN`)**.

---

## 2. Realtime Streaming STT (`saaras:v3`)

### 2.1 Transport Architecture
- **Protocol**: WebSocket over TLS (`wss://api.sarvam.ai/speech-to-text-realtime/ws`).
- **Auth Header**: `api-subscription-key: <SARVAM_API_KEY>`.
- **Audio Framing**: 16-bit Linear PCM, 8000Hz mono, 20ms frames (320 bytes).

```
Exotel 8kHz PCM (320B)
       │
       ▼
AudioAdapter (RMS Energy & VAD)
       │
       ▼
SarvamSTTProvider.send_audio_chunk()
       │
       ▼ (WebSocket Binary Frames)
Sarvam Cloud STT Engine
       │
       ▼ (JSON Text Events)
TranscriptEvent (partial / final)
       │
       ▼
ConversationOrchestrator
```

### 2.2 Transcript Event Parsing
Sarvam STT returns structured JSON messages indicating partial drafts or final turn boundaries:
```json
{
  "type": "transcript",
  "data": {
    "transcript": "வணக்கம் எனக்கு உதவி வேண்டும்",
    "is_final": true,
    "confidence": 0.96,
    "language_code": "ta-IN",
    "start_time": 0,
    "end_time": 1820
  }
}
```
- When `is_final == false`: Orchestrator transitions to `TRANSCRIBING` and broadcasts `TRANSCRIPT_PARTIAL` to the operator UI.
- When `is_final == true`: Turn boundary reached. Orchestrator records caller utterance, calculates latency, transitions to `THINKING`, and triggers Gemini reasoning.

---

## 3. Realtime Speech Synthesis (`bulbul:v3`)

### 3.1 8000Hz WAV Header Stripping
Exotel telephony requires raw 16-bit 8000Hz Linear PCM without container headers. Sarvam Bulbul produces standard 8kHz WAV files with a 44-byte RIFF/WAVE header:

```python
def strip_wav_header(wav_bytes: bytes) -> bytes:
    """Strips standard 44-byte RIFF header to yield raw PCM frames."""
    if len(wav_bytes) > 44 and wav_bytes[:4] == b"RIFF" and wav_bytes[8:12] == b"WAVE":
        return wav_bytes[44:]
    return wav_bytes
```

This yields raw 16-bit Linear PCM audio that is sliced into 320-byte (20ms) canonical `AudioFrame`s and pushed directly to `session.outbound_queue`.

### 3.2 Voice Persona Mapping
| Language Code | Language | Voice Model | Persona / Pitch |
| :--- | :--- | :--- | :--- |
| `ta-IN` | Tamil | `bulbul:v3` | `ananya` (Empathetic, clear, helpline pace) |
| `hi-IN` | Hindi | `bulbul:v3` | `aditi` (Supportive, calm, national standard) |
| `en-IN` | Indian English | `bulbul:v3` | `priya` (Professional, empathetic) |

---

## 4. Deterministic DEV & SIMULATION Mode
In local development, automated CI, and offline hackathon testing:
- Paid API keys are **not required**.
- `MockSpeechToTextProvider` deterministically simulates partial and final transcripts in Tamil, Hindi, and English.
- `MockTextToSpeechProvider` generates canonical 320-byte 8kHz PCM audio frames.
- Tests execute in milliseconds without external network dependencies.
