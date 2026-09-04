# SAMVED — Database Architecture & Migrations (`infra/db`)

## PostgreSQL Engine
SAMVED uses PostgreSQL as the primary transactional datastore.

## Core Tables
- `users` & `roles`: Role-based access control (Admin, Supervisor, Operator, Auditor)
- `cases`: Core victim case management records with status and assigned tele-counselor
- `calls`: Telephony call logs (caller numbers masked for privacy)
- `conversations` & `utterances`: Multi-turn dialogue transcript segments
- `safety_alerts`: High-priority safety events requiring human review
- `risk_scores`: SVI scores and explainability factors
- `recommendations`: Grounded support referrals
- `audit_logs`: Immutable security, data access, and override records
- `model_runs`: Performance and latency tracking for LLM/ASR/TTS runs

## Migration Strategy
For Phase 0 development:
- `init.sql` provides the clean relational baseline schema.
- In Phase 1+, Alembic will manage incremental schema migrations against the PostgreSQL container.
