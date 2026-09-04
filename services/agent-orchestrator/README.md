# SAMVED — Multi-Agent Orchestrator (`services/agent-orchestrator`)

## Purpose
Coordinates bounded, specialized AI agents operating under strict governance, preventing uncontrolled generative hallucination.

## Specialized Agent Roles
1. **Safety Agent**: Monitors dialogue turns for immediate threat indicators and triggers deterministic safety policies.
2. **Legal Agent**: Formulates queries against authoritative legal statutes (NDPS Act, Mental Healthcare Act) via RAG.
3. **Care Agent**: Synthesizes empathetic, non-judgmental conversational responses in the caller's language.
4. **Case Agent**: Extracts structured entity data (substances mentioned, duration, family context, previous treatment) for case records.
5. **Follow-up Agent**: Evaluates scheduled check-in needs and drafts follow-up cadences.
6. **Policy & Governance Agent**: Enforces data redaction, audit logging, and human-in-the-loop escalation boundaries.

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary and `AGENT_ACTION` event schema.
- **Phase 9 (Upcoming)**: Multi-agent message bus, state graph orchestration, and tool execution governance.
