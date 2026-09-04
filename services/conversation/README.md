# SAMVED — Conversation Engine (`services/conversation`)

## Purpose
The Conversation Engine orchestrates the dynamic dialogue state machine, turn-taking, contextual prompt synthesis, and conversational guardrails for the live helpline agent.

## Architectural Responsibility
- Track dialogue state across turns (Caller statement → Interpretation → Context update → Determine missing info → Choose next-best question → Response generation).
- Handle multi-lingual turn transitions (e.g. Hindi, Tamil, Telugu, Indian English, code-switching).
- Enforce conversational pacing, empathy guidelines, and grounding without clinical diagnosis or therapeutic claims.
- Manage barge-in events and conversational repairs.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary established. Dialogue schemas and turn contracts defined.
- **Phase 2 (Upcoming)**: Sarvam STT/TTS + Gemini conversation loop.
- **Phase 7 (Upcoming)**: Advanced adaptive conversation, state tracking, and barge-in recovery.
