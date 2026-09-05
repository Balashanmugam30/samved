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

---

## 7. Verifying Phase 10 Legal / Policy RAG

### 7.1 Subsystem Health & Registered Sources
```bash
# Verify knowledge subsystem status
curl http://localhost:8000/v1/knowledge/status

# List registered authoritative sources and authority tiers
curl http://localhost:8000/v1/knowledge/sources
```

### 7.2 Governed Search & Citation Verification
```bash
# Perform governed knowledge search
curl -X POST http://localhost:8000/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "scholarship eligibility criteria",
    "jurisdiction": "TAMIL_NADU",
    "language": "en-IN",
    "effective_only": true,
    "max_results": 5
  }'

# Inspect cryptographic citation provenance
curl http://localhost:8000/v1/knowledge/citations/CITATION_ID
```

### 7.3 Workstation Knowledge Support Panel UI Testing
1. Navigate to `http://localhost:3000/calls` and select an active call.
2. Inspect the **Knowledge Support Panel** (`data-testid="knowledge-panel"`):
   - Enter a policy query in `data-testid="knowledge-query-input"` (e.g. `scholarship eligibility criteria`).
   - Filter by jurisdiction (`TAMIL_NADU` or `CENTRAL`) and language.
   - Click **Retrieve Guidance** (`data-testid="knowledge-search-button"`).
3. Inspect **Authoritative Source Cards**:
   - Verify Tier badge (Tier 1–4), publisher, jurisdiction, status, section, effective date, and verbatim excerpt.
   - Click **Official Source** external link to verify source documentation.
4. Inspect **AI Synthesized Summary**:
   - Verify claims reference verbatim citation tags (e.g. `[cit:...]`).
   - Click **Save to Notes** (`data-testid="save-knowledge-note-button"`):
     - Confirms note is added to the case record with structured `citation_ref`.
5. Test Conflict and Stale Banners:
   - Query conflicting schemes to view `SOURCE CONFLICT DETECTED` (`data-testid="knowledge-conflict-banner"`).
   - Toggle off `Current Only` and query expired policies to view `SOURCE MAY BE OUTDATED` (`data-testid="knowledge-stale-banner"`).
6. Inspect **Event Timeline**:
   - Click `KNOWLEDGE` filter pill to isolate `KNOWLEDGE_SEARCH_STARTED` and completion events.

---

## 8. Verifying Phase 11 Case Intelligence & Knowledge Graph

### 8.1 Subsystem Health & Fixture Verification
```bash
# Verify Case Intelligence subsystem status
curl http://localhost:8000/v1/cases/status

# Get details of active case
curl http://localhost:8000/v1/cases/case-1001

# Inspect graph structure with configurable depth
curl "http://localhost:8000/v1/cases/case-1001/graph?depth=2&include_candidates=true"

# Verify cryptographic graph integrity
curl http://localhost:8000/v1/cases/case-1001/integrity
```

### 8.2 Workstation Case Intelligence Panel UI Testing
1. Navigate to `http://localhost:3000/calls` and select active call `call-1001` (or `call-op-test-01`).
2. Inspect the **Case Intelligence Panel** (`data-testid="case-intelligence-panel"`):
   - Verify Case ID header (`case-1001`), call ID, status badge (`OPEN`), and epistemic disclaimer badges.
   - Inspect the **Metrics Strip** (`data-testid="case-metrics-strip"`): entities count, active relationships count, pending candidates count.
3. Inspect the **Interactive Graph Visualizer** (`data-testid="case-graph-visualizer"`):
   - View entity nodes (`data-testid="entity-node-..."`) with role chips and canonical labels.
   - View directed relationship edges (`data-testid="graph-edge-..."`).
   - Click an entity node to open the **Node Inspector drawer** (`data-testid="node-inspector"`): inspect metadata, claim status, and SHA-256 evidence anchor.
   - Click a relationship edge to open the **Edge Inspector drawer** (`data-testid="edge-inspector"`): inspect relationship type, confidence, and temporal validity.
4. Test **Candidate Relationship Confirmation**:
   - Locate candidate relationship cards (`data-testid="candidate-card-..."`).
   - Review verbatim excerpt grounding.
   - Click **Confirm** (`data-testid="confirm-cand-..."`): candidate graduates to active edge, metrics increment, and event logs to timeline.
   - Click **Reject** (`data-testid="reject-cand-..."`): candidate is dismissed with reason recorded in audit log.
5. Inspect **Depth Traversal Selector**:
   - Select 1, 2, 3, or 4 hops (`data-testid="graph-depth-select"`) to traverse subgraphs dynamically.
6. Inspect **Immutable Case Audit Trail**:
   - Click **Audit Trail** (`data-testid="view-case-audit-button"`) to open `data-testid="case-audit-modal"`.
7. Inspect **Event Timeline**:
   - Click `CASE` filter pill (`data-testid="event-filter-CASE"`) to isolate `CASE_ENTITY_EXTRACTED`, `CASE_RELATIONSHIP_CREATED`, and `CASE_CANDIDATE_CONFIRMED` events.

---

## 9. Verifying Phase 12 Follow-up Workflows & Continuity Engine

### 9.1 Subsystem Health & Workqueue Summary
```bash
# Verify follow-up subsystem status
curl http://localhost:8000/v1/followups/status

# Retrieve workqueue summary KPI metrics
curl http://localhost:8000/v1/followups/summary

# List all follow-up tasks
curl http://localhost:8000/v1/followups

# List follow-ups for a specific case
curl http://localhost:8000/v1/cases/case-1001/followups
```

### 9.2 Scheduling & Executing Safe Follow-ups via REST
```bash
# 1. Schedule a new safe follow-up
curl -X POST http://localhost:8000/v1/cases/case-1001/followups \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CHECK_IN",
    "priority": "HIGH",
    "purpose": "Verify shelter admittance and caller safety",
    "channel": "OPERATOR_CALLBACK",
    "scheduled_for": "2026-04-01T10:00:00Z",
    "due_at": "2026-04-02T10:00:00Z",
    "safe_contact_window": "09:00-12:00",
    "consent_state": "GRANTED",
    "contact_preferences": {
      "preferred_channel": "OPERATOR_CALLBACK",
      "safe_to_contact": true,
      "human_only": true,
      "preferred_time_window": "09:00-12:00"
    }
  }'

# 2. Start follow-up task
curl -X POST http://localhost:8000/v1/followups/fol-1001/start \
  -H "Content-Type: application/json" \
  -d '{"operator_id": "operator_1"}'

# 3. Record human contact attempt
curl -X POST http://localhost:8000/v1/followups/fol-1001/attempt \
  -H "Content-Type: application/json" \
  -d '{
    "operator_id": "operator_1",
    "channel": "OPERATOR_CALLBACK",
    "result": "CONTACTED_SUCCESSFULLY",
    "notes": "Caller confirmed safe in temporary shelter"
  }'

# 4. Complete follow-up task
curl -X POST http://localhost:8000/v1/followups/fol-1001/complete \
  -H "Content-Type: application/json" \
  -d '{
    "operator_id": "operator_1",
    "outcome": "CONTACTED_SUCCESSFULLY",
    "notes": "Completed shelter check-in"
  }'

# 5. Revoke consent (emergency halt)
curl -X POST http://localhost:8000/v1/cases/case-1001/followups/revoke-consent \
  -H "Content-Type: application/json" \
  -d '{"operator_id": "operator_1", "reason": "Caller requested no further callbacks"}'

# 6. View follow-up audit trail
curl http://localhost:8000/v1/followups/fol-1001/audit
```

### 9.3 Workstation Follow-up Workqueue UI Testing
1. Navigate to `http://localhost:3000/calls` and select an active call.
2. Locate the **Follow-up Workqueue & Continuity Engine** panel (`data-testid="followup-workqueue-panel"`):
   - Verify governance badges: `HUMAN_SUPERVISED`, `CONSENT_GUARDED`.
   - Inspect the **Metrics Strip**: Total Active, Due Today, Overdue, Blocked, Completed Today.
3. Test **Status Filter Pills**:
   - Filter by `All Tasks`, `Scheduled`, `Ready`, `In Progress`, `Blocked`, `Completed`.
4. Test **Schedule Follow-up Modal**:
   - Click **"+ Schedule Follow-up"** (`data-testid="create-followup-btn"`).
   - Fill Type, Priority, Purpose, Channel, Scheduled Time, and Safe Contact Window.
   - Click **Schedule Follow-up** (`data-testid="submit-create-followup-btn"`).
5. Test **Task Execution & Contact Attempts**:
   - Click **"Start Task"** (`data-testid="start-followup-btn"`).
   - Click **"Record Attempt"** (`data-testid="record-attempt-btn"`):
     - Select Channel and Result, enter notes, click **"Save Attempt Record"**.
6. Test **Rescheduling**:
   - Click **"Reschedule"** (`data-testid="reschedule-followup-btn"`), enter new time and reason, click **"Confirm Reschedule"**.
7. Test **Caller Consent Revocation (Immediate Halt)**:
   - Click **"Revoke Consent"** (`data-testid="revoke-consent-btn"`):
     - Confirm all active tasks for the case transition to `BLOCKED`.
8. Inspect **Follow-up Audit Trail**:
   - Click **"Audit Trail"** (`data-testid="view-all-followup-audit-btn"`) to open `data-testid="followup-audit-modal"`.
9. Inspect **Event Timeline**:
   - Click `FOLLOWUP` filter pill (`data-testid="timeline-filter-FOLLOWUP"`) to isolate follow-up lifecycle events.

---

## 10. Verifying Phase 13 District Intelligence & Operational Analytics

### 10.1 Subsystem Health & Metric Catalog
```bash
# Verify analytics status and governance parameters
curl http://localhost:8000/v1/analytics/status

# List complete versioned catalog of metrics (v1.0.0)
curl http://localhost:8000/v1/analytics/metrics

# List normalized districts
curl http://localhost:8000/v1/analytics/districts
```

### 10.2 District Operational Summaries & Distributions
```bash
# Fetch district operational summary (Chennai)
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/summary

# Fetch period-over-period trend points
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/trends

# Fetch multilingual language mix
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/languages

# Fetch standardized service category demand
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/services

# Fetch deterministic safety state distribution
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/safety

# Fetch SVI vulnerability band distribution
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/svi

# Fetch care continuity follow-up completion rates
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/followups

# Fetch counselor workload and response times
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/TN-CHE/operations
```

### 10.3 Privacy & Suppression Verification
```bash
# Query low-cohort district (Karaikal, PY-KKL: <10 records)
# Verifies privacy_status=SUPPRESSED and raw_value=null
curl -H "X-User-Role: DISTRICT_ADMIN" http://localhost:8000/v1/analytics/districts/PY-KKL/summary

# Verify OPERATOR role access denial (403 Forbidden)
curl -H "X-User-Role: OPERATOR" http://localhost:8000/v1/analytics/districts/TN-CHE/summary
```

### 10.4 Web Dashboard Verification (`/analytics`)
1. Navigate to `http://localhost:3000/analytics`.
2. Verify **Governance Watermark Banner** (`data-testid="governance-watermark"`):
   - Confirms non-predictive policy: *"Not a predictive risk score. Not for individual enforcement decisions."*
3. Test **Role Switcher**:
   - Select `OPERATOR` &rarr; verify `data-testid="access-denied-banner"` appears with 403 explanation.
   - Select `DISTRICT_ADMIN` &rarr; verify dashboard metrics restore.
4. Test **District Filter**:
   - Select `Chennai (TN-CHE)` &rarr; verify KPI strip, trends, and distributions render.
   - Select `Karaikal (PY-KKL)` &rarr; verify `data-testid="suppressed-cohort-banner"` appears and KPI counts show `SUPPRESSED`.
5. Test **Chart & Table View Toggle**:
   - Click `Table View` (`data-testid="table-toggle-btn"`) to verify accessible tabular display.
6. Test **Metric Inspector Drawer**:
   - Click any KPI card (e.g. `Total Calls`) to open `data-testid="metric-detail-drawer"`.
   - Inspect mathematical formula, trust classification (`OBSERVED`), privacy status (`PASS`), and version (`v1.0.0`).
7. Test **Operator Workstation Link**:
   - Navigate to `http://localhost:3000/calls`.
   - In the top action bar, click **Operations Analytics** (`data-testid="link-operations-analytics"`).
   - Confirms smooth navigation back to `/analytics`.

---

## 11. Verifying Phase 14 Scenario Simulation Engine & Operator Training Sandbox

### 11.1 Simulation Subsystem Health & Synthetic Scenarios Catalog
```bash
# Check simulation subsystem status & scenario count
curl http://localhost:8000/v1/simulation/status

# List all 24 calibrated synthetic scenarios across 11 Indic languages
curl http://localhost:8000/v1/simulation/scenarios

# Filter scenarios by risk band (e.g. CRITICAL)
curl "http://localhost:8000/v1/simulation/scenarios?band=CRITICAL"

# Inspect specific scenario details (e.g. SCEN-CRIT-001)
curl http://localhost:8000/v1/simulation/scenarios/SCEN-CRIT-001
```

### 11.2 Automated Benchmark Harness
```bash
# Trigger automated benchmark run (SMOKE suite: 12 scenarios)
curl -X POST http://localhost:8000/v1/simulation/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"suite": "SMOKE"}'

# Trigger automated benchmark run (FULL suite: 24 scenarios)
curl -X POST http://localhost:8000/v1/simulation/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"suite": "FULL"}'

# View benchmark run history & safety recall rate (100% target)
curl http://localhost:8000/v1/simulation/benchmark/runs
```

### 11.3 Indic ASR Normalization & Word Error Rate (WER/CER) Calculator
```bash
# Evaluate Indic ASR transcription accuracy with Wagner-Fischer dynamic programming
curl -X POST http://localhost:8000/v1/simulation/wer/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "reference": "नमस्ते मुझे तुरंत सहायता चाहिए सांस नहीं आ रही",
    "hypothesis": "नमस्ते तुरंत सहायता चाहिए सांस नहीं आ रही"
  }'
```

### 11.4 Operator Training Sandbox & Real-time SOP Rubric Scoring
```bash
# List curated training drills
curl http://localhost:8000/v1/simulation/training/drills

# Start interactive drill session (e.g. DRILL-OVERDOSE-001)
curl -X POST http://localhost:8000/v1/simulation/training/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "drill_key": "DRILL-OVERDOSE-001",
    "trainee_id": "T-OPERATOR-01",
    "trainee_name": "Trainee Tele-Counselor"
  }'

# Submit trainee turn and receive real-time SOP scoring
curl -X POST http://localhost:8000/v1/simulation/training/session/SESSION_ID/turn \
  -H "Content-Type: application/json" \
  -d '{
    "trainee_input": "Please turn him into the recovery position immediately while I coordinate the ambulance."
  }'

# Retrieve final session report with competency ratings
curl http://localhost:8000/v1/simulation/training/session/SESSION_ID
```

### 11.5 Web Console Verification (`/simulation`)
1. Navigate to `http://localhost:3000/simulation` (or click **Simulation & Sandbox** in the sidebar).
2. Verify **Governance Watermark Banner** (`data-testid="governance-watermark"`):
   - Confirms synthetic benchmark isolation: *"All conversational scenarios, ASR evaluations, and training drills are strictly synthetic. No real helpline records or active Exotel carrier lines are engaged."*
3. Check **Top KPI Cards** (`data-testid="kpi-strip"`):
   - Critical Safety Recall (Target 100%, 0 false negatives), Mean WER, Mean CER, SVI Calibration Accuracy, and P95 Triage Latency (< 1200ms SLA).
4. Run **Automated Benchmark Runner Tab**:
   - Toggle between `Smoke Suite (12)` and `Full Suite (24)`.
   - Click `Run Benchmark` (`data-testid="btn-run-benchmark"`).
   - Filter results table by risk band: `ALL`, `CRITICAL`, `HIGH`, `MODERATE`, `LOW`.
   - Click `Details` on any scenario row to inspect full trigger firing and latency breakdown.
5. Explore **Indic ASR & WER Lab Tab** (`data-testid="tab-wer-lab"`):
   - Click Hindi Medical or Tamil Crisis preset buttons.
   - Click `Compute WER & CER` (`data-testid="btn-compute-wer"`).
   - Observe the color-coded token alignment diff visualization (Match, Substitution, Deletion, Insertion) and calculated metrics.
6. Practice in the **Operator Training Sandbox Tab** (`data-testid="tab-sandbox"`):
   - Select `Critical Opioid Overdose Rapid Intake` drill.
   - Read caller dialogue in the timeline.
   - Enter response: *"Please turn him on his side in recovery position immediately while I coordinate the ambulance."*
   - Click `Submit Turn` (`data-testid="btn-submit-turn"`).
   - Verify immediate SOP Rubric scoring (Safety Protocol 35/35, Empathy 22/25, Pacing 18/20, Referral 17/20) and feedback hints.

---

## 12. Verifying Phase 14 Scenario Simulator & Evaluation Lab (`/evaluation`)

### 12.1 Evaluation Lab Subsystem Status
```bash
# Check evaluation lab health, registered scenarios, and baselines count
curl http://localhost:8000/v1/evaluation/status
```

### 12.2 Calibrated Benchmark Scenarios (19 Scenarios, Categories A through Q)
```bash
# List all calibrated scenarios
curl http://localhost:8000/v1/evaluation/scenarios

# Filter scenarios by tag (e.g. smoke, safety, multilingual, rag)
curl "http://localhost:8000/v1/evaluation/scenarios?tag=safety"

# Inspect detailed scenario specification with multi-turn narrative & golden expectations
curl http://localhost:8000/v1/evaluation/scenarios/SCEN-CRIT-001
```

### 12.3 Execute Evaluation Replays & Fault Injection
```bash
# Execute offline deterministic replay (Seed 42)
curl -X POST http://localhost:8000/v1/evaluation/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-CRIT-001",
    "mode": "OFFLINE",
    "seed": 42
  }'

# Execute replay with injected fault (e.g. statutory RAG knowledge timeout)
curl -X POST http://localhost:8000/v1/evaluation/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-RAG-001",
    "mode": "INTEGRATED",
    "seed": 42,
    "fault": {
      "fault_type": "KNOWLEDGE_TIMEOUT",
      "target_subsystem": "rag",
      "delay_ms": 3500
    }
  }'

# Execute batch benchmark suite (e.g. smoke suite)
curl -X POST http://localhost:8000/v1/evaluation/suites/run \
  -H "Content-Type: application/json" \
  -d '{
    "suite_name": "smoke",
    "mode": "OFFLINE",
    "seed": 42
  }'
```

### 12.4 Golden Baselines & Regression Detection
```bash
# List golden baselines
curl http://localhost:8000/v1/evaluation/baselines

# Capture run as a new golden baseline
curl -X POST http://localhost:8000/v1/evaluation/baselines \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-GEN-001",
    "run_id": "RUN-EVAL-XXXXXX",
    "created_by": "eval_lead",
    "description": "Golden baseline for general information triage"
  }'

# Compare current run against baseline snapshot to detect regressions
curl -X POST http://localhost:8000/v1/evaluation/diff \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "BASE-SCEN-GEN-001-v1",
    "current_run_id": "RUN-EVAL-YYYYYY"
  }'
```

### 12.5 Web Console Verification (`/evaluation`)
1. Navigate to `http://localhost:3000/evaluation` (or click **Evaluation Lab** in the sidebar).
2. Verify **Governance Warning Banner**:
   - Amber warning banner prominently declaring: *"Synthetic Evaluation Environment: All scenarios, caller personas, and telephone interactions are simulated benchmarks. Zero connection to live telecom carriers, production victim registries, or real emergency dispatchers. AUTONOMOUS DISPATCH: FALSE. ISOLATED SANDBOX."*
3. Explore **Scenario Library Tab**:
   - Filter scenarios using search input or category pills (`All`, `Smoke`, `Safety`, `Multilingual`, `RAG`, etc.).
   - Click `Inspect Spec` on any card to slide out the Scenario Narrative & Machine-Checkable Expectations drawer.
   - Click `Run Scenario Replay` (`data-testid="run-scenario-btn"`) on any card to execute in-memory simulation.
4. Inspect **Active Run Telemetry Tab**:
   - Observe `STATUS: PASS` / `FAIL` badge, scenario ID, and P95 replay latency KPI card.
   - Click **Findings** sub-tab: Displays structured findings catalog.
   - Click **Assertions** sub-tab: Confirms machine-checkable golden expectations against actual run telemetry.
   - Click **Subsystem Telemetry** sub-tab: Inspects per-subsystem telemetry (Safety rules & human review required, SVI score & band, Adaptive policy, Acoustic frames & silence, Orchestration DAG, RAG citations, Case Intelligence handoff, Follow-up continuity).
   - Click **Latency Waterfall** sub-tab: Visualizes millisecond breakdown per pipeline stage.
   - Click **Baseline Diff** sub-tab: Select a baseline snapshot and click `Compute Regression Diff` to verify `NO REGRESSION` or inspect field deltas.
5. Benchmark with **Suite Runner Tab**:
   - Select evaluation suite (`Smoke`, `Safety`, `Multilingual`, `Adaptive`, `Orchestration`, `RAG`, `Case`, `Follow-up`, `Privacy`, `Full`).
   - Choose Replay Mode (`Offline Replay` or `Integrated Pipeline`).
   - Enter deterministic seed (e.g. `42`).
   - Click `Execute Suite` to run batch benchmark evaluation.

---

## 13. Phase 15: Security, Privacy & Governance Hardening

### 13.1 Security Status & Living Controls Inventory
```bash
# Check security posture and subsystem health
curl http://localhost:8000/v1/security/status

# List all 11 active security & governance controls
curl http://localhost:8000/v1/security/controls
```

### 13.2 Verify SHA-256 Cryptographic Audit Trail
```bash
# Verify cryptographic hash chaining across all log entries
curl http://localhost:8000/v1/security/audit/verify \
  -H "X-User-Role: SUPERVISOR" \
  -H "X-User-Id: usr-supervisor-01"

# Query audit trail entries with role scoping
curl "http://localhost:8000/v1/security/audit?limit=10" \
  -H "X-User-Role: SUPERVISOR"
```

### 13.3 Test Indian PII Redaction Pipeline
```bash
curl -X POST http://localhost:8000/v1/security/pii/redact \
  -H "Content-Type: application/json" \
  -H "X-User-Role: OPERATOR" \
  -d '{
    "text": "Caller mobile is +91-9876543210, Aadhaar is 2345 6789 0123, PAN is ABCDE1234F, bank A/C 123456789012."
  }'
```

### 13.4 Web Console Verification
1. **Security & Governance Dashboard** (`http://localhost:3000/security`):
   - Observe posture KPI cards (`HEALTHY`, `SHA-256 VALID`, `ACTIVE`).
   - Switch personas using the **Active RBAC Persona** switcher (`OPERATOR`, `SUPERVISOR`, `DISTRICT_ADMIN`, `SYSTEM_ADMIN`, `AUDITOR`).
   - Test the **Indian PII Redaction Lab** with preset or custom text.
   - Inspect the **RBAC & IDOR Matrix** and **Data Retention** policies.
2. **Audit Trail Explorer** (`http://localhost:3000/audit`):
   - Click **Verify SHA-256 Chain** to execute cryptographic integrity verification.
   - Filter entries by actor, action, district, or status (`ALLOWED`, `MUTATED`, `DENIED`).
   - Click any row to expand the full JSON event payload and cryptographic hash hashes.

---

## 14. Phase 16: Deployment, Reliability & SIH Finalization

### 14.1 Verifying Kubernetes Probes & Reliability Endpoints
```bash
# Liveness Probe (process responsive)
curl http://localhost:8000/healthz

# Readiness Probe (dependencies and configuration)
curl http://localhost:8000/ready

# Startup Probe (config validation)
curl http://localhost:8000/health/startup

# Release Version Information
curl http://localhost:8000/version
```

### 14.2 Operations & Circuit Breaker Telemetry
```bash
# Get comprehensive operational status
curl http://localhost:8000/v1/operations/status

# List all circuit breakers and their trip states
curl http://localhost:8000/v1/operations/circuits

# Manually reset all circuit breakers to CLOSED
curl -X POST http://localhost:8000/v1/operations/circuits/reset-all
```

### 14.3 SIH Presentation Demo Mode
```bash
# Inspect demo status and safety boundaries
curl http://localhost:8000/v1/demo/status

# Fetch flagship Tamil/English scenario specification
curl http://localhost:8000/v1/demo/flagship

# Replay flagship scenario through all 8 pipeline stages
curl -X POST http://localhost:8000/v1/demo/flagship/replay

# Reset demo environment back to pristine state
curl -X POST http://localhost:8000/v1/demo/reset
```

### 14.4 Web Console Verification
1. **SIH Demo Hub** (`http://localhost:3000/demo`):
   - Confirm prominent **SIH DEMO / SYNTHETIC ENVIRONMENT** banner.
   - Click **Replay Flagship Scenario** to execute live 8-stage pipeline.
   - Verify SVI Score 88 (CRITICAL), Protocol `P0_EMERGENCY_DISPATCH_ASSIST`, and 3-point warm transfer brief.
   - Expand stages to inspect verified assertions and stage payloads.
   - Click **Reset Environment** to restore pristine evaluation state.
2. **Operations & Reliability Console** (`http://localhost:3000/operations`):
   - Inspect Service Uptime, Version `1.0.0-sih2026`, Telephony Sessions, and WebSocket Gateway status.
   - Review 6 active Circuit Breakers (`sarvam-stt`, `sarvam-tts`, `gemini-llm`, `exotel-telephony`, `database`, `redis`).
   - Click **Reset All Circuit Breakers** and verify instantaneous state restoration.
