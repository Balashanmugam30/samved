# SAMVED — Case Intelligence Service (`services/case-service`)

## Purpose
Manages victim case records, conversation linkages, risk progression histories, safety incidents, follow-up scheduling, and longitudinal outcome tracking.

## Core Responsibilities
- Lifecycle management of `Case` records (`INTAKE` → `TRIAGED` → `ESCALATED` → `FOLLOW_UP_PENDING` → `CLOSED`).
- Association of multiple calls/sessions to a unified anonymous victim timeline.
- Privacy-preserving redaction and pseudonymization of victim identifiers.
- Aggregation of recommendations (IRCAs, de-addiction centers, legal aid clinics).
- Audit trail emission for every case state transition.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary, relational models, and Pydantic/TypeScript domain schemas (`Case`, `Followup`, `ConsentRecord`).
- **Phase 11 (Upcoming)**: Full case management API, timeline synthesis, and case graph persistence.
