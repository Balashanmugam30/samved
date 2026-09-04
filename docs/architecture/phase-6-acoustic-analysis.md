# SAMVED Phase 6 — Acoustic Analysis Engine & Non-Verbal Signal Layer

## 1. Executive Summary & Goals

The **Acoustic Analysis Engine** provides NHAA 14566 crisis helpline operators with real-time, explainable, and deterministic non-verbal speech indicators derived directly from canonical 8kHz PCM telephony audio.

### Goals
- Process canonical 20ms audio frames (8kHz, 16-bit signed mono PCM) downstream of telephony ingress without duplicating audio transport.
- Extract objective physical speech features: voice activity ratio, silence/pause duration, turn duration, barge-in/interruption patterns, energy RMS & variability, clipping, and bounded fundamental frequency ($F_0$).
- Detect evidence-based operational signals (e.g., `PROLONGED_SILENCE_OBSERVED`, `FREQUENT_INTERRUPTION_PATTERN`, `HIGH_SPEECH_ACTIVITY`, `AUDIO_QUALITY_LOW`).
- Provide human operators with actionable contextual triage awareness via the Next.js Operator Console (`/calls`).
- Maintain strict sub-5ms deterministic performance without dependency on heavy generative AI or external LLM inference.
- Preserve complete privacy: ephemeral in-memory processing only, zero raw audio disk persistence, and zero biometric profiling.

### Strict Non-Goals (Ethical Boundaries)
- ❌ **NO Clinical Diagnosis**: No inferences of clinical depression, PTSD, anxiety disorders, panic attacks, or trauma.
- ❌ **NO Lie Detection or Credibility Scoring**: No truthfulness assessment, deception detection, or guilt evaluation.
- ❌ **NO Autonomous Dispatch**: Acoustic signals can never independently trigger police, emergency medical, or welfare dispatches.
- ❌ **NO Biometric Profiling**: No voiceprints, speaker identity embeddings, accent recognition, or demographic inference.
- ❌ **NO Safety State Override**: The Phase 4 Deterministic Safety Engine remains strictly authoritative; acoustic data cannot override safety signals or lower critical safety floors.

---

## 2. Canonical Telephony Audio Ingress

SAMVED standardizes telephony ingress on 8kHz 16-bit signed linear PCM:

```
📱 Caller Mobile Phone
         ↓
📞 Exotel Telephony Cloud
         ↓
⚡ WebSocket Media Ingress (/ws/telephony/exotel)
         ↓
Canonical AudioFrame (20ms, 160 samples, 320 bytes)
         ↓
┌────────────────────────────────────────────────────────┐
│             TelephonySession Ingest Pipeline           │
│                                                        │
│  1. Sequence gap & jitter tracking                     │
│  2. Inbound ring buffer storage (bounded)              │
│  3. Conversational Orchestrator (STT forwarding)       │
│  4. Acoustic Analysis Engine (Downstream Consumer)     │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             ACOUSTIC ANALYSIS ENGINE (v1.0.0)          │
│                                                        │
│  [Frame Layer] (20ms)                                  │
│   • Sample unpacking (<160h)                           │
│   • Clipping detection (|s_i| >= 32000)                │
│   • RMS Energy calculation                             │
│   • Zero-Crossing Rate (ZCR)                           │
│   • Bounded Autocorrelation Pitch (F0: 80–350 Hz)      │
│                                                        │
│  [Aggregation Layer] (Rolling Window & Turn Level)     │
│   • Voice Activity Ratio & Silence Ratio               │
│   • Pause Count, Mean Pause & Max Silence              │
│   • Turn Duration & Density                            │
│   • Interruption & Overlap Metrics                     │
│   • Energy Variability (Normalized StdDev)             │
│   • Audio Quality State & Confidence Computation       │
│                                                        │
│  [Operational Classifier Layer]                        │
│   • PROLONGED_SILENCE_OBSERVED                         │
│   • FREQUENT_INTERRUPTION_PATTERN                      │
│   • HIGH_SPEECH_ACTIVITY / LOW_VOICE_ACTIVITY          │
│   • ELEVATED_ENERGY_VARIABILITY                        │
│   • AUDIO_QUALITY_LOW / SIGNAL_INSUFFICIENT            │
└───────────────────────────┬────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
    ACOUSTIC_UPDATE Event           REST API Endpoints
     (ws/operator channel)          GET /v1/acoustic/calls/{id}
            │                       POST /v1/acoustic/evaluate
            ▼                               │
    Operator Console Panel                  ▼
     (/calls SVI & Acoustic)        SVI Context Grounding
```

---

## 3. Mathematical Feature Formulations

### 1. RMS Energy
$$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} s_i^2}$$
where $s_i \in [-32768, 32767]$ and $N = 160$ samples per 20ms frame at 8000 Hz.

### 2. Clipping Ratio
$$\text{Clipping Ratio} = \frac{\sum_{i=0}^{N-1} \mathbb{I}(|s_i| \ge 32000)}{N}$$
Flags analog/digital saturation and microphone overdrive.

### 3. Voice Activity Detection (VAD)
A 20ms frame is designated as voiced speech if:
$$\text{RMS} \ge \text{Threshold}_{\text{VAD}} \quad (\text{calibrated default } = 300.0)$$
$$\text{Speech Activity Ratio} = \frac{\text{Voiced Frames}}{\text{Total Window Frames}}$$

### 4. Bounded Autocorrelation Pitch ($F_0$)
For voiced frames, pitch period is bounded between $80\text{ Hz}$ ($k_{\max} = 100$ samples) and $350\text{ Hz}$ ($k_{\min} = 23$ samples):
$$R(k) = \sum_{n=0}^{N-1-k} s_n \cdot s_{n+k}$$
$$F_0 = \frac{f_s}{k^*} \quad \text{where } k^* = \arg\max_{k \in [23, 100]} \frac{R(k)}{\sqrt{\sum s_n^2 \sum s_{n+k}^2}}$$

### 5. Energy Variability
$$\text{CV}_{\text{energy}} = \frac{\sigma_{\text{RMS}}}{\mu_{\text{RMS}}}$$
Quantifies vocal dynamic range variation within the turn or evaluation window.

---

## 4. Operational Signal Vocabulary

| Signal Code | Trigger Condition | Explainable Evidence Chip |
|-------------|-------------------|---------------------------|
| `PROLONGED_SILENCE_OBSERVED` | Max silence $\ge 3000\text{ms}$ | `X ms sustained low-activity window` |
| `FREQUENT_INTERRUPTION_PATTERN` | Caller barge-ins $\ge 2$ in window | `X interruptions observed in active turn` |
| `HIGH_SPEECH_ACTIVITY` | Voice activity $\ge 85\%$ ($>2\text{s}$) | `Continuous rapid caller speech (X% voiced)` |
| `LOW_VOICE_ACTIVITY` | Voice activity $\le 15\%$ ($>2\text{s}$) | `Extended caller hesitation (X% voiced)` |
| `ELEVATED_ENERGY_VARIABILITY` | Energy variability $\ge 0.50$ | `Substantial volume modulation detected` |
| `AUDIO_QUALITY_LOW` | Clipping $\ge 10\%$ or Low Signal $\ge 70\%$ | `Distorted or severely attenuated signal` |
| `SIGNAL_INSUFFICIENT` | Audio duration $< 500\text{ms}$ | `Insufficient audio frames for assessment` |
| `ACOUSTIC_UNAVAILABLE` | Processing timeout or pipeline error | `Acoustic telemetry temporarily offline` |

---

## 5. Privacy & Data Retention Boundary

1. **No Disk Persistence of Raw Audio**: Inbound PCM chunks reside only in bounded ring buffers in volatile memory.
2. **Ephemeral Feature Tracking**: Only summary objects (`AcousticAssessment`) containing float/int metrics, confidence, and timestamps are held for the duration of the call.
3. **Zero Biometrics**: The system never generates or stores speaker identity embeddings, voiceprints, or demographic identifiers.
4. **Masked Metadata**: All associated call records strictly mask phone numbers (`+91******3210`).

---

## 6. SVI Interaction & Safety Primacy

- Acoustic analysis acts as a **supportive, decoupled evidence stream**.
- When an acoustic assessment is present, SVI records `acoustic_evidence_available = True` and incorporates a descriptive `acoustic_evidence_note`.
- Any optional acoustic contribution to SVI is strictly bounded within $\pm 2$ points and cannot pierce or lower the safety floors established by the Phase 4 Deterministic Safety Engine (CRITICAL $\ge 76$, HIGH $\ge 51$).
- If acoustic analysis encounters degraded audio or pipeline error, the call continues seamlessly and safety evaluation remains 100% operational.
