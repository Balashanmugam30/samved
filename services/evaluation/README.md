# SAMVED — Evaluation & Benchmarking Service (`services/evaluation`)

## Purpose
Continuous offline and shadow evaluation of speech recognition, multilingual dialogue, deterministic safety triggers, risk index calibration, and operator alignment.

## Core Evaluation Dimensions
1. **ASR Quality**: Word Error Rate (WER) and Character Error Rate (CER) across 11 Indian languages and acoustic noise profiles (low SNR, mobile codecs).
2. **Safety Recall**: Critical safety signal recall (Target: 100% recall on high-threat triggers; zero tolerance for false negatives on imminent harm).
3. **Escalation Precision & Operator Override Rate**: Measuring the rate at which human operators accept vs. override SAMVED automated recommendations.
4. **Code-Switching Robustness**: Dialect and Hinglish/Tanglish/Tenglish conversational handling.
5. **Turn Latency**: Measuring end-of-speech to start-of-audio TTS latency to ensure natural real-time telephony pacing (<1200ms).

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary, synthetic scenario schema (`EvaluationScenario`), and initial synthetic benchmark fixtures in `scenarios/`.
- **Phase 14 (Upcoming)**: Automated benchmark harness, shadow evaluation runner, and metric tracking dashboard.
