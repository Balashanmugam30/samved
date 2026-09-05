-- SAMVED Database Schema Initialization (Phase 0 Baseline)
-- Target: PostgreSQL 15+ (pgvector prepared)

-- Optional: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Optional: CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Users & Roles
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    permissions JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL REFERENCES roles(name),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Cases
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(36) PRIMARY KEY,
    case_number VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'INTAKE',
    primary_language VARCHAR(20) DEFAULT 'hi-IN',
    svi_score INT CHECK (svi_score >= 0 AND svi_score <= 100),
    svi_band VARCHAR(20),
    assigned_operator_id VARCHAR(36) REFERENCES users(id),
    consent_recorded BOOLEAN DEFAULT FALSE,
    notes_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Telephony Calls
CREATE TABLE IF NOT EXISTS calls (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) REFERENCES cases(id),
    telephony_provider VARCHAR(50) NOT NULL,
    external_call_id VARCHAR(100) NOT NULL,
    caller_masked_number VARCHAR(30) NOT NULL,
    start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMPTZ,
    duration_seconds INT,
    status VARCHAR(50) DEFAULT 'in_progress'
);

-- 4. Conversations & Utterances
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    session_id VARCHAR(100) NOT NULL,
    language VARCHAR(20) DEFAULT 'hi-IN',
    turns_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS utterances (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    speaker VARCHAR(30) NOT NULL,
    text TEXT NOT NULL,
    language VARCHAR(20),
    start_time_ms INT,
    end_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. Safety Alerts & Risk Scores
CREATE TABLE IF NOT EXISTS safety_alerts (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    alert_level VARCHAR(30) NOT NULL,
    trigger_reason TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    acknowledged_by VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    score INT NOT NULL CHECK (score >= 0 AND score <= 100),
    band VARCHAR(30) NOT NULL,
    explainability_summary TEXT,
    is_clinical_diagnosis BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Recommendations & Legal Sources
CREATE TABLE IF NOT EXISTS recommendations (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    legal_grounding_ref VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Audit Logs & Model Runs
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_runs (
    id VARCHAR(36) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    purpose VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. Operator Workstation (Phase 8)
CREATE TABLE IF NOT EXISTS operator_notes (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    operator_id VARCHAR(36) DEFAULT 'operator',
    category VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operator_actions (
    id VARCHAR(36) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    actor_id VARCHAR(36) DEFAULT 'operator',
    action_type VARCHAR(50) NOT NULL,
    previous_state VARCHAR(50),
    new_state VARCHAR(50),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS call_operator_states (
    call_id VARCHAR(36) PRIMARY KEY REFERENCES calls(id),
    ownership_state VARCHAR(50) NOT NULL DEFAULT 'UNASSIGNED',
    handoff_status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    adaptive_paused BOOLEAN DEFAULT FALSE,
    active_operator_id VARCHAR(36),
    handoff_target VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. Multi-Agent Orchestration (Phase 9)
CREATE TABLE IF NOT EXISTS orchestration_runs (
    id VARCHAR(64) PRIMARY KEY,
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    turn_id VARCHAR(64) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    selected_agents JSONB DEFAULT '[]'::jsonb,
    completed_agents JSONB DEFAULT '[]'::jsonb,
    failed_agents JSONB DEFAULT '[]'::jsonb,
    timed_out_agents JSONB DEFAULT '[]'::jsonb,
    cancelled_agents JSONB DEFAULT '[]'::jsonb,
    briefing JSONB DEFAULT '{}'::jsonb,
    validated_context JSONB DEFAULT '{}'::jsonb,
    total_latency_ms FLOAT DEFAULT 0.0,
    warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_executions (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) REFERENCES orchestration_runs(id),
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    agent_name VARCHAR(100) NOT NULL,
    agent_version VARCHAR(50) DEFAULT '1.0.0',
    status VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    latency_ms FLOAT DEFAULT 0.0,
    result JSONB DEFAULT '{}'::jsonb,
    evidence_refs JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    produced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_call_id ON orchestration_runs(call_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_call_id ON agent_executions(call_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_run_id ON agent_executions(run_id);

-- Seed baseline roles
INSERT INTO roles (id, name, permissions) VALUES
    ('role-admin', 'ADMIN', '["*"]'::jsonb),
    ('role-supervisor', 'SUPERVISOR', '["cases:read", "cases:write", "alerts:override", "audit:read"]'::jsonb),
    ('role-operator', 'OPERATOR', '["cases:read", "cases:write", "calls:handle"]'::jsonb),
    ('role-auditor', 'AUDITOR', '["audit:read", "reports:read"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

