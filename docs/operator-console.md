# SAMVED Operator Console & Realtime Transcript Platform

The Operator Console is SAMVED's real-time observation and supervisory interface designed for helpline supervisors, call evaluators, and automated QA. It enables non-intrusive, low-latency monitoring of live multilingual calls without streaming heavy raw audio frames to the browser.

---

## 1. Architectural Overview

```
                        ┌───────────────────────────────┐
                        │   Exotel Telephony Ingress    │
                        │ (Linear PCM 8kHz mono 20ms)   │
                        └──────────────┬────────────────┘
                                       │ /ws/telephony/exotel
                                       ▼
                        ┌───────────────────────────────┐
                        │ Realtime Telephony Gateway    │
                        │  & Session State Machine      │
                        └──────────────┬────────────────┘
                                       │ AudioFrames
                                       ▼
                        ┌───────────────────────────────┐
                        │ Conversation Turn Orchestrator│
                        │ (Sarvam STT → Gemini → Bulbul)│
                        └──────────────┬────────────────┘
                                       │ Domain & Latency Events
                                       ▼
                        ┌───────────────────────────────┐
                        │ Realtime Session Manager      │
                        │  Bounded Ring Buffers         │
                        └──────────────┬────────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
                ▼ /ws/operator                                ▼ /v1/calls
    ┌───────────────────────────┐                 ┌───────────────────────────┐
    │ Dedicated Operator WS     │                 │ REST Snapshot APIs        │
    │ (Filtered JSON Envelope)  │                 │ (Calls, Turns, History)   │
    └───────────┬───────────────┘                 └───────────┬───────────────┘
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │ Next.js 14 Operator Console   │
                        │ (/calls - Master/Detail View) │
                        └───────────────────────────────┘
```

---

## 2. Dedicated Operator WebSocket (`/ws/operator`)

To protect operator network bandwidth and isolate audio data, the operator channel streams **only structured JSON event envelopes** (`EventEnvelope`), completely separated from the 8kHz binary audio transport.

### 2.1 Initial Connection Handshake & Snapshot
Upon connecting to `/ws/operator`, the backend immediately transmits an `OPERATOR_SNAPSHOT` envelope containing the current state:

```json
{
  "event_id": "0dfa0d1e-e2b2-4d2b-a37a-fcaeb3544321",
  "event_type": "OPERATOR_SNAPSHOT",
  "schema_version": "1.0",
  "timestamp": "2026-09-04T15:30:00.000Z",
  "session_id": "operator-session",
  "call_id": "global",
  "payload": {
    "system_mode": "DEV",
    "active_calls": [
      {
        "session_id": "sess-a1",
        "call_id": "call-1234",
        "caller_masked_number": "+91******3210",
        "state": "CONNECTED",
        "conversation_state": "LISTENING",
        "current_language": "ta-IN",
        "duration_seconds": 18.5,
        "utterances_count": 4,
        "is_active": true
      }
    ],
    "recent_calls": [],
    "total_active": 1,
    "total_recent": 0,
    "total_operators": 1
  }
}
```

### 2.2 Operator Inbound Actions
The operator console can send control messages over the WebSocket:

1. **Subscribe to a Specific Call**:
   ```json
   {
     "action": "SUBSCRIBE_CALL",
     "call_id": "call-1234"
   }
   ```
   The backend filters the event stream to only deliver events matching `call-1234` or global announcements.

2. **Subscribe to All Calls**:
   ```json
   {
     "action": "SUBSCRIBE_ALL"
   }
   ```
   The backend delivers events across all active calls.

3. **Liveness Ping**:
   ```json
   {
     "action": "PING"
   }
   ```
   Responds immediately with `HEARTBEAT_PONG`.

---

## 3. REST Snapshot Endpoints

The operator console uses REST endpoints for snapshot recovery, page refreshes, and deep inspection:

- `GET /v1/calls`: Returns structured lists of active and recently completed calls with duration, masked numbers, and state.
- `GET /v1/calls/{call_id}`: Retrieves single call metadata and duration.
- `GET /v1/calls/{call_id}/transcript`: Returns chronological list of all caller and AI utterances for the call.
- `GET /v1/calls/{call_id}/events`: Returns the bounded event history (up to 100 recent domain events).

---

## 4. Conversation States & Timeline Filters

### 4.1 Dialogue State Machine
The operator console tracks the conversational turn lifecycle in real time:

- **`LISTENING`**: Caller channel open; waiting for voice activity.
- **`TRANSCRIBING`**: Voice detected; receiving provisional partial draft tokens.
- **`THINKING`**: Final caller transcript sealed; Gemini reasoning active.
- **`SPEAKING`**: Sarvam Bulbul TTS streaming synthesized audio back to caller.
- **`INTERRUPTED`**: Barge-in detected; AI cancelled synthesis and yielded floor.
- **`ENDING`**: Normal wrap-up or caller disconnect.
- **`ERROR`**: Transport or provider error with fallback response.

### 4.2 Timeline Category Filters
Operators can filter the high-density event stream by category:
- **`ALL`**: Complete chronological timeline.
- **`TRANSCRIPT`**: Partial and final transcripts, language detection events.
- **`CONVERSATION`**: State changes, AI response events, TTS start/end, barge-in.
- **`ERRORS`**: Transport errors, STT/LLM/TTS errors, safety alerts.
- **`LATENCY`**: Real-time turn latency metrics (`stt_ms`, `llm_ms`, `tts_ms`, `total_turn_ms`).

---

## 5. Caller Privacy & Data Retention

1. **Phone Number Masking**: Raw telephone numbers are isolated to internal telephony session handlers and never exposed in REST responses or operator UI (`+91******3210`).
2. **Zero Audio Retention**: Audio frames are transiently processed in memory and discarded upon playback. No raw audio files are written to disk.
3. **Bounded In-Memory Ring Buffers**:
   - `100 events` maximum per call session.
   - `50 completed calls` retained in recent history before FIFO eviction.
