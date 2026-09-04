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
