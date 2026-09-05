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
    citation_ref VARCHAR(255),
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

-- 10. Legal / Policy Knowledge RAG (Phase 10)
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    authority_tier INT NOT NULL DEFAULT 1,
    verified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'MARKDOWN',
    jurisdiction VARCHAR(50) NOT NULL DEFAULT 'INDIA',
    language VARCHAR(20) DEFAULT 'en-IN',
    topic VARCHAR(50) DEFAULT 'GOVERNMENT_SCHEME',
    issued_at TIMESTAMPTZ,
    effective_from DATE NOT NULL,
    effective_to DATE,
    current_version VARCHAR(50) DEFAULT '1.0',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    authority_tier INT NOT NULL DEFAULT 1,
    checksum VARCHAR(64) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    license_notes TEXT,
    verified_source BOOLEAN DEFAULT TRUE,
    verification_method VARCHAR(100) DEFAULT 'checksum_match',
    retrieved_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_document_versions (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES knowledge_documents(id),
    version_number VARCHAR(50) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    superseded_by VARCHAR(50),
    supersedes VARCHAR(50),
    checksum VARCHAR(64) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    retrieved_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES knowledge_documents(id),
    version_number VARCHAR(50) NOT NULL,
    heading_path JSONB DEFAULT '[]'::jsonb,
    section_page VARCHAR(255),
    paragraph_range VARCHAR(100),
    text TEXT NOT NULL,
    language VARCHAR(20) DEFAULT 'en-IN',
    jurisdiction VARCHAR(50) DEFAULT 'INDIA',
    effective_from DATE NOT NULL,
    effective_to DATE,
    qualifiers JSONB DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_citations (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL REFERENCES knowledge_documents(id),
    document_title VARCHAR(500) NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    version_number VARCHAR(50) NOT NULL,
    section_page VARCHAR(255) NOT NULL,
    effective_date VARCHAR(100) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    excerpt TEXT NOT NULL,
    authority_tier INT NOT NULL,
    jurisdiction VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_retrieval_events (
    id VARCHAR(64) PRIMARY KEY,
    call_id VARCHAR(36) REFERENCES calls(id),
    query TEXT NOT NULL,
    jurisdiction VARCHAR(50),
    language VARCHAR(20),
    as_of_date DATE,
    status VARCHAR(50) NOT NULL,
    total_found INT DEFAULT 0,
    selected_citations JSONB DEFAULT '[]'::jsonb,
    conflict_detected BOOLEAN DEFAULT FALSE,
    requires_human_review BOOLEAN DEFAULT FALSE,
    search_latency_ms FLOAT DEFAULT 0.0,
    executed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_ingestion_audit (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    version_number VARCHAR(50) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    action VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_jurisdiction ON knowledge_documents(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status ON knowledge_documents(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc_id ON knowledge_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_retrieval_call_id ON knowledge_retrieval_events(call_id);

-- 11. Case Intelligence & Knowledge Graph (Phase 11)
CREATE TABLE IF NOT EXISTS case_calls (
    id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    call_id VARCHAR(36) NOT NULL REFERENCES calls(id),
    linked_by VARCHAR(50) DEFAULT 'operator',
    is_primary BOOLEAN DEFAULT FALSE,
    linked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    unlinked_at TIMESTAMPTZ,
    UNIQUE(case_id, call_id)
);

CREATE TABLE IF NOT EXISTS case_entities (
    entity_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    entity_type VARCHAR(50) NOT NULL,
    role VARCHAR(50),
    label VARCHAR(255) NOT NULL,
    claim_status VARCHAR(30) NOT NULL DEFAULT 'REPORTED',
    confidence FLOAT NOT NULL DEFAULT 1.0,
    source_refs JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    first_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_relationships (
    edge_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    source_entity VARCHAR(64) NOT NULL REFERENCES case_entities(entity_id),
    relationship_type VARCHAR(50) NOT NULL,
    target_entity VARCHAR(64) NOT NULL REFERENCES case_entities(entity_id),
    claim_status VARCHAR(30) NOT NULL DEFAULT 'REPORTED',
    confidence FLOAT NOT NULL DEFAULT 1.0,
    source_refs JSONB DEFAULT '[]'::jsonb,
    valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMPTZ,
    observed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    superseded_at TIMESTAMPTZ,
    superseded_by VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_events (
    event_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    severity VARCHAR(30),
    actor_id VARCHAR(50),
    source_type VARCHAR(50) DEFAULT 'SYSTEM',
    evidence_refs JSONB DEFAULT '[]'::jsonb,
    claim_status VARCHAR(30) NOT NULL DEFAULT 'REPORTED',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_evidence_links (
    link_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    entity_id VARCHAR(64) REFERENCES case_entities(entity_id),
    edge_id VARCHAR(64) REFERENCES case_relationships(edge_id),
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    turn_index INT,
    verbatim_excerpt TEXT,
    citation_ref VARCHAR(255),
    content_hash VARCHAR(64),
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_entity_candidates (
    candidate_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    source_entity VARCHAR(64) NOT NULL,
    source_label VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,
    target_entity VARCHAR(64) NOT NULL,
    target_label VARCHAR(255) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    evidence_excerpt TEXT NOT NULL,
    source_turn VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    confirmed_by VARCHAR(50),
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_merge_operations (
    operation_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    operation_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(50) NOT NULL,
    primary_entity_id VARCHAR(64) NOT NULL,
    secondary_entity_id VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    executed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_case_calls_case_id ON case_calls(case_id);
CREATE INDEX IF NOT EXISTS idx_case_calls_call_id ON case_calls(call_id);
CREATE INDEX IF NOT EXISTS idx_case_entities_case_id ON case_entities(case_id);
CREATE INDEX IF NOT EXISTS idx_case_entities_type ON case_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_case_relationships_case_id ON case_relationships(case_id);
CREATE INDEX IF NOT EXISTS idx_case_relationships_source ON case_relationships(source_entity);
CREATE INDEX IF NOT EXISTS idx_case_relationships_target ON case_relationships(target_entity);
CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id);
CREATE INDEX IF NOT EXISTS idx_case_events_time ON case_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_case_evidence_case_id ON case_evidence_links(case_id);
CREATE INDEX IF NOT EXISTS idx_case_candidates_case_id ON case_entity_candidates(case_id);
CREATE INDEX IF NOT EXISTS idx_case_candidates_status ON case_entity_candidates(status);

-- Phase 12: Follow-up Workflow & Continuity Engine Tables
CREATE TABLE IF NOT EXISTS followup_consents (
    consent_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    followup_id VARCHAR(64),
    consent_state VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    purpose VARCHAR(255) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    recorded_by VARCHAR(50) NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS followup_preferences (
    preference_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    preferred_channel VARCHAR(30) NOT NULL DEFAULT 'OPERATOR_CALLBACK',
    preferred_time_window VARCHAR(50),
    days_allowed JSONB DEFAULT '[]'::jsonb,
    safe_to_contact BOOLEAN DEFAULT TRUE,
    preferred_language VARCHAR(20) DEFAULT 'en-IN',
    human_only BOOLEAN DEFAULT TRUE,
    no_voicemail BOOLEAN DEFAULT FALSE,
    no_text BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followups (
    followup_id VARCHAR(64) PRIMARY KEY,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    call_id VARCHAR(64),
    created_by VARCHAR(50) NOT NULL,
    assigned_to VARCHAR(50),
    type VARCHAR(40) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    priority VARCHAR(30) NOT NULL DEFAULT 'NORMAL',
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMPTZ NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    consent_state VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    safe_contact_window VARCHAR(50),
    channel VARCHAR(30) NOT NULL DEFAULT 'OPERATOR_CALLBACK',
    purpose VARCHAR(255) NOT NULL,
    notes_ref VARCHAR(64),
    citation_ref VARCHAR(128),
    source_event VARCHAR(64),
    last_attempt_at TIMESTAMPTZ,
    attempt_count INT DEFAULT 0,
    max_attempts INT DEFAULT 2,
    outcome VARCHAR(40),
    policy_version VARCHAR(20) DEFAULT 'v1.0',
    blocked_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followup_attempts (
    attempt_id VARCHAR(64) PRIMARY KEY,
    followup_id VARCHAR(64) NOT NULL REFERENCES followups(followup_id),
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    attempt_number INT NOT NULL,
    operator_id VARCHAR(50) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    result VARCHAR(40) NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS followup_events (
    event_id VARCHAR(64) PRIMARY KEY,
    followup_id VARCHAR(64) NOT NULL REFERENCES followups(followup_id),
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id),
    event_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(50) NOT NULL,
    previous_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    reason TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_followups_case_id ON followups(case_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON followups(status);
CREATE INDEX IF NOT EXISTS idx_followups_scheduled_for ON followups(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_followups_due_at ON followups(due_at);
CREATE INDEX IF NOT EXISTS idx_followups_assigned_to ON followups(assigned_to);
CREATE INDEX IF NOT EXISTS idx_followups_consent_state ON followups(consent_state);
CREATE INDEX IF NOT EXISTS idx_followups_priority ON followups(priority);
CREATE INDEX IF NOT EXISTS idx_followup_attempts_followup_id ON followup_attempts(followup_id);
CREATE INDEX IF NOT EXISTS idx_followup_events_followup_id ON followup_events(followup_id);

-- 10. District Intelligence & Operational Analytics (Phase 13)
CREATE TABLE IF NOT EXISTS analytics_metric_definitions (
    metric_id VARCHAR(64) PRIMARY KEY,
    metric_version VARCHAR(20) NOT NULL DEFAULT 'v1.0.0',
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    definition TEXT NOT NULL,
    calculation_method TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OBSERVED',
    privacy_level VARCHAR(30) NOT NULL DEFAULT 'AGGREGATE',
    source_event_types JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_district_summaries (
    summary_id VARCHAR(64) PRIMARY KEY,
    district_code VARCHAR(30) NOT NULL,
    district_name VARCHAR(100) NOT NULL,
    state_code VARCHAR(10) NOT NULL,
    state_name VARCHAR(100) NOT NULL,
    period VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    metrics_json JSONB NOT NULL,
    privacy_status VARCHAR(30) NOT NULL DEFAULT 'PASS',
    data_quality_status VARCHAR(30) NOT NULL DEFAULT 'HEALTHY',
    metric_version VARCHAR(20) DEFAULT 'v1.0.0',
    computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_metric_values (
    value_id VARCHAR(64) PRIMARY KEY,
    metric_id VARCHAR(64) NOT NULL REFERENCES analytics_metric_definitions(metric_id),
    district_code VARCHAR(30) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    dimension_values JSONB DEFAULT '{}'::jsonb,
    raw_value NUMERIC,
    display_value VARCHAR(50) NOT NULL,
    suppressed BOOLEAN DEFAULT FALSE,
    metric_status VARCHAR(30) NOT NULL DEFAULT 'OBSERVED',
    computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_access_audit (
    audit_id VARCHAR(64) PRIMARY KEY,
    actor_id VARCHAR(50) NOT NULL,
    actor_role VARCHAR(30) NOT NULL,
    endpoint VARCHAR(128) NOT NULL,
    district_code VARCHAR(30),
    period VARCHAR(20),
    privacy_status VARCHAR(30) DEFAULT 'PASS',
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_job_runs (
    job_id VARCHAR(64) PRIMARY KEY,
    metric_version VARCHAR(20) NOT NULL DEFAULT 'v1.0.0',
    period VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'RUNNING',
    source_event_count INT DEFAULT 0,
    processed_count INT DEFAULT 0,
    suppressed_count INT DEFAULT 0,
    error_count INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_analytics_summaries_district ON analytics_district_summaries(district_code);
CREATE INDEX IF NOT EXISTS idx_analytics_summaries_period ON analytics_district_summaries(period, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_analytics_values_metric ON analytics_metric_values(metric_id, district_code);
CREATE INDEX IF NOT EXISTS idx_analytics_audit_actor ON analytics_access_audit(actor_id, accessed_at);
CREATE INDEX IF NOT EXISTS idx_analytics_job_status ON analytics_job_runs(status, started_at);

-- Seed baseline roles
INSERT INTO roles (id, name, permissions) VALUES
    ('role-admin', 'ADMIN', '["*"]'::jsonb),
    ('role-supervisor', 'SUPERVISOR', '["cases:read", "cases:write", "alerts:override", "audit:read", "analytics:read", "simulation:read", "simulation:write"]'::jsonb),
    ('role-district-admin', 'DISTRICT_ADMIN', '["analytics:read", "districts:read"]'::jsonb),
    ('role-operator', 'OPERATOR', '["cases:read", "cases:write", "calls:handle", "training:use"]'::jsonb),
    ('role-auditor', 'AUDITOR', '["audit:read", "reports:read", "simulation:read"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- Phase 14: Scenario Simulation Engine & Operator Training Sandbox Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id VARCHAR(64) PRIMARY KEY,
    scenario_id VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    language VARCHAR(10) NOT NULL,
    expected_svi_band VARCHAR(20) NOT NULL,
    expected_score_range INT[] DEFAULT ARRAY[0, 100],
    expected_safety_triggers JSONB DEFAULT '[]'::jsonb,
    prohibited_safety_triggers JSONB DEFAULT '[]'::jsonb,
    noise_profile VARCHAR(30) DEFAULT 'CLEAN',
    synthetic_dialogue JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_rag_citations JSONB DEFAULT '[]'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS simulation_benchmark_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    suite VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    total_scenarios INT DEFAULT 0,
    passed_scenarios INT DEFAULT 0,
    failed_scenarios INT DEFAULT 0,
    pass_rate FLOAT DEFAULT 0.0,
    mean_wer FLOAT DEFAULT 0.0,
    mean_cer FLOAT DEFAULT 0.0,
    safety_recall_rate FLOAT DEFAULT 1.0,
    svi_band_accuracy FLOAT DEFAULT 1.0,
    p95_latency_ms FLOAT DEFAULT 0.0,
    critical_safety_passed BOOLEAN DEFAULT TRUE,
    results JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS operator_training_drills (
    id VARCHAR(64) PRIMARY KEY,
    drill_key VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    difficulty VARCHAR(30) NOT NULL,
    language VARCHAR(10) NOT NULL,
    description TEXT,
    scenario_context TEXT,
    expected_competencies JSONB DEFAULT '[]'::jsonb,
    turns JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operator_training_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    drill_id VARCHAR(64) REFERENCES operator_training_drills(id),
    trainee_id VARCHAR(64) NOT NULL,
    trainee_name VARCHAR(128) DEFAULT 'Counselor Trainee',
    status VARCHAR(30) DEFAULT 'ACTIVE',
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    current_turn INT DEFAULT 1,
    total_turns INT DEFAULT 2,
    overall_score FLOAT,
    performance_rating VARCHAR(30),
    competency_breakdown JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    evaluated_turns JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_sim_scenarios_lang_band ON simulation_scenarios(language, expected_svi_band);
CREATE INDEX IF NOT EXISTS idx_sim_runs_suite_status ON simulation_benchmark_runs(suite, status);
CREATE INDEX IF NOT EXISTS idx_training_drills_diff ON operator_training_drills(difficulty, category);
CREATE INDEX IF NOT EXISTS idx_training_sessions_trainee ON operator_training_sessions(trainee_id, started_at);




