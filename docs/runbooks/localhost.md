# SAMVED Localhost Runbook (Phase 6)

This runbook guides operators and engineers through running and verifying SAMVED locally, including the Phase 6 Acoustic Analysis Engine and Operator Console.

---

## 1. Quick Start

### 1.1 Prerequisites
- Node.js >= 20.0.0
- pnpm >= 9.0.0
- Python >= 3.11 with `uv`
- Git

### 1.2 Start Backend
```bash
# In terminal 1:
uv --directory apps/api sync
uv --directory apps/api run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.3 Start Frontend
```bash
# In terminal 2:
pnpm install
pnpm --filter @samved/schemas build
pnpm --filter @samved/web dev
```

The web console will be accessible at: `http://localhost:3000`
The backend API docs will be at: `http://localhost:8000/docs`

---

## 2. Verifying Phase 6 Acoustic Endpoints

### 2.1 Engine Status
```bash
curl http://localhost:8000/v1/acoustic/status
```
Response confirms engine readiness, audio sample rate (`8000`), frame size (`160`), rolling window (`30.0s`), and ethical constraints.

### 2.2 Rules Catalog
```bash
curl http://localhost:8000/v1/acoustic/rules
```
Returns all 8 operational acoustic signal definitions and threshold values.

### 2.3 Standalone Acoustic Simulation
```bash
curl -X POST http://localhost:8000/v1/acoustic/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "pitch_hz": 240.0,
    "speech_ratio": 0.85,
    "max_unvoiced_ms": 1200,
    "clipping_ratio": 0.01,
    "energy_cv": 0.55,
    "interruption_count": 4
  }'
```
Returns a fully attributed `AcousticAssessment` containing operational signals (`HIGH_SPEECH_ACTIVITY`, `FREQUENT_INTERRUPTION_PATTERN`, `ELEVATED_ENERGY_VARIABILITY`), audio quality (`GOOD`), and confidence.

---

## 3. Testing Realtime Console UI

1. Open `http://localhost:3000/calls` in your browser.
2. Observe active and completed calls in the left panel.
3. Click any call to inspect:
   - **Acoustic Signals Panel**: Quality badge, confidence score, metrics grid (speech ratio, pause duration, interruptions, RMS, pitch), active signal chips, and non-clinical disclaimer.
   - **Stress Vulnerability Index (SVI)**: Score gauge, vulnerability band, trend, and factual acoustic evidence notes.
   - **Deterministic Safety Engine**: Authoritative signals and rule triggers.
4. Click **Acoustic Lab** in the top navigation bar to open the interactive simulation modal:
   - Select presets (e.g. *Acute Agitation*, *Flat Affect / Withdrawal*, *Line Degradation / Clipping*).
   - Adjust sliders in realtime and click **Evaluate Acoustics** to inspect live engine response.
