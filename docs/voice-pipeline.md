# Real-Time Voice Pipeline & Barge-In Architecture

## 1. End-to-End Conversational Loop

SAMVED connects live telephony media to conversational AI via a low-latency, asynchronous loop:

```
                  ┌───────────────────────────────┐
                  │       REAL MOBILE PHONE       │
                  └──────────────┬────────────────┘
                                 │ Inbound PSTN Call (14566)
                                 ▼
                  ┌───────────────────────────────┐
                  │            EXOTEL             │
                  └──────────────┬────────────────┘
                                 │ Inbound Webhook / Media WS
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │                   SAMVED TELEPHONY BACKEND                      │
 │                                                                 │
 │   Inbound Stream                                                │
 │   16-bit 8000Hz PCM                                             │
 │          │                                                      │
 │          ▼                                                      │
 │   AudioAdapter ──(Voice Activity / Energy)────────────────┐     │
 │          │                                                │     │
 │          ▼                                                │     │
 │   Sarvam STT Provider (saaras:v3-realtime)                │     │
 │          │                                                │     │
 │          ▼ (TranscriptEvent: partial / final)             │     │
 │   ConversationOrchestrator ◄──────────────────────────────┘     │
 │          │                   (Barge-in Trigger)                 │
 │          ▼                                                      │
 │   Gemini LLM Provider (gemini-2.5-flash)                        │
 │          │                                                      │
 │          ▼ (Structured ConversationalResponse)                  │
 │   Sarvam TTS Provider (bulbul:v3 @ 8000Hz)                      │
 │          │                                                      │
 │          ▼ (320B PCM Frames)                                    │
 │   TelephonySession.outbound_queue                               │
 │          │                                                      │
 └──────────┼──────────────────────────────────────────────────────┘
            │ Outbound Media WebSocket
            ▼
    ┌───────────────┐
    │    EXOTEL     │
    └───────┬───────┘
            │ Spoken Audio Feedback
            ▼
    ┌───────────────┐
    │ CALLER PHONE  │
    └───────────────┘
```

---

## 2. Orchestrator State Machine

```
              ┌───────────────┐
              │     IDLE      │
              └───────┬───────┘
                      │ Call Connected
                      ▼
     ┌──────────► LISTENING ◄─────────────┐
     │                │                   │
     │                │ Partial STT       │ Turn Completed /
     │                ▼                   │ Barge-in Cleared
     │          TRANSCRIBING              │
     │                │                   │
     │                │ Final STT         │
     │                ▼                   │
     │             THINKING               │
     │                │                   │
     │                │ Structured Turn   │
     │                ▼                   │
     │             SPEAKING               │
     │                │                   │
     │                │ Caller Speaks     │
     │                ▼                   │
     └───────── INTERRUPTED ──────────────┘
```

---

## 3. Barge-In / Interruption Engine

Natural conversation requires that a caller can interrupt the AI at any time. When SAMVED is in `SPEAKING` state:
1. Inbound audio frames are monitored for RMS energy above threshold ($> 350.0$), or Exotel sends a `CLEAR` command.
2. `orchestrator.interrupt(reason="caller_barge_in")` is invoked immediately.
3. The background synthesis task (`_current_speech_task`) is cancelled via `asyncio.Task.cancel()`.
4. `session.outbound_queue` is drained completely to stop buffered audio from being transmitted to the caller.
5. An Exotel `clear` frame is queued to flush carrier hardware buffers.
6. A `SPEECH_INTERRUPTED` domain event is broadcast to the operator UI.
7. State immediately resets to `LISTENING`.

---

## 4. Multi-Turn Simulation Scenarios
SAMVED includes built-in realistic simulation scenarios callable via `/v1/telephony/simulate/conversation` and the Web UI:
- `tamil_help`: Emergency distress query and safety verification in Tamil (`ta-IN`).
- `hindi_help`: De-addiction assistance inquiry in Hindi (`hi-IN`).
- `english_help`: Legal guidance request in Indian English (`en-IN`).
- `code_switch`: Code-switching turn handling between Tamil and English.
- `interruption`: Mid-speech interruption and immediate queue draining.
