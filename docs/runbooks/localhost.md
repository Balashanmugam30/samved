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

## 3. Testing Realtime Console UI (Phases 3–6)

1. Open `http://localhost:3000/calls` in your browser.
2. Observe active and completed calls in the left panel.
3. Click any call to inspect:
   - **Acoustic Signals Panel**: Quality badge, confidence score, metrics grid (speech ratio, pause duration, interruptions, RMS, pitch), active signal chips, and non-clinical disclaimer.
   - **Stress Vulnerability Index (SVI)**: Score gauge, vulnerability band, trend, and factual acoustic evidence notes.
   - **Deterministic Safety Engine**: Authoritative signals and rule triggers.
4. Click **Acoustic Lab** in the top navigation bar to open the interactive simulation modal:
   - Select presets (e.g. *Acute Agitation*, *Flat Affect / Withdrawal*, *Line Degradation / Clipping*).
   - Adjust sliders in realtime and click **Evaluate Acoustics** to inspect live engine response.

---

## 4. Verifying Phase 7 Adaptive Conversation Engine

### 4.1 Engine Status & Policy Catalog
```bash
curl http://localhost:8000/v1/adaptive/status
curl http://localhost:8000/v1/adaptive/policy
```
Confirms operational readiness, strict safety precedence (P0 > P1 > P2 > P3 > P4 > P5), and active policy rules.

### 4.2 Standalone Adaptive Planning Simulation
```bash
curl -X POST http://localhost:8000/v1/adaptive/plan \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "sim-test-01",
    "session_id": "sim-sess-01",
    "turn_index": 2,
    "language": "ta-IN",
    "safety_state": "CRITICAL",
    "safety_signals": [{"signal_type": "THREAT", "severity": "CRITICAL", "confidence": 0.99}],
    "svi_score": 85,
    "svi_band": "CRITICAL",
    "svi_trend": "INITIAL",
    "acoustic_quality": "GOOD",
    "acoustic_signals": [],
    "known_facts": {},
    "last_caller_utterance": "He is right outside, please help"
  }'
```
Returns deterministic strategy (`SAFETY_CHECK`, `P0`, `immediate_danger_clarification`, reason `CRITICAL_THREAT_PRESENT`).

### 4.3 Operator Overrides via REST
```bash
curl -X POST http://localhost:8000/v1/adaptive/calls/CALL_ID/override \
  -H "Content-Type: application/json" \
  -d '{
    "action": "operator_force_human",
    "reason": "Counselor manual escalation"
  }'
```

### 4.4 Console UI Testing
1. In `http://localhost:3000/calls`, select a call.
2. Locate the **Adaptive Policy Panel**:
   - Strategy badge (`ASK_SUPPORT`, `SAFETY_CHECK`, `HUMAN_HANDOFF`), priority badge (`P0`–`P5`), target information gap, confidence score, and deterministic reason chips.
   - Quick operator override buttons: **Force Human**, **Pause Questions**, **Safety Check**.
3. Click **Adaptive Lab** in the header toolbar:
   - Select presets (*Critical Threat*, *High Vulnerability*, *Degraded Audio*, *Human Request*, *Caller Refusal*, *Closure Ready*).
   - Click **Run Adaptive Strategy Evaluation** to inspect live deterministic strategy outputs and fallback responses.

---

## 5. Verifying Phase 8 Human Operator Workstation

### 5.1 Workstation & Subsystems Status
```bash
curl http://localhost:8000/v1/operator/status
```
Returns comprehensive operational health of safety, SVI, acoustic, adaptive, and telephony subsystems.

### 5.2 Operator Actions via REST
```bash
# Human Takeover
curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/takeover \
  -H "Content-Type: application/json" \
  -d '{"reason": "Operator initiated human takeover", "operator_id": "op_01"}'

# Pause / Resume Adaptive AI
curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/pause \
  -H "Content-Type: application/json" \
  -d '{"reason": "Pause for sensitive disclosure", "operator_id": "op_01"}'

curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/resume \
  -H "Content-Type: application/json" \
  -d '{"reason": "Resume AI support", "operator_id": "op_01"}'

# Add Structured Note
curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/notes \
  -H "Content-Type: application/json" \
  -d '{"category": "SAFETY", "text": "Caller confirmed in secure location", "operator_id": "op_01"}'

# Request and Confirm Handoff
curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/handoff \
  -H "Content-Type: application/json" \
  -d '{"reason": "Escalation to Tier-2 counselor", "operator_id": "op_01"}'

curl -X POST http://localhost:8000/v1/operator/calls/CALL_ID/handoff/confirm \
  -H "Content-Type: application/json" \
  -d '{"transfer_confirmed_by": "supervisor_01", "target_agent": "tier2_counselor"}'
```

### 5.3 Workstation UI Testing
1. Navigate to `http://localhost:3000/calls`.
2. Inspect the **Master Call List**:
   - Filter active calls using queue pills: `All`, `Critical`, `Elevated`, `Takeover`, `High SVI`.
3. Inspect the **Active Call Header**:
   - Masked phone number (`+91******3210`), call ID, provider, and `AI_ASSISTED` / `HUMAN_ACTIVE` ownership badge.
4. Inspect the **Operator Control Bar**:
   - Click **Take Over**: transitions ownership to `HUMAN_ACTIVE` and suppresses autonomous AI speech.
   - Click **Pause Adaptive**: pauses automated AI prompts, changes badge to `AI Paused`, and displays **Resume Adaptive**.
   - Click **Request Safety Check**: triggers immediate deterministic safety verification banner.
   - Click **Request Handoff**: transitions handoff status to `REQUESTED`, revealing `Confirm Handoff` and `Cancel`.
   - Click **Notes**: opens structured notes modal with category selector (`GENERAL`, `SAFETY`, `FOLLOW_UP_NOTE`, `HANDOFF_NOTE`, `TECHNICAL`), append-only input, and chronological notes audit trail.
   - Click **End Call**: prompts confirmation modal before terminating session.
5. Inspect the **Unified Call Triage Summary**:
   - Synthesizes Safety State, SVI Index (0–100), Acoustic Signal, Adaptive Policy, Human Authority, and Multi-Agent status dimensions with mandatory non-clinical advisory disclaimer.
6. Inspect the **Event Timeline**:
   - Filter stream by `OPERATOR`, `SAFETY`, `SVI`, `ACOUSTIC`, `ADAPTIVE`, `ORCHESTRATION`, `TRANSCRIPT`, `CONVERSATION`, `ERRORS`, `LATENCY`.

---

## 6. Verifying Phase 9 Multi-Agent Orchestration

### 6.1 Engine Status & Registered Workers
```bash
# Verify orchestrator engine status
curl http://localhost:8000/v1/orchestration/status

# List all registered worker specifications
curl http://localhost:8000/v1/orchestration/agents
```

### 6.2 Deterministic Planning & Call Refresh
```bash
# Query deterministic execution plan for a turn
curl -X POST http://localhost:8000/v1/orchestration/plan \
  -H "Content-Type: application/json" \
  -d '{"task_type": "turn_triage", "safety_state": "CRITICAL"}'

# Trigger manual orchestration refresh for an active call
curl -X POST http://localhost:8000/v1/orchestration/calls/CALL_ID/refresh
```

### 6.3 Multi-Agent UI Testing
1. Navigate to `http://localhost:3000/calls` and select an active call.
2. Inspect the **Multi-Agent Orchestration Panel** (`data-testid="multi-agent-panel"`):
   - Check the **Orchestration State Badge** (`READY`, `RUNNING`, `COMPLETED`, `DEGRADED`).
   - Check the **Execution Latency** badge (e.g. `135 ms`).
   - Inspect the **6 Worker Chips** (`safety_context_agent`, `acoustic_context_agent`, `language_context_agent`, `conversation_context_agent`, `support_options_agent`, `operator_briefing_agent`).
3. Inspect the **Operator Briefing Card** (`data-testid="operator-briefing-card"`):
   - View synthesized Safety Context, SVI Vulnerability, Acoustic Biomarkers, Adaptive Recommendation, Key Contextual Facts, and Evidence Chains.
4. Click **Refresh** (`data-testid="refresh-orchestration-button"`):
   - Verifies on-demand orchestration refresh and immediate UI update.
5. Inspect **Event Timeline**:
   - Click `ORCHESTRATION` filter pill to view `ORCHESTRATION_STARTED`, `ORCHESTRATION_COMPLETED`, and `OPERATOR_BRIEFING_GENERATED` events.

