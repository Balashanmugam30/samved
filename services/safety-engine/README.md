# SAMVED — Deterministic Safety Engine (`services/safety-engine`)

## Purpose
The Safety Engine provides deterministic, explainable, and auditable safety policy enforcement. It acts as an authoritative safeguard that cannot be bypassed by probabilistic LLM outputs.

## Core Architectural Invariants
1. **LLM is Not the Safety Authority**: While LLM agents may detect candidate nuance or extract contextual signals, safety escalation triggers are adjudicated by deterministic rules.
2. **No Autonomous Emergency Coercion**: The safety engine does NOT independently dispatch emergency services, order arrests, or take coercive actions.
3. **No Clinical Diagnosis**: The engine detects situational vulnerability and threat indicators, not psychiatric or clinical diagnoses.
4. **Mandatory Human-in-the-Loop**: High-stakes alerts generate operator notifications with explicit rationale, allowing human operators to confirm, escalate, or override.

## Detected Signals (Phase 4+)
- Immediate physical danger
- Ongoing violence / perpetrator proximity
- Self-harm / suicide ideation signals
- Acute withdrawal / medical distress indicators
- Displacement or unsafe physical environment

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary and safety event contracts (`SAFETY_SIGNAL`, `HUMAN_ALERT`, `ESCALATION_RECOMMENDED`).
- **Phase 4 (Upcoming)**: Full deterministic safety rule engine, keyword/pattern matching, and operator notification dispatch.
