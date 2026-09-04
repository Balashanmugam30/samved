# SAMVED — Voice Gateway Service (`services/voice-gateway`)

## Purpose
The Voice Gateway manages bidirectional real-time audio streaming between telephony providers (Exotel / Twilio) and internal SAMVED audio pipelines.

## Architectural Responsibility
- Ingest live audio streams (8kHz / 16kHz PCM / μ-law / Opus) from telecom webhooks and media streams.
- Chunk, buffer, and dispatch audio frames to Indian-language STT engines (Sarvam AI).
- Receive synthesized TTS audio streams from Sarvam and relay them back to the caller over the active telephony call leg.
- Support caller interruption / barge-in detection.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary established. Telephony interfaces and mock audio stream providers defined in `apps/api/app/providers/telephony.py`.
- **Phase 1 (Upcoming)**: Real Exotel Voice Streaming integration, SIP/WebRTC ingress, media stream WebSocket handlers.
- **Phase 2 (Upcoming)**: Full duplex audio pipeline connecting Exotel to Sarvam STT/TTS.
