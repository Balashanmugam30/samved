# SAMVED — Risk & Stress Vulnerability Index (SVI) Engine (`services/risk-engine`)

## Purpose
Calculates and updates the real-time Stress Vulnerability Index (SVI) score during helpline calls.

## SVI Score Range & Operational Prototype Bands
- **0–25**: `LOW` — Standard inquiry, informational or advisory support needed.
- **26–50**: `MODERATE` — Situational distress, counseling guidance and community support recommended.
- **51–75**: `HIGH` — Elevated vulnerability, prioritized counselor review, psychosocial intervention.
- **76–100**: `CRITICAL` — Severe acute crisis, immediate human operator takeover and priority escalation.

## Design Principles
- **Explainability**: Every score increment or decrement must be traceable to explicit contributing factors (e.g. substance history, lack of shelter, isolation, acoustic distress, verbal indicators).
- **Non-Diagnostic**: SVI is an operational triage metric to assist human helpline operators in prioritizing assistance; it is strictly NOT a diagnostic clinical instrument.
- **Auditable History**: Longitudinal evolution of the score throughout the call is logged and persisted.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary, SVI bands enum, and `SVI_UPDATED` event payload contract.
- **Phase 5 (Upcoming)**: Calibrated scoring engine, factor weighting, and operator dashboard real-time calculation.
