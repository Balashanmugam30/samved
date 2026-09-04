# SAMVED — Acoustic Signal Engine (`services/acoustic-engine`)

## Purpose
Extracts non-verbal acoustic and paralinguistic cues from caller speech streams to provide supporting signals for triage prioritization.

## Acoustic Signals Extracted
- Fundamental frequency (Pitch / F0) and pitch variation
- Speaking rate (words / syllables per minute)
- Pause frequency and silence-to-speech ratio
- Energy / root-mean-square (RMS) intensity
- Micro-tremor indicators (Jitter and Shimmer)
- Voice stability and turn-taking response latency

## Critical Ethical & Architectural Invariant
> **Voice/acoustic signals are supporting evidence and must never be represented as clinical diagnoses or definitive proof of trauma.**

Public or acted datasets used during training/testing provide baseline signal extraction capability, not clinical trauma ground truth.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary and `ACOUSTIC_UPDATE` event schema.
- **Phase 6 (Upcoming)**: DSP feature extraction pipeline, streaming audio buffer analysis, and non-blocking background signal emission.
