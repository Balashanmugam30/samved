# SAMVED Phase 5 — Explainable Stress Vulnerability Index (SVI) Engine

## Overview

The Stress Vulnerability Index (SVI) is a **deterministic, explainable operational prioritization metric** (0–100) designed to help NHAA 14566 human operators triage incoming crisis calls objectively based on verifiable conversational evidence.

> **IMPORTANT**: SVI is an **Operational Prototype Priority Indicator** — NOT a clinical diagnosis, medical score, PTSD score, depression score, truthfulness detector, guilt detector, crime detector, legal verdict, or automatic emergency dispatch authority.

## Architecture

```
REAL TELEPHONY CALL / SIMULATION
               ↓
Final Transcript Event (TRANSCRIPT_FINAL / Utterance)
               ↓
Deterministic Realtime Safety Engine (Phase 4)
               ↓
  [Safety Signals: Immediate Danger, Active Violence, Weapons, etc.]
               ↓
┌─────────────────────────────────────────────────────────────┐
│             EXPLAINABLE SVI SCORING ENGINE (v1)             │
│                                                             │
│  1. Feature Extractors (6 categories)                       │
│  2. Temporal Recency Weighting                              │
│  3. Negation Detection                                      │
│  4. Category Subscore Aggregation & Upper Bounds            │
│  5. Critical Safety Floor Override                          │
│  6. Protective Factor Bounded Reduction (max -15)           │
│  7. Completeness Metric Calculation (0.0 – 1.0)            │
│  8. Trend Evaluation (RISING, FALLING, STABLE, INITIAL)    │
│  9. Explicit Provenance & Top Contributors Assembly        │
│ 10. Non-verbal Acoustic Notice (Phase 6 deferred)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       SVI_UPDATED Event              REST Endpoints
        (svi.updated)                 GET /v1/svi/calls/{id}
               │                      GET /v1/svi/calls/{id}/history
               ▼                      POST /v1/svi/evaluate
     Operator Realtime WebSocket
               │
               ▼
   Operator Console SVI Panel + SVI Simulation Lab
```

## Score Bands

| Range  | Band       | Description |
|--------|------------|-------------|
| 0–25   | LOW        | Routine support request, informational, high protective factors |
| 26–50  | MODERATE   | Elevated distress, emerging coercion or isolation |
| 51–75  | HIGH       | Severe distress, acute coercion, significant barriers. **Mandates operator review** |
| 76–100 | CRITICAL   | Active violence, lethal weapons, immediate escape need. **Critical floor override** |

## Feature Categories

| Category | Max Weight | Description |
|----------|-----------|-------------|
| Immediate Safety | 40 pts | Active violence, weapons, life threats (from Phase 4 safety signals) |
| Coercion & Control | 25 pts | Confinement, surveillance, movement restriction |
| Isolation & Support | 15 pts | Absence of trusted support, isolated location |
| Distress & Overwhelm | 20 pts | Explicit panic, acute distress, inability to cope |
| Help Barriers | 15 pts | Unable to leave, no transport, monitored phone |
| Protective Factors | Max -15 pts | Safe space, trusted person nearby (bounded reduction) |

## Recency Multipliers

| Temporal Context | Multiplier |
|-----------------|------------|
| PRESENT (now, right now, currently) | 1.0 |
| RECENT (earlier today, few hours ago) | 0.75 |
| HISTORICAL (last year, previously) | 0.35 |

## Override Rules

1. **Critical Floor Override**: If any CRITICAL safety signal is present → `score = max(score, 76)`
2. **High Safety Floor**: If any HIGH safety signal is present → `score = max(score, 51)`
3. **Protective Factor Cap**: Max reduction is 15 points. Cannot override safety floors.
4. **Range Clamping**: Always 0 ≤ SVI ≤ 100

## Ethical Boundaries

- LLM (Gemini) is **strictly decoupled** from SVI scoring authority
- SVI computation is 100% deterministic, offline, sub-5ms
- Missing evidence lowers `assessment_completeness`, does NOT inflate score
- Any score ≥ 51 mandates `requires_human_review = true`
- Acoustic evidence explicitly deferred to Phase 6

## API Endpoints

- `GET /v1/svi/status` — Engine readiness, version, ethical boundaries
- `GET /v1/svi/rules` — Category weights, lexicons, thresholds
- `POST /v1/svi/evaluate` — Standalone deterministic evaluation
- `GET /v1/svi/calls/{call_id}` — Latest SVI for active/completed call
- `GET /v1/svi/calls/{call_id}/history` — Turn-by-turn SVI history
