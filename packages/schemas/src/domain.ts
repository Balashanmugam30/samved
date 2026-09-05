/**
 * SAMVED Core Domain Contracts
 * Strongly typed interface contracts for domain entities across the monorepo.
 */

export enum RoleType {
  ADMIN = "ADMIN",
  SUPERVISOR = "SUPERVISOR",
  OPERATOR = "OPERATOR",
  AUDITOR = "AUDITOR"
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: RoleType;
  created_at: string;
  is_active: boolean;
}

export interface Role {
  id: string;
  name: RoleType;
  permissions: string[];
}

export enum CaseStatus {
  OPEN = "OPEN",
  ACTIVE = "ACTIVE",
  INTAKE = "INTAKE",
  TRIAGED = "TRIAGED",
  ESCALATED = "ESCALATED",
  ON_HOLD = "ON_HOLD",
  FOLLOW_UP_PENDING = "FOLLOW_UP_PENDING",
  RESOLVED = "RESOLVED",
  CLOSED = "CLOSED",
  ARCHIVED = "ARCHIVED",
  UNKNOWN = "UNKNOWN"
}

export interface Case {
  id: string;
  case_number: string;
  status: CaseStatus;
  primary_language: string;
  svi_score?: number | null;
  svi_band?: string | null;
  assigned_operator_id?: string | null;
  created_at: string;
  updated_at: string;
  consent_recorded: boolean;
  notes_summary?: string | null;
}

export interface Call {
  id: string;
  telephony_provider: "exotel" | "twilio" | "mock";
  external_call_id: string;
  caller_masked_number: string; // Masked for privacy (e.g. +91-XXXXX-12345)
  start_time: string;
  end_time?: string | null;
  duration_seconds?: number | null;
  case_id?: string | null;
  status: "in_progress" | "completed" | "dropped" | "transferred";
}

export interface Conversation {
  id: string;
  call_id: string;
  session_id: string;
  language: string;
  turns_count: number;
  created_at: string;
}

export interface Utterance {
  id: string;
  conversation_id: string;
  speaker: "caller" | "ai_assistant" | "operator";
  text: string;
  language: string;
  timestamp: string;
  start_time_ms: number;
  end_time_ms: number;
}

export interface RiskEvent {
  id: string;
  call_id: string;
  timestamp: string;
  risk_type: string;
  severity: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  evidence_snippet: string;
  detected_by: "safety_rule" | "acoustic_engine" | "nlp_classifier";
}

export interface RiskScore {
  id: string;
  call_id: string;
  timestamp: string;
  score: number; // 0–100
  band: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  explainability_summary: string;
  is_clinical_diagnosis: false;
}

export interface SafetyAlert {
  id: string;
  call_id: string;
  alert_level: "CRITICAL" | "HIGH" | "MODERATE";
  trigger_reason: string;
  status: "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "OVERRIDDEN";
  acknowledged_by?: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  case_id: string;
  category: "MEDICAL_ASSISTANCE" | "SHELTER" | "LEGAL_AID" | "DE_ADDICTION_CENTER" | "PSYCHOSOCIAL_SUPPORT";
  title: string;
  description: string;
  legal_grounding_ref?: string | null;
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  category: "POLICY" | "STANDARD_OPERATING_PROCEDURE" | "LEGAL_STATUTE" | "SCHEME";
  content_url: string;
  version: string;
}

export interface LegalSource {
  id: string;
  act_name: string;
  section: string;
  description: string;
  official_gazette_ref?: string | null;
  is_authoritative: true;
}

export interface Followup {
  id: string;
  case_id: string;
  scheduled_at: string;
  status: "SCHEDULED" | "COMPLETED" | "MISSED" | "CANCELLED";
  priority: "HIGH" | "STANDARD";
  notes?: string | null;
}

export interface ConsentRecord {
  id: string;
  case_id: string;
  call_id: string;
  consent_given: boolean;
  consent_timestamp: string;
  language_used: string;
  scope: "TRIAGE_AND_SUPPORT_ONLY";
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address?: string;
  details?: Record<string, unknown>;
}

export interface ModelRun {
  id: string;
  model_name: string;
  model_provider: "gemini" | "sarvam" | "openai" | "mock";
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  purpose: "TRIAGE_CLASSIFICATION" | "CONVERSATION_RESPONSE" | "LEGAL_CITATION";
  timestamp: string;
}

export interface EvaluationScenario {
  id: string;
  name: string;
  description: string;
  expected_svi_band: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  expected_safety_triggers: string[];
  synthetic_dialogue: Array<{
    speaker: "caller" | "agent";
    text: string;
  }>;
  is_synthetic: true;
}
