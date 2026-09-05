/**
 * SAMVED Event Envelope & Taxonomy Contract (v1.0)
 * Canonical event definitions for Realtime WebSocket and internal streaming.
 */

export const SCHEMA_VERSION = "1.0";

export enum EventType {
  // Telephony lifecycle
  CALL_STARTED = "CALL_STARTED",
  CALL_CONNECTED = "CALL_CONNECTED",
  CALL_ENDED = "CALL_ENDED",

  // Language & speech
  LANGUAGE_DETECTED = "LANGUAGE_DETECTED",
  LANGUAGE_CHANGED = "LANGUAGE_CHANGED",
  TRANSCRIPT_PARTIAL = "TRANSCRIPT_PARTIAL",
  TRANSCRIPT_FINAL = "TRANSCRIPT_FINAL",
  ACOUSTIC_UPDATE = "ACOUSTIC_UPDATE",

  // Safety & risk
  SAFETY_SIGNAL = "SAFETY_SIGNAL",
  SAFETY_STATE_UPDATED = "SAFETY_STATE_UPDATED",
  SAFETY_SIGNAL_ACKNOWLEDGED = "SAFETY_SIGNAL_ACKNOWLEDGED",
  RISK_UPDATED = "RISK_UPDATED",
  SVI_UPDATED = "SVI_UPDATED",

  // Adaptive conversation policy (Phase 7)
  ADAPTIVE_STRATEGY_SELECTED = "ADAPTIVE_STRATEGY_SELECTED",

  // Multi-agent & AI response
  AGENT_ACTION = "AGENT_ACTION",
  AI_THINKING = "AI_THINKING",
  AI_RESPONSE_STARTED = "AI_RESPONSE_STARTED",
  AI_RESPONSE_ENDED = "AI_RESPONSE_ENDED",
  TTS_STARTED = "TTS_STARTED",
  TTS_ENDED = "TTS_ENDED",
  SPEECH_INTERRUPTED = "SPEECH_INTERRUPTED",
  CONVERSATION_STATE_CHANGED = "CONVERSATION_STATE_CHANGED",
  TURN_LATENCY = "TURN_LATENCY",
  OPERATOR_SNAPSHOT = "OPERATOR_SNAPSHOT",
  STT_ERROR = "STT_ERROR",
  LLM_ERROR = "LLM_ERROR",
  TTS_ERROR = "TTS_ERROR",

  // Escalation & human oversight
  HUMAN_ALERT = "HUMAN_ALERT",
  ESCALATION_RECOMMENDED = "ESCALATION_RECOMMENDED",
  ESCALATION_ACCEPTED = "ESCALATION_ACCEPTED",
  ESCALATION_OVERRIDDEN = "ESCALATION_OVERRIDDEN",

  // Human Operator Workstation (Phase 8)
  OPERATOR_TAKEOVER = "OPERATOR_TAKEOVER",
  OPERATOR_RESUME_AI = "OPERATOR_RESUME_AI",
  OPERATOR_PAUSE_ADAPTIVE = "OPERATOR_PAUSE_ADAPTIVE",
  OPERATOR_REQUEST_SAFETY_CHECK = "OPERATOR_REQUEST_SAFETY_CHECK",
  OPERATOR_HANDOFF_REQUESTED = "OPERATOR_HANDOFF_REQUESTED",
  OPERATOR_HANDOFF_CONFIRMED = "OPERATOR_HANDOFF_CONFIRMED",
  OPERATOR_HANDOFF_CANCELLED = "OPERATOR_HANDOFF_CANCELLED",
  OPERATOR_NOTE_ADDED = "OPERATOR_NOTE_ADDED",
  OPERATOR_CALL_ENDED = "OPERATOR_CALL_ENDED",
  OPERATOR_STATE_CHANGED = "OPERATOR_STATE_CHANGED",

  // Multi-Agent Orchestration (Phase 9)
  ORCHESTRATION_STARTED = "ORCHESTRATION_STARTED",
  ORCHESTRATION_COMPLETED = "ORCHESTRATION_COMPLETED",
  ORCHESTRATION_DEGRADED = "ORCHESTRATION_DEGRADED",
  AGENT_STARTED = "AGENT_STARTED",
  AGENT_COMPLETED = "AGENT_COMPLETED",
  AGENT_FAILED = "AGENT_FAILED",
  AGENT_TIMEOUT = "AGENT_TIMEOUT",
  AGENT_CANCELLED = "AGENT_CANCELLED",
  OPERATOR_BRIEFING_GENERATED = "OPERATOR_BRIEFING_GENERATED",

  // Legal / Policy Knowledge RAG (Phase 10)
  KNOWLEDGE_SEARCH_STARTED = "KNOWLEDGE_SEARCH_STARTED",
  KNOWLEDGE_SEARCH_COMPLETED = "KNOWLEDGE_SEARCH_COMPLETED",
  KNOWLEDGE_SEARCH_FAILED = "KNOWLEDGE_SEARCH_FAILED",
  KNOWLEDGE_SOURCE_SELECTED = "KNOWLEDGE_SOURCE_SELECTED",
  KNOWLEDGE_SOURCE_CONFLICT = "KNOWLEDGE_SOURCE_CONFLICT",
  KNOWLEDGE_REVIEW_RECOMMENDED = "KNOWLEDGE_REVIEW_RECOMMENDED",
  KNOWLEDGE_ANSWER_BLOCKED = "KNOWLEDGE_ANSWER_BLOCKED",

  // Case & follow-up
  CASE_CREATED = "CASE_CREATED",
  FOLLOWUP_SCHEDULED = "FOLLOWUP_SCHEDULED",

  // Heartbeat / ping-pong
  HEARTBEAT_PING = "HEARTBEAT_PING",
  HEARTBEAT_PONG = "HEARTBEAT_PONG"
}

export interface EventEnvelope<T = Record<string, unknown>> {
  event_id: string;
  event_type: EventType;
  schema_version: string;
  timestamp: string; // ISO-8601 UTC
  session_id: string;
  call_id: string;
  case_id?: string | null;
  payload: T;
}

// Payload definitions
export interface CallStartedPayload {
  caller_channel: "exotel" | "twilio" | "simulation" | "dev";
  initiated_at: string;
}

export interface CallConnectedPayload {
  telephony_call_id: string;
  connected_at: string;
}

export interface CallEndedPayload {
  duration_seconds: number;
  disconnect_reason: "caller_hangup" | "agent_transfer" | "timeout" | "error";
  ended_at: string;
}

export interface TranscriptPayload {
  speaker: "caller" | "agent" | "system";
  text: string;
  confidence: number;
  is_final: boolean;
  language: string;
  start_time_ms: number;
  end_time_ms: number;
}

export interface AcousticSignalItem {
  code: string;
  evidence: string;
  confidence: number;
}

export interface AcousticUpdatePayload {
  quality: "EXCELLENT" | "GOOD" | "DEGRADED" | "POOR" | "INSUFFICIENT";
  confidence: number; // 0.0 to 1.0
  speech_activity_ratio: number;
  silence_ratio: number;
  longest_pause_ms: number;
  pause_count: number;
  interruption_count: number;
  energy_variability: number;
  mean_energy_rms: number;
  median_f0_hz?: number | null;
  signals: AcousticSignalItem[];
  engine_version?: string;
  disclaimer?: string;
  is_supporting_signal?: boolean; // Explicitly non-diagnostic
  // Legacy / backward-compatible optional fields
  pitch_hz?: number;
  speaking_rate_wpm?: number;
  pause_ratio?: number;
  energy_rms?: number;
  jitter?: number;
  shimmer?: number;
}

export interface SafetySignalPayload {
  signal_type: "IMMEDIATE_DANGER" | "ONGOING_VIOLENCE" | "SELF_HARM" | "UNSAFE_ENVIRONMENT" | "PERPETRATOR_PROXIMITY";
  triggered_by: "deterministic_rule" | "acoustic_pattern" | "keyword_match";
  severity: "CRITICAL" | "HIGH" | "MODERATE";
  description: string;
  requires_human_confirmation: boolean;
}

export enum SVIBand {
  LOW = "LOW",             // 0–25
  MODERATE = "MODERATE",   // 26–50
  HIGH = "HIGH",           // 51–75
  CRITICAL = "CRITICAL"    // 76–100
}

export enum SVITrend {
  INITIAL = "INITIAL",
  RISING = "RISING",
  FALLING = "FALLING",
  STABLE = "STABLE"
}

export interface SVIUpdatedPayload {
  score: number; // 0 to 100
  band: SVIBand;
  confidence: number;
  contributing_factors: Array<{
    factor: string;
    weight: number;
    evidence: string;
  }>;
  trend?: SVITrend;
  delta?: number;
  assessment_completeness?: number;
  top_contributors?: string[];
  protective_factor_reduction?: number;
  critical_override_applied?: boolean;
  requires_human_review?: boolean;
  acoustic_evidence_note?: string;
  is_clinical_diagnosis: false; // Explicit architectural guarantee
}

export interface HumanAlertPayload {
  alert_id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  title: string;
  message: string;
  action_required: boolean;
}

export interface AdaptiveStrategySelectedPayload {
  call_id: string;
  session_id: string;
  turn_index: number;
  action: string;
  priority: string;
  target_information: string;
  reason_codes: string[];
  evidence_refs: string[];
  language: string;
  confidence: number;
  constraints?: string[];
  requires_human_review?: boolean;
  operator_override_active?: boolean;
  fallback_applied?: boolean;
  disclaimer?: string;
  evaluated_at: string;
}

export enum OperatorOwnershipState {
  UNASSIGNED = "UNASSIGNED",
  AI_ASSISTED = "AI_ASSISTED",
  HUMAN_ASSIGNED = "HUMAN_ASSIGNED",
  HUMAN_ACTIVE = "HUMAN_ACTIVE",
  HANDOFF_PENDING = "HANDOFF_PENDING",
  ENDED = "ENDED"
}

export enum HandoffStatus {
  AVAILABLE = "AVAILABLE",
  REQUESTED = "REQUESTED",
  PENDING = "PENDING",
  CONFIRMED = "CONFIRMED",
  CANCELLED = "CANCELLED",
  FAILED = "FAILED"
}

export enum OperatorNoteCategory {
  GENERAL = "GENERAL",
  SAFETY = "SAFETY",
  FOLLOW_UP_NOTE = "FOLLOW_UP_NOTE",
  HANDOFF_NOTE = "HANDOFF_NOTE",
  TECHNICAL = "TECHNICAL"
}

export interface OperatorNotePayload {
  note_id: string;
  call_id: string;
  operator_id: string;
  category: OperatorNoteCategory;
  text: string;
  timestamp: string;
  is_structured: boolean;
}

export interface OperatorActionPayload {
  action_id: string;
  call_id: string;
  actor_id: string;
  action_type: string;
  previous_state?: string;
  new_state?: string;
  details?: Record<string, unknown>;
  summary: string;
  timestamp: string;
}

export interface OperatorStateChangedPayload {
  call_id: string;
  ownership_state: OperatorOwnershipState;
  handoff_status: HandoffStatus;
  adaptive_paused: boolean;
  active_operator_id?: string | null;
  updated_at: string;
}

// Phase 9 Multi-Agent Orchestration Enums & Contracts
export enum AgentType {
  DETERMINISTIC_ADAPTER = "DETERMINISTIC_ADAPTER",
  RULE_WORKER = "RULE_WORKER",
  LLM_WORKER = "LLM_WORKER",
  FORMATTER = "FORMATTER",
  SUMMARIZER = "SUMMARIZER",
  INTERFACE_STUB = "INTERFACE_STUB"
}

export enum AgentSafetyClassification {
  READ_ONLY_SAFETY = "READ_ONLY_SAFETY",
  OPERATIONAL = "OPERATIONAL",
  ADVISORY = "ADVISORY",
  NON_CRITICAL = "NON_CRITICAL",
  PLACEHOLDER = "PLACEHOLDER"
}

export enum AgentTimeoutTier {
  REALTIME_CRITICAL = "REALTIME_CRITICAL",
  REALTIME_NORMAL = "REALTIME_NORMAL",
  BACKGROUND = "BACKGROUND"
}

export enum AgentStatus {
  SUCCESS = "SUCCESS",
  FAILED = "FAILED",
  TIMED_OUT = "TIMED_OUT",
  CANCELLED = "CANCELLED",
  DEGRADED = "DEGRADED",
  UNAVAILABLE = "UNAVAILABLE"
}

export enum OrchestrationState {
  READY = "READY",
  RUNNING = "RUNNING",
  COMPLETED = "COMPLETED",
  DEGRADED = "DEGRADED",
  FAILED = "FAILED"
}

export interface AgentSpecPayload {
  name: string;
  version: string;
  agent_type: AgentType;
  capabilities: string[];
  timeout_tier: AgentTimeoutTier;
  max_latency_ms: number;
  safety_classification: AgentSafetyClassification;
  requires_human_review: boolean;
  is_realtime_capable: boolean;
  enabled: boolean;
}

export interface AgentResponsePayload {
  request_id: string;
  call_id: string;
  turn_id: string;
  agent_name: string;
  agent_version: string;
  status: AgentStatus;
  result: Record<string, unknown>;
  confidence: number;
  evidence_refs: string[];
  latency_ms: number;
  warnings?: string[];
  produced_at: string;
}

export interface OperatorBriefingPayload {
  safety_summary: string;
  svi_summary: string;
  acoustic_summary: string;
  adaptive_recommendation: string;
  key_facts: string[];
  evidence_refs: string[];
  confidence: number;
  generated_at: string;
}

export interface OrchestrationResultPayload {
  request_id: string;
  call_id: string;
  turn_id: string;
  state: OrchestrationState;
  selected_agents: string[];
  completed_agents: string[];
  failed_agents: string[];
  timed_out_agents: string[];
  cancelled_agents: string[];
  briefing?: OperatorBriefingPayload;
  total_latency_ms: number;
  warnings?: string[];
  completed_at: string;
}

// ==========================================
// Phase 10: Legal / Policy Knowledge RAG Enums & Contracts
// ==========================================

export enum AuthorityTier {
  TIER_1 = 1, // Official GoI / State Official Sources, Statutory Gazettes
  TIER_2 = 2, // Official Courts, Tribunals, Statutory Commissions
  TIER_3 = 3, // Approved Institutional Partners & Shelters
  TIER_4 = 4, // Secondary References & Operational SOPs
}

export enum DocumentStatus {
  DISCOVERED = "DISCOVERED",
  INGESTED = "INGESTED",
  PARSED = "PARSED",
  VALIDATED = "VALIDATED",
  INDEXED = "INDEXED",
  ACTIVE = "ACTIVE",
  SUPERSEDED = "SUPERSEDED",
  RETIRED = "RETIRED",
  REJECTED = "REJECTED",
}

export enum FreshnessStatus {
  CURRENT = "CURRENT",
  STALE = "STALE",
  EXPIRED = "EXPIRED",
  UNKNOWN = "UNKNOWN",
}

export enum KnowledgeJurisdiction {
  INDIA = "INDIA",
  TAMIL_NADU = "TAMIL_NADU",
  CENTRAL_GOVERNMENT = "CENTRAL_GOVERNMENT",
  JURISDICTION_UNCERTAIN = "JURISDICTION_UNCERTAIN",
}

export interface CitationMetadata {
  citation_id: string;
  document_id: string;
  document_title: string;
  publisher: string;
  version: string;
  section_page: string;
  effective_date: string;
  source_url: string;
  retrieved_at: string;
  excerpt: string;
  authority_tier: number;
  jurisdiction: string;
}

export interface KnowledgeItemPayload {
  document_id: string;
  version: string;
  title: string;
  publisher: string;
  jurisdiction: string;
  source_url: string;
  chunk_id: string;
  excerpt: string;
  relevance: number;
  authority_tier: number;
  effective_status: string;
  source_date: string;
  retrieved_at: string;
  citation: CitationMetadata;
}

export interface KnowledgeQueryPayload {
  query: string;
  language?: string;
  jurisdiction?: string;
  topic?: string;
  source_tiers?: number[];
  as_of_date?: string;
  effective_only?: boolean;
  max_results?: number;
}

export interface KnowledgeResultPayload {
  query_id: string;
  call_id?: string;
  query: string;
  status: "COMPLETED" | "NO_RELIABLE_SOURCE_FOUND" | "CONFLICT" | "DEGRADED" | "FAILED";
  total_found: number;
  results: KnowledgeItemPayload[];
  citations: CitationMetadata[];
  ai_summary?: string;
  requires_human_review: boolean;
  review_reasons?: string[];
  conflict_detected?: boolean;
  conflicting_sources?: Array<{
    source_a: string;
    source_b: string;
    description: string;
  }>;
  search_latency_ms: number;
  executed_at: string;
}

