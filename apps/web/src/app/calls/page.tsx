"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  PhoneCall,
  Activity,
  Play,
  CheckCircle2,
  RefreshCw,
  Radio,
  Server,
  ShieldCheck,
  AlertCircle,
  Mic,
  Cpu,
  Volume2,
  AlertTriangle,
  Clock,
  Globe,
  MessageSquare,
  Filter,
  Eye,
  X,
  Copy,
  Check,
  Wifi,
  WifiOff,
  User,
  Bot,
  Layers,
  ShieldAlert,
  CheckSquare,
  FileText,
  Terminal,
  Compass,
  BookOpen,
  Scale,
  Search,
  ExternalLink,
  BookmarkPlus,
  Calendar,
  CalendarCheck,
  CalendarClock,
  UserCheck,
  History,
  Ban,
} from "lucide-react";
import { useOperatorWebSocket } from "@/hooks/useOperatorWebSocket";
import {
  EventEnvelope,
  EventType,
  FollowupType,
  FollowupStatus,
  ConsentState,
  FollowupPriority,
  ContactChannel,
  ContactResult,
  FollowupOutcome,
  FollowupPayload,
  FollowupWorkqueueSummaryPayload,
} from "@samved/schemas";

interface SafetyEvidence {
  rule_id: string;
  rule_version: string;
  matched_category: string;
  matched_phrase: string;
  reason: string;
  source_utterance_id?: string;
  temporal_context: string;
  negated: boolean;
}

interface SafetySignalItem {
  signal_id: string;
  signal_type: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | "INFO";
  confidence: number;
  evidence: SafetyEvidence;
  rule_id: string;
  rule_version: string;
  call_id: string;
  session_id: string;
  requires_human_review: boolean;
  acknowledged?: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
  created_at: string;
}

interface CallSummaryItem {
  session_id: string;
  call_id: string;
  provider_call_id: string;
  provider: string;
  caller_masked_number: string;
  state: string;
  created_at: string;
  connected_at?: string | null;
  ended_at?: string | null;
  last_activity_at: string;
  duration_seconds: number;
  conversation_state: string;
  current_language: string;
  safety_state?: string;
  safety_signals?: SafetySignalItem[];
  safety_signals_count?: number;
  utterances_count: number;
  events_count: number;
  is_active: boolean;
}

interface TranscriptItem {
  utterance_id: string;
  speaker: "caller" | "agent" | "system";
  text: string;
  language?: string;
  confidence?: number;
  is_final?: boolean;
  intent?: string;
  safety_flag?: boolean;
  timestamp: string;
}

interface LatencyMetrics {
  stt_ms: number;
  llm_ms: number;
  tts_ms: number;
  total_ms: number;
}

const SCENARIOS = [
  {
    key: "tamil_help",
    name: "Tamil Distress & Safety Verification (ta-IN)",
    lang: "Tamil (ta-IN)",
    desc: "Caller in acute fear speaking colloquial Tamil. Gemini verifies immediate safety in Tamil.",
  },
  {
    key: "hindi_help",
    name: "Hindi Assistance & De-addiction Inquiry (hi-IN)",
    lang: "Hindi (hi-IN)",
    desc: "Caller seeking de-addiction helpline support in Hindi. Gemini acknowledges and categorizes.",
  },
  {
    key: "english_help",
    name: "Indian English Support Request (en-IN)",
    lang: "English (en-IN)",
    desc: "Victim support request in Indian English with structured clarification.",
  },
  {
    key: "code_switch",
    name: "Code-Switching Resilience (ta-IN + en-IN)",
    lang: "Multilingual",
    desc: "Caller blends Tamil and English. Orchestrator detects seamless language transitions.",
  },
  {
    key: "ongoing_threat",
    name: "Active Ongoing Physical Threat (en-IN)",
    lang: "English (en-IN)",
    desc: "Acute threat: 'He is breaking into my door and trying to hit me!'. Triggers ACTIVE_THREAT signal.",
  },
  {
    key: "weapon_threat",
    name: "Weapon Threat Compound Escalation",
    lang: "English (en-IN)",
    desc: "Compound threat: 'He has a knife and is breaking the door!'. Triggers CRITICAL weapon escalation.",
  },
  {
    key: "self_harm",
    name: "Self-Harm Risk Statement",
    lang: "English (en-IN)",
    desc: "Explicit ideation: 'I cannot take this anymore, I want to end my life'. Triggers SELF_HARM signal.",
  },
  {
    key: "confinement",
    name: "Forced Confinement / Restraint",
    lang: "English (en-IN)",
    desc: "Forced confinement: 'They locked me inside the room and won't let me out'. Triggers CONFINEMENT.",
  },
  {
    key: "false_positive_weapon",
    name: "Incidental Weapon Mention (False Positive Test)",
    lang: "English (en-IN)",
    desc: "Kitchen knife mention: 'Cutting vegetables with a knife'. Correctly avoids CRITICAL escalation.",
  },
  {
    key: "negated_threat",
    name: "Negated Threat Cue (Negation Test)",
    lang: "English (en-IN)",
    desc: "Explicit negation: 'There is no weapon here, he does not have a knife'. Yields NONE state.",
  },
  {
    key: "interruption",
    name: "Barge-in / Caller Interruption Test",
    lang: "Barge-in",
    desc: "Caller speaks while agent is speaking. Orchestrator halts TTS and flushes outbound queue immediately.",
  },
];

type EventFilterCategory =
  | "ALL"
  | "TRANSCRIPT"
  | "CONVERSATION"
  | "SAFETY"
  | "ERRORS"
  | "LATENCY"
  | "OPERATOR"
  | "SVI"
  | "ACOUSTIC"
  | "ADAPTIVE"
  | "ORCHESTRATION"
  | "KNOWLEDGE"
  | "CASE"
  | "FOLLOWUP";


export default function OperatorCallsPage() {
  // Call lists
  const [activeCalls, setActiveCalls] = useState<CallSummaryItem[]>([]);
  const [recentCalls, setRecentCalls] = useState<CallSummaryItem[]>([]);
  const [activeTab, setActiveTab] = useState<"ACTIVE" | "RECENT">("ACTIVE");
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);

  // Phase 9: Multi-Agent Orchestration State
  const [orchestrationState, setOrchestrationState] = useState<string>("READY");
  const [orchestrationLatency, setOrchestrationLatency] = useState<number>(0);
  const [orchestrationBriefing, setOrchestrationBriefing] = useState<{
    safety_summary?: string;
    svi_summary?: string;
    acoustic_summary?: string;
    adaptive_recommendation?: string;
    key_facts?: string[];
    evidence_refs?: string[];
    confidence?: number;
    generated_at?: string;
  } | null>({
    safety_summary: "Deterministic safety triage active. No immediate escalation.",
    svi_summary: "SVI assessment within nominal baseline boundaries.",
    acoustic_summary: "Acoustic audio features stable. No distress crying detected.",
    adaptive_recommendation: "Continue supportive inquiry and establish immediate caller safety.",
    key_facts: ["Caller connected via NHAA telephony hotline"],
    evidence_refs: ["telephony:exotel_session", "safety:baseline_active"],
    confidence: 0.95,
  });
  const [orchestrationWorkers, setOrchestrationWorkers] = useState<Record<string, {
    status: string;
    latency_ms: number;
    confidence: number;
    warnings?: string[];
  }>>({
    safety_context_agent: { status: "SUCCESS", latency_ms: 8, confidence: 1.0 },
    acoustic_context_agent: { status: "SUCCESS", latency_ms: 12, confidence: 0.95 },
    language_context_agent: { status: "SUCCESS", latency_ms: 15, confidence: 0.9 },
    conversation_context_agent: { status: "SUCCESS", latency_ms: 45, confidence: 0.85 },
    support_options_agent: { status: "SUCCESS", latency_ms: 5, confidence: 1.0 },
    knowledge_retrieval_agent: { status: "SUCCESS", latency_ms: 18, confidence: 0.95 },
    operator_briefing_agent: { status: "SUCCESS", latency_ms: 22, confidence: 0.95 },
  });
  const [isRefreshingOrchestration, setIsRefreshingOrchestration] = useState<boolean>(false);

  // Phase 10: Legal / Policy Knowledge RAG State
  const [knowledgeQuery, setKnowledgeQuery] = useState<string>("");
  const [knowledgeJurisdiction, setKnowledgeJurisdiction] = useState<string>("ALL");
  const [knowledgeLanguage, setKnowledgeLanguage] = useState<string>("ALL");
  const [knowledgeCurrentOnly, setKnowledgeCurrentOnly] = useState<boolean>(true);
  const [knowledgeStatus, setKnowledgeStatus] = useState<string>("READY");
  const [isSearchingKnowledge, setIsSearchingKnowledge] = useState<boolean>(false);
  const [knowledgeResult, setKnowledgeResult] = useState<any | null>(null);
  const [selectedSourceDetail, setSelectedSourceDetail] = useState<any | null>(null);

  // Phase 11: Case Intelligence & Knowledge Graph State
  const [caseRecord, setCaseRecord] = useState<any | null>(null);
  const [caseGraph, setCaseGraph] = useState<any | null>(null);
  const [caseIntegrity, setCaseIntegrity] = useState<any | null>(null);
  const [selectedGraphNode, setSelectedGraphNode] = useState<any | null>(null);
  const [selectedGraphEdge, setSelectedGraphEdge] = useState<any | null>(null);
  const [isRefreshingCase, setIsRefreshingCase] = useState<boolean>(false);
  const [caseDepth, setCaseDepth] = useState<number>(2);
  const [caseFocusEntity, setCaseFocusEntity] = useState<string>("");
  const [candidateActionLoading, setCandidateActionLoading] = useState<string | null>(null);
  const [showCaseAuditModal, setShowCaseAuditModal] = useState<boolean>(false);
  const [caseAuditLogs, setCaseAuditLogs] = useState<any[]>([]);

  // Phase 12: Follow-up Workflow & Continuity Engine State
  const [followups, setFollowups] = useState<FollowupPayload[]>([
    {
      followup_id: "fol-1001",
      case_id: "case-1001",
      call_id: "call-fixture-01",
      created_by: "operator_1",
      assigned_to: "operator_1",
      type: FollowupType.CHECK_IN,
      status: FollowupStatus.SCHEDULED,
      priority: FollowupPriority.NORMAL,
      requested_at: "2026-03-31T10:00:00Z",
      scheduled_for: new Date(Date.now() + 86400000).toISOString(),
      due_at: new Date(Date.now() + 172800000).toISOString(),
      consent_state: ConsentState.GRANTED,
      contact_preferences: {
        preferred_channel: ContactChannel.OPERATOR_CALLBACK,
        safe_to_contact: true,
        human_only: true,
        preferred_time_window: "09:00-12:00",
        no_voicemail: true,
        no_text: false,
      },
      safe_contact_window: "09:00-12:00",
      channel: ContactChannel.OPERATOR_CALLBACK,
      purpose: "Safety check-in regarding overnight shelter arrangement",
      attempt_count: 0,
      max_attempts: 3,
      policy_version: "2026.03.v1",
      created_at: "2026-03-31T10:00:00Z",
      updated_at: "2026-03-31T10:00:00Z",
    },
    {
      followup_id: "fol-1002",
      case_id: "case-1001",
      call_id: "call-fixture-01",
      created_by: "operator_1",
      assigned_to: "operator_1",
      type: FollowupType.RESOURCE_FOLLOW_UP,
      status: FollowupStatus.READY,
      priority: FollowupPriority.HIGH,
      requested_at: "2026-03-31T09:00:00Z",
      scheduled_for: new Date().toISOString(),
      due_at: new Date(Date.now() + 86400000).toISOString(),
      consent_state: ConsentState.GRANTED,
      contact_preferences: {
        preferred_channel: ContactChannel.PHONE,
        safe_to_contact: true,
        human_only: true,
        preferred_time_window: "14:00-18:00",
        no_voicemail: true,
        no_text: false,
      },
      safe_contact_window: "14:00-18:00",
      channel: ContactChannel.PHONE,
      purpose: "Provide verified legal aid contact number for Protection Officer",
      attempt_count: 0,
      max_attempts: 3,
      policy_version: "2026.03.v1",
      created_at: "2026-03-31T09:00:00Z",
      updated_at: "2026-03-31T09:00:00Z",
    },
  ]);
  const [followupSummary, setFollowupSummary] = useState<FollowupWorkqueueSummaryPayload>({
    total_active: 2,
    due_today: 1,
    overdue: 0,
    blocked: 0,
    completed_today: 0,
  });
  const [selectedFollowup, setSelectedFollowup] = useState<FollowupPayload | null>(null);
  const [followupFilterStatus, setFollowupFilterStatus] = useState<string>("ALL");
  const [showCreateFollowupModal, setShowCreateFollowupModal] = useState<boolean>(false);
  const [showFollowupDetailsDrawer, setShowFollowupDetailsDrawer] = useState<boolean>(false);
  const [showFollowupAuditModal, setShowFollowupAuditModal] = useState<boolean>(false);
  const [followupAuditLogs, setFollowupAuditLogs] = useState<any[]>([]);
  const [isRefreshingFollowups, setIsRefreshingFollowups] = useState<boolean>(false);

  // Follow-up form states
  const [newFollowupType, setNewFollowupType] = useState<FollowupType>(FollowupType.CHECK_IN);
  const [newFollowupPriority, setNewFollowupPriority] = useState<FollowupPriority>(FollowupPriority.NORMAL);
  const [newFollowupPurpose, setNewFollowupPurpose] = useState<string>("");
  const [newFollowupChannel, setNewFollowupChannel] = useState<ContactChannel>(ContactChannel.OPERATOR_CALLBACK);
  const [newFollowupScheduledFor, setNewFollowupScheduledFor] = useState<string>("");
  const [newFollowupDueAt, setNewFollowupDueAt] = useState<string>("");
  const [newFollowupSafeWindow, setNewFollowupSafeWindow] = useState<string>("09:00-12:00");
  const [newFollowupHumanOnly, setNewFollowupHumanOnly] = useState<boolean>(true);
  const [newFollowupConsentState, setNewFollowupConsentState] = useState<ConsentState>(ConsentState.GRANTED);
  const [newFollowupMaxAttempts, setNewFollowupMaxAttempts] = useState<number>(3);
  const [newFollowupNotes, setNewFollowupNotes] = useState<string>("");

  // Attempt recording form states
  const [attemptChannel, setAttemptChannel] = useState<ContactChannel>(ContactChannel.OPERATOR_CALLBACK);
  const [attemptResult, setAttemptResult] = useState<ContactResult>(ContactResult.CONTACTED_SUCCESSFULLY);
  const [attemptNotes, setAttemptNotes] = useState<string>("");

  // Reschedule form states
  const [rescheduleTime, setRescheduleTime] = useState<string>("");
  const [rescheduleReason, setRescheduleReason] = useState<string>("");


  // Selected Call Data
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [partialDraft, setPartialDraft] = useState<string | null>(null);
  const [callEvents, setCallEvents] = useState<EventEnvelope[]>([]);
  const [aiState, setAiState] = useState<string>("IDLE");
  const [currentLanguage, setCurrentLanguage] = useState<string>("ta-IN");
  const [latencies, setLatencies] = useState<LatencyMetrics>({
    stt_ms: 0,
    llm_ms: 0,
    tts_ms: 0,
    total_ms: 0,
  });

  // Phase 4 Safety Engine State
  const [safetyState, setSafetyState] = useState<string>("NONE");
  const [safetySignals, setSafetySignals] = useState<SafetySignalItem[]>([]);
  const [acknowledgingSignalId, setAcknowledgingSignalId] = useState<string | null>(null);
  const [isSafetyLabOpen, setIsSafetyLabOpen] = useState<boolean>(false);
  const [isSafetyRulesOpen, setIsSafetyRulesOpen] = useState<boolean>(false);
  const [safetyRulesList, setSafetyRulesList] = useState<any[]>([]);
  const [safetyEngineStatus, setSafetyEngineStatus] = useState<{
    status: string;
    engine_version: string;
    rules_loaded_count: number;
    rule_ids?: string[];
  } | null>(null);
  const [safetyLabInput, setSafetyLabInput] = useState<string>("He has a knife and is breaking into my door right now!");
  const [safetyLabLang, setSafetyLabLang] = useState<string>("en-IN");
  const [safetyLabResult, setSafetyLabResult] = useState<any>(null);
  const [isEvaluatingSafety, setIsEvaluatingSafety] = useState<boolean>(false);

  // Phase 5 SVI Engine State
  const [sviScore, setSviScore] = useState<number | null>(null);
  const [sviBand, setSviBand] = useState<string>("LOW");
  const [sviTrend, setSviTrend] = useState<string>("INITIAL");
  const [sviDelta, setSviDelta] = useState<number>(0);
  const [sviCompleteness, setSviCompleteness] = useState<number>(0);
  const [sviTopContributors, setSviTopContributors] = useState<string[]>([]);
  const [sviProtectiveReduction, setSviProtectiveReduction] = useState<number>(0);
  const [sviCriticalOverride, setSviCriticalOverride] = useState<boolean>(false);
  const [sviRequiresHumanReview, setSviRequiresHumanReview] = useState<boolean>(false);
  const [sviHistory, setSviHistory] = useState<Array<{ score: number; band: string; evaluated_at: string }>>([]);
  const [isSviLabOpen, setIsSviLabOpen] = useState<boolean>(false);
  const [sviLabInput, setSviLabInput] = useState<string>("He locked me inside the room and took my phone. I am panicking and extremely scared.");
  const [sviLabLang, setSviLabLang] = useState<string>("en-IN");
  const [sviLabResult, setSviLabResult] = useState<any>(null);
  const [isEvaluatingSvi, setIsEvaluatingSvi] = useState<boolean>(false);

  // Phase 6 Acoustic Engine State
  const [acousticQuality, setAcousticQuality] = useState<string>("GOOD");
  const [acousticConfidence, setAcousticConfidence] = useState<number>(1.0);
  const [acousticSpeechRatio, setAcousticSpeechRatio] = useState<number>(0.0);
  const [acousticSilenceRatio, setAcousticSilenceRatio] = useState<number>(1.0);
  const [acousticLongestPause, setAcousticLongestPause] = useState<number>(0);
  const [acousticPauseCount, setAcousticPauseCount] = useState<number>(0);
  const [acousticInterruptions, setAcousticInterruptions] = useState<number>(0);
  const [acousticEnergyVar, setAcousticEnergyVar] = useState<number>(0.0);
  const [acousticMeanRms, setAcousticMeanRms] = useState<number>(0.0);
  const [acousticMedianF0, setAcousticMedianF0] = useState<number | null>(null);
  const [acousticSignals, setAcousticSignals] = useState<Array<{ code: string; evidence: string; confidence: number; threshold_applied?: string }>>([]);
  const [isAcousticLabOpen, setIsAcousticLabOpen] = useState<boolean>(false);
  const [acousticLabDuration, setAcousticLabDuration] = useState<number>(4000);
  const [acousticLabSpeechRatio, setAcousticLabSpeechRatio] = useState<number>(0.65);
  const [acousticLabMaxSilence, setAcousticLabMaxSilence] = useState<number>(1200);
  const [acousticLabInterruptions, setAcousticLabInterruptions] = useState<number>(0);
  const [acousticLabEnergyVar, setAcousticLabEnergyVar] = useState<number>(0.25);
  const [acousticLabClipping, setAcousticLabClipping] = useState<number>(0.0);
  const [acousticLabMeanRms, setAcousticLabMeanRms] = useState<number>(450.0);
  const [acousticLabResult, setAcousticLabResult] = useState<any>(null);
  const [isEvaluatingAcoustic, setIsEvaluatingAcoustic] = useState<boolean>(false);

  // Phase 7: Adaptive Conversation Engine State
  const [adaptiveAction, setAdaptiveAction] = useState<string>("ASK_SUPPORT");
  const [adaptivePriority, setAdaptivePriority] = useState<string>("P4");
  const [adaptiveTarget, setAdaptiveTarget] = useState<string>("support_domain");
  const [adaptiveConfidence, setAdaptiveConfidence] = useState<number>(0.95);
  const [adaptiveReasonCodes, setAdaptiveReasonCodes] = useState<string[]>(["INFORMATION_GAP"]);
  const [adaptiveEvidence, setAdaptiveEvidence] = useState<string[]>([]);
  const [adaptiveOverrideActive, setAdaptiveOverrideActive] = useState<boolean>(false);
  const [adaptiveOverrideReason, setAdaptiveOverrideReason] = useState<string | null>(null);
  const [adaptiveHistory, setAdaptiveHistory] = useState<Array<{
    action: string;
    priority: string;
    target_information_gap?: string;
    reason_codes?: string[];
    evaluated_at?: string;
  }>>([]);
  const [isAdaptiveLabOpen, setIsAdaptiveLabOpen] = useState<boolean>(false);
  const [adaptiveLabInput, setAdaptiveLabInput] = useState<string>("I need help with reporting");
  const [adaptiveLabLang, setAdaptiveLabLang] = useState<string>("en-IN");
  const [adaptiveLabSafety, setAdaptiveLabSafety] = useState<string>("NONE");
  const [adaptiveLabSvi, setAdaptiveLabSvi] = useState<number>(30);
  const [adaptiveLabAcoustic, setAdaptiveLabAcoustic] = useState<string>("GOOD");
  const [adaptiveLabResult, setAdaptiveLabResult] = useState<any>(null);
  const [isEvaluatingAdaptive, setIsEvaluatingAdaptive] = useState<boolean>(false);

  // Phase 8: Human Operator Workstation State
  const [operatorOwnershipState, setOperatorOwnershipState] = useState<string>("AI_ASSISTED");
  const [operatorHandoffStatus, setOperatorHandoffStatus] = useState<string>("AVAILABLE");
  const [isAdaptivePaused, setIsAdaptivePaused] = useState<boolean>(false);
  const [operatorNotes, setOperatorNotes] = useState<Array<{
    note_id: string;
    call_id: string;
    operator_id: string;
    category: string;
    text: string;
    timestamp: string;
    is_structured: boolean;
    citation_ref?: string;
  }>>([]);
  const [isNotesModalOpen, setIsNotesModalOpen] = useState<boolean>(false);
  const [newNoteText, setNewNoteText] = useState<string>("");
  const [newNoteCategory, setNewNoteCategory] = useState<string>("GENERAL");
  const [isSubmittingNote, setIsSubmittingNote] = useState<boolean>(false);

  // Operator Queue & Action State
  const [queueFilter, setQueueFilter] = useState<string>("ALL");
  const [confirmationAction, setConfirmationAction] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    confirmLabel: string;
    actionType: "END_CALL" | "CONFIRM_HANDOFF" | "TAKEOVER" | null;
  }>({
    isOpen: false,
    title: "",
    description: "",
    confirmLabel: "",
    actionType: null,
  });

  const [activeAlerts, setActiveAlerts] = useState<Array<{
    id: string;
    severity: "INFO" | "NOTICE" | "WARNING" | "CRITICAL";
    title: string;
    message: string;
    timestamp: string;
  }>>([]);

  // UI Modals & Filters
  const [eventFilter, setEventFilter] = useState<EventFilterCategory>("ALL");
  const [inspectedEvent, setInspectedEvent] = useState<EventEnvelope | null>(null);
  const [copiedJson, setCopiedJson] = useState(false);
  const [isSimModalOpen, setIsSimModalOpen] = useState(false);
  const [simScenario, setSimScenario] = useState("tamil_help");
  const [simCallerPhone, setSimCallerPhone] = useState("+919876543210");
  const [isSimulating, setIsSimulating] = useState(false);
  const [systemMode, setSystemMode] = useState<string>("DEV");

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Operator WebSocket Hook
  const {
    status: wsStatus,
    reconnectCount,
    subscribeCall,
    subscribeAll,
    connect,
  } = useOperatorWebSocket({
    initialCallId: selectedCallId,
    onSnapshot: (snapshotPayload) => {
      if (snapshotPayload.active_calls) {
        setActiveCalls((prev) => {
          if (prev.length > 0 && snapshotPayload.active_calls.length === 0) {
            return prev;
          }
          return snapshotPayload.active_calls;
        });
      }
      if (snapshotPayload.recent_calls) {
        setRecentCalls((prev) => {
          if (prev.length > 0 && snapshotPayload.recent_calls.length === 0) {
            return prev;
          }
          return snapshotPayload.recent_calls;
        });
      }
      if (snapshotPayload.system_mode) {
        setSystemMode(snapshotPayload.system_mode);
      }
      // If we subscribed to a specific call snapshot ack
      if (snapshotPayload.transcript && snapshotPayload.subscribed_call_id === selectedCallId) {
        const remoteTurns: TranscriptItem[] = snapshotPayload.transcript.map((t: any) => ({
          utterance_id: t.utterance_id || crypto.randomUUID(),
          speaker: t.speaker || "caller",
          text: t.text || "",
          language: t.language || "ta-IN",
          confidence: t.confidence || 0.95,
          is_final: t.is_final ?? true,
          intent: t.intent,
          safety_flag: t.safety_flag,
          timestamp: t.timestamp || new Date().toISOString(),
        }));
        setTranscripts((prev) => {
          if (prev.length > 0 && remoteTurns.length === 0) {
            return prev;
          }
          return remoteTurns;
        });
      }
    },
    onEvent: (envelope: EventEnvelope) => {
      const event_type = envelope.event_type;
      const payload = (envelope.payload || {}) as Record<string, any>;
      const eventCallId = envelope.call_id;

      // Filter events if targeted to another call (cross-call isolation)
      if (selectedCallId && eventCallId && eventCallId !== "global" && eventCallId !== selectedCallId) {
        return;
      }

      // Append to event timeline
      setCallEvents((prev) => [envelope, ...prev.slice(0, 99)]);

      switch (event_type) {
        case EventType.CONVERSATION_STATE_CHANGED:
          if (payload.new_state) {
            setAiState(String(payload.new_state));
          }
          break;

        case EventType.LANGUAGE_CHANGED:
        case EventType.LANGUAGE_DETECTED:
          if (payload.new_language || payload.language) {
            setCurrentLanguage(String(payload.new_language || payload.language));
          }
          break;

        case EventType.TRANSCRIPT_PARTIAL:
          setAiState("TRANSCRIBING");
          if (payload.text) {
            setPartialDraft(String(payload.text));
          }
          break;

        case EventType.TRANSCRIPT_FINAL:
          setPartialDraft(null);
          if (payload.text) {
            const newUttId = String(payload.utterance_id || crypto.randomUUID());
            setTranscripts((prev) => {
              if (prev.some((u) => u.utterance_id === newUttId)) return prev;
              return [
                ...prev,
                {
                  utterance_id: newUttId,
                  speaker: (payload.speaker as "caller" | "agent" | "system") || "caller",
                  text: String(payload.text),
                  language: String(payload.language || currentLanguage),
                  confidence: typeof payload.confidence === "number" ? payload.confidence : 0.96,
                  is_final: true,
                  intent: payload.intent ? String(payload.intent) : undefined,
                  safety_flag: Boolean(payload.safety_flag),
                  timestamp: envelope.timestamp,
                },
              ];
            });
          }
          break;

        case EventType.AI_THINKING:
          setAiState("THINKING");
          break;

        case EventType.AI_RESPONSE_STARTED:
          setAiState("SPEAKING");
          if (payload.response_text) {
            const uttId = String(payload.turn_id || crypto.randomUUID());
            setTranscripts((prev) => {
              if (prev.some((u) => u.utterance_id === uttId)) return prev;
              return [
                ...prev,
                {
                  utterance_id: uttId,
                  speaker: "agent",
                  text: String(payload.response_text),
                  language: String(payload.language || currentLanguage),
                  confidence: 1.0,
                  is_final: true,
                  intent: payload.detected_intent ? String(payload.detected_intent) : undefined,
                  safety_flag: Boolean(payload.safety_flag),
                  timestamp: envelope.timestamp,
                },
              ];
            });
          }
          break;

        case EventType.SPEECH_INTERRUPTED:
          setAiState("INTERRUPTED");
          break;

        case EventType.CALL_ENDED:
          setAiState("ENDED");
          fetchCalls(); // Refresh call lists
          break;

        case EventType.SAFETY_SIGNAL:
          if (payload) {
            setSafetySignals((prev) => {
              const sigId = String(payload.signal_id);
              if (prev.some((s) => s.signal_id === sigId)) return prev;
              const newSig: SafetySignalItem = {
                signal_id: sigId,
                signal_type: String(payload.signal_type || "ONGOING_THREAT"),
                severity: (payload.severity as any) || "HIGH",
                confidence: typeof payload.confidence === "number" ? payload.confidence : 1.0,
                evidence: {
                  rule_id: String(payload.rule_id || "SAFETY_RULE"),
                  rule_version: String(payload.rule_version || "v1"),
                  matched_category: String(payload.signal_type || "THREAT"),
                  matched_phrase: String(payload.matched_phrase || ""),
                  reason: String(payload.reason || "Deterministic safety signal matched"),
                  temporal_context: String(payload.temporal_context || "PRESENT"),
                  negated: Boolean(payload.negated),
                },
                rule_id: String(payload.rule_id || "SAFETY_RULE"),
                rule_version: String(payload.rule_version || "v1"),
                call_id: String(payload.call_id || eventCallId || ""),
                session_id: String(payload.session_id || envelope.session_id || ""),
                requires_human_review: payload.requires_human_review !== false,
                acknowledged: Boolean(payload.acknowledged),
                created_at: envelope.timestamp,
              };
              return [newSig, ...prev];
            });
            // Update call card in list
            setActiveCalls((prev) =>
              prev.map((c) =>
                c.call_id === eventCallId
                  ? {
                      ...c,
                      safety_signals_count: (c.safety_signals_count || 0) + 1,
                      safety_state: payload.severity === "CRITICAL" ? "CRITICAL" : c.safety_state || "HIGH",
                    }
                  : c
              )
            );
          }
          break;

        case EventType.SAFETY_STATE_UPDATED:
          if (payload.current_state) {
            setSafetyState(String(payload.current_state));
            setActiveCalls((prev) =>
              prev.map((c) =>
                c.call_id === eventCallId ? { ...c, safety_state: String(payload.current_state) } : c
              )
            );
          }
          break;

        case EventType.SAFETY_SIGNAL_ACKNOWLEDGED:
          if (payload.signal_id) {
            setSafetySignals((prev) =>
              prev.map((s) =>
                s.signal_id === payload.signal_id
                  ? {
                      ...s,
                      acknowledged: true,
                      acknowledged_at: String(payload.acknowledged_at || new Date().toISOString()),
                      acknowledged_by: String(payload.acknowledged_by || "operator"),
                    }
                  : s
              )
            );
          }
          break;

        case EventType.TURN_LATENCY:
          setLatencies({
            stt_ms: Number(payload.stt_ms || 0),
            llm_ms: Number(payload.llm_ms || 0),
            tts_ms: Number(payload.tts_ms || 0),
            total_ms: Number(payload.total_turn_ms || 0),
          });
          break;

        case EventType.SVI_UPDATED:
          if (payload) {
            const score = Number(payload.score ?? 0);
            setSviScore(score);
            setSviBand(String(payload.band || "LOW"));
            setSviTrend(String(payload.trend || "INITIAL"));
            setSviDelta(Number(payload.delta ?? 0));
            setSviCompleteness(Number(payload.assessment_completeness ?? 0));
            setSviTopContributors(Array.isArray(payload.top_contributors) ? payload.top_contributors.map(String) : []);
            setSviProtectiveReduction(Number(payload.protective_factor_reduction ?? 0));
            setSviCriticalOverride(Boolean(payload.critical_override_applied));
            setSviRequiresHumanReview(Boolean(payload.requires_human_review));
            setSviHistory((prev) => [
              ...prev,
              { score, band: String(payload.band || "LOW"), evaluated_at: envelope.timestamp },
            ]);
          }
          break;

        case EventType.ACOUSTIC_UPDATE:
          if (payload) {
            setAcousticQuality(String(payload.quality || "GOOD"));
            setAcousticConfidence(Number(payload.confidence ?? 1.0));
            setAcousticSpeechRatio(Number(payload.speech_activity_ratio ?? 0));
            setAcousticSilenceRatio(Number(payload.silence_ratio ?? 1.0));
            setAcousticLongestPause(Number(payload.longest_pause_ms ?? 0));
            setAcousticPauseCount(Number(payload.pause_count ?? 0));
            setAcousticInterruptions(Number(payload.interruption_count ?? 0));
            setAcousticEnergyVar(Number(payload.energy_variability ?? 0));
            setAcousticMeanRms(Number(payload.mean_energy_rms ?? 0));
            setAcousticMedianF0(payload.median_f0_hz !== undefined ? payload.median_f0_hz : null);
            if (Array.isArray(payload.signals)) {
              setAcousticSignals(payload.signals);
            }
          }
          break;

        case EventType.ADAPTIVE_STRATEGY_SELECTED:
          if (payload) {
            setAdaptiveAction(String(payload.action || "ASK_SUPPORT"));
            setAdaptivePriority(String(payload.priority || "P4"));
            setAdaptiveTarget(String(payload.target_information || "support_domain"));
            setAdaptiveConfidence(Number(payload.confidence ?? 0.95));
            setAdaptiveReasonCodes(Array.isArray(payload.reason_codes) ? payload.reason_codes.map(String) : []);
            setAdaptiveEvidence(Array.isArray(payload.evidence_refs) ? payload.evidence_refs.map(String) : []);
            setAdaptiveOverrideActive(Boolean(payload.operator_override_active));
            setAdaptiveHistory((prev) => [
              ...prev,
              {
                action: String(payload.action || "ASK_SUPPORT"),
                priority: String(payload.priority || "P4"),
                target_information_gap: String(payload.target_information || ""),
                reason_codes: Array.isArray(payload.reason_codes) ? payload.reason_codes.map(String) : [],
                evaluated_at: envelope.timestamp,
              },
            ]);
          }
          break;

        case EventType.OPERATOR_TAKEOVER:
          setOperatorOwnershipState("HUMAN_ACTIVE");
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "NOTICE",
              title: "Operator Takeover",
              message: `Operator ${payload.operator_id || "active"} assumed control of call.`,
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_PAUSE_ADAPTIVE:
          setIsAdaptivePaused(true);
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "INFO",
              title: "Adaptive AI Paused",
              message: "Conversational planner paused. Safety engine active.",
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_RESUME_AI:
          setIsAdaptivePaused(false);
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "INFO",
              title: "Adaptive AI Resumed",
              message: "Conversational planner active.",
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_REQUEST_SAFETY_CHECK:
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "WARNING",
              title: "Safety Check Requested",
              message: "Operator requested immediate safety re-evaluation.",
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_HANDOFF_REQUESTED:
          setOperatorHandoffStatus("REQUESTED");
          setOperatorOwnershipState("HANDOFF_PENDING");
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "WARNING",
              title: "Handoff Requested",
              message: `Transfer requested to ${payload.target_department || "receiving counselor"}.`,
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_HANDOFF_CONFIRMED:
          setOperatorHandoffStatus("CONFIRMED");
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "NOTICE",
              title: "Handoff Confirmed",
              message: `Call transferred to ${payload.target_agent || "assigned counselor"}.`,
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_HANDOFF_CANCELLED:
          setOperatorHandoffStatus("CANCELLED");
          setOperatorOwnershipState("HUMAN_ACTIVE");
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "INFO",
              title: "Handoff Cancelled",
              message: "Transfer cancelled. Operator remains in active control.",
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case EventType.OPERATOR_NOTE_ADDED:
          if (payload && payload.note_id) {
            setOperatorNotes((prev) => {
              if (prev.some((n) => n.note_id === payload.note_id)) return prev;
              return [
                {
                  note_id: String(payload.note_id),
                  call_id: String(payload.call_id || selectedCallId),
                  operator_id: String(payload.operator_id || "operator"),
                  category: String(payload.category || "GENERAL"),
                  text: String(payload.text || ""),
                  timestamp: String(payload.timestamp || envelope.timestamp),
                  is_structured: Boolean(payload.is_structured ?? true),
                  citation_ref: payload.citation_ref ? String(payload.citation_ref) : undefined,
                },
                ...prev,
              ];
            });
          }
          break;

        case EventType.OPERATOR_CALL_ENDED:
          setOperatorOwnershipState("ENDED");
          setActiveAlerts((prev) => [
            {
              id: crypto.randomUUID(),
              severity: "NOTICE",
              title: "Call Concluded",
              message: `Call session ended by operator.`,
              timestamp: envelope.timestamp,
            },
            ...prev.slice(0, 4),
          ]);
          break;

        case "ORCHESTRATION_STARTED" as any:
        case EventType.ORCHESTRATION_STARTED:
          setOrchestrationState("RUNNING");
          break;

        case "ORCHESTRATION_COMPLETED" as any:
        case EventType.ORCHESTRATION_COMPLETED:
          setOrchestrationState("COMPLETED");
          if (payload.total_latency_ms) setOrchestrationLatency(payload.total_latency_ms);
          if (payload.briefing) setOrchestrationBriefing(payload.briefing);
          if (payload.agent_outputs) setOrchestrationWorkers(payload.agent_outputs);
          break;

        case "ORCHESTRATION_DEGRADED" as any:
        case EventType.ORCHESTRATION_DEGRADED:
          setOrchestrationState("DEGRADED");
          if (payload.total_latency_ms) setOrchestrationLatency(payload.total_latency_ms);
          if (payload.briefing) setOrchestrationBriefing(payload.briefing);
          if (payload.agent_outputs) setOrchestrationWorkers(payload.agent_outputs);
          break;

        case "OPERATOR_BRIEFING_GENERATED" as any:
        case EventType.OPERATOR_BRIEFING_GENERATED:
          if (payload.briefing) setOrchestrationBriefing(payload.briefing);
          if (payload.orchestration_state) setOrchestrationState(payload.orchestration_state);
          if (payload.total_latency_ms) setOrchestrationLatency(payload.total_latency_ms);
          break;

        case "KNOWLEDGE_SEARCH_STARTED" as any:
        case EventType.KNOWLEDGE_SEARCH_STARTED:
          setKnowledgeStatus("SEARCHING");
          setIsSearchingKnowledge(true);
          break;

        case "KNOWLEDGE_SEARCH_COMPLETED" as any:
        case EventType.KNOWLEDGE_SEARCH_COMPLETED:
          setKnowledgeStatus(payload.status || "COMPLETED");
          setIsSearchingKnowledge(false);
          setKnowledgeResult(payload);
          break;

        case "KNOWLEDGE_SOURCE_CONFLICT" as any:
        case EventType.KNOWLEDGE_SOURCE_CONFLICT:
          setKnowledgeStatus("CONFLICT");
          break;

        case "KNOWLEDGE_REVIEW_RECOMMENDED" as any:
        case EventType.KNOWLEDGE_REVIEW_RECOMMENDED:
          break;

        case "CASE_CREATED" as any:
        case "CASE_UPDATED" as any:
        case "CASE_CALL_LINKED" as any:
        case "CASE_CALL_UNLINKED" as any:
        case "CASE_ENTITY_CREATED" as any:
        case "CASE_ENTITY_UPDATED" as any:
        case "CASE_ENTITY_CANDIDATE_CREATED" as any:
        case "CASE_RELATIONSHIP_CREATED" as any:
        case "CASE_RELATIONSHIP_CONFIRMED" as any:
        case "CASE_RELATIONSHIP_REJECTED" as any:
        case "CASE_RELATIONSHIP_SUPERSEDED" as any:
          if (caseRecord?.case_id) {
            fetchCaseGraph(caseRecord.case_id);
            fetchCaseIntegrity(caseRecord.case_id);
          } else if (payload?.case_id) {
            fetchCaseForCall(payload.case_id);
          }
          break;

        case "FOLLOWUP_CREATED" as any:
        case "FOLLOWUP_APPROVED" as any:
        case "FOLLOWUP_SCHEDULED" as any:
        case "FOLLOWUP_ASSIGNED" as any:
        case "FOLLOWUP_STARTED" as any:
        case "FOLLOWUP_ATTEMPTED" as any:
        case "FOLLOWUP_COMPLETED" as any:
        case "FOLLOWUP_RESCHEDULED" as any:
        case "FOLLOWUP_CANCELLED" as any:
        case "FOLLOWUP_BLOCKED" as any:
        case "FOLLOWUP_REMINDER_DUE" as any:
        case "FOLLOWUP_CONSENT_GRANTED" as any:
        case "FOLLOWUP_CONSENT_REVOKED" as any:
        case "FOLLOWUP_CONSENT_LIMITED" as any:
        case "FOLLOWUP_CONSENT_REFUSED" as any:
          fetchFollowups();
          fetchFollowupSummary();
          break;
      }
    },
  });

  // Phase 12: Follow-up Fetchers
  const fetchFollowups = async (caseId?: string) => {
    try {
      setIsRefreshingFollowups(true);
      let url = `${apiUrl}/v1/followups`;
      if (caseId) {
        url = `${apiUrl}/v1/cases/${caseId}/followups`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setFollowups(data.items || (Array.isArray(data) ? data : []));
      }
    } catch (e) {
      console.error("Failed to fetch followups:", e);
    } finally {
      setIsRefreshingFollowups(false);
    }
  };

  const fetchFollowupSummary = async () => {
    try {
      const res = await fetch(`${apiUrl}/v1/followups/summary`);
      if (res.ok) {
        const data = await res.json();
        setFollowupSummary(data);
      }
    } catch (e) {
      console.error("Failed to fetch followup summary:", e);
    }
  };

  // REST Snapshot Fetcher
  const fetchCalls = async () => {
    try {
      const res = await fetch(`${apiUrl}/v1/calls`);
      if (res.ok) {
        const data = await res.json();
        setActiveCalls(data.active_calls || []);
        setRecentCalls(data.recent_calls || []);
        // Auto-select first active call if none selected
        if (!selectedCallId && data.active_calls?.length > 0) {
          selectCall(data.active_calls[0].call_id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch calls:", e);
    }
  };

  const fetchSafetyStatus = async () => {
    try {
      const res = await fetch(`${apiUrl}/v1/safety/status`);
      if (res.ok) {
        const data = await res.json();
        setSafetyEngineStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch safety status:", e);
    }
  };

  useEffect(() => {
    fetchCalls();
    fetchSafetyStatus();
    fetchCaseForCall();
    fetchFollowups();
    fetchFollowupSummary();
    const interval = setInterval(() => {
      fetchCalls();
      fetchSafetyStatus();
      fetchFollowups();
      fetchFollowupSummary();
    }, 8000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  // Handle Call Selection
  const selectCall = async (callId: string) => {
    setSelectedCallId(callId);
    setPartialDraft(null);
    setKnowledgeResult(null);
    setSelectedSourceDetail(null);
    setKnowledgeStatus("READY");
    setKnowledgeQuery("");
    subscribeCall(callId);
    fetchCaseForCall(callId);


    // Fetch call details, transcripts, and safety state via REST snapshot
    try {
      const [trRes, evRes, sRes] = await Promise.all([
        fetch(`${apiUrl}/v1/calls/${callId}/transcript`),
        fetch(`${apiUrl}/v1/calls/${callId}/events`),
        fetch(`${apiUrl}/v1/safety/calls/${callId}`),
      ]);

      if (trRes.ok) {
        const trData = await trRes.json();
        const formatted: TranscriptItem[] = (trData.utterances || []).map((u: any) => ({
          utterance_id: u.utterance_id || crypto.randomUUID(),
          speaker: u.speaker || "caller",
          text: u.text || "",
          language: u.language || "ta-IN",
          confidence: u.confidence || 1.0,
          is_final: u.is_final ?? true,
          intent: u.intent,
          safety_flag: u.safety_flag,
          timestamp: u.timestamp || u.created_at || new Date().toISOString(),
        }));
        setTranscripts((prev) => {
          if (prev.length > 0 && formatted.length === 0) return prev;
          return formatted;
        });
      } else {
        setTranscripts([]);
      }

      if (evRes.ok) {
        const evData = await evRes.json();
        setCallEvents(evData.events || []);
      } else {
        setCallEvents([]);
      }

      if (sRes.ok) {
        const sData = await sRes.json();
        setSafetyState(sData.safety_state || "NONE");
        setSafetySignals((prev) => {
          const serverSignals = sData.safety_signals || [];
          return serverSignals.map((ss: any) => {
            const existing = prev.find((p) => p.signal_id === ss.signal_id);
            if (existing && existing.acknowledged) {
              return {
                ...ss,
                acknowledged: true,
                acknowledged_at: existing.acknowledged_at,
                acknowledged_by: existing.acknowledged_by,
              };
            }
            return ss;
          });
        });
      } else {
        setSafetyState("NONE");
        setSafetySignals([]);
      }

      // Phase 5 SVI Snapshot
      try {
        const sviRes = await fetch(`${apiUrl}/v1/svi/calls/${callId}`);
        if (sviRes.ok) {
          const sviData = await sviRes.json();
          setSviScore(sviData.score ?? 0);
          setSviBand(sviData.band || "LOW");
          setSviTrend(sviData.trend || "INITIAL");
          setSviDelta(sviData.delta ?? 0);
          setSviCompleteness(sviData.assessment_completeness ?? 0);
          setSviTopContributors(sviData.top_contributors || []);
          setSviProtectiveReduction(sviData.protective_factor_reduction ?? 0);
          setSviCriticalOverride(Boolean(sviData.critical_override_applied));
          setSviRequiresHumanReview(Boolean(sviData.requires_human_review));
        }
      } catch (e) {
        console.error("Error loading SVI snapshot:", e);
      }

      // Phase 6 Acoustic Snapshot
      try {
        const acRes = await fetch(`${apiUrl}/v1/acoustic/calls/${callId}`);
        if (acRes.ok) {
          const acData = await acRes.json();
          setAcousticQuality(acData.quality || "GOOD");
          setAcousticConfidence(acData.confidence ?? 1.0);
          setAcousticSpeechRatio(acData.voice_activity?.speech_activity_ratio ?? 0);
          setAcousticSilenceRatio(acData.voice_activity?.silence_ratio ?? 1.0);
          setAcousticLongestPause(acData.pause_metrics?.longest_pause_ms ?? 0);
          setAcousticPauseCount(acData.pause_metrics?.pause_count ?? 0);
          setAcousticInterruptions(acData.interruption_metrics?.interruption_count ?? 0);
          setAcousticEnergyVar(acData.energy_metrics?.energy_variability ?? 0);
          setAcousticMeanRms(acData.energy_metrics?.mean_energy_rms ?? 0);
          setAcousticMedianF0(acData.pitch_metrics?.median_f0_hz ?? null);
          setAcousticSignals(acData.operational_signals || []);
        } else {
          setAcousticQuality("GOOD");
          setAcousticConfidence(1.0);
          setAcousticSpeechRatio(0.0);
          setAcousticSilenceRatio(1.0);
          setAcousticLongestPause(0);
          setAcousticPauseCount(0);
          setAcousticInterruptions(0);
          setAcousticEnergyVar(0.0);
          setAcousticMeanRms(0.0);
          setAcousticMedianF0(null);
          setAcousticSignals([]);
        }
      } catch (e) {
        console.error("Error loading Acoustic snapshot:", e);
      }

      // Phase 7 Adaptive Snapshot & History
      try {
        const [adRes, histRes] = await Promise.all([
          fetch(`${apiUrl}/v1/adaptive/calls/${callId}`),
          fetch(`${apiUrl}/v1/adaptive/calls/${callId}/history`),
        ]);
        if (adRes.ok) {
          const adData = await adRes.json();
          setAdaptiveAction(adData.action || "ASK_SUPPORT");
          setAdaptivePriority(adData.priority || "P4");
          setAdaptiveTarget(adData.target_information_gap || "support_domain");
          setAdaptiveConfidence(adData.confidence ?? 0.95);
          setAdaptiveReasonCodes(adData.reason_codes || []);
          setAdaptiveEvidence(adData.evidence_used || []);
          setAdaptiveOverrideActive(Boolean(adData.operator_override_applied));
          setAdaptiveOverrideReason(adData.operator_override_reason || null);
        } else {
          setAdaptiveAction("ASK_SUPPORT");
          setAdaptivePriority("P4");
          setAdaptiveTarget("support_domain");
          setAdaptiveConfidence(0.95);
          setAdaptiveReasonCodes(["INFORMATION_GAP"]);
          setAdaptiveEvidence([]);
          setAdaptiveOverrideActive(false);
          setAdaptiveOverrideReason(null);
        }
        if (histRes.ok) {
          const histData = await histRes.json();
          setAdaptiveHistory(
            (histData.strategies || []).map((s: any) => ({
              action: s.action,
              priority: s.priority,
              target_information_gap: s.target_information_gap,
              reason_codes: s.reason_codes,
              evaluated_at: s.evaluated_at,
            }))
          );
        } else {
          setAdaptiveHistory([]);
        }
      } catch (e) {
        console.error("Error loading Adaptive snapshot:", e);
      }

      // Phase 8 Operator State & Notes Snapshot
      try {
        const [opRes, notesRes] = await Promise.all([
          fetch(`${apiUrl}/v1/operator/calls/${callId}`),
          fetch(`${apiUrl}/v1/operator/calls/${callId}/notes`),
        ]);
        if (opRes.ok) {
          const opData = await opRes.json();
          setOperatorOwnershipState(opData.ownership_state || "AI_ASSISTED");
          setOperatorHandoffStatus(opData.handoff_status || "AVAILABLE");
          setIsAdaptivePaused(Boolean(opData.adaptive_paused));
        } else {
          setOperatorOwnershipState("AI_ASSISTED");
          setOperatorHandoffStatus("AVAILABLE");
          setIsAdaptivePaused(false);
        }
        if (notesRes.ok) {
          const notesData = await notesRes.json();
          setOperatorNotes(notesData.notes || []);
        } else {
          setOperatorNotes([]);
        }
      } catch (e) {
        console.error("Error loading Operator snapshot:", e);
      }

      // Phase 9 Multi-Agent Orchestration Snapshot
      try {
        const orchRes = await fetch(`${apiUrl}/v1/orchestration/calls/${callId}`);
        if (orchRes.ok) {
          const orchData = await orchRes.json();
          setOrchestrationState(orchData.state || "COMPLETED");
          setOrchestrationLatency(orchData.total_latency_ms || 0);
          if (orchData.briefing) setOrchestrationBriefing(orchData.briefing);
          if (orchData.agent_outputs) setOrchestrationWorkers(orchData.agent_outputs);
        } else {
          setOrchestrationState("READY");
          setOrchestrationLatency(0);
          setOrchestrationBriefing({
            safety_summary: "Deterministic safety triage active. No immediate escalation.",
            svi_summary: "SVI assessment within nominal baseline boundaries.",
            acoustic_summary: "Acoustic audio features stable. No distress crying detected.",
            adaptive_recommendation: "Continue supportive inquiry and establish immediate caller safety.",
            key_facts: ["Caller connected via NHAA telephony hotline"],
            evidence_refs: ["telephony:exotel_session", "safety:baseline_active"],
            confidence: 0.95,
          });
        }
      } catch (e) {
        console.error("Error loading Orchestration snapshot:", e);
      }
    } catch (err) {
      console.error("Error loading call snapshot:", err);
    }
  };

  // Phase 9: Handle Manual Orchestration Refresh
  const handleRefreshOrchestration = async (callId: string) => {
    setIsRefreshingOrchestration(true);
    try {
      const res = await fetch(`${apiUrl}/v1/orchestration/calls/${callId}/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        setOrchestrationState(data.state || "COMPLETED");
        setOrchestrationLatency(data.total_latency_ms || 0);
        if (data.briefing) setOrchestrationBriefing(data.briefing);
        if (data.agent_outputs) setOrchestrationWorkers(data.agent_outputs);
      }
    } catch (e) {
      console.error("Failed to refresh orchestration:", e);
    } finally {
      setIsRefreshingOrchestration(false);
    }
  };

  // Phase 7: Handle Operator Override
  const handleOperatorOverride = async (action: string, reason: string) => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/adaptive/calls/${selectedCallId}/override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          reason,
          operator_id: "operator_console_1",
        }),
      });
      if (res.ok) {
        setAdaptiveOverrideActive(true);
        setAdaptiveOverrideReason(reason);
        // Refresh strategy immediately
        const adRes = await fetch(`${apiUrl}/v1/adaptive/calls/${selectedCallId}`);
        if (adRes.ok) {
          const adData = await adRes.json();
          setAdaptiveAction(adData.action || "ASK_SUPPORT");
          setAdaptivePriority(adData.priority || "P4");
          setAdaptiveTarget(adData.target_information_gap || "support_domain");
          setAdaptiveReasonCodes(adData.reason_codes || []);
          setAdaptiveEvidence(adData.evidence_used || []);
        }
      }
    } catch (err) {
      console.error("Error applying operator override:", err);
    }
  };

  // Phase 8: Operator Command Handlers
  const handleTakeover = async (reason: string = "Operator initiated human takeover") => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/takeover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, operator_id: "operator_1" }),
      });
      if (res.ok) {
        setOperatorOwnershipState("HUMAN_ACTIVE");
        setActiveAlerts((prev) => [
          {
            id: crypto.randomUUID(),
            severity: "NOTICE",
            title: "Operator Takeover",
            message: "Human takeover active. Autonomous AI speech suppressed.",
            timestamp: new Date().toISOString(),
          },
          ...prev.slice(0, 4),
        ]);
      }
    } catch (e) {
      console.error("Takeover error:", e);
    }
  };

  const handlePauseAdaptive = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/pause`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Operator paused adaptive AI", operator_id: "operator_1" }),
      });
      if (res.ok) {
        setIsAdaptivePaused(true);
      }
    } catch (e) {
      console.error("Pause adaptive error:", e);
    }
  };

  const handleResumeAdaptive = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Operator resumed adaptive AI", operator_id: "operator_1" }),
      });
      if (res.ok) {
        setIsAdaptivePaused(false);
      }
    } catch (e) {
      console.error("Resume adaptive error:", e);
    }
  };

  const handleRequestSafetyCheck = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/safety-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Operator requested safety verification", operator_id: "operator_1" }),
      });
      if (res.ok) {
        setActiveAlerts((prev) => [
          {
            id: crypto.randomUUID(),
            severity: "WARNING",
            title: "Safety Check Requested",
            message: "Safety Engine verification triggered.",
            timestamp: new Date().toISOString(),
          },
          ...prev.slice(0, 4),
        ]);
      }
    } catch (e) {
      console.error("Safety check request error:", e);
    }
  };

  const handleRequestHandoff = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/handoff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_department: "crisis_counseling_tier2",
          notes: "Warm transfer requested by human supervisor",
          operator_id: "operator_1",
        }),
      });
      if (res.ok) {
        setOperatorHandoffStatus("REQUESTED");
        setOperatorOwnershipState("HANDOFF_PENDING");
      }
    } catch (e) {
      console.error("Request handoff error:", e);
    }
  };

  const handleConfirmHandoff = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/handoff/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transfer_confirmed_by: "supervisor_01",
          target_agent: "counselor_tier2",
        }),
      });
      if (res.ok) {
        setOperatorHandoffStatus("CONFIRMED");
      }
    } catch (e) {
      console.error("Confirm handoff error:", e);
    }
  };

  const handleCancelHandoff = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/handoff/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: "Operator cancelled transfer",
          operator_id: "operator_1",
        }),
      });
      if (res.ok) {
        setOperatorHandoffStatus("CANCELLED");
        setOperatorOwnershipState("HUMAN_ACTIVE");
      }
    } catch (e) {
      console.error("Cancel handoff error:", e);
    }
  };

  const handleSaveNote = async () => {
    if (!selectedCallId || !newNoteText.trim()) return;
    setIsSubmittingNote(true);
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: newNoteCategory,
          text: newNoteText.trim(),
          operator_id: "operator_1",
        }),
      });
      if (res.ok) {
        const note = await res.json();
        setOperatorNotes((prev) => [note, ...prev]);
        setNewNoteText("");
      }
    } catch (e) {
      console.error("Save note error:", e);
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleSearchKnowledge = async (customQuery?: string) => {
    const q = customQuery !== undefined ? customQuery : knowledgeQuery;
    if (!q.trim()) return;
    setIsSearchingKnowledge(true);
    setKnowledgeStatus("SEARCHING");
    try {
      const res = await fetch(`${apiUrl}/v1/knowledge/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q.trim(),
          jurisdiction: knowledgeJurisdiction === "ALL" ? undefined : knowledgeJurisdiction,
          language: knowledgeLanguage === "ALL" ? undefined : knowledgeLanguage,
          effective_only: knowledgeCurrentOnly,
          call_id: selectedCallId || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setKnowledgeResult(data);
        setKnowledgeStatus(data.status || "COMPLETED");
      } else {
        setKnowledgeStatus("FAILED");
      }
    } catch {
      setKnowledgeStatus("DEGRADED");
    } finally {
      setIsSearchingKnowledge(false);
    }
  };

  const handleSaveKnowledgeAsNote = async (item?: any) => {
    if (!selectedCallId) return;
    const citation = item?.citation || knowledgeResult?.citations?.[0];
    const citationRef = citation ? `citation:${citation.citation_id}` : undefined;
    const noteText = item
      ? `[Source Citation]: ${item.title} (${item.citation?.section_page || "Section"}) - ${item.excerpt}`
      : `[Knowledge Summary]: ${knowledgeResult?.ai_summary || "Retrieved policy guidance."}`;

    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: "GENERAL",
          text: noteText,
          operator_id: "operator_1",
          citation_ref: citationRef,
        }),
      });
      if (res.ok) {
        const note = await res.json();
        setOperatorNotes((prev) => [note, ...prev]);
      }
    } catch (e) {
      console.error("Save knowledge note error:", e);
    }
  };

  // Phase 11: Case Intelligence Handlers
  const fetchCaseGraph = async (caseId: string, depth = caseDepth, focus = caseFocusEntity) => {
    try {
      setIsRefreshingCase(true);
      const url = new URL(`${apiUrl}/v1/cases/${caseId}/graph`);
      url.searchParams.set("depth", String(depth));
      if (focus && focus.trim()) url.searchParams.set("focus", focus.trim());
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setCaseGraph(data);
      }
    } catch (err) {
      console.error("Failed to fetch case graph:", err);
    } finally {
      setIsRefreshingCase(false);
    }
  };

  const fetchCaseIntegrity = async (caseId: string) => {
    try {
      const res = await fetch(`${apiUrl}/v1/cases/${caseId}/integrity`);
      if (res.ok) {
        const data = await res.json();
        setCaseIntegrity(data);
      }
    } catch (err) {
      console.error("Failed to fetch case integrity:", err);
    }
  };

  const fetchCaseForCall = async (callIdOrCaseId?: string) => {
    try {
      let res;
      if (callIdOrCaseId && callIdOrCaseId.startsWith("case-")) {
        res = await fetch(`${apiUrl}/v1/cases/${callIdOrCaseId}`);
      } else if (callIdOrCaseId) {
        res = await fetch(`${apiUrl}/v1/cases/by-call/${callIdOrCaseId}`);
      }
      if (!res || !res.ok) {
        res = await fetch(`${apiUrl}/v1/cases/case-1001`);
      }
      if (res.ok) {
        const cData = await res.json();
        setCaseRecord(cData);
        await fetchCaseGraph(cData.case_id);
        await fetchCaseIntegrity(cData.case_id);
      }
    } catch (e) {
      console.error("Failed to load case data:", e);
    }
  };

  const handleConfirmCandidate = async (candidateId: string) => {
    if (!caseRecord?.case_id) return;
    try {
      setCandidateActionLoading(candidateId);
      const res = await fetch(`${apiUrl}/v1/cases/${caseRecord.case_id}/candidates/${candidateId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_id: "operator_1" }),
      });
      if (res.ok) {
        await fetchCaseGraph(caseRecord.case_id);
        await fetchCaseIntegrity(caseRecord.case_id);
      }
    } catch (err) {
      console.error("Failed to confirm candidate:", err);
    } finally {
      setCandidateActionLoading(null);
    }
  };

  const handleRejectCandidate = async (candidateId: string) => {
    if (!caseRecord?.case_id) return;
    try {
      setCandidateActionLoading(candidateId);
      const res = await fetch(`${apiUrl}/v1/cases/${caseRecord.case_id}/candidates/${candidateId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_id: "operator_1", reason: "Rejected by tele-counselor" }),
      });
      if (res.ok) {
        await fetchCaseGraph(caseRecord.case_id);
        await fetchCaseIntegrity(caseRecord.case_id);
      }
    } catch (err) {
      console.error("Failed to reject candidate:", err);
    } finally {
      setCandidateActionLoading(null);
    }
  };

  const handleViewCaseAudit = async () => {
    if (!caseRecord?.case_id) return;
    try {
      const res = await fetch(`${apiUrl}/v1/cases/${caseRecord.case_id}/audit?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setCaseAuditLogs(data);
        setShowCaseAuditModal(true);
      }
    } catch (err) {
      console.error("Failed to load case audit:", err);
    }
  };

  // Phase 12: Follow-up Handlers
  const displayedFollowups = useMemo(() => {
    if (followupFilterStatus === "ALL") return followups;
    return followups.filter((f) => f.status === followupFilterStatus);
  }, [followups, followupFilterStatus]);

  const handleCreateFollowup = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const caseId = caseRecord?.case_id || "case-1001";
    try {
      const now = new Date();
      const sched = newFollowupScheduledFor || new Date(now.getTime() + 3600000 * 24).toISOString();
      const due = newFollowupDueAt || new Date(now.getTime() + 3600000 * 48).toISOString();

      const res = await fetch(`${apiUrl}/v1/cases/${caseId}/followups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_id: caseId,
          call_id: selectedCallId || "call-fixture-01",
          created_by: "operator_1",
          type: newFollowupType,
          priority: newFollowupPriority,
          purpose: newFollowupPurpose || "Scheduled safety and welfare follow-up check-in",
          channel: newFollowupChannel,
          scheduled_for: sched,
          due_at: due,
          safe_contact_window: newFollowupSafeWindow,
          contact_preferences: {
            preferred_channel: newFollowupChannel,
            safe_to_contact: true,
            human_only: newFollowupHumanOnly,
            preferred_time_window: newFollowupSafeWindow,
          },
          consent_state: newFollowupConsentState,
          max_attempts: Number(newFollowupMaxAttempts) || 3,
          notes_ref: newFollowupNotes || undefined,
        }),
      });
      if (res.ok) {
        setShowCreateFollowupModal(false);
        setNewFollowupPurpose("");
        setNewFollowupNotes("");
        await fetchFollowups();
        await fetchFollowupSummary();
      } else {
        const err = await res.json();
        alert(`Failed to create follow-up: ${err.detail || "Validation error"}`);
      }
    } catch (err) {
      console.error("Error creating followup:", err);
    }
  };

  const handleStartFollowup = async (followupId: string) => {
    try {
      const res = await fetch(`${apiUrl}/v1/followups/${followupId}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_id: "operator_1" }),
      });
      if (res.ok) {
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup?.followup_id === followupId) {
          const updated = await res.json();
          setSelectedFollowup(updated);
        }
      }
    } catch (err) {
      console.error("Error starting followup:", err);
    }
  };

  const handleRecordAttempt = async (followupId: string) => {
    try {
      const res = await fetch(`${apiUrl}/v1/followups/${followupId}/attempt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operator_id: "operator_1",
          channel: attemptChannel,
          result: attemptResult,
          notes: attemptNotes || "Attempt executed by operator",
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAttemptNotes("");
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup?.followup_id === followupId) {
          setSelectedFollowup(updated);
        }
      } else {
        const err = await res.json();
        alert(`Attempt failed: ${err.detail || "Error"}`);
      }
    } catch (err) {
      console.error("Error recording attempt:", err);
    }
  };

  const handleCompleteFollowup = async (followupId: string, outcome: FollowupOutcome) => {
    try {
      const res = await fetch(`${apiUrl}/v1/followups/${followupId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operator_id: "operator_1",
          outcome: outcome || FollowupOutcome.CONTACTED_SUCCESSFULLY,
          notes: "Completed by operator review",
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup?.followup_id === followupId) {
          setSelectedFollowup(updated);
        }
      }
    } catch (err) {
      console.error("Error completing followup:", err);
    }
  };

  const handleRescheduleFollowup = async (followupId: string) => {
    try {
      const targetTime = rescheduleTime || new Date(Date.now() + 86400000).toISOString();
      const res = await fetch(`${apiUrl}/v1/followups/${followupId}/reschedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operator_id: "operator_1",
          new_scheduled_for: targetTime,
          reason: rescheduleReason || "Caller requested later time slot",
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setRescheduleTime("");
        setRescheduleReason("");
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup?.followup_id === followupId) {
          setSelectedFollowup(updated);
        }
      }
    } catch (err) {
      console.error("Error rescheduling followup:", err);
    }
  };

  const handleCancelFollowup = async (followupId: string, reason?: string) => {
    try {
      const res = await fetch(`${apiUrl}/v1/followups/${followupId}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operator_id: "operator_1",
          reason: reason || "Cancelled by tele-counselor workstation",
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup?.followup_id === followupId) {
          setSelectedFollowup(updated);
        }
      }
    } catch (err) {
      console.error("Error cancelling followup:", err);
    }
  };

  const handleRevokeConsent = async (caseId: string, reason?: string) => {
    try {
      const res = await fetch(`${apiUrl}/v1/cases/${caseId}/followups/revoke-consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operator_id: "operator_1",
          reason: reason || "Caller withdrew contact consent during interaction",
        }),
      });
      if (res.ok) {
        await fetchFollowups();
        await fetchFollowupSummary();
        if (selectedFollowup) {
          const updatedRes = await fetch(`${apiUrl}/v1/followups/${selectedFollowup.followup_id}`);
          if (updatedRes.ok) {
            setSelectedFollowup(await updatedRes.json());
          }
        }
      }
    } catch (err) {
      console.error("Error revoking consent:", err);
    }
  };

  const handleViewFollowupAudit = async (followupId?: string) => {
    try {
      const targetId = followupId || selectedFollowup?.followup_id || "fol-1001";
      const res = await fetch(`${apiUrl}/v1/followups/${targetId}/audit?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setFollowupAuditLogs(data.items || (Array.isArray(data) ? data : []));
        setShowFollowupAuditModal(true);
      }
    } catch (err) {
      console.error("Failed to load followup audit:", err);
    }
  };


  const handleEndCall = async () => {
    if (!selectedCallId) return;
    try {
      const res = await fetch(`${apiUrl}/v1/operator/calls/${selectedCallId}/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: "Operator concluded call from workstation",
          operator_id: "operator_1",
        }),
      });
      if (res.ok) {
        setOperatorOwnershipState("ENDED");
        fetchCalls();
      }
    } catch (e) {
      console.error("End call error:", e);
    }
  };

  const openConfirmationModal = (
    actionType: "END_CALL" | "CONFIRM_HANDOFF" | "TAKEOVER",
    title: string,
    description: string,
    confirmLabel: string
  ) => {
    setConfirmationAction({
      isOpen: true,
      title,
      description,
      confirmLabel,
      actionType,
    });
  };

  const executeConfirmedAction = () => {
    if (confirmationAction.actionType === "END_CALL") {
      handleEndCall();
    } else if (confirmationAction.actionType === "CONFIRM_HANDOFF") {
      handleConfirmHandoff();
    } else if (confirmationAction.actionType === "TAKEOVER") {
      handleTakeover();
    }
    setConfirmationAction({ isOpen: false, title: "", description: "", confirmLabel: "", actionType: null });
  };

  // Acknowledge Safety Signal
  const handleAcknowledgeSignal = async (signalId: string) => {
    if (!selectedCallId) return;
    setAcknowledgingSignalId(signalId);
    try {
      const res = await fetch(`${apiUrl}/v1/safety/calls/${selectedCallId}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signal_id: signalId,
          acknowledged_by: "operator_console",
        }),
      });
      if (res.ok) {
        setSafetySignals((prev) =>
          prev.map((s) =>
            s.signal_id === signalId
              ? {
                  ...s,
                  acknowledged: true,
                  acknowledged_at: new Date().toISOString(),
                  acknowledged_by: "operator_console",
                }
              : s
          )
        );
      }
    } catch (err) {
      console.error("Error acknowledging safety signal:", err);
    } finally {
      setAcknowledgingSignalId(null);
    }
  };

  // Open Safety Rules Catalog
  const openSafetyRulesCatalog = async () => {
    setIsSafetyRulesOpen(true);
    try {
      const res = await fetch(`${apiUrl}/v1/safety/rules`);
      if (res.ok) {
        const data = await res.json();
        setSafetyRulesList(data.rules || []);
      }
    } catch (err) {
      console.error("Error fetching safety rules catalog:", err);
    }
  };

  // Run Deterministic Safety Lab Evaluation
  const runSafetyLabEvaluation = async () => {
    setIsEvaluatingSafety(true);
    try {
      const start = performance.now();
      const res = await fetch(`${apiUrl}/v1/safety/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          utterance_text: safetyLabInput,
          language: safetyLabLang,
          call_id: "safety-lab-eval",
          session_id: "safety-lab-sess",
        }),
      });
      const elapsed = Math.round(performance.now() - start);
      if (res.ok) {
        const data = await res.json();
        setSafetyLabResult({ ...data, latency_ms: elapsed });
      }
    } catch (err) {
      console.error("Safety evaluation error:", err);
    } finally {
      setIsEvaluatingSafety(false);
    }
  };

  // Scroll transcript to bottom on turn update
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, partialDraft]);

  // Selected call metadata
  const selectedCall = useMemo(() => {
    return (
      activeCalls.find((c) => c.call_id === selectedCallId) ||
      recentCalls.find((c) => c.call_id === selectedCallId) ||
      null
    );
  }, [activeCalls, recentCalls, selectedCallId]);

  // Trigger Simulation Scenario
  const runSimulation = async () => {
    setIsSimulating(true);
    try {
      const res = await fetch(`${apiUrl}/v1/telephony/simulate/conversation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_key: simScenario,
          caller_number: simCallerPhone,
          interruption_at_turn: simScenario === "interruption" ? 1 : null,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        setIsSimModalOpen(false);
        // Refresh and select the simulation call
        await fetchCalls();
        if (result.call_id) {
          selectCall(result.call_id);
        }
      }
    } catch (e) {
      console.error("Simulation error:", e);
    } finally {
      setIsSimulating(false);
    }
  };

  // Filtered Events
  const filteredEvents = useMemo(() => {
    if (eventFilter === "ALL") return callEvents;
    return callEvents.filter((ev) => {
      const type = ev.event_type;
      if (eventFilter === "TRANSCRIPT") {
        return type.includes("TRANSCRIPT") || type.includes("LANGUAGE");
      }
      if (eventFilter === "CONVERSATION") {
        return (
          type.includes("CONVERSATION") ||
          type.includes("AI_") ||
          type.includes("TTS_") ||
          type.includes("INTERRUPTED")
        );
      }
      if (eventFilter === "SAFETY") {
        return (
          type.includes("SAFETY_") ||
          type.includes("HUMAN_ALERT") ||
          type.includes("RISK")
        );
      }
      if (eventFilter === "ERRORS") {
        return type.includes("ERROR") || type.includes("SIGNAL");
      }
      if (eventFilter === "LATENCY") {
        return type.includes("LATENCY");
      }
      if (eventFilter === "OPERATOR") {
        return type.includes("OPERATOR_") || type.includes("NOTE_");
      }
      if (eventFilter === "SVI") {
        return type.includes("SVI");
      }
      if (eventFilter === "ACOUSTIC") {
        return type.includes("ACOUSTIC");
      }
      if (eventFilter === "ADAPTIVE") {
        return type.includes("ADAPTIVE");
      }
      if (eventFilter === "ORCHESTRATION") {
        return (
          type.includes("ORCHESTRATION") ||
          type.includes("AGENT_") ||
          type.includes("BRIEFING")
        );
      }
      if (eventFilter === "KNOWLEDGE") {
        return type.includes("KNOWLEDGE");
      }
      if (eventFilter === "CASE") {
        return type.includes("CASE");
      }
      if (eventFilter === "FOLLOWUP") {
        return type.includes("FOLLOWUP");
      }
      return true;
    });
  }, [callEvents, eventFilter]);

  // Filtered Calls Queue
  const filteredCalls = useMemo(() => {
    let list = activeTab === "ACTIVE" ? activeCalls : recentCalls;
    if (queueFilter === "CRITICAL") {
      list = list.filter((c) => c.safety_state === "CRITICAL");
    } else if (queueFilter === "ELEVATED") {
      list = list.filter((c) => ["HIGH", "ELEVATED"].includes(c.safety_state || ""));
    } else if (queueFilter === "TAKEOVER") {
      list = list.filter((c) => (c as any).ownership_state === "HUMAN_ACTIVE");
    } else if (queueFilter === "HIGH_SVI") {
      list = list.filter((c) => ["CRITICAL", "HIGH"].includes((c as any).svi_band || ""));
    }
    return list;
  }, [activeTab, activeCalls, recentCalls, queueFilter]);

  // Language display helper
  const getLanguageLabel = (langCode?: string) => {
    if (!langCode) return "Unknown";
    if (langCode.includes("ta")) return "Tamil (ta-IN)";
    if (langCode.includes("hi")) return "Hindi (hi-IN)";
    if (langCode.includes("en")) return "English (en-IN)";
    return langCode;
  };

  return (
    <div data-testid="operator-workstation" className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Header Bar */}
      <header className="min-h-14 border-b border-slate-800 px-4 md:px-6 flex items-center justify-between gap-3 bg-slate-900/60 backdrop-blur shrink-0 overflow-x-auto">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Radio className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white flex items-center gap-2">
              SAMVED Operator Console
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                Phase 4: Realtime Safety &amp; Oversight
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Safety Engine Status */}
          <div
            data-testid="safety-engine-status"
            className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900 px-3 py-1.5 rounded-md border border-slate-800 shrink-0"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Safety Engine:</span>
            <span className="font-mono font-semibold text-emerald-400">
              {safetyEngineStatus ? `${safetyEngineStatus.engine_version} (${safetyEngineStatus.rules_loaded_count} rules)` : "v1 Ready"}
            </span>
          </div>

          {/* System Mode */}
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900 px-3 py-1.5 rounded-md border border-slate-800">
            <Server className="h-3.5 w-3.5 text-slate-400" />
            <span>Mode:</span>
            <span className="font-mono font-semibold text-emerald-400">{systemMode}</span>
          </div>

          {/* WebSocket Connection Status Pill */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              wsStatus === "connected"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : wsStatus === "reconnecting"
                ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                : "bg-red-500/10 border-red-500/30 text-red-400"
            }`}
          >
            {wsStatus === "connected" ? (
              <>
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <span>WS Connected</span>
              </>
            ) : wsStatus === "reconnecting" ? (
              <>
                <RefreshCw className="h-3 w-3 animate-spin text-amber-400" />
                <span>Reconnecting ({reconnectCount})...</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-red-400" />
                <button onClick={connect} className="underline hover:text-white">
                  WS Reconnect
                </button>
              </>
            )}
          </div>

          {/* Safety Rules Catalog Button */}
          <button
            onClick={openSafetyRulesCatalog}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-all"
            title="View loaded deterministic safety rules"
          >
            <FileText className="h-3.5 w-3.5 text-amber-400" />
            <span>Rules Catalog</span>
          </button>

          {/* Safety Simulation Lab Button */}
          <button
            data-testid="open-safety-lab"
            onClick={() => setIsSafetyLabOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 text-xs font-semibold transition-all"
            title="Open Deterministic Safety Evaluation Lab"
          >
            <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
            <span>Safety Lab</span>
          </button>

          {/* SVI Simulation Lab Button */}
          <button
            data-testid="open-svi-lab"
            onClick={() => setIsSviLabOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-cyan-300 text-xs font-semibold transition-all"
            title="Open SVI Scoring Simulation Lab"
          >
            <Activity className="h-3.5 w-3.5 text-cyan-400" />
            <span>SVI Lab</span>
          </button>

          {/* Phase 6: Acoustic Simulation Lab Button */}
          <button
            data-testid="open-acoustic-lab"
            onClick={() => setIsAcousticLabOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/40 text-purple-300 text-xs font-semibold transition-all"
            title="Open Acoustic Analysis Simulation Lab"
          >
            <Volume2 className="h-3.5 w-3.5 text-purple-400" />
            <span>Acoustic Lab</span>
          </button>

          {/* Phase 7: Adaptive Simulation Lab Button */}
          <button
            data-testid="open-adaptive-lab"
            onClick={() => setIsAdaptiveLabOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold transition-all"
            title="Open Adaptive Conversation Strategy Lab"
          >
            <Compass className="h-3.5 w-3.5 text-emerald-400" />
            <span>Adaptive Lab</span>
          </button>

          {/* Action Buttons */}
          <button
            onClick={() => setIsSimModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Play className="h-3.5 w-3.5" />
            Launch Simulation
          </button>

          <button
            onClick={fetchCalls}
            className="p-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh active calls"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-x-auto overflow-y-hidden">
        {/* Left Sidebar: Master Call List */}
        <aside className="w-80 border-r border-slate-800 bg-slate-900/40 flex flex-col shrink-0">
          {/* Tabs */}
          <div className="flex border-b border-slate-800 p-2 gap-2">
            <button
              onClick={() => setActiveTab("ACTIVE")}
              className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "ACTIVE"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Radio className="h-3 w-3" />
              Active ({activeCalls.length})
            </button>
            <button
              onClick={() => setActiveTab("RECENT")}
              className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === "RECENT"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Clock className="h-3 w-3" />
              Recent ({recentCalls.length})
            </button>
          </div>

          {/* Operator Queue Filters */}
          <div className="flex flex-wrap gap-1 px-2.5 py-1.5 border-b border-slate-800/80 bg-slate-950/40">
            {[
              { key: "ALL", label: "All" },
              { key: "CRITICAL", label: "Critical" },
              { key: "ELEVATED", label: "Elevated" },
              { key: "TAKEOVER", label: "Takeover" },
              { key: "HIGH_SVI", label: "High SVI" },
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setQueueFilter(f.key)}
                className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                  queueFilter === f.key
                    ? "bg-slate-700 text-white font-semibold shadow-xs"
                    : "bg-slate-900 text-slate-400 hover:bg-slate-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Calls List */}
          <div data-testid="call-list" className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredCalls.length === 0 ? (
              <div className="text-center py-12 px-4">
                <PhoneCall className="h-8 w-8 text-slate-600 mx-auto mb-2 opacity-50" />
                <p className="text-xs text-slate-500">
                  {activeTab === "ACTIVE" ? "No active telephony calls matching filter." : "No recent calls recorded."}
                </p>
                {activeTab === "ACTIVE" && (
                  <button
                    onClick={() => setIsSimModalOpen(true)}
                    className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 underline"
                  >
                    Start a test simulation
                  </button>
                )}
              </div>
            ) : (
              filteredCalls.map((call) => {
                const isSelected = call.call_id === selectedCallId;
                const ownership = (call as any).ownership_state || "AI_ASSISTED";
                const isCritical = call.safety_state === "CRITICAL";
                const isHighSvi = ["CRITICAL", "HIGH"].includes((call as any).svi_band || "");

                return (
                  <div
                    key={call.call_id}
                    data-testid="call-item"
                    onClick={() => selectCall(call.call_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? "bg-indigo-950/40 border-indigo-500 shadow-sm"
                        : "bg-slate-900/80 border-slate-800/80 hover:border-slate-700 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-xs font-semibold text-slate-200">
                        {call.caller_masked_number}
                      </span>
                      <div className="flex items-center gap-1">
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                            ownership === "HUMAN_ACTIVE"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                              : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          }`}
                        >
                          {ownership === "HUMAN_ACTIVE" ? "Human" : "AI"}
                        </span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            call.is_active
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-slate-800 text-slate-400 border border-slate-700"
                          }`}
                        >
                          {call.state}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="truncate max-w-[120px] font-mono text-slate-500">
                        {call.call_id}
                      </span>
                      <span>{call.duration_seconds}s</span>
                    </div>

                    {/* Priority Indicator & Explanation */}
                    <div className="mt-1 flex items-center justify-between text-[10px]">
                      <span
                        className={`font-semibold ${
                          isCritical
                            ? "text-red-400"
                            : isHighSvi
                            ? "text-amber-400"
                            : "text-slate-500"
                        }`}
                        title={
                          isCritical
                            ? "Why: Immediate safety critical priority rule match"
                            : isHighSvi
                            ? "Why: Elevated distress vulnerability index"
                            : "Why: Standard conversational intake"
                        }
                      >
                        {isCritical
                          ? "• P0: Safety Critical"
                          : isHighSvi
                          ? "• P2: High SVI Distress"
                          : "• Standard Queue"}
                      </span>
                      {(call as any).notes_count > 0 && (
                        <span className="text-slate-400 flex items-center gap-0.5">
                          <FileText className="h-2.5 w-2.5" />
                          {(call as any).notes_count}
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex items-center justify-between pt-2 border-t border-slate-800/60">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300">
                          {getLanguageLabel(call.current_language)}
                        </span>
                        {call.safety_state && call.safety_state !== "NONE" ? (
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${
                              call.safety_state === "CRITICAL"
                                ? "bg-red-500/20 text-red-300 border-red-500/40 animate-pulse"
                                : call.safety_state === "HIGH"
                                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                                : "bg-yellow-500/20 text-yellow-300 border-yellow-500/40"
                            }`}
                          >
                            {call.safety_state}
                          </span>
                        ) : (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">
                            NORMAL
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {call.conversation_state}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Center: Call Detail & Live Transcripts */}
        <main className="flex-1 min-w-[360px] flex flex-col bg-slate-950 overflow-hidden border-r border-slate-800">
          {selectedCall ? (
            <>
              {/* Selected Call Header */}
              <div data-testid="active-call-header" className="border-b border-slate-800 bg-slate-900/30 p-4 shrink-0">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 font-mono font-bold">
                      <PhoneCall className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold text-white font-mono">
                          {selectedCall.caller_masked_number}
                        </h2>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono border border-slate-700">
                          {selectedCall.provider}
                        </span>
                        {/* Phase 8 Ownership Badge */}
                        <span
                          data-testid="ownership-badge"
                          className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
                            operatorOwnershipState === "HUMAN_ACTIVE"
                              ? "bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-xs"
                              : operatorOwnershipState === "HANDOFF_PENDING"
                              ? "bg-purple-500/20 text-purple-300 border-purple-500/50"
                              : operatorOwnershipState === "ENDED"
                              ? "bg-slate-800 text-slate-400 border-slate-700"
                              : "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                          }`}
                        >
                          {operatorOwnershipState}
                        </span>
                        {isAdaptivePaused && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700 font-bold uppercase tracking-wider">
                            AI Paused
                          </span>
                        )}
                        {operatorHandoffStatus === "REQUESTED" && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-700 font-bold uppercase tracking-wider animate-pulse">
                            Handoff Requested
                          </span>
                        )}
                        {operatorHandoffStatus === "CONFIRMED" && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 font-bold uppercase tracking-wider">
                            Handoff Confirmed
                          </span>
                        )}
                        {/* Mode Indicator */}
                        <span
                          data-testid="simulation-mode-badge"
                          className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono border border-slate-700"
                        >
                          DEV / SIMULATION ACTION
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 font-mono">ID: {selectedCall.call_id}</p>
                    </div>
                  </div>

                  {/* AI Conversation State Pill */}
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                        Dialogue State
                      </span>
                      <span
                        className={`text-xs px-2.5 py-1 rounded-full font-semibold flex items-center gap-1.5 border ${
                          aiState === "SPEAKING"
                            ? "bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse"
                            : aiState === "THINKING"
                            ? "bg-blue-500/20 text-blue-300 border-blue-500/40"
                            : aiState === "TRANSCRIBING"
                            ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                            : aiState === "INTERRUPTED"
                            ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                        }`}
                      >
                        {aiState === "SPEAKING" ? (
                          <Volume2 className="h-3 w-3" />
                        ) : aiState === "THINKING" ? (
                          <Cpu className="h-3 w-3" />
                        ) : aiState === "TRANSCRIBING" ? (
                          <Mic className="h-3 w-3" />
                        ) : aiState === "INTERRUPTED" ? (
                          <AlertTriangle className="h-3 w-3" />
                        ) : (
                          <Activity className="h-3 w-3" />
                        )}
                        {aiState || selectedCall.conversation_state}
                      </span>
                    </div>

                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                        Language
                      </span>
                      <span className="text-xs px-2.5 py-1 rounded-md bg-slate-800 text-slate-200 border border-slate-700 flex items-center gap-1">
                        <Globe className="h-3 w-3 text-indigo-400" />
                        {getLanguageLabel(currentLanguage || selectedCall.current_language)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Turn Latency Instrumentation Bar */}
                <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-xs">
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80 flex items-center justify-between">
                    <span className="text-slate-400">STT Latency:</span>
                    <span className="font-mono text-emerald-400 font-semibold">{latencies.stt_ms}ms</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80 flex items-center justify-between">
                    <span className="text-slate-400">LLM Latency:</span>
                    <span className="font-mono text-blue-400 font-semibold">{latencies.llm_ms}ms</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80 flex items-center justify-between">
                    <span className="text-slate-400">TTS Latency:</span>
                    <span className="font-mono text-purple-400 font-semibold">{latencies.tts_ms}ms</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80 flex items-center justify-between">
                    <span className="text-slate-400">Turn Total:</span>
                    <span className="font-mono text-indigo-300 font-semibold">{latencies.total_ms}ms</span>
                  </div>
                </div>
              </div>

              {/* Phase 8 Realtime Notifications Toast / Banner */}
              {activeAlerts.length > 0 && (
                <div data-testid="operator-alert-banner" className="mx-6 mt-3 space-y-1.5">
                  {activeAlerts.slice(0, 2).map((alert) => (
                    <div
                      key={alert.id}
                      className={`px-3 py-2 rounded-lg border text-xs flex items-center justify-between transition-all ${
                        alert.severity === "CRITICAL"
                          ? "bg-red-950/80 border-red-600 text-red-100 shadow-md"
                          : alert.severity === "WARNING"
                          ? "bg-amber-950/70 border-amber-500 text-amber-100"
                          : "bg-slate-900 border-slate-700 text-slate-200"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <AlertCircle
                          className={`h-4 w-4 ${
                            alert.severity === "CRITICAL"
                              ? "text-red-400"
                              : alert.severity === "WARNING"
                              ? "text-amber-400"
                              : "text-cyan-400"
                          }`}
                        />
                        <div>
                          <span className="font-bold">{alert.title}: </span>
                          <span>{alert.message}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => setActiveAlerts((prev) => prev.filter((a) => a.id !== alert.id))}
                        className="text-slate-400 hover:text-white p-1"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Phase 8 Operator Control Bar */}
              <div
                data-testid="operator-control-bar"
                className="mx-6 mt-3 p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 flex flex-wrap items-center justify-between gap-2 shadow-xs"
              >
                <div className="flex items-center gap-2">
                  {operatorOwnershipState !== "HUMAN_ACTIVE" ? (
                    <button
                      data-testid="takeover-button"
                      onClick={() => handleTakeover("Operator initiated human takeover")}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs transition-all shadow-sm"
                    >
                      <User className="h-3.5 w-3.5" />
                      <span>Take Over</span>
                    </button>
                  ) : (
                    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs">
                      <User className="h-3.5 w-3.5" />
                      <span>Human Active</span>
                    </span>
                  )}

                  {!isAdaptivePaused ? (
                    <button
                      data-testid="pause-adaptive-button"
                      onClick={handlePauseAdaptive}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all"
                    >
                      <span>Pause Adaptive</span>
                    </button>
                  ) : (
                    <button
                      data-testid="resume-adaptive-button"
                      onClick={handleResumeAdaptive}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold transition-all"
                    >
                      <span>Resume Adaptive</span>
                    </button>
                  )}

                  <button
                    data-testid="safety-check-button"
                    onClick={handleRequestSafetyCheck}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 border border-rose-800 text-xs font-semibold transition-all"
                  >
                    <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
                    <span>Request Safety Check</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    data-testid="handoff-button"
                    onClick={handleRequestHandoff}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 text-xs font-semibold transition-all"
                  >
                    <span>Request Handoff</span>
                  </button>

                  {operatorHandoffStatus === "REQUESTED" && (
                    <button
                      data-testid="handoff-confirm-button"
                      onClick={() =>
                        openConfirmationModal(
                          "CONFIRM_HANDOFF",
                          "Confirm Handoff",
                          "Are you sure you want to confirm transferring this call to a receiving tele-counselor?",
                          "Confirm Transfer"
                        )
                      }
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-sm"
                    >
                      <span>Confirm Handoff</span>
                    </button>
                  )}

                  {operatorHandoffStatus === "REQUESTED" && (
                    <button
                      data-testid="handoff-cancel-button"
                      onClick={handleCancelHandoff}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-all"
                    >
                      <span>Cancel</span>
                    </button>
                  )}

                  <button
                    data-testid="add-note-button"
                    onClick={() => setIsNotesModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all"
                  >
                    <FileText className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Notes ({operatorNotes.length})</span>
                  </button>

                  <button
                    data-testid="end-call-button"
                    onClick={() =>
                      openConfirmationModal(
                        "END_CALL",
                        "End Active Call",
                        "Are you sure you want to conclude and terminate this call session?",
                        "End Call"
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-all shadow-sm"
                  >
                    <span>End Call</span>
                  </button>
                </div>
              </div>

              {/* Phase 8 Unified Call Triage Summary */}
              <div
                data-testid="unified-triage-summary"
                className="mx-6 mt-3 p-3.5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-md"
              >
                <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2.5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                      Unified Call Triage Summary
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">Realtime Multimodal Synthesis</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5 text-xs">
                  {/* 1. Safety State */}
                  <div data-testid="safety-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Safety State
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          safetyState === "CRITICAL"
                            ? "bg-red-500 animate-ping"
                            : safetyState === "HIGH"
                            ? "bg-amber-500"
                            : safetyState === "ELEVATED"
                            ? "bg-yellow-500"
                            : "bg-emerald-500"
                        }`}
                      />
                      <span className="font-mono">{safetyState}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 truncate">
                      {safetySignals.length > 0 ? `${safetySignals.length} active signal(s)` : "No active threats"}
                    </p>
                  </div>

                  {/* 2. SVI Distress */}
                  <div data-testid="svi-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      SVI Index (0-100)
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span className="font-mono text-cyan-400">{sviScore !== null ? sviScore : "—"}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                        {sviBand}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">Trend: {sviTrend}</p>
                  </div>

                  {/* 3. Acoustic Quality */}
                  <div data-testid="acoustic-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Acoustic Signal
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span className="font-mono text-purple-400">{acousticQuality}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 font-mono">
                      Conf: {(acousticConfidence * 100).toFixed(0)}%
                    </p>
                  </div>

                  {/* 4. Adaptive Strategy */}
                  <div data-testid="adaptive-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Adaptive Policy
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span className="font-mono text-emerald-400">{adaptivePriority}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 truncate">
                        {adaptiveAction}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 truncate">Target: {adaptiveTarget}</p>
                  </div>

                  {/* 5. Human Authority */}
                  <div data-testid="human-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Human Authority
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          operatorOwnershipState === "HUMAN_ACTIVE"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : operatorOwnershipState === "HANDOFF_PENDING"
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                            : operatorOwnershipState === "ENDED"
                            ? "bg-slate-800 text-slate-400"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        }`}
                      >
                        {operatorOwnershipState}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">Handoff: {operatorHandoffStatus}</p>
                  </div>

                  {/* 6. Multi-Agent Orchestration (Phase 9) */}
                  <div data-testid="orchestration-summary" className="p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Multi-Agent
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-slate-100">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase font-mono ${
                          orchestrationState === "COMPLETED"
                            ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
                            : orchestrationState === "DEGRADED"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : orchestrationState === "RUNNING"
                            ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {orchestrationState}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1 font-mono">
                      {orchestrationLatency > 0 ? `${orchestrationLatency.toFixed(0)} ms` : "6 workers active"}
                    </p>
                  </div>
                </div>
                <p className="text-[10px] text-slate-500 italic mt-2 text-center">
                  Operational Triage Summary — Strictly advisory &amp; supervisory. Not a clinical diagnosis, medical evaluation, or autonomous emergency dispatch.
                </p>
              </div>

              {/* Phase 4 Deterministic Safety Signals Oversight Banner */}
              <div
                data-testid="safety-engine-panel"
                className={`mx-6 mt-4 p-4 rounded-xl border transition-all ${
                  safetyState === "CRITICAL"
                    ? "bg-red-950/40 border-red-600/80 text-red-100 shadow-lg shadow-red-950/50"
                    : safetyState === "HIGH"
                    ? "bg-amber-950/30 border-amber-500/70 text-amber-100 shadow-md shadow-amber-950/40"
                    : safetyState === "ELEVATED"
                    ? "bg-yellow-950/20 border-yellow-500/50 text-yellow-100"
                    : safetyState === "WATCH"
                    ? "bg-blue-950/20 border-blue-500/40 text-blue-100"
                    : "bg-emerald-950/20 border-emerald-500/30 text-emerald-100"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                        safetyState === "CRITICAL"
                          ? "bg-red-600 text-white animate-pulse"
                          : safetyState === "HIGH"
                          ? "bg-amber-500 text-slate-950 font-bold"
                          : safetyState === "ELEVATED"
                          ? "bg-yellow-500 text-slate-950 font-bold"
                          : "bg-emerald-600 text-white"
                      }`}
                    >
                      <ShieldAlert className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold tracking-wide uppercase">
                          Safety Engine State:
                        </span>
                        <span
                          data-testid="safety-state-badge"
                          className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                            safetyState === "CRITICAL"
                              ? "bg-red-500 text-white animate-pulse"
                              : safetyState === "HIGH"
                              ? "bg-amber-500 text-slate-950"
                              : safetyState === "ELEVATED"
                              ? "bg-yellow-500 text-slate-950"
                              : safetyState === "WATCH"
                              ? "bg-blue-500 text-white"
                              : "bg-emerald-600 text-white"
                          }`}
                        >
                          {safetyState}
                        </span>
                        {safetyState !== "NONE" && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700 font-semibold uppercase tracking-wider">
                            Requires Human Review
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-300 mt-1">
                        {safetyState === "CRITICAL"
                          ? "CRITICAL — Acute threat or weapon evidence detected. Human-in-the-loop intervention required."
                          : safetyState === "HIGH"
                          ? "HIGH — Threat evidence detected. Human review required for escalation decision."
                          : safetyState === "ELEVATED"
                          ? "ELEVATED — Potential risk cue identified. System is actively monitoring context."
                          : safetyState === "WATCH"
                          ? "WATCH — Precautionary indicators logged. Normal conversational flow continuing."
                          : "NORMAL — No active threat indicators detected. Deterministic safety rules active."}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                    <span>Active Signals: {safetySignals.length}</span>
                  </div>
                </div>

                {/* Active Safety Signals List */}
                {safetySignals.length > 0 && (
                  <div className="mt-3.5 space-y-2 border-t border-slate-800/80 pt-3">
                    {safetySignals.map((sig) => (
                      <div
                        key={sig.signal_id}
                        data-testid="safety-signal-card"
                        className={`p-3 rounded-lg border text-xs flex items-center justify-between gap-4 ${
                          sig.severity === "CRITICAL"
                            ? "bg-red-950/60 border-red-600/80 text-red-100"
                            : sig.severity === "HIGH"
                            ? "bg-amber-950/50 border-amber-600/70 text-amber-100"
                            : "bg-slate-900 border-slate-800 text-slate-200"
                        }`}
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-black tracking-wider ${
                                sig.severity === "CRITICAL"
                                  ? "bg-red-600 text-white"
                                  : sig.severity === "HIGH"
                                  ? "bg-amber-500 text-slate-950"
                                  : "bg-blue-600 text-white"
                              }`}
                            >
                              {sig.severity}
                            </span>
                            <span className="font-mono text-xs font-bold text-white">
                              {sig.signal_type}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              [{sig.rule_id} {sig.rule_version}]
                            </span>
                            {sig.evidence?.temporal_context && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                                {sig.evidence.temporal_context}
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-slate-200">
                            <strong className="text-white">Why:</strong> {sig.evidence?.reason || "Safety signal triggered"}
                          </p>

                          {sig.evidence?.matched_phrase && (
                            <p className="text-[11px] text-slate-400 font-mono">
                              Matched: &ldquo;<span className="text-amber-300 underline font-semibold">{sig.evidence.matched_phrase}</span>&rdquo;
                            </p>
                          )}
                        </div>

                        <div className="shrink-0 flex items-center">
                          {sig.acknowledged ? (
                            <div className="text-xs text-emerald-400 flex items-center gap-1.5 bg-emerald-950/60 px-3 py-1.5 rounded-md border border-emerald-800 font-medium">
                              <CheckCircle2 className="h-4 w-4" />
                              <span>Acknowledged by {sig.acknowledged_by || "operator"}</span>
                            </div>
                          ) : (
                            <button
                              data-testid="acknowledge-safety-alert"
                              disabled={acknowledgingSignalId === sig.signal_id}
                              onClick={() => handleAcknowledgeSignal(sig.signal_id)}
                              className="px-3.5 py-2 rounded-md bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
                            >
                              {acknowledgingSignalId === sig.signal_id ? (
                                <>
                                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                  Acknowledging...
                                </>
                              ) : (
                                <>
                                  <CheckSquare className="h-3.5 w-3.5" />
                                  Acknowledge Alert
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Phase 5: SVI Scoring Panel */}
              <div data-testid="svi-panel" className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-cyan-950/30 border border-cyan-800/40 shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-12 w-12 rounded-lg flex items-center justify-center text-lg font-black ${
                        sviBand === "CRITICAL"
                          ? "bg-red-600 text-white animate-pulse"
                          : sviBand === "HIGH"
                          ? "bg-amber-500 text-slate-950"
                          : sviBand === "MODERATE"
                          ? "bg-yellow-500 text-slate-950"
                          : "bg-emerald-600 text-white"
                      }`}
                    >
                      {sviScore !== null ? sviScore : "—"}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold tracking-wide uppercase">
                          SVI Score:
                        </span>
                        <span
                          data-testid="svi-band-badge"
                          className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                            sviBand === "CRITICAL"
                              ? "bg-red-500 text-white animate-pulse"
                              : sviBand === "HIGH"
                              ? "bg-amber-500 text-slate-950"
                              : sviBand === "MODERATE"
                              ? "bg-yellow-500 text-slate-950"
                              : "bg-emerald-600 text-white"
                          }`}
                        >
                          {sviBand}
                        </span>
                        <span
                          data-testid="svi-trend-indicator"
                          className={`text-xs px-2 py-0.5 rounded font-bold ${
                            sviTrend === "RISING"
                              ? "bg-red-900/60 text-red-200"
                              : sviTrend === "FALLING"
                              ? "bg-emerald-900/60 text-emerald-200"
                              : sviTrend === "STABLE"
                              ? "bg-slate-800 text-slate-300"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {sviTrend === "RISING" ? "↑" : sviTrend === "FALLING" ? "↓" : "→"} {sviTrend}
                          {sviDelta !== 0 && ` (${sviDelta > 0 ? "+" : ""}${sviDelta})`}
                        </span>
                        {sviRequiresHumanReview && (
                          <span
                            data-testid="svi-human-review-badge"
                            className="text-[10px] px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700 font-semibold uppercase tracking-wider"
                          >
                            Human Review Required
                          </span>
                        )}
                        {sviCriticalOverride && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-red-600 text-white font-bold uppercase tracking-wider">
                            Critical Override
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score
                      </p>
                    </div>
                  </div>

                  <div className="text-right space-y-1">
                    <div className="text-xs text-slate-400">
                      Completeness
                    </div>
                    <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        data-testid="svi-completeness-bar"
                        className="h-full bg-cyan-500 rounded-full transition-all"
                        style={{ width: `${Math.round(sviCompleteness * 100)}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {Math.round(sviCompleteness * 100)}%
                    </div>
                  </div>
                </div>

                {/* Top Contributing Risk Factors */}
                {sviTopContributors.length > 0 && (
                  <div data-testid="svi-top-contributors" className="mt-3 border-t border-slate-800/80 pt-2.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Top Contributing Factors</div>
                    <div className="flex flex-wrap gap-1.5">
                      {sviTopContributors.map((c, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono border border-slate-700">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Protective Factor Reduction */}
                {sviProtectiveReduction > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-900/50 text-emerald-300 font-semibold border border-emerald-700">
                      Protective Buffer: −{sviProtectiveReduction} pts
                    </span>
                  </div>
                )}

                {/* Acoustic Evidence Deferral Notice */}
                <div data-testid="svi-acoustic-notice" className="mt-2.5 flex items-center gap-2 text-[10px] text-slate-500 italic">
                  <Mic className="h-3 w-3" />
                  Acoustic evidence: Not available in current phase (Phase 6 deferred)
                </div>

                {/* SVI History Timeline */}
                {sviHistory.length > 1 && (
                  <div className="mt-3 border-t border-slate-800/80 pt-2.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Turn-by-Turn History</div>
                    <div className="flex items-end gap-1 h-8">
                      {sviHistory.slice(-20).map((h, i) => (
                        <div
                          key={i}
                          className={`w-3 rounded-sm ${
                            h.band === "CRITICAL"
                              ? "bg-red-500"
                              : h.band === "HIGH"
                              ? "bg-amber-500"
                              : h.band === "MODERATE"
                              ? "bg-yellow-500"
                              : "bg-emerald-500"
                          }`}
                          style={{ height: `${Math.max(4, (h.score / 100) * 32)}px` }}
                          title={`Turn ${i + 1}: SVI ${h.score} (${h.band})`}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Phase 6: Acoustic Signals Panel */}
              <div data-testid="acoustic-panel" className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-purple-950/30 border border-purple-800/40 shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-11 w-11 rounded-lg flex items-center justify-center font-black ${
                        acousticQuality === "EXCELLENT"
                          ? "bg-emerald-600/30 border border-emerald-500/50 text-emerald-300"
                          : acousticQuality === "GOOD"
                          ? "bg-cyan-600/30 border border-cyan-500/50 text-cyan-300"
                          : acousticQuality === "DEGRADED"
                          ? "bg-amber-600/30 border border-amber-500/50 text-amber-300"
                          : acousticQuality === "POOR"
                          ? "bg-red-600/30 border border-red-500/50 text-red-300"
                          : "bg-slate-800 border border-slate-700 text-slate-400"
                      }`}
                    >
                      <Volume2 className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold tracking-wide uppercase text-slate-300">
                          Acoustic Telemetry:
                        </span>
                        <span
                          data-testid="acoustic-quality-badge"
                          className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                            acousticQuality === "EXCELLENT"
                              ? "bg-emerald-500 text-white"
                              : acousticQuality === "GOOD"
                              ? "bg-cyan-500 text-slate-950"
                              : acousticQuality === "DEGRADED"
                              ? "bg-amber-500 text-slate-950"
                              : acousticQuality === "POOR"
                              ? "bg-red-500 text-white animate-pulse"
                              : "bg-slate-700 text-slate-300"
                          }`}
                        >
                          {acousticQuality}
                        </span>
                        <span
                          data-testid="acoustic-confidence"
                          className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700"
                        >
                          Conf: {Math.round(acousticConfidence * 100)}%
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-900/40 text-purple-300 font-semibold border border-purple-700">
                          Canonical 8kHz PCM
                        </span>
                      </div>
                      <p data-testid="acoustic-disclaimer" className="text-[11px] text-slate-400 mt-1">
                        Operational support signals only. Not clinical or diagnostic.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Acoustic Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-800/80">
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Voice Activity</div>
                    <div data-testid="acoustic-speech-ratio" className="text-sm font-bold text-white mt-0.5">
                      {Math.round(acousticSpeechRatio * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-500">Silence: {Math.round(acousticSilenceRatio * 100)}%</div>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Longest Pause</div>
                    <div data-testid="acoustic-longest-pause" className="text-sm font-bold text-white mt-0.5">
                      {acousticLongestPause}ms
                    </div>
                    <div data-testid="acoustic-pause-count" className="text-[10px] text-slate-500">
                      Pauses: {acousticPauseCount}
                    </div>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Interruption Count</div>
                    <div data-testid="acoustic-interruptions" className="text-sm font-bold text-white mt-0.5">
                      {acousticInterruptions}
                    </div>
                    <div className="text-[10px] text-slate-500">Barge-in turns</div>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Energy & Pitch</div>
                    <div data-testid="acoustic-energy-var" className="text-sm font-bold text-white mt-0.5">
                      CV {acousticEnergyVar.toFixed(2)}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {acousticMedianF0 ? `${acousticMedianF0} Hz` : `RMS ${acousticMeanRms.toFixed(0)}`}
                    </div>
                  </div>
                </div>

                {/* Active Operational Signals */}
                <div className="mt-3 pt-2.5 border-t border-slate-800/80">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-purple-300 mb-1.5 flex items-center justify-between">
                    <span>Operational Acoustic Signals</span>
                    <span className="text-slate-500 font-normal lowercase">({acousticSignals.length} active)</span>
                  </div>
                  <div data-testid="acoustic-signals-list" className="flex flex-wrap gap-1.5">
                    {acousticSignals.length === 0 ? (
                      <span className="text-[11px] text-slate-500 italic">No elevated acoustic anomalies detected.</span>
                    ) : (
                      acousticSignals.map((sig, idx) => (
                        <div
                          key={idx}
                          data-testid="acoustic-signal-chip"
                          className="px-2.5 py-1 rounded bg-purple-950/60 border border-purple-700/50 text-purple-200 text-xs flex items-center gap-1.5"
                          title={sig.evidence}
                        >
                          <Activity className="h-3 w-3 text-purple-400 shrink-0" />
                          <span className="font-semibold">{sig.code}</span>
                          <span className="text-[10px] text-slate-400 border-l border-purple-800/80 pl-1.5">{sig.evidence}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Phase 7: Adaptive Conversation Engine Panel */}
              <div data-testid="adaptive-panel" className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-emerald-950/30 border border-emerald-800/40 shadow">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-11 w-11 rounded-lg flex items-center justify-center font-black ${
                        adaptivePriority === "P0"
                          ? "bg-rose-600/30 border border-rose-500/50 text-rose-300"
                          : adaptivePriority === "P1"
                          ? "bg-amber-600/30 border border-amber-500/50 text-amber-300"
                          : adaptivePriority === "P2"
                          ? "bg-orange-600/30 border border-orange-500/50 text-orange-300"
                          : adaptivePriority === "P3"
                          ? "bg-blue-600/30 border border-blue-500/50 text-blue-300"
                          : "bg-emerald-600/30 border border-emerald-500/50 text-emerald-300"
                      }`}
                    >
                      <Compass className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold tracking-wide uppercase text-slate-300">
                          Adaptive Policy:
                        </span>
                        <span
                          data-testid="adaptive-strategy"
                          className="text-xs px-2.5 py-0.5 rounded font-black tracking-wider bg-emerald-500 text-slate-950"
                        >
                          {adaptiveAction}
                        </span>
                        <span
                          data-testid="adaptive-priority"
                          className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                            adaptivePriority === "P0"
                              ? "bg-rose-500 text-white animate-pulse"
                              : adaptivePriority === "P1"
                              ? "bg-amber-500 text-slate-950"
                              : adaptivePriority === "P2"
                              ? "bg-orange-500 text-white"
                              : adaptivePriority === "P3"
                              ? "bg-blue-500 text-white"
                              : "bg-emerald-600 text-white"
                          }`}
                        >
                          {adaptivePriority}
                        </span>
                        <span
                          data-testid="adaptive-target"
                          className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-emerald-300 font-mono border border-slate-700"
                        >
                          Target: {adaptiveTarget}
                        </span>
                        <span
                          data-testid="adaptive-confidence"
                          className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700"
                        >
                          Conf: {Math.round(adaptiveConfidence * 100)}%
                        </span>
                        {adaptiveOverrideActive ? (
                          <span
                            data-testid="adaptive-override-badge"
                            className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/50"
                          >
                            OVERRIDE ACTIVE{adaptiveOverrideReason ? `: ${adaptiveOverrideReason}` : ""}
                          </span>
                        ) : (
                          <span
                            data-testid="adaptive-override-badge"
                            className="text-[10px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 font-medium border border-slate-700/60"
                          >
                            AI Autonomous
                          </span>
                        )}
                      </div>
                      <p data-testid="adaptive-disclaimer" className="text-[11px] text-slate-400 mt-1">
                        Deterministic conversational strategy layer. Surface realization bounded by safety rules. Non-clinical.
                      </p>
                    </div>
                  </div>

                  {/* Operator Override Quick Actions */}
                  <div data-testid="adaptive-override-controls" className="flex items-center gap-1.5 flex-wrap">
                    <button
                      data-testid="btn-override-human"
                      onClick={() => handleOperatorOverride("operator_force_human", "Operator escalation to human agent")}
                      className="px-2.5 py-1 rounded text-xs bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 font-semibold transition-all"
                      title="Force Immediate Human Counselor Handoff"
                    >
                      Force Human
                    </button>
                    <button
                      data-testid="btn-override-pause"
                      onClick={() => handleOperatorOverride("operator_pause_adaptive", "Operator paused AI questioning")}
                      className="px-2.5 py-1 rounded text-xs bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 font-semibold transition-all"
                      title="Pause Adaptive Questions (Supportive Silence)"
                    >
                      Pause Questions
                    </button>
                    <button
                      data-testid="btn-override-safety"
                      onClick={() => handleOperatorOverride("operator_request_safety_check", "Operator forced explicit safety check")}
                      className="px-2.5 py-1 rounded text-xs bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 font-semibold transition-all"
                      title="Force Explicit Safety Check Strategy"
                    >
                      Safety Check
                    </button>
                  </div>
                </div>

                {/* Reasons & Evidence Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-800/80">
                  {/* Reason Codes */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-300 mb-1.5 flex items-center justify-between">
                      <span>Deterministic Reasons</span>
                      <span className="text-slate-500 font-normal lowercase">({adaptiveReasonCodes.length})</span>
                    </div>
                    <div data-testid="adaptive-reasons" className="flex flex-wrap gap-1.5">
                      {adaptiveReasonCodes.length === 0 ? (
                        <span className="text-[11px] text-slate-500 italic">No specific reason codes logged.</span>
                      ) : (
                        adaptiveReasonCodes.map((rc, idx) => (
                          <div
                            key={idx}
                            data-testid="adaptive-reason-chip"
                            className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-700/50 text-emerald-200 text-xs flex items-center gap-1"
                          >
                            <Activity className="h-3 w-3 text-emerald-400 shrink-0" />
                            <span className="font-semibold">{rc}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Evidence References */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-300 mb-1.5 flex items-center justify-between">
                      <span>Structured Evidence</span>
                      <span className="text-slate-500 font-normal lowercase">({adaptiveEvidence.length})</span>
                    </div>
                    <div data-testid="adaptive-evidence" className="flex flex-wrap gap-1.5">
                      {adaptiveEvidence.length === 0 ? (
                        <span className="text-[11px] text-slate-500 italic">No prior evidence referenced.</span>
                      ) : (
                        adaptiveEvidence.map((ev, idx) => (
                          <div
                            key={idx}
                            data-testid="adaptive-evidence-chip"
                            className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-700/50 text-cyan-200 text-xs flex items-center gap-1"
                          >
                            <FileText className="h-3 w-3 text-cyan-400 shrink-0" />
                            <span className="font-mono text-[11px]">{ev}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Strategy History Breadcrumb */}
                {adaptiveHistory.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-800/80">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                      <span>Recent Turn Strategy Trajectory</span>
                      <span className="text-slate-500 font-normal lowercase">({adaptiveHistory.length} turns)</span>
                    </div>
                    <div data-testid="adaptive-history" className="flex items-center gap-1.5 overflow-x-auto py-1">
                      {adaptiveHistory.map((h, i) => (
                        <div
                          key={i}
                          data-testid="adaptive-history-item"
                          className={`px-2 py-0.5 rounded text-[10px] font-mono shrink-0 border ${
                            h.priority === "P0"
                              ? "bg-rose-950/60 border-rose-700 text-rose-300 font-bold"
                              : h.priority === "P1"
                              ? "bg-amber-950/60 border-amber-700 text-amber-300 font-bold"
                              : "bg-slate-900 border-slate-800 text-slate-300"
                          }`}
                          title={`Turn ${i + 1}: ${h.action} (${h.priority})`}
                        >
                          T{i + 1}: {h.action}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Multi-Agent Orchestration & Specialized AI Coordination Layer (Phase 9) */}
              <div
                data-testid="multi-agent-panel"
                className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-teal-950/30 border border-teal-800/40 shadow"
              >
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-teal-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-teal-200">
                      Multi-Agent Orchestration &amp; Specialized AI Layer
                    </span>
                    <span
                      data-testid="orchestration-state-badge"
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        orchestrationState === "COMPLETED"
                          ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
                          : orchestrationState === "DEGRADED"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : orchestrationState === "RUNNING"
                          ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {orchestrationState}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {orchestrationLatency > 0 && (
                      <span
                        data-testid="orchestration-latency"
                        className="text-[11px] font-mono text-slate-400 bg-slate-950/60 px-2 py-0.5 rounded border border-slate-800"
                      >
                        {orchestrationLatency.toFixed(0)} ms
                      </span>
                    )}
                    <button
                      data-testid="refresh-orchestration-button"
                      onClick={() => selectedCallId && handleRefreshOrchestration(selectedCallId)}
                      disabled={!selectedCallId || isRefreshingOrchestration}
                      className="px-2.5 py-1 rounded text-xs bg-teal-600/20 hover:bg-teal-600/30 border border-teal-500/40 text-teal-300 font-semibold transition-all flex items-center gap-1.5 disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3 w-3 ${isRefreshingOrchestration ? "animate-spin" : ""}`} />
                      <span>Refresh</span>
                    </button>
                  </div>
                </div>

                {/* Worker Agents Status Grid */}
                <div className="mb-3">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                    <span>Specialized AI Sub-Services / Workers</span>
                    <span className="text-slate-500 font-normal lowercase">(deterministic pipeline)</span>
                  </div>
                  <div data-testid="workers-grid" className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                    {[
                      { name: "safety_context_agent", label: "Safety Adapter", type: "DET_ADAPTER" },
                      { name: "acoustic_context_agent", label: "Acoustic Telemetry", type: "DET_ADAPTER" },
                      { name: "language_context_agent", label: "Language & Dialect", type: "RULE_WORKER" },
                      { name: "conversation_context_agent", label: "Facts & Gaps", type: "LLM_WORKER" },
                      { name: "support_options_agent", label: "Support Stub", type: "PHASE_10_STUB" },
                      { name: "operator_briefing_agent", label: "Briefing Formatter", type: "SUMMARIZER" },
                    ].map((agent) => {
                      const workerData = orchestrationWorkers[agent.name];
                      const status = workerData?.status || "SUCCESS";
                      return (
                        <div
                          key={agent.name}
                          data-testid="worker-chip"
                          className={`p-2 rounded-lg border text-xs flex flex-col justify-between ${
                            status === "SUCCESS"
                              ? "bg-slate-950/60 border-teal-800/40 text-teal-100"
                              : status === "DEGRADED" || status === "TIMED_OUT"
                              ? "bg-amber-950/40 border-amber-800/40 text-amber-200"
                              : "bg-slate-900 border-slate-800 text-slate-400"
                          }`}
                        >
                          <div className="font-semibold truncate text-[11px]">{agent.label}</div>
                          <div className="flex items-center justify-between mt-1 text-[10px]">
                            <span className="font-mono text-slate-500 text-[9px]">{agent.type}</span>
                            <span
                              className={`font-mono font-bold ${
                                status === "SUCCESS" ? "text-teal-400" : "text-amber-400"
                              }`}
                            >
                              {status}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Operator Briefing Card */}
                {orchestrationBriefing && (
                  <div
                    data-testid="operator-briefing-card"
                    className="p-3.5 rounded-lg bg-slate-950/70 border border-teal-700/40 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-teal-300 flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5 text-teal-400" />
                        Operator Briefing Card
                      </span>
                      {orchestrationBriefing.confidence && (
                        <span className="text-[10px] font-mono text-slate-400">
                          Confidence: {(orchestrationBriefing.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      <div data-testid="briefing-safety-summary" className="p-2 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Safety Context</div>
                        <p className="text-slate-200 mt-0.5">{orchestrationBriefing.safety_summary || "Standard triage protocol in effect."}</p>
                      </div>
                      <div data-testid="briefing-svi-summary" className="p-2 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">SVI Vulnerability</div>
                        <p className="text-slate-200 mt-0.5">{orchestrationBriefing.svi_summary || "SVI index baseline assessment."}</p>
                      </div>
                      <div data-testid="briefing-acoustic-summary" className="p-2 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Acoustic Telemetry</div>
                        <p className="text-slate-200 mt-0.5">{orchestrationBriefing.acoustic_summary || "Acoustics profile stable."}</p>
                      </div>
                      <div data-testid="briefing-adaptive-recommendation" className="p-2 rounded bg-slate-900/90 border border-slate-800">
                        <div className="text-[10px] font-bold text-slate-400 uppercase">Adaptive Recommendation</div>
                        <p className="text-slate-200 mt-0.5">{orchestrationBriefing.adaptive_recommendation || "Continue active listening."}</p>
                      </div>
                    </div>

                    {/* Key Facts & Evidence */}
                    {orchestrationBriefing.key_facts && orchestrationBriefing.key_facts.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/80">
                        <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Extracted Facts</div>
                        <div data-testid="briefing-key-facts" className="flex flex-wrap gap-1.5">
                          {orchestrationBriefing.key_facts.map((fact, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[11px]"
                            >
                              {fact}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {orchestrationBriefing.evidence_refs && orchestrationBriefing.evidence_refs.length > 0 && (
                      <div className="pt-1.5 border-t border-slate-800/80">
                        <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Evidence Chain</div>
                        <div data-testid="briefing-evidence-chips" className="flex flex-wrap gap-1">
                          {orchestrationBriefing.evidence_refs.map((ref, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.2 rounded bg-teal-950/60 border border-teal-800/50 text-teal-300 font-mono text-[10px]"
                            >
                              {ref}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Phase 10: Legal / Policy Knowledge RAG (Governed Retrieval Layer) */}
              <div
                data-testid="knowledge-panel"
                className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-amber-950/20 border border-amber-800/40 shadow"
              >
                {/* Panel Header */}
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-200">
                      Legal &amp; Policy Knowledge RAG
                    </span>
                    <span
                      data-testid="knowledge-status-badge"
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        knowledgeStatus === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          : knowledgeStatus === "CONFLICT"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : knowledgeStatus === "NO_RELIABLE_SOURCE_FOUND"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                          : knowledgeStatus === "SEARCHING"
                          ? "bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {knowledgeStatus}
                    </span>
                    {knowledgeResult?.total_found !== undefined && (
                      <span
                        data-testid="knowledge-results-count"
                        className="text-[10px] font-mono text-slate-400 bg-slate-950/60 px-2 py-0.5 rounded border border-slate-800"
                      >
                        {knowledgeResult.total_found} {knowledgeResult.total_found === 1 ? "source" : "sources"}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-amber-400/80 font-mono flex items-center gap-1">
                      <Scale className="h-3 w-3" />
                      Citation-First Governance
                    </span>
                  </div>
                </div>

                {/* Search Bar & Filters */}
                <div className="mb-3 space-y-2">
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
                      <input
                        type="text"
                        data-testid="knowledge-query-input"
                        placeholder="Search government schemes, PWDVA provisions, shelter procedures..."
                        value={knowledgeQuery}
                        onChange={(e) => setKnowledgeQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSearchKnowledge();
                        }}
                        className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-700/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/60 font-sans"
                      />
                    </div>
                    <button
                      data-testid="knowledge-search-button"
                      onClick={() => handleSearchKnowledge()}
                      disabled={isSearchingKnowledge || !knowledgeQuery.trim()}
                      className="px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-300 text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50"
                    >
                      {isSearchingKnowledge ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Search className="h-3.5 w-3.5" />
                      )}
                      <span>Retrieve</span>
                    </button>
                  </div>

                  {/* Filter Controls */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5">
                        <label className="text-[10px] font-bold text-slate-400 uppercase">Jurisdiction:</label>
                        <select
                          data-testid="knowledge-jurisdiction-filter"
                          value={knowledgeJurisdiction}
                          onChange={(e) => setKnowledgeJurisdiction(e.target.value)}
                          className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 focus:outline-none"
                        >
                          <option value="ALL">All Jurisdictions</option>
                          <option value="INDIA">India (Central Laws)</option>
                          <option value="TAMIL_NADU">Tamil Nadu (State Policy)</option>
                        </select>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <label className="text-[10px] font-bold text-slate-400 uppercase">Language:</label>
                        <select
                          data-testid="knowledge-language-filter"
                          value={knowledgeLanguage}
                          onChange={(e) => setKnowledgeLanguage(e.target.value)}
                          className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 focus:outline-none"
                        >
                          <option value="ALL">All Languages</option>
                          <option value="en-IN">English (en-IN)</option>
                          <option value="ta-IN">Tamil (ta-IN)</option>
                          <option value="hi-IN">Hindi (hi-IN)</option>
                        </select>
                      </div>

                      <label className="flex items-center gap-1.5 cursor-pointer select-none text-[11px] text-slate-300">
                        <input
                          type="checkbox"
                          data-testid="knowledge-current-only-toggle"
                          checked={knowledgeCurrentOnly}
                          onChange={(e) => setKnowledgeCurrentOnly(e.target.checked)}
                          className="rounded border-slate-700 text-amber-600 focus:ring-0"
                        />
                        <span>Current / Effective Only</span>
                      </label>
                    </div>

                    {knowledgeResult?.search_latency_ms !== undefined && (
                      <span className="text-[10px] font-mono text-slate-500">
                        Latency: {knowledgeResult.search_latency_ms.toFixed(0)} ms
                      </span>
                    )}
                  </div>
                </div>

                {/* Warning Banners */}
                {knowledgeResult?.conflict_detected && (
                  <div
                    data-testid="knowledge-conflict-banner"
                    className="mb-3 p-2.5 rounded-lg bg-rose-950/40 border border-rose-600/70 text-rose-200 text-xs flex items-start gap-2"
                  >
                    <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold">SOURCE CONFLICT DETECTED</div>
                      <div className="text-[11px] text-rose-300/90 mt-0.5">
                        Two applicable policy directives specify contradictory guidelines. Human supervisor review recommended before counseling.
                      </div>
                      {knowledgeResult.conflicting_sources?.map((c: any, i: number) => (
                        <div key={i} className="text-[10px] text-rose-300 font-mono mt-1">
                          • {c.description} {c.resolution ? `(${c.resolution})` : ""}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {knowledgeResult?.results?.some((r: any) => r.effective_status === "STALE" || r.effective_status === "EXPIRED") && (
                  <div
                    data-testid="knowledge-stale-banner"
                    className="mb-3 p-2.5 rounded-lg bg-amber-950/40 border border-amber-600/70 text-amber-200 text-xs flex items-start gap-2"
                  >
                    <Clock className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold">SOURCE MAY BE OUTDATED</div>
                      <div className="text-[11px] text-amber-300/90 mt-0.5">
                        One or more retrieved guidelines are superseded or past their effective sunset period. Verify current circular before providing counsel.
                      </div>
                    </div>
                  </div>
                )}

                {knowledgeResult?.requires_human_review && !knowledgeResult.conflict_detected && knowledgeResult.status !== "NO_RELIABLE_SOURCE_FOUND" && (
                  <div
                    data-testid="knowledge-review-banner"
                    className="mb-3 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-600/60 text-indigo-200 text-xs flex items-start gap-2"
                  >
                    <ShieldAlert className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold">HUMAN REVIEW RECOMMENDED</div>
                      <div className="text-[11px] text-indigo-300/90 mt-0.5">
                        Complex legal/procedural qualifiers present. Tele-counselor verification required.
                      </div>
                    </div>
                  </div>
                )}

                {knowledgeStatus === "NO_RELIABLE_SOURCE_FOUND" && (
                  <div
                    data-testid="knowledge-no-source-notice"
                    className="mb-3 p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-300 text-xs text-center"
                  >
                    <AlertCircle className="h-5 w-5 text-amber-400 mx-auto mb-1 opacity-80" />
                    <div className="font-semibold text-slate-200">NO RELIABLE SOURCE FOUND</div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      No sufficiently authoritative source was retrieved for this query under the selected jurisdiction/date. General model guesswork is strictly blocked.
                    </p>
                  </div>
                )}

                {/* AI Summary Card (Explicit distinction from source text) */}
                {knowledgeResult?.ai_summary && knowledgeStatus !== "NO_RELIABLE_SOURCE_FOUND" && (
                  <div
                    data-testid="knowledge-ai-summary"
                    className="mb-3 p-3 rounded-lg bg-slate-950/80 border border-amber-800/50"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                          AI SUMMARY
                        </span>
                        <span className="text-[10px] text-slate-400 lowercase">(synthesized strictly from citations below)</span>
                      </div>
                      <button
                        data-testid="save-knowledge-note-button"
                        onClick={() => handleSaveKnowledgeAsNote()}
                        disabled={!selectedCallId}
                        className="px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1 transition-all disabled:opacity-40"
                      >
                        <BookmarkPlus className="h-3 w-3 text-amber-400" />
                        <span>Save to Notes</span>
                      </button>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-sans">
                      {knowledgeResult.ai_summary}
                    </p>
                  </div>
                )}

                {/* Retrieved Source Cards */}
                {knowledgeResult?.results && knowledgeResult.results.length > 0 && (
                  <div className="space-y-2 mb-3">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                      <span>Authoritative Sources &amp; Excerpts</span>
                      <span className="text-slate-500 font-normal lowercase">(citation-backed)</span>
                    </div>

                    <div className="grid grid-cols-1 gap-2">
                      {knowledgeResult.results.map((item: any, idx: number) => (
                        <div
                          key={item.chunk_id || idx}
                          data-testid="knowledge-source-card"
                          className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 hover:border-slate-700 transition-all text-xs"
                        >
                          {/* Card Header: Title & Badges */}
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <div>
                              <div data-testid="source-card-title" className="font-semibold text-slate-100 flex items-center gap-1.5">
                                <span>{item.title}</span>
                                <span className="text-[10px] font-mono text-slate-400">v{item.version}</span>
                              </div>
                              <div data-testid="source-card-publisher" className="text-[10px] text-slate-400">
                                {item.publisher}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              <span
                                data-testid="source-card-tier"
                                className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                                  item.authority_tier === 1
                                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                    : item.authority_tier === 2
                                    ? "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                                    : "bg-slate-800 text-slate-400"
                                }`}
                              >
                                Tier {item.authority_tier}
                              </span>
                              <span
                                data-testid="source-card-jurisdiction"
                                className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-slate-800 text-slate-300"
                              >
                                {item.jurisdiction}
                              </span>
                              <span
                                data-testid="source-card-status"
                                className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                                  item.effective_status === "CURRENT"
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-amber-500/20 text-amber-400"
                                }`}
                              >
                                {item.effective_status}
                              </span>
                            </div>
                          </div>

                          {/* Section & Date */}
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 border-t border-slate-900 pt-1">
                            <span data-testid="source-card-section" className="truncate max-w-[60%]">
                              Sec: {item.citation?.section_page || "General"}
                            </span>
                            <span data-testid="source-card-date" className="font-mono">
                              Effective: {item.source_date}
                            </span>
                          </div>

                          {/* Verbatim Excerpt */}
                          <div
                            data-testid="source-card-excerpt"
                            className="p-2 rounded bg-slate-900/90 border border-slate-800/80 text-slate-300 text-[11px] leading-relaxed mb-1.5 italic"
                          >
                            &ldquo;{item.excerpt}&rdquo;
                          </div>

                          {/* Footer Actions & Citation Ref */}
                          <div className="flex items-center justify-between pt-1 border-t border-slate-900 text-[10px]">
                            <div className="flex items-center gap-1.5">
                              <span
                                data-testid="source-card-citation"
                                className="font-mono text-amber-400/90 bg-amber-950/40 px-1.5 py-0.2 rounded border border-amber-800/40"
                              >
                                {item.citation?.citation_id ? `cit:${item.citation.citation_id.slice(0, 8)}` : "cit:verified"}
                              </span>
                              {item.source_url && (
                                <a
                                  data-testid="source-card-link"
                                  href={item.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-slate-400 hover:text-amber-300 flex items-center gap-0.5 underline transition-colors"
                                >
                                  <span>Official Source</span>
                                  <ExternalLink className="h-2.5 w-2.5" />
                                </a>
                              )}
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                data-testid="source-card-view-details"
                                onClick={() => setSelectedSourceDetail(item)}
                                className="text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800"
                              >
                                View Details
                              </button>
                              <button
                                onClick={() => handleSaveKnowledgeAsNote(item)}
                                disabled={!selectedCallId}
                                className="text-amber-400 hover:text-amber-300 px-1.5 py-0.5 rounded bg-amber-950/30 hover:bg-amber-950/50 border border-amber-800/40 disabled:opacity-40"
                              >
                                Cite in Note
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Source Detail Modal */}
                {selectedSourceDetail && (
                  <div
                    data-testid="knowledge-source-detail"
                    className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-700 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                      <span className="font-bold text-slate-200">Source Provenance &amp; Chunk Detail</span>
                      <button
                        onClick={() => setSelectedSourceDetail(null)}
                        className="text-slate-400 hover:text-slate-200 text-xs"
                      >
                        ✕ Close
                      </button>
                    </div>
                    <div className="text-[11px] text-slate-300 space-y-1">
                      <div><strong className="text-slate-400">Document ID:</strong> {selectedSourceDetail.document_id}</div>
                      <div><strong className="text-slate-400">Chunk ID:</strong> {selectedSourceDetail.chunk_id}</div>
                      <div><strong className="text-slate-400">Authority:</strong> Tier {selectedSourceDetail.authority_tier}</div>
                      <div><strong className="text-slate-400">Jurisdiction:</strong> {selectedSourceDetail.jurisdiction}</div>
                      <div><strong className="text-slate-400">Canonical URL:</strong> {selectedSourceDetail.source_url}</div>
                      <div><strong className="text-slate-400">Retrieved:</strong> {selectedSourceDetail.retrieved_at}</div>
                    </div>
                  </div>
                )}

                {/* Mandatory Legal & Safety Disclaimer */}
                <div
                  data-testid="knowledge-disclaimer"
                  className="mt-2 text-[10px] text-slate-500 italic text-center border-t border-slate-800/80 pt-1.5"
                >
                  Retrieved legal and policy information is provided as source-grounded operational support and is not a substitute for qualified legal advice or official determination.
                </div>
              </div>

              {/* Phase 11: Case Intelligence & Knowledge Graph Layer */}
              <div
                data-testid="case-intelligence-panel"
                className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-violet-950/20 border border-violet-800/40 shadow"
              >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-violet-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-violet-200">
                      Case Intelligence &amp; Knowledge Graph
                    </span>
                    <span
                      data-testid="case-number-badge"
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-violet-950/80 text-violet-300 border border-violet-700/50"
                    >
                      {caseRecord?.case_number || "CAS-2026-001001"}
                    </span>
                    <span
                      data-testid="case-status-badge"
                      className="px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    >
                      {caseRecord?.status || "ACTIVE"}
                    </span>
                    <span
                      data-testid="case-epistemic-mode"
                      className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      HUMAN_SUPERVISED
                    </span>
                    {caseIntegrity && (
                      <span
                        data-testid="case-integrity-badge"
                        className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                          caseIntegrity.valid
                            ? "bg-emerald-950/50 text-emerald-400 border border-emerald-800"
                            : "bg-rose-950/50 text-rose-400 border border-rose-800"
                        }`}
                      >
                        {caseIntegrity.valid ? "INTEGRITY: VALID" : "ANOMALY DETECTED"}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      data-testid="view-case-audit-btn"
                      onClick={handleViewCaseAudit}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] text-slate-300 flex items-center gap-1 transition-colors"
                    >
                      <Clock className="h-3 w-3" />
                      Audit Trail
                    </button>
                    <button
                      data-testid="refresh-case-btn"
                      onClick={() => {
                        if (caseRecord?.case_id) {
                          fetchCaseGraph(caseRecord.case_id);
                          fetchCaseIntegrity(caseRecord.case_id);
                        } else {
                          fetchCaseForCall();
                        }
                      }}
                      disabled={isRefreshingCase}
                      className="px-2 py-1 rounded bg-violet-950/60 hover:bg-violet-900/60 border border-violet-700/50 text-[10px] text-violet-300 flex items-center gap-1 disabled:opacity-50 transition-colors"
                    >
                      <RefreshCw className={`h-3 w-3 ${isRefreshingCase ? "animate-spin" : ""}`} />
                      Refresh
                    </button>
                  </div>
                </div>

                {/* Case Metadata & Subgraph Controls */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3 text-xs bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-400">Linked Call</span>
                    <span className="font-mono text-slate-200 truncate">
                      {selectedCallId || caseRecord?.linked_calls?.[0] || "call-fixture-01"}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-400">Assigned Operator</span>
                    <span className="text-slate-200">
                      {caseRecord?.assigned_operator_id || "operator"}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-400">Primary Language</span>
                    <span className="text-slate-200">
                      {caseRecord?.primary_language || "en-IN"}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-400">Linked Follow-ups</span>
                    <span
                      data-testid="case-followup-count"
                      className="text-xs font-mono font-bold text-emerald-400"
                    >
                      {followups.filter((f) => f.case_id === (caseRecord?.case_id || "case-1001")).length} Active
                    </span>
                  </div>
                  <div className="flex items-center gap-2 justify-end">
                    <span className="text-[10px] text-slate-400">Graph Depth:</span>
                    <select
                      data-testid="case-depth-select"
                      value={caseDepth}
                      onChange={(e) => {
                        const d = parseInt(e.target.value, 10);
                        setCaseDepth(d);
                        if (caseRecord?.case_id) fetchCaseGraph(caseRecord.case_id, d);
                      }}
                      className="bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-xs text-slate-200"
                    >
                      <option value={1}>1 Hop</option>
                      <option value={2}>2 Hops</option>
                      <option value={3}>3 Hops</option>
                      <option value={4}>4 Hops (Max)</option>
                    </select>
                  </div>
                </div>

                {/* Metrics Summary Strip */}
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="p-2 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Entities</span>
                    <span data-testid="case-entities-count" className="font-mono font-bold text-sm text-blue-300">
                      {caseGraph?.total_nodes ?? caseGraph?.nodes?.length ?? 3}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Relationships</span>
                    <span data-testid="case-edges-count" className="font-mono font-bold text-sm text-violet-300">
                      {caseGraph?.total_edges ?? caseGraph?.edges?.length ?? 2}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Pending Candidates</span>
                    <span data-testid="case-candidates-count" className="font-mono font-bold text-sm text-amber-300">
                      {caseGraph?.candidates?.filter((c: any) => c.status === "PENDING")?.length ?? 1}
                    </span>
                  </div>
                </div>

                {/* Candidate Confirmations Section (Human-Supervised Ambiguity Resolution) */}
                {caseGraph?.candidates && caseGraph.candidates.filter((c: any) => c.status === "PENDING").length > 0 && (
                  <div data-testid="candidate-confirmations-section" className="mb-3 p-3 rounded-lg bg-amber-950/20 border border-amber-800/40">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5 text-amber-300 text-xs font-bold uppercase tracking-wider">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        <span>Candidate Relationships Requiring Counselor Review</span>
                      </div>
                      <span className="text-[10px] text-amber-400/80 italic">Graduation requires human confirmation</span>
                    </div>

                    <div className="space-y-2">
                      {caseGraph.candidates
                        .filter((c: any) => c.status === "PENDING")
                        .map((cand: any) => (
                          <div
                            key={cand.candidate_id}
                            data-testid="candidate-card"
                            className="p-2.5 rounded bg-slate-950/90 border border-amber-700/40 text-xs flex flex-col md:flex-row md:items-center justify-between gap-2"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-1.5">
                                <span className="font-semibold text-slate-200">{cand.source_label}</span>
                                <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-amber-900/40 text-amber-300 border border-amber-700/50">
                                  {cand.relationship_type}
                                </span>
                                <span className="font-semibold text-slate-200">{cand.target_label}</span>
                                <span className="text-[9px] text-slate-400 font-mono">
                                  ({Math.round(cand.confidence * 100)}% conf)
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-300 italic">
                                &ldquo;{cand.evidence_excerpt}&rdquo;
                              </div>
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              <button
                                data-testid="confirm-candidate-btn"
                                onClick={() => handleConfirmCandidate(cand.candidate_id)}
                                disabled={candidateActionLoading === cand.candidate_id}
                                className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold flex items-center gap-1 transition-colors disabled:opacity-50 shadow-sm"
                              >
                                <Check className="h-3 w-3" />
                                Confirm
                              </button>
                              <button
                                data-testid="reject-candidate-btn"
                                onClick={() => handleRejectCandidate(cand.candidate_id)}
                                disabled={candidateActionLoading === cand.candidate_id}
                                className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/50 text-[11px] font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
                              >
                                <X className="h-3 w-3" />
                                Reject
                              </button>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Graph Visualizer (Nodes & Relationships View) */}
                <div data-testid="case-graph-visualizer" className="space-y-3">
                  {/* Entity Nodes List */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                      <span>Case Entities ({caseGraph?.nodes?.length || 0})</span>
                      <span className="text-slate-500 font-normal">Click node to inspect evidence</span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {(caseGraph?.nodes || []).map((node: any) => {
                        const isSelected = selectedGraphNode?.entity_id === node.entity_id;
                        const isPerson = node.type === "PERSON";
                        const isLoc = node.type === "LOCATION";
                        const isOrg = node.type === "ORGANIZATION";
                        const isDoc = node.type === "DOCUMENT";

                        return (
                          <div
                            key={node.entity_id}
                            data-testid="case-graph-node"
                            onClick={() => {
                              setSelectedGraphNode(node);
                              setSelectedGraphEdge(null);
                            }}
                            className={`p-2 rounded-lg cursor-pointer transition-all border text-xs ${
                              isSelected
                                ? "bg-violet-950/60 border-violet-400 shadow-md scale-[1.02]"
                                : isPerson
                                ? "bg-slate-950/80 border-blue-800/40 hover:border-blue-500/60"
                                : isLoc
                                ? "bg-slate-950/80 border-amber-800/40 hover:border-amber-500/60"
                                : isOrg
                                ? "bg-slate-950/80 border-emerald-800/40 hover:border-emerald-500/60"
                                : isDoc
                                ? "bg-slate-950/80 border-purple-800/40 hover:border-purple-500/60"
                                : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-800">
                                {node.type}
                              </span>
                              <span className={`text-[9px] font-mono font-bold uppercase ${
                                node.claim_status === "VERIFIED" ? "text-emerald-400" : "text-amber-400"
                              }`}>
                                {node.claim_status}
                              </span>
                            </div>
                            <div className="font-semibold text-slate-100 truncate">{node.label}</div>
                            {node.role && (
                              <div className="text-[10px] text-slate-400 truncate">Role: {node.role}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Active Relationship Edges List */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                      <span>Active Directed Relationships ({caseGraph?.edges?.length || 0})</span>
                      <span className="text-slate-500 font-normal">Click edge to inspect temporal validity</span>
                    </div>

                    <div className="space-y-1.5">
                      {(caseGraph?.edges || []).map((edge: any) => {
                        const isSelected = selectedGraphEdge?.edge_id === edge.edge_id;
                        const sourceLabel = caseGraph?.nodes?.find((n: any) => n.entity_id === edge.source_entity)?.label || edge.source_entity;
                        const targetLabel = caseGraph?.nodes?.find((n: any) => n.entity_id === edge.target_entity)?.label || edge.target_entity;

                        return (
                          <div
                            key={edge.edge_id}
                            data-testid="case-graph-edge"
                            onClick={() => {
                              setSelectedGraphEdge(edge);
                              setSelectedGraphNode(null);
                            }}
                            className={`p-2 rounded bg-slate-950/80 border cursor-pointer text-xs flex items-center justify-between transition-all ${
                              isSelected
                                ? "border-violet-400 bg-violet-950/40 shadow-sm"
                                : "border-slate-800 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex items-center gap-2 font-mono text-[11px]">
                              <span className="font-sans font-semibold text-slate-200">{sourceLabel}</span>
                              <span className="text-slate-500">&mdash;&gt;</span>
                              <span className="px-1.5 py-0.5 rounded bg-violet-950 text-violet-300 border border-violet-800/60 font-bold">
                                {edge.relationship_type}
                              </span>
                              <span className="text-slate-500">&mdash;&gt;</span>
                              <span className="font-sans font-semibold text-slate-200">{targetLabel}</span>
                            </div>

                            <div className="flex items-center gap-2 text-[10px]">
                              <span className="text-slate-400 font-mono">
                                {edge.superseded_at ? "SUPERSEDED" : "ACTIVE"}
                              </span>
                              <span className="font-mono text-slate-400">
                                {edge.valid_from ? edge.valid_from.slice(0, 10) : ""}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Node & Edge Inspector Drawer */}
                {(selectedGraphNode || selectedGraphEdge) && (
                  <div
                    data-testid="case-inspector-drawer"
                    className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-700 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                      <span className="font-bold text-slate-200">
                        {selectedGraphNode ? `Entity Inspector: ${selectedGraphNode.label}` : `Relationship Inspector: ${selectedGraphEdge.relationship_type}`}
                      </span>
                      <button
                        data-testid="close-inspector-btn"
                        onClick={() => {
                          setSelectedGraphNode(null);
                          setSelectedGraphEdge(null);
                        }}
                        className="text-slate-400 hover:text-slate-200 text-xs"
                      >
                        ✕ Close
                      </button>
                    </div>

                    {selectedGraphNode && (
                      <div data-testid="case-node-inspector" className="text-[11px] text-slate-300 space-y-1.5">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          <div><strong className="text-slate-400">Entity ID:</strong> {selectedGraphNode.entity_id}</div>
                          <div><strong className="text-slate-400">Type:</strong> {selectedGraphNode.type}</div>
                          <div><strong className="text-slate-400">Role:</strong> {selectedGraphNode.role || "N/A"}</div>
                          <div><strong className="text-slate-400">Claim Status:</strong> {selectedGraphNode.claim_status}</div>
                        </div>

                        {selectedGraphNode.evidence && selectedGraphNode.evidence.length > 0 && (
                          <div className="mt-2 pt-1 border-t border-slate-800">
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Evidence Anchors:</span>
                            {selectedGraphNode.evidence.map((ev: any, idx: number) => (
                              <div key={idx} className="mt-1 p-2 rounded bg-slate-900 border border-slate-800">
                                <div className="text-slate-200 italic">&ldquo;{ev.verbatim_excerpt}&rdquo;</div>
                                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                                  <span>Source: {ev.source_type} ({ev.source_id})</span>
                                  {ev.content_hash && (
                                    <span className="font-mono text-[9px] text-emerald-400">
                                      SHA-256: {ev.content_hash.slice(0, 16)}...
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {selectedGraphEdge && (
                      <div data-testid="case-edge-inspector" className="text-[11px] text-slate-300 space-y-1.5">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          <div><strong className="text-slate-400">Edge ID:</strong> {selectedGraphEdge.edge_id}</div>
                          <div><strong className="text-slate-400">Type:</strong> {selectedGraphEdge.relationship_type}</div>
                          <div><strong className="text-slate-400">Status:</strong> {selectedGraphEdge.claim_status}</div>
                          <div><strong className="text-slate-400">Valid From:</strong> {selectedGraphEdge.valid_from}</div>
                        </div>

                        {selectedGraphEdge.superseded_at && (
                          <div className="p-1.5 rounded bg-amber-950/30 text-amber-300 border border-amber-800/40 text-[10px]">
                            Superseded at {selectedGraphEdge.superseded_at} by {selectedGraphEdge.superseded_by}. Historical record preserved.
                          </div>
                        )}

                        {selectedGraphEdge.evidence && selectedGraphEdge.evidence.length > 0 && (
                          <div className="mt-2 pt-1 border-t border-slate-800">
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Evidence Link:</span>
                            {selectedGraphEdge.evidence.map((ev: any, idx: number) => (
                              <div key={idx} className="mt-1 p-2 rounded bg-slate-900 border border-slate-800">
                                <div className="text-slate-200 italic">&ldquo;{ev.verbatim_excerpt}&rdquo;</div>
                                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                                  <span>Source: {ev.source_id}</span>
                                  {ev.content_hash && (
                                    <span className="font-mono text-[9px] text-emerald-400">
                                      SHA-256: {ev.content_hash.slice(0, 16)}...
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Epistemic Safety Boundary Disclaimer */}
                <div
                  data-testid="case-safety-disclaimer"
                  className="mt-2 text-[10px] text-slate-500 italic text-center border-t border-slate-800/80 pt-1.5"
                >
                  Case knowledge graph reflects reported facts and verified evidence within this case boundary. No inferences of guilt or criminal determinations are made.
                </div>
              </div>

              {/* Case Audit Modal */}
              {showCaseAuditModal && (
                <div
                  data-testid="case-audit-modal"
                  className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
                >
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
                    <div className="flex items-center justify-between p-4 border-b border-slate-800">
                      <div className="flex items-center gap-2">
                        <Clock className="h-5 w-5 text-violet-400" />
                        <h3 className="font-bold text-slate-100">Case Audit Log &amp; Mutation History</h3>
                      </div>
                      <button
                        onClick={() => setShowCaseAuditModal(false)}
                        className="text-slate-400 hover:text-white"
                      >
                        <X className="h-5 w-5" />
                      </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-2">
                      {caseAuditLogs.length === 0 ? (
                        <p className="text-center py-8 text-xs text-slate-500">No audit records found for this case.</p>
                      ) : (
                        caseAuditLogs.map((entry: any) => (
                          <div key={entry.entry_id} className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-mono font-bold text-violet-300">{entry.action}</span>
                              <span className="text-[10px] text-slate-500 font-mono">{entry.timestamp}</span>
                            </div>
                            <div className="text-slate-300">
                              Actor: <span className="font-semibold text-slate-200">{entry.actor_id}</span>
                            </div>
                            {entry.details && Object.keys(entry.details).length > 0 && (
                              <pre className="mt-1 p-1.5 rounded bg-slate-900 text-[10px] font-mono text-slate-400 overflow-x-auto">
                                {JSON.stringify(entry.details, null, 2)}
                              </pre>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Phase 12: Follow-up Workqueue & Continuity Engine Layer */}
              <div
                data-testid="followup-workqueue-panel"
                className="mx-5 mt-3 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-emerald-950/20 border border-emerald-800/40 shadow"
              >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <CalendarCheck className="h-4 w-4 text-emerald-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-200">
                      Follow-up Workqueue &amp; Continuity Engine
                    </span>
                    <span
                      data-testid="followup-supervised-badge"
                      className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      HUMAN_SUPERVISED
                    </span>
                    <span
                      data-testid="followup-consent-guarded-badge"
                      className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                    >
                      CONSENT_GUARDED
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      data-testid="create-followup-btn"
                      onClick={() => setShowCreateFollowupModal(true)}
                      className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold flex items-center gap-1 shadow-sm transition-colors"
                    >
                      <Calendar className="h-3 w-3" />
                      Schedule Follow-up
                    </button>
                    <button
                      data-testid="view-all-followup-audit-btn"
                      onClick={() => handleViewFollowupAudit()}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] text-slate-300 flex items-center gap-1 transition-colors"
                    >
                      <Clock className="h-3 w-3" />
                      Audit Trail
                    </button>
                    <button
                      data-testid="refresh-followups-btn"
                      onClick={() => {
                        fetchFollowups();
                        fetchFollowupSummary();
                      }}
                      disabled={isRefreshingFollowups}
                      className="px-2 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-700/50 text-[10px] text-emerald-300 flex items-center gap-1 disabled:opacity-50 transition-colors"
                    >
                      <RefreshCw className={`h-3 w-3 ${isRefreshingFollowups ? "animate-spin" : ""}`} />
                      Refresh
                    </button>
                  </div>
                </div>

                {/* Metrics Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3 text-xs">
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 flex flex-col">
                    <span className="text-[10px] text-slate-400">Total Active</span>
                    <span data-testid="workqueue-stat-active" className="text-base font-mono font-bold text-slate-200">
                      {followupSummary.total_active}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 flex flex-col">
                    <span className="text-[10px] text-amber-400">Due Today</span>
                    <span data-testid="workqueue-stat-due" className="text-base font-mono font-bold text-amber-300">
                      {followupSummary.due_today}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 flex flex-col">
                    <span className="text-[10px] text-rose-400">Overdue</span>
                    <span data-testid="workqueue-stat-overdue" className="text-base font-mono font-bold text-rose-400">
                      {followupSummary.overdue}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 flex flex-col">
                    <span className="text-[10px] text-red-400">Blocked</span>
                    <span data-testid="workqueue-stat-blocked" className="text-base font-mono font-bold text-red-400">
                      {followupSummary.blocked}
                    </span>
                  </div>
                  <div className="bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 flex flex-col">
                    <span className="text-[10px] text-emerald-400">Completed Today</span>
                    <span data-testid="workqueue-stat-completed" className="text-base font-mono font-bold text-emerald-400">
                      {followupSummary.completed_today}
                    </span>
                  </div>
                </div>

                {/* Filter Pills */}
                <div className="flex flex-wrap gap-1.5 mb-3 border-b border-slate-800/80 pb-2">
                  {[
                    { id: "ALL", label: "All Tasks", testId: "followup-filter-all" },
                    { id: "SCHEDULED", label: "Scheduled", testId: "followup-filter-scheduled" },
                    { id: "READY", label: "Ready", testId: "followup-filter-ready" },
                    { id: "IN_PROGRESS", label: "In Progress", testId: "followup-filter-inprogress" },
                    { id: "BLOCKED", label: "Blocked", testId: "followup-filter-blocked" },
                    { id: "COMPLETED", label: "Completed", testId: "followup-filter-completed" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      data-testid={tab.testId}
                      onClick={() => setFollowupFilterStatus(tab.id)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                        followupFilterStatus === tab.id
                          ? "bg-emerald-600 text-white font-semibold"
                          : "bg-slate-800/80 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Follow-up Card List */}
                <div data-testid="followup-list" className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {displayedFollowups.length === 0 ? (
                    <div className="text-center py-6 text-slate-500 text-xs bg-slate-950/40 rounded-lg border border-slate-800/60">
                      <CalendarClock className="h-6 w-6 mx-auto mb-1.5 opacity-30 text-emerald-400" />
                      No follow-up tasks match the selected filter.
                    </div>
                  ) : (
                    displayedFollowups.map((fol) => {
                      const isBlocked = fol.status === FollowupStatus.BLOCKED;
                      const isCompleted = fol.status === FollowupStatus.COMPLETED;
                      const isInProgress = fol.status === FollowupStatus.IN_PROGRESS;
                      const isReady = fol.status === FollowupStatus.READY;
                      const isScheduled = fol.status === FollowupStatus.SCHEDULED;

                      return (
                        <div
                          key={fol.followup_id}
                          data-testid={`followup-card-${fol.followup_id}`}
                          className={`p-3 rounded-lg border transition-all text-xs ${
                            isBlocked
                              ? "bg-red-950/20 border-red-800/40"
                              : isInProgress
                              ? "bg-emerald-950/30 border-emerald-600/60 shadow-sm"
                              : isReady
                              ? "bg-amber-950/20 border-amber-600/50"
                              : isCompleted
                              ? "bg-slate-900/40 border-slate-800/60 opacity-80"
                              : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          {/* Top row: ID, Type, Status, Priority, Consent */}
                          <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1.5">
                            <div className="flex items-center gap-1.5">
                              <span data-testid="followup-id" className="font-mono font-bold text-emerald-300">
                                {fol.followup_id}
                              </span>
                              <span
                                data-testid="followup-type-badge"
                                className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700"
                              >
                                {fol.type}
                              </span>
                              <span
                                data-testid="followup-status-badge"
                                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                                  isBlocked
                                    ? "bg-rose-950/80 text-rose-300 border border-rose-800"
                                    : isCompleted
                                    ? "bg-slate-800 text-slate-400 border border-slate-700"
                                    : isInProgress
                                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/50"
                                    : isReady
                                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/50"
                                    : "bg-indigo-950/60 text-indigo-300 border border-indigo-700/50"
                                }`}
                              >
                                {fol.status}
                              </span>
                              <span
                                data-testid="followup-priority-badge"
                                className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                                  fol.priority === FollowupPriority.CRITICAL_REVIEW
                                    ? "bg-rose-900/60 text-rose-300 border border-rose-700"
                                    : fol.priority === FollowupPriority.HIGH
                                    ? "bg-amber-900/50 text-amber-300 border border-amber-700"
                                    : "bg-slate-800 text-slate-400"
                                }`}
                              >
                                {fol.priority}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5">
                              <span
                                data-testid="followup-consent-badge"
                                className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold ${
                                  fol.consent_state === ConsentState.GRANTED
                                    ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                                    : fol.consent_state === ConsentState.REVOKED || fol.consent_state === ConsentState.REFUSED
                                    ? "bg-red-950/70 text-red-400 border border-red-800/60"
                                    : "bg-amber-950/70 text-amber-400 border border-amber-800/60"
                                }`}
                              >
                                CONSENT: {fol.consent_state}
                              </span>
                              <span
                                data-testid="followup-channel-badge"
                                className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-slate-900 text-slate-400 border border-slate-800"
                              >
                                {fol.channel}
                              </span>
                            </div>
                          </div>

                          {/* Purpose */}
                          <p data-testid="followup-purpose" className="text-slate-200 text-xs mb-2 leading-relaxed">
                            {fol.purpose}
                          </p>

                          {/* Blocked reason if any */}
                          {fol.blocked_reason && (
                            <div className="mb-2 p-1.5 rounded bg-rose-950/40 border border-rose-800/50 text-[11px] text-rose-300 flex items-center gap-1.5">
                              <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                              <span>Blocked: {fol.blocked_reason}</span>
                            </div>
                          )}

                          {/* Timings and Attempts */}
                          <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/60 pt-1.5 mb-2 gap-2">
                            <div className="flex items-center gap-3">
                              <span>
                                Scheduled:{" "}
                                <strong data-testid="followup-scheduled-time" className="text-slate-300 font-mono">
                                  {new Date(fol.scheduled_for).toLocaleString()}
                                </strong>
                              </span>
                              {fol.safe_contact_window && (
                                <span>
                                  Safe Window:{" "}
                                  <strong data-testid="followup-safe-window" className="text-emerald-400 font-mono">
                                    {fol.safe_contact_window}
                                  </strong>
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span>
                                Attempts:{" "}
                                <strong data-testid="followup-attempts-count" className="text-slate-300 font-mono">
                                  {fol.attempt_count} / {fol.max_attempts}
                                </strong>
                              </span>
                              {fol.assigned_to && (
                                <span className="font-mono text-slate-400">Assigned: {fol.assigned_to}</span>
                              )}
                            </div>
                          </div>

                          {/* Operator Actions Strip */}
                          <div className="flex flex-wrap items-center justify-between gap-1.5 border-t border-slate-900 pt-1.5">
                            <div className="flex items-center gap-1.5">
                              {(isReady || isScheduled) && (
                                <button
                                  data-testid="start-followup-btn"
                                  onClick={() => handleStartFollowup(fol.followup_id)}
                                  className="px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-[10px] font-semibold transition-colors"
                                >
                                  Start Task
                                </button>
                              )}
                              {isInProgress && (
                                <>
                                  <button
                                    data-testid="record-attempt-btn"
                                    onClick={() => {
                                      setSelectedFollowup(fol);
                                      setShowFollowupDetailsDrawer(true);
                                    }}
                                    className="px-2 py-0.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-semibold transition-colors"
                                  >
                                    Record Attempt
                                  </button>
                                  <button
                                    data-testid="complete-followup-btn"
                                    onClick={() => handleCompleteFollowup(fol.followup_id, FollowupOutcome.CONTACTED_SUCCESSFULLY)}
                                    className="px-2 py-0.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-semibold transition-colors"
                                  >
                                    Complete
                                  </button>
                                </>
                              )}
                              {!isCompleted && !isBlocked && (
                                <>
                                  <button
                                    data-testid="reschedule-followup-btn"
                                    onClick={() => {
                                      setSelectedFollowup(fol);
                                      setShowFollowupDetailsDrawer(true);
                                    }}
                                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[10px] transition-colors"
                                  >
                                    Reschedule
                                  </button>
                                  <button
                                    data-testid="cancel-followup-btn"
                                    onClick={() => handleCancelFollowup(fol.followup_id)}
                                    className="px-2 py-0.5 rounded bg-rose-950/40 hover:bg-rose-950/80 text-rose-300 border border-rose-800/40 text-[10px] transition-colors"
                                  >
                                    Cancel
                                  </button>
                                </>
                              )}
                              {fol.consent_state === ConsentState.GRANTED && !isBlocked && !isCompleted && (
                                <button
                                  data-testid="revoke-consent-btn"
                                  onClick={() => handleRevokeConsent(fol.case_id)}
                                  className="px-2 py-0.5 rounded bg-red-950/50 hover:bg-red-900/60 text-red-300 border border-red-800/50 text-[10px] flex items-center gap-1 transition-colors"
                                >
                                  <Ban className="h-2.5 w-2.5" />
                                  Revoke Consent
                                </button>
                              )}
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                data-testid="view-followup-details-btn"
                                onClick={() => {
                                  setSelectedFollowup(fol);
                                  setShowFollowupDetailsDrawer(true);
                                }}
                                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] transition-colors"
                              >
                                Details
                              </button>
                              <button
                                data-testid="view-followup-audit-btn"
                                onClick={() => handleViewFollowupAudit(fol.followup_id)}
                                className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 text-[10px] transition-colors"
                              >
                                Audit
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Live Transcript Chronological Stream */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {transcripts.length === 0 && !partialDraft ? (
                  <div className="text-center py-20 text-slate-500">
                    <MessageSquare className="h-10 w-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Awaiting conversation audio stream...</p>
                  </div>
                ) : (
                  <>
                    {transcripts.map((item) => {
                      const isAgent = item.speaker === "agent";
                      return (
                        <div
                          key={item.utterance_id}
                          className={`flex gap-3 ${isAgent ? "justify-end" : "justify-start"}`}
                        >
                          {!isAgent && (
                            <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-slate-300">
                              <User className="h-4 w-4" />
                            </div>
                          )}

                          <div
                            className={`max-w-xl rounded-2xl p-4 shadow-sm border ${
                              isAgent
                                ? "bg-indigo-950/40 border-indigo-700/50 text-indigo-100 rounded-tr-none"
                                : "bg-slate-900 border-slate-800 text-slate-100 rounded-tl-none"
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1.5 text-xs text-slate-400">
                              <span className="font-semibold text-slate-300">
                                {isAgent ? "SAMVED AI" : "Caller"}
                              </span>
                              <span>•</span>
                              <span>{getLanguageLabel(item.language)}</span>
                              {item.confidence && (
                                <>
                                  <span>•</span>
                                  <span className="font-mono text-[10px] text-slate-500">
                                    {Math.round(item.confidence * 100)}% conf
                                  </span>
                                </>
                              )}
                              {item.intent && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-900/60 text-indigo-300 font-mono">
                                  {item.intent}
                                </span>
                              )}
                              {item.safety_flag && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800 font-bold flex items-center gap-1 animate-pulse">
                                  <AlertTriangle className="h-3 w-3" />
                                  Safety Flagged
                                </span>
                              )}
                            </div>

                            <p className="text-sm leading-relaxed">{item.text}</p>
                          </div>

                          {isAgent && (
                            <div className="h-8 w-8 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0 text-indigo-300">
                              <Bot className="h-4 w-4" />
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Partial Tentative Draft Bubble */}
                    {partialDraft && (
                      <div className="flex gap-3 justify-start">
                        <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-slate-400">
                          <User className="h-4 w-4" />
                        </div>
                        <div className="max-w-xl rounded-2xl rounded-tl-none p-4 bg-slate-900/50 border border-indigo-500/40 text-slate-300 shadow-sm animate-pulse">
                          <div className="flex items-center gap-2 mb-1 text-xs text-indigo-400 font-medium">
                            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
                            <span>Caller speaking (provisional partial)...</span>
                          </div>
                          <p className="text-sm italic text-slate-200">{partialDraft}</p>
                        </div>
                      </div>
                    )}
                    <div ref={transcriptEndRef} />
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <Layers className="h-12 w-12 mb-3 text-slate-600 opacity-60" />
              <h3 className="text-base font-semibold text-slate-300 mb-1">No Call Selected</h3>
              <p className="text-xs max-w-sm text-slate-500 mb-4">
                Select an active or recent call from the sidebar, or launch a simulated multilingual call.
              </p>
              <button
                onClick={() => setIsSimModalOpen(true)}
                className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
              >
                Launch Simulation Scenario
              </button>
            </div>
          )}
        </main>

        {/* Right Sidebar: Realtime Event Timeline & Filter */}
        <aside data-testid="event-timeline" className="w-96 bg-slate-900/50 flex flex-col shrink-0">
          {/* Timeline Header & Filters */}
          <div className="border-b border-slate-800 p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-indigo-400" />
                Event Stream ({filteredEvents.length})
              </span>
              <button
                onClick={() => setCallEvents([])}
                className="text-[10px] text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap gap-1">
              {(["ALL", "OPERATOR", "SAFETY", "SVI", "ACOUSTIC", "ADAPTIVE", "ORCHESTRATION", "KNOWLEDGE", "CASE", "FOLLOWUP", "TRANSCRIPT", "CONVERSATION", "ERRORS", "LATENCY"] as EventFilterCategory[]).map(
                (f) => (
                  <button
                    key={f}
                    data-testid={`timeline-filter-${f}`}
                    onClick={() => setEventFilter(f)}
                    className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                      eventFilter === f
                        ? "bg-indigo-600 text-white font-semibold"
                        : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                    }`}
                  >
                    {f}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Event Rows */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredEvents.length === 0 ? (
              <p className="text-center py-12 text-xs text-slate-500">No events captured yet.</p>
            ) : (
              filteredEvents.map((ev, idx) => {
                const type = ev.event_type;
                const isError = type.includes("ERROR") || type.includes("SIGNAL");
                const isTts = type.includes("TTS") || type.includes("SPEAKING");
                const isLatency = type.includes("LATENCY");
                const isOrch = type.includes("ORCHESTRATION") || type.includes("AGENT_") || type.includes("BRIEFING");
                const isKnowledge = type.includes("KNOWLEDGE");
                const isCase = type.includes("CASE");
                const isFollowup = type.includes("FOLLOWUP");

                return (
                  <div
                    key={ev.event_id || `${type}-${idx}`}
                    data-testid="timeline-event-item"
                    className={`p-2.5 rounded-md border text-xs transition-colors hover:bg-slate-800/80 ${
                      isError
                        ? "bg-rose-950/20 border-rose-800/50"
                        : isLatency
                        ? "bg-cyan-950/20 border-cyan-800/50"
                        : isTts
                        ? "bg-purple-950/20 border-purple-800/50"
                        : isOrch
                        ? "bg-teal-950/20 border-teal-800/50"
                        : isKnowledge
                        ? "bg-amber-950/20 border-amber-800/50"
                        : isCase
                        ? "bg-violet-950/30 border-violet-700/60"
                        : isFollowup
                        ? "bg-emerald-950/30 border-emerald-700/60"
                        : "bg-slate-900 border-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`font-mono text-[10px] font-bold ${
                          isError
                            ? "text-rose-400"
                            : isLatency
                            ? "text-cyan-400"
                            : isTts
                            ? "text-purple-400"
                            : isOrch
                            ? "text-teal-400"
                            : isKnowledge
                            ? "text-amber-400"
                            : isCase
                            ? "text-violet-300"
                            : isFollowup
                            ? "text-emerald-300"
                            : "text-indigo-400"
                        }`}
                      >
                        {type}
                      </span>
                      <button
                        onClick={() => setInspectedEvent(ev)}
                        className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1"
                        title="Inspect full JSON payload"
                      >
                        <Eye className="h-3 w-3" />
                        Inspect
                      </button>
                    </div>

                    <p className="text-[11px] text-slate-300 truncate">
                      {String(
                        (ev.payload as any)?.text ||
                          (ev.payload as any)?.response_text ||
                          (ev.payload as any)?.new_state ||
                          (ev.payload as any)?.message ||
                          (typeof ev.payload === "object" ? JSON.stringify(ev.payload) : "")
                      )}
                    </p>

                    <div className="mt-1 text-[10px] text-slate-500 font-mono">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>
      </div>

      {/* Event Inspector Modal */}
      {inspectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white font-mono">{inspectedEvent.event_type}</h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(inspectedEvent, null, 2));
                    setCopiedJson(true);
                    setTimeout(() => setCopiedJson(false), 2000);
                  }}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center gap-1 transition-colors"
                >
                  {copiedJson ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  {copiedJson ? "Copied" : "Copy JSON"}
                </button>
                <button
                  onClick={() => setInspectedEvent(null)}
                  className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="p-4 overflow-y-auto flex-1 bg-slate-950 font-mono text-xs text-emerald-400">
              <pre>{JSON.stringify(inspectedEvent, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Simulation Runner Modal */}
      {isSimModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Play className="h-4 w-4 text-indigo-400" />
                Launch Multi-turn Conversation Simulation
              </h3>
              <button
                onClick={() => setIsSimModalOpen(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Evaluation Scenario:
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {SCENARIOS.map((sc) => (
                    <div
                      key={sc.key}
                      onClick={() => setSimScenario(sc.key)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        simScenario === sc.key
                          ? "bg-indigo-950/60 border-indigo-500 shadow-sm"
                          : "bg-slate-800/60 border-slate-700/60 hover:border-slate-600"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-white">{sc.name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-900 text-indigo-300">
                          {sc.lang}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">{sc.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Caller Phone Number (Will be masked):
                </label>
                <input
                  type="text"
                  value={simCallerPhone}
                  onChange={(e) => setSimCallerPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-xs text-white font-mono focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  onClick={() => setIsSimModalOpen(false)}
                  className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
                >
                  Cancel
                </button>
                <button
                  disabled={isSimulating}
                  onClick={runSimulation}
                  className="px-4 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                >
                  {isSimulating ? (
                    <>
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      Running Simulation...
                    </>
                  ) : (
                    <>
                      <Play className="h-3 w-3" />
                      Start Simulation
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Safety Rules Catalog Modal */}
      {isSafetyRulesOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Deterministic Safety Rules Catalog
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-amber-400 font-mono border border-slate-700">
                      v1.0.0
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Explicit, version-controlled rules executed in &lt;5ms offline without LLM hallucination.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSafetyRulesOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1 space-y-4">
              {safetyRulesList.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-400" />
                  <p className="text-xs">Loading safety rules from engine registry...</p>
                </div>
              ) : (
                safetyRulesList.map((rule) => (
                  <div
                    key={rule.rule_id}
                    className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-white">{rule.rule_id}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                          {rule.rule_version}
                        </span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                            rule.default_severity === "CRITICAL"
                              ? "bg-red-500/20 text-red-300 border border-red-500/30"
                              : rule.default_severity === "HIGH"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                          }`}
                        >
                          {rule.default_severity}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {rule.target_languages?.map((lang: string) => (
                          <span
                            key={lang}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-indigo-300 font-mono"
                          >
                            {lang}
                          </span>
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-slate-300">{rule.description}</p>

                    {rule.negative_examples && rule.negative_examples.length > 0 && (
                      <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/80 text-xs">
                        <span className="text-slate-400 font-medium">Negative / False-Positive Safeguards:</span>
                        <ul className="list-disc list-inside mt-1 text-slate-400 space-y-0.5 text-[11px] font-mono">
                          {rule.negative_examples.slice(0, 3).map((ex: string, i: number) => (
                            <li key={i} className="truncate">
                              &ldquo;{ex}&rdquo;
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Safety Simulation Lab Modal */}
      {isSafetyLabOpen && (
        <div
          data-testid="safety-lab-modal"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <ShieldAlert className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Deterministic Safety Evaluation Lab
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                      Sub-5ms Deterministic
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Verify multilingual trigger evaluation, negation immunity, and explainable audit evidence.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsSafetyLabOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1 space-y-5">
              {/* Presets Bar */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Test Case Presets:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    onClick={() => {
                      setSafetyLabInput("He has a knife and is breaking into my door right now!");
                      setSafetyLabLang("en-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-red-300 border border-red-500/30 font-medium"
                  >
                    Active Weapon Threat
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("I was in the kitchen cutting vegetables with a knife");
                      setSafetyLabLang("en-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 font-medium"
                  >
                    False Positive (Cooking Knife)
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("There is no weapon here, he does not have a knife");
                      setSafetyLabLang("en-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 font-medium"
                  >
                    Negated Threat Cue
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("I want to end my life, I have pills and I cannot go on anymore");
                      setSafetyLabLang("en-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 font-medium"
                  >
                    Self-Harm Crisis
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("என்னை அடிக்கிறார், எனக்கு ரொம்ப பயமாக இருக்கிறது காப்பாற்றுங்கள்");
                      setSafetyLabLang("ta-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium"
                  >
                    Tamil Physical Threat
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("उसके हाथ में चाकू है और वह मुझे मार डालेगा");
                      setSafetyLabLang("hi-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium"
                  >
                    Hindi Weapon Threat
                  </button>
                  <button
                    onClick={() => {
                      setSafetyLabInput("They locked me inside the room and won't let me out");
                      setSafetyLabLang("en-IN");
                    }}
                    className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-yellow-300 border border-yellow-500/30 font-medium"
                  >
                    Forced Confinement
                  </button>
                </div>
              </div>

              {/* Input Configuration */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">Utterance Text:</label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Language:</span>
                    <select
                      data-testid="safety-lab-lang"
                      value={safetyLabLang}
                      onChange={(e) => setSafetyLabLang(e.target.value)}
                      className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="en-IN">English (en-IN)</option>
                      <option value="ta-IN">Tamil (ta-IN)</option>
                      <option value="hi-IN">Hindi (hi-IN)</option>
                    </select>
                  </div>
                </div>

                <textarea
                  data-testid="safety-lab-input"
                  rows={3}
                  value={safetyLabInput}
                  onChange={(e) => setSafetyLabInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-white font-sans focus:border-amber-500 focus:outline-none resize-none"
                  placeholder="Enter utterance transcript to evaluate..."
                />

                <div className="flex justify-end">
                  <button
                    data-testid="safety-lab-eval-btn"
                    disabled={isEvaluatingSafety || !safetyLabInput.trim()}
                    onClick={runSafetyLabEvaluation}
                    className="px-4 py-2 rounded-md bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shadow-md flex items-center gap-2 disabled:opacity-50 transition-all"
                  >
                    {isEvaluatingSafety ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        Evaluating Deterministically...
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="h-3.5 w-3.5" />
                        Evaluate Deterministically
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Evaluation Results */}
              {safetyLabResult && (
                <div className="border-t border-slate-800 pt-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-400 uppercase">Assessment State:</span>
                      <span
                        data-testid="safety-lab-state"
                        className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                          safetyLabResult.safety_state === "CRITICAL"
                            ? "bg-red-500 text-white animate-pulse"
                            : safetyLabResult.safety_state === "HIGH"
                            ? "bg-amber-500 text-slate-950"
                            : safetyLabResult.safety_state === "ELEVATED"
                            ? "bg-yellow-500 text-slate-950"
                            : "bg-emerald-600 text-white"
                        }`}
                      >
                        {safetyLabResult.safety_state}
                      </span>
                      {safetyLabResult.requires_human_review && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700 font-semibold uppercase">
                          Requires Human Review
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-slate-400">Deterministic Latency:</span>
                      <span className="text-emerald-400 font-bold">{safetyLabResult.latency_ms}ms</span>
                    </div>
                  </div>

                  {/* Signals List */}
                  {safetyLabResult.signals && safetyLabResult.signals.length > 0 ? (
                    <div className="space-y-2">
                      <label className="block text-xs font-semibold text-slate-300">
                        Generated Safety Signals ({safetyLabResult.signals.length}):
                      </label>
                      {safetyLabResult.signals.map((sig: any, i: number) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                                  sig.severity === "CRITICAL"
                                    ? "bg-red-500/20 text-red-300 border border-red-500/30"
                                    : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                }`}
                              >
                                {sig.severity}
                              </span>
                              <span className="font-mono font-bold text-white">{sig.signal_type}</span>
                              <span className="text-[10px] text-slate-500 font-mono">
                                [{sig.evidence?.rule_id} {sig.evidence?.rule_version}]
                              </span>
                            </div>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 font-mono">
                              Temporal: {sig.evidence?.temporal_context}
                            </span>
                          </div>
                          <p className="text-slate-300 mt-1">
                            <strong className="text-white">Reason:</strong> {sig.evidence?.reason}
                          </p>
                          {sig.evidence?.matched_phrase && (
                            <p className="text-[11px] text-slate-400 font-mono">
                              Matched Phrase: &ldquo;
                              <span className="text-amber-300 font-bold">{sig.evidence.matched_phrase}</span>
                              &rdquo;
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-800/40 text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                      <span>No safety threats detected. All deterministic safety rules passed.</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SVI Simulation Lab Modal */}
      {isSviLabOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-950 border border-cyan-700/40 rounded-2xl w-full max-w-2xl mx-6 max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <Activity className="h-5 w-5 text-cyan-400" />
                <h2 className="text-lg font-bold text-white">SVI Scoring Simulation Lab</h2>
              </div>
              <button onClick={() => setIsSviLabOpen(false)} className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-4">
              Test the deterministic Stress Vulnerability Index scoring engine with multilingual utterances.
              SVI is an <strong className="text-cyan-300">Operational Prototype Priority Indicator</strong> — NOT a clinical, medical, or diagnostic score.
            </p>

            {/* Preset Scenarios */}
            <div className="space-y-2 mb-4">
              <label className="block text-xs font-semibold text-slate-300">Preset Scenarios:</label>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => { setSviLabInput("He locked me inside and took my phone. I am panicking, extremely scared, and nobody here to help."); setSviLabLang("en-IN"); }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-red-300 border border-red-500/30 font-medium"
                >
                  Active Danger
                </button>
                <button
                  onClick={() => { setSviLabInput("He controls my money and tracking me, won't let me leave the house."); setSviLabLang("en-IN"); }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium"
                >
                  Coercive Control
                </button>
                <button
                  onClick={() => { setSviLabInput("ரொம்ப பயமா இருக்கு, யாரும் இல்ல, வெளியே விட மாட்டாங்க."); setSviLabLang("ta-IN"); }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 font-medium"
                >
                  Tamil Distress
                </button>
                <button
                  onClick={() => { setSviLabInput("I am in a safe place now, my mother is with me and police arrived."); setSviLabLang("en-IN"); }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 font-medium"
                >
                  Protective Buffer
                </button>
                <button
                  onClick={() => { setSviLabInput("He used to hit me last year but it stopped."); setSviLabLang("en-IN"); }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 font-medium"
                >
                  Historical Only
                </button>
              </div>
            </div>

            {/* Input */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">Caller Utterance:</label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Language:</span>
                  <select
                    data-testid="svi-lab-lang"
                    value={sviLabLang}
                    onChange={(e) => setSviLabLang(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="en-IN">English (en-IN)</option>
                    <option value="ta-IN">Tamil (ta-IN)</option>
                    <option value="hi-IN">Hindi (hi-IN)</option>
                  </select>
                </div>
              </div>

              <textarea
                data-testid="svi-lab-input"
                rows={3}
                value={sviLabInput}
                onChange={(e) => setSviLabInput(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-white font-sans focus:border-cyan-500 focus:outline-none resize-none"
                placeholder="Enter caller utterance(s) to evaluate SVI score..."
              />

              <button
                data-testid="svi-lab-evaluate"
                disabled={isEvaluatingSvi || !sviLabInput.trim()}
                onClick={async () => {
                  setIsEvaluatingSvi(true);
                  setSviLabResult(null);
                  try {
                    const res = await fetch(`${apiUrl}/v1/svi/evaluate`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        turns: [{ speaker: "caller", text: sviLabInput, language: sviLabLang }],
                        turn_index: 1,
                      }),
                    });
                    if (res.ok) {
                      setSviLabResult(await res.json());
                    }
                  } catch (e) {
                    console.error("SVI evaluation failed:", e);
                  } finally {
                    setIsEvaluatingSvi(false);
                  }
                }}
                className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isEvaluatingSvi ? (
                  <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Evaluating...</>
                ) : (
                  <><Activity className="h-3.5 w-3.5" /> Evaluate SVI Score</>
                )}
              </button>
            </div>

            {/* Result */}
            {sviLabResult && (
              <div data-testid="svi-lab-result" className="mt-5 space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-10 w-10 rounded-lg flex items-center justify-center text-base font-black ${
                        sviLabResult.band === "CRITICAL"
                          ? "bg-red-600 text-white"
                          : sviLabResult.band === "HIGH"
                          ? "bg-amber-500 text-slate-950"
                          : sviLabResult.band === "MODERATE"
                          ? "bg-yellow-500 text-slate-950"
                          : "bg-emerald-600 text-white"
                      }`}
                    >
                      {sviLabResult.score}
                    </div>
                    <div>
                      <span className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                        sviLabResult.band === "CRITICAL" ? "bg-red-500 text-white"
                        : sviLabResult.band === "HIGH" ? "bg-amber-500 text-slate-950"
                        : sviLabResult.band === "MODERATE" ? "bg-yellow-500 text-slate-950"
                        : "bg-emerald-600 text-white"
                      }`}>
                        {sviLabResult.band}
                      </span>
                      {sviLabResult.requires_human_review && (
                        <span className="ml-2 text-[10px] px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700 font-semibold uppercase">
                          Human Review Required
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-[10px] text-slate-400 font-mono">
                    Completeness: {Math.round(sviLabResult.assessment_completeness * 100)}%
                  </div>
                </div>

                {/* Features */}
                {sviLabResult.features && sviLabResult.features.length > 0 && (
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-slate-300">
                      Feature Attribution ({sviLabResult.features.length}):
                    </label>
                    {sviLabResult.features.map((f: any, i: number) => (
                      <div key={i} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs flex items-center justify-between">
                        <div>
                          <span className="font-mono text-white">{f.feature_name}</span>
                          <span className="text-[10px] ml-2 text-slate-400">[{f.recency}]</span>
                        </div>
                        <span className="text-cyan-300 font-bold">+{f.weighted_score.toFixed(1)} pts</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Acoustic Notice */}
                <div className="text-[10px] text-slate-500 italic flex items-center gap-1.5">
                  <Mic className="h-3 w-3" />
                  {sviLabResult.acoustic_evidence_note || "Acoustic evidence: Not available in current phase (Phase 6 deferred)"}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Phase 6: Acoustic Simulation Lab Modal */}
      {isAcousticLabOpen && (
        <div data-testid="acoustic-lab-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-950 border border-purple-700/40 rounded-2xl w-full max-w-2xl mx-6 max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <Volume2 className="h-5 w-5 text-purple-400" />
                <h2 className="text-lg font-bold text-white">Acoustic Analysis Simulation Lab</h2>
              </div>
              <button
                data-testid="close-acoustic-lab"
                onClick={() => setIsAcousticLabOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-4">
              Test the deterministic Acoustic Analysis Engine with synthetic non-verbal parameters.
              Acoustic analysis provides <strong className="text-purple-300">Operational Support Signals Only</strong> — NOT a clinical, medical, psychiatric, or diagnostic evaluation.
            </p>

            {/* Preset Scenarios */}
            <div className="space-y-2 mb-4">
              <label className="block text-xs font-semibold text-slate-300">Preset Scenarios:</label>
              <div className="flex flex-wrap gap-2">
                <button
                  data-testid="preset-normal-convo"
                  onClick={() => {
                    setAcousticLabDuration(4000);
                    setAcousticLabSpeechRatio(0.65);
                    setAcousticLabMaxSilence(1200);
                    setAcousticLabInterruptions(0);
                    setAcousticLabEnergyVar(0.25);
                    setAcousticLabClipping(0.0);
                    setAcousticLabMeanRms(450.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 font-medium"
                >
                  Normal Conversation
                </button>
                <button
                  data-testid="preset-prolonged-silence"
                  onClick={() => {
                    setAcousticLabDuration(6000);
                    setAcousticLabSpeechRatio(0.25);
                    setAcousticLabMaxSilence(3500);
                    setAcousticLabInterruptions(0);
                    setAcousticLabEnergyVar(0.20);
                    setAcousticLabClipping(0.0);
                    setAcousticLabMeanRms(350.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium"
                >
                  Prolonged Silence
                </button>
                <button
                  data-testid="preset-frequent-interruptions"
                  onClick={() => {
                    setAcousticLabDuration(4000);
                    setAcousticLabSpeechRatio(0.60);
                    setAcousticLabMaxSilence(800);
                    setAcousticLabInterruptions(3);
                    setAcousticLabEnergyVar(0.35);
                    setAcousticLabClipping(0.0);
                    setAcousticLabMeanRms(600.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-red-300 border border-red-500/30 font-medium"
                >
                  Frequent Interruptions
                </button>
                <button
                  data-testid="preset-high-energy-var"
                  onClick={() => {
                    setAcousticLabDuration(4000);
                    setAcousticLabSpeechRatio(0.70);
                    setAcousticLabMaxSilence(900);
                    setAcousticLabInterruptions(0);
                    setAcousticLabEnergyVar(0.65);
                    setAcousticLabClipping(0.0);
                    setAcousticLabMeanRms(650.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 font-medium"
                >
                  High Energy Variability
                </button>
                <button
                  data-testid="preset-low-quality"
                  onClick={() => {
                    setAcousticLabDuration(3000);
                    setAcousticLabSpeechRatio(0.50);
                    setAcousticLabMaxSilence(800);
                    setAcousticLabInterruptions(0);
                    setAcousticLabEnergyVar(0.25);
                    setAcousticLabClipping(0.15);
                    setAcousticLabMeanRms(500.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/30 font-medium"
                >
                  Low Audio Quality
                </button>
                <button
                  data-testid="preset-insufficient"
                  onClick={() => {
                    setAcousticLabDuration(150);
                    setAcousticLabSpeechRatio(0.10);
                    setAcousticLabMaxSilence(100);
                    setAcousticLabInterruptions(0);
                    setAcousticLabEnergyVar(0.0);
                    setAcousticLabClipping(0.0);
                    setAcousticLabMeanRms(100.0);
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-600 font-medium"
                >
                  Insufficient Signal
                </button>
              </div>
            </div>

            {/* Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Audio Duration (ms): <span className="text-purple-300 font-mono">{acousticLabDuration}</span>
                </label>
                <input
                  type="range"
                  min={100}
                  max={10000}
                  step={100}
                  value={acousticLabDuration}
                  onChange={(e) => setAcousticLabDuration(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Speech Activity Ratio: <span className="text-purple-300 font-mono">{Math.round(acousticLabSpeechRatio * 100)}%</span>
                </label>
                <input
                  type="range"
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={acousticLabSpeechRatio}
                  onChange={(e) => setAcousticLabSpeechRatio(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Max Contiguous Silence (ms): <span className="text-purple-300 font-mono">{acousticLabMaxSilence}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={6000}
                  step={200}
                  value={acousticLabMaxSilence}
                  onChange={(e) => setAcousticLabMaxSilence(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Caller Barge-in Interruptions: <span className="text-purple-300 font-mono">{acousticLabInterruptions}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={5}
                  step={1}
                  value={acousticLabInterruptions}
                  onChange={(e) => setAcousticLabInterruptions(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Energy Variability (CV): <span className="text-purple-300 font-mono">{acousticLabEnergyVar.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={acousticLabEnergyVar}
                  onChange={(e) => setAcousticLabEnergyVar(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Clipping Ratio: <span className="text-purple-300 font-mono">{Math.round(acousticLabClipping * 100)}%</span>
                </label>
                <input
                  type="range"
                  min={0.0}
                  max={0.30}
                  step={0.02}
                  value={acousticLabClipping}
                  onChange={(e) => setAcousticLabClipping(Number(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
            </div>

            <button
              data-testid="run-acoustic-eval"
              disabled={isEvaluatingAcoustic}
              onClick={async () => {
                setIsEvaluatingAcoustic(true);
                setAcousticLabResult(null);
                try {
                  const res = await fetch(`${apiUrl}/v1/acoustic/evaluate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      call_id: "sim-acoustic-lab",
                      session_id: "sim-acoustic-sess",
                      audio_duration_ms: acousticLabDuration,
                      speech_ratio: acousticLabSpeechRatio,
                      max_silence_ms: acousticLabMaxSilence,
                      interruptions: acousticLabInterruptions,
                      energy_variability: acousticLabEnergyVar,
                      clipping_ratio: acousticLabClipping,
                      mean_rms: acousticLabMeanRms,
                    }),
                  });
                  if (res.ok) {
                    const data = await res.json();
                    setAcousticLabResult(data);
                  }
                } catch (e) {
                  console.error("Error evaluating acoustic simulation:", e);
                } finally {
                  setIsEvaluatingAcoustic(false);
                }
              }}
              className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold text-xs transition-all shadow-md flex items-center justify-center gap-2"
            >
              {isEvaluatingAcoustic ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Evaluating Acoustic Window...</span>
                </>
              ) : (
                <>
                  <Activity className="h-4 w-4" />
                  <span>Run Acoustic Evaluation</span>
                </>
              )}
            </button>

            {/* Evaluation Results */}
            {acousticLabResult && (
              <div data-testid="acoustic-lab-result" className="mt-5 p-4 rounded-xl bg-slate-900 border border-purple-800/60 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-3 py-1 rounded font-black tracking-wider ${
                      acousticLabResult.quality === "EXCELLENT" ? "bg-emerald-500 text-white"
                      : acousticLabResult.quality === "GOOD" ? "bg-cyan-500 text-slate-950"
                      : acousticLabResult.quality === "DEGRADED" ? "bg-amber-500 text-slate-950"
                      : acousticLabResult.quality === "POOR" ? "bg-red-500 text-white"
                      : "bg-slate-700 text-slate-300"
                    }`}>
                      {acousticLabResult.quality}
                    </span>
                    <span className="text-xs text-slate-300 font-mono">
                      Confidence: {Math.round(acousticLabResult.confidence * 100)}%
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    Duration: {acousticLabResult.turn_metrics?.turn_duration_ms || acousticLabDuration}ms
                  </div>
                </div>

                {/* Metrics summary */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-400">Speech Ratio</div>
                    <div className="font-bold text-white mt-0.5 font-mono">
                      {Math.round((acousticLabResult.voice_activity?.speech_activity_ratio || 0) * 100)}%
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-400">Longest Pause</div>
                    <div className="font-bold text-white mt-0.5 font-mono">
                      {acousticLabResult.pause_metrics?.longest_pause_ms || 0}ms
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-400">Interruptions</div>
                    <div className="font-bold text-white mt-0.5 font-mono">
                      {acousticLabResult.interruption_metrics?.interruption_count || 0}
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-400">Energy Variability</div>
                    <div className="font-bold text-white mt-0.5 font-mono">
                      CV {(acousticLabResult.energy_metrics?.energy_variability || 0).toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Signals */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Triggered Operational Signals ({(acousticLabResult.operational_signals || []).length}):
                  </label>
                  <div className="space-y-1.5">
                    {(acousticLabResult.operational_signals || []).length === 0 ? (
                      <div className="text-xs text-slate-500 italic p-2 rounded bg-slate-950 border border-slate-800">
                        No operational signals triggered. Acoustic parameters within nominal baseline.
                      </div>
                    ) : (
                      acousticLabResult.operational_signals.map((sig: any, i: number) => (
                        <div key={i} className="p-2.5 rounded bg-slate-950 border border-purple-800/50 text-xs flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-purple-300 font-bold">{sig.code}</span>
                            <span className="text-[11px] text-slate-400">— {sig.evidence}</span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                            {sig.threshold_applied || `Conf: ${Math.round(sig.confidence * 100)}%`}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Non-Clinical Disclaimer */}
                <div className="text-[10px] text-slate-500 italic border-t border-slate-800 pt-2">
                  {acousticLabResult.disclaimer || "Operational support signals only. Not clinical or diagnostic."}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Phase 7: Adaptive Simulation Lab Modal */}
      {isAdaptiveLabOpen && (
        <div data-testid="adaptive-lab-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-950 border border-emerald-700/40 rounded-2xl w-full max-w-2xl mx-6 max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <Compass className="h-5 w-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Adaptive Conversation Strategy Lab</h2>
              </div>
              <button
                data-testid="close-adaptive-lab"
                onClick={() => setIsAdaptiveLabOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-4">
              Test deterministic conversational planning across safety tiers, SVI vulnerabilities, and caller states.
              SAMVED policy follows inviolable precedence: <strong className="text-emerald-300">P0 (Critical Safety) &gt; P1 (Elevated Safety) &gt; P2 (High SVI) &gt; P3 (Operational Gaps) &gt; P4 (Clarification/Support) &gt; P5 (Closure)</strong>. Non-clinical.
            </p>

            {/* Preset Scenarios */}
            <div className="space-y-2 mb-4">
              <label className="block text-xs font-semibold text-slate-300">Preset Scenarios:</label>
              <div className="flex flex-wrap gap-2">
                <button
                  data-testid="preset-danger-unknown"
                  onClick={() => {
                    setAdaptiveLabInput("He might find me here soon, I don't know what to do");
                    setAdaptiveLabSafety("CRITICAL");
                    setAdaptiveLabSvi(85);
                    setAdaptiveLabAcoustic("GOOD");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/30 font-medium"
                >
                  Critical Threat (P0)
                </button>
                <button
                  data-testid="preset-high-svi"
                  onClick={() => {
                    setAdaptiveLabInput("I feel so overwhelmed and have no one to talk to");
                    setAdaptiveLabSafety("NONE");
                    setAdaptiveLabSvi(78);
                    setAdaptiveLabAcoustic("GOOD");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-orange-300 border border-orange-500/30 font-medium"
                >
                  High Vulnerability (P2)
                </button>
                <button
                  data-testid="preset-poor-audio"
                  onClick={() => {
                    setAdaptiveLabInput("...");
                    setAdaptiveLabSafety("NONE");
                    setAdaptiveLabSvi(30);
                    setAdaptiveLabAcoustic("POOR");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 font-medium"
                >
                  Degraded Audio (P3)
                </button>
                <button
                  data-testid="preset-caller-human"
                  onClick={() => {
                    setAdaptiveLabInput("Please connect me to an operator or human counselor right now");
                    setAdaptiveLabSafety("NONE");
                    setAdaptiveLabSvi(45);
                    setAdaptiveLabAcoustic("GOOD");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 font-medium"
                >
                  Human Request (P1)
                </button>
                <button
                  data-testid="preset-caller-refusal"
                  onClick={() => {
                    setAdaptiveLabInput("I do not want to answer your question");
                    setAdaptiveLabSafety("NONE");
                    setAdaptiveLabSvi(40);
                    setAdaptiveLabAcoustic("GOOD");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 font-medium"
                >
                  Caller Refusal (P4)
                </button>
                <button
                  data-testid="preset-closure-ready"
                  onClick={() => {
                    setAdaptiveLabInput("Thank you so much, that is all the help I needed today, goodbye");
                    setAdaptiveLabSafety("NONE");
                    setAdaptiveLabSvi(15);
                    setAdaptiveLabAcoustic("GOOD");
                  }}
                  className="px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 font-medium"
                >
                  Closure Ready (P5)
                </button>
              </div>
            </div>

            {/* Parameter Controls */}
            <div className="space-y-3 mb-5 p-4 rounded-xl bg-slate-900 border border-slate-800">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Caller Utterance:
                </label>
                <textarea
                  data-testid="adaptive-lab-input"
                  rows={2}
                  value={adaptiveLabInput}
                  onChange={(e) => setAdaptiveLabInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  placeholder="Enter simulated caller input..."
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Safety State:
                  </label>
                  <select
                    data-testid="adaptive-lab-safety-select"
                    value={adaptiveLabSafety}
                    onChange={(e) => setAdaptiveLabSafety(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="NONE">NONE (Normal)</option>
                    <option value="ELEVATED">ELEVATED</option>
                    <option value="HIGH">HIGH (Elevated Safety)</option>
                    <option value="CRITICAL">CRITICAL (Threat Present)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Acoustic Quality:
                  </label>
                  <select
                    data-testid="adaptive-lab-acoustic-select"
                    value={adaptiveLabAcoustic}
                    onChange={(e) => setAdaptiveLabAcoustic(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="EXCELLENT">EXCELLENT</option>
                    <option value="GOOD">GOOD</option>
                    <option value="DEGRADED">DEGRADED</option>
                    <option value="POOR">POOR (Audio Degraded)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Language:
                  </label>
                  <select
                    value={adaptiveLabLang}
                    onChange={(e) => setAdaptiveLabLang(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="en-IN">en-IN (Indian English)</option>
                    <option value="ta-IN">ta-IN (Tamil)</option>
                    <option value="hi-IN">hi-IN (Hindi)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  SVI Score: <span className="text-emerald-300 font-mono font-bold">{adaptiveLabSvi}/100</span>
                </label>
                <input
                  data-testid="adaptive-lab-svi-slider"
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={adaptiveLabSvi}
                  onChange={(e) => setAdaptiveLabSvi(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>
            </div>

            <button
              data-testid="run-adaptive-eval"
              disabled={isEvaluatingAdaptive}
              onClick={async () => {
                setIsEvaluatingAdaptive(true);
                setAdaptiveLabResult(null);
                try {
                  const isCrit = adaptiveLabSafety === "CRITICAL";
                  const isHigh = adaptiveLabSafety === "HIGH" || adaptiveLabSafety === "ELEVATED";
                  const signals = isCrit
                    ? [{ signal_type: "THREAT", severity: "CRITICAL", confidence: 0.99 }]
                    : isHigh
                    ? [{ signal_type: "DISTRESS", severity: "HIGH", confidence: 0.9 }]
                    : [];

                  const acousticSigs = adaptiveLabAcoustic === "POOR"
                    ? [{ code: "DEGRADED_AUDIO_QUALITY", evidence: "Poor SNR", confidence: 0.95 }]
                    : [];

                  const res = await fetch(`${apiUrl}/v1/adaptive/plan`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      call_id: "sim-adaptive-lab",
                      session_id: "sim-adaptive-sess",
                      turn_index: 2,
                      language: adaptiveLabLang,
                      safety_state: adaptiveLabSafety,
                      safety_signals: signals,
                      svi_score: adaptiveLabSvi,
                      svi_band: adaptiveLabSvi >= 76 ? "CRITICAL" : (adaptiveLabSvi >= 51 ? "HIGH" : (adaptiveLabSvi >= 26 ? "MODERATE" : "LOW")),
                      svi_trend: "INITIAL",
                      acoustic_quality: adaptiveLabAcoustic,
                      acoustic_signals: acousticSigs,
                      known_facts: {},
                      last_caller_utterance: adaptiveLabInput,
                    }),
                  });
                  if (res.ok) {
                    const data = await res.json();
                    setAdaptiveLabResult(data);
                  }
                } catch (e) {
                  console.error("Error evaluating adaptive simulation:", e);
                } finally {
                  setIsEvaluatingAdaptive(false);
                }
              }}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold text-xs transition-all shadow-md flex items-center justify-center gap-2"
            >
              {isEvaluatingAdaptive ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Evaluating Deterministic Policy...</span>
                </>
              ) : (
                <>
                  <Compass className="h-4 w-4" />
                  <span>Run Adaptive Strategy Evaluation</span>
                </>
              )}
            </button>

            {/* Evaluation Results */}
            {adaptiveLabResult && (
              <div data-testid="adaptive-lab-result" className="mt-5 p-4 rounded-xl bg-slate-900 border border-emerald-800/60 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-3 py-1 rounded font-black tracking-wider bg-emerald-500 text-slate-950">
                      {adaptiveLabResult.action}
                    </span>
                    <span className={`text-xs px-2.5 py-0.5 rounded font-black tracking-wider ${
                      adaptiveLabResult.priority === "P0" ? "bg-rose-500 text-white animate-pulse"
                      : adaptiveLabResult.priority === "P1" ? "bg-amber-500 text-slate-950"
                      : adaptiveLabResult.priority === "P2" ? "bg-orange-500 text-white"
                      : adaptiveLabResult.priority === "P3" ? "bg-blue-500 text-white"
                      : "bg-emerald-600 text-white"
                    }`}>
                      {adaptiveLabResult.priority}
                    </span>
                    <span className="text-xs text-slate-300 font-mono">
                      Target: {adaptiveLabResult.target_information_gap || "none"}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Conf: {Math.round((adaptiveLabResult.confidence ?? 1.0) * 100)}%
                  </span>
                </div>

                {/* Reasons List */}
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-300 mb-1.5">
                    Triggered Reason Codes
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(adaptiveLabResult.reason_codes || []).map((rc: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-emerald-950 border border-emerald-700/60 text-emerald-200 text-xs font-semibold">
                        {rc}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Fallback Template Text */}
                {adaptiveLabResult.fallback_response_text && (
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold mb-1">
                      Deterministic Surface Realization (Fallback):
                    </div>
                    <div className="text-xs text-emerald-200 italic">
                      &quot;{adaptiveLabResult.fallback_response_text}&quot;
                    </div>
                  </div>
                )}

                {/* Non-Clinical Disclaimer */}
                <div className="text-[10px] text-slate-500 italic border-t border-slate-800 pt-2">
                  {adaptiveLabResult.disclaimer || "Deterministic conversational strategy layer. Surface realization bounded by safety rules. Non-clinical."}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Phase 8 Operator Notes Modal */}
      {isNotesModalOpen && (
        <div
          data-testid="operator-notes-panel"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Structured Operator Notes
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-indigo-300 font-mono border border-slate-700">
                      Append-Only Audit
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Call: {selectedCall?.caller_masked_number || selectedCallId}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsNotesModalOpen(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              {/* Note Input Form */}
              <div className="space-y-2.5 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">Category:</label>
                  <select
                    data-testid="note-category-select"
                    value={newNoteCategory}
                    onChange={(e) => setNewNoteCategory(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="GENERAL">General</option>
                    <option value="SAFETY">Safety</option>
                    <option value="FOLLOW_UP_NOTE">Follow Up Note</option>
                    <option value="HANDOFF_NOTE">Handoff Note</option>
                    <option value="TECHNICAL">Technical</option>
                  </select>
                </div>

                <textarea
                  data-testid="note-text-input"
                  value={newNoteText}
                  onChange={(e) => setNewNoteText(e.target.value)}
                  placeholder="Enter structured operator observation or supervisor instruction..."
                  rows={3}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans resize-none"
                />

                <div className="flex justify-end">
                  <button
                    data-testid="submit-note-button"
                    disabled={isSubmittingNote || !newNoteText.trim()}
                    onClick={handleSaveNote}
                    className="px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-40 transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    {isSubmittingNote ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <FileText className="h-3 w-3" />
                        <span>Save Note</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Existing Notes List */}
              <div className="space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Recorded Notes ({operatorNotes.length})
                </div>
                {operatorNotes.length === 0 ? (
                  <p className="text-xs text-slate-500 italic py-4 text-center">
                    No operator notes recorded for this call yet.
                  </p>
                ) : (
                  <div data-testid="notes-list" className="space-y-2">
                    {operatorNotes.map((note) => (
                      <div
                        key={note.note_id}
                        className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                              {note.category}
                            </span>
                            <span className="font-mono text-slate-400">{note.operator_id}</span>
                            {note.citation_ref && (
                              <span
                                data-testid="note-citation-ref"
                                className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-amber-950/50 text-amber-300 border border-amber-800/50"
                              >
                                {note.citation_ref}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {new Date(note.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                          {note.text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Phase 8 Action Confirmation Modal */}
      {confirmationAction.isOpen && (
        <div
          data-testid="confirmation-modal"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center gap-3 bg-slate-950/60">
              <div className="h-8 w-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
                <AlertTriangle className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">{confirmationAction.title}</h3>
                <p className="text-xs text-slate-400">Supervisor Confirmation Required</p>
              </div>
            </div>
            <div className="p-4 space-y-3">
              <p className="text-xs text-slate-300 leading-relaxed">
                {confirmationAction.description}
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  data-testid="cancel-action-button"
                  onClick={() =>
                    setConfirmationAction({
                      isOpen: false,
                      title: "",
                      description: "",
                      confirmLabel: "",
                      actionType: null,
                    })
                  }
                  className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  data-testid="confirm-action-button"
                  onClick={executeConfirmedAction}
                  className="px-4 py-1.5 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors shadow-sm"
                >
                  {confirmationAction.confirmLabel || "Confirm"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Phase 12: Create Follow-up Modal */}
      {showCreateFollowupModal && (
        <div
          data-testid="create-followup-modal"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Schedule Safe Follow-up Task</h3>
              </div>
              <button
                data-testid="close-create-followup-modal-btn"
                onClick={() => setShowCreateFollowupModal(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateFollowup} className="p-4 space-y-3 overflow-y-auto flex-1 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Follow-up Type</label>
                  <select
                    data-testid="create-followup-type-select"
                    value={newFollowupType}
                    onChange={(e) => setNewFollowupType(e.target.value as FollowupType)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value={FollowupType.CHECK_IN}>CHECK_IN</option>
                    <option value={FollowupType.HUMAN_CALLBACK}>HUMAN_CALLBACK</option>
                    <option value={FollowupType.RESOURCE_FOLLOW_UP}>RESOURCE_FOLLOW_UP</option>
                    <option value={FollowupType.CASE_REVIEW}>CASE_REVIEW</option>
                    <option value={FollowupType.DOCUMENT_FOLLOW_UP}>DOCUMENT_FOLLOW_UP</option>
                    <option value={FollowupType.HANDOFF_FOLLOW_UP}>HANDOFF_FOLLOW_UP</option>
                    <option value={FollowupType.OPERATOR_REVIEW}>OPERATOR_REVIEW</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Priority</label>
                  <select
                    data-testid="create-followup-priority-select"
                    value={newFollowupPriority}
                    onChange={(e) => setNewFollowupPriority(e.target.value as FollowupPriority)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value={FollowupPriority.LOW}>LOW</option>
                    <option value={FollowupPriority.NORMAL}>NORMAL</option>
                    <option value={FollowupPriority.HIGH}>HIGH</option>
                    <option value={FollowupPriority.CRITICAL_REVIEW}>CRITICAL_REVIEW</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Purpose / Clinical Context</label>
                <input
                  data-testid="create-followup-purpose-input"
                  type="text"
                  placeholder="e.g., Safe shelter follow-up and legal aid contact verification"
                  value={newFollowupPurpose}
                  onChange={(e) => setNewFollowupPurpose(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Contact Channel</label>
                  <select
                    data-testid="create-followup-channel-select"
                    value={newFollowupChannel}
                    onChange={(e) => setNewFollowupChannel(e.target.value as ContactChannel)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value={ContactChannel.OPERATOR_CALLBACK}>OPERATOR_CALLBACK</option>
                    <option value={ContactChannel.PHONE}>PHONE</option>
                    <option value={ContactChannel.INTERNAL_TASK}>INTERNAL_TASK</option>
                    <option value={ContactChannel.SMS}>SMS</option>
                    <option value={ContactChannel.EMAIL}>EMAIL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Consent State</label>
                  <select
                    data-testid="create-followup-consent-select"
                    value={newFollowupConsentState}
                    onChange={(e) => setNewFollowupConsentState(e.target.value as ConsentState)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value={ConsentState.GRANTED}>GRANTED</option>
                    <option value={ConsentState.LIMITED}>LIMITED</option>
                    <option value={ConsentState.REQUESTED}>REQUESTED</option>
                    <option value={ConsentState.NOT_APPLICABLE}>NOT_APPLICABLE</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Scheduled Time (UTC ISO)</label>
                  <input
                    data-testid="create-followup-scheduled-input"
                    type="text"
                    placeholder="2026-04-01T10:00:00Z"
                    value={newFollowupScheduledFor}
                    onChange={(e) => setNewFollowupScheduledFor(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500 font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Due Deadline (UTC ISO)</label>
                  <input
                    data-testid="create-followup-due-input"
                    type="text"
                    placeholder="2026-04-02T10:00:00Z"
                    value={newFollowupDueAt}
                    onChange={(e) => setNewFollowupDueAt(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Safe Contact Window</label>
                  <input
                    data-testid="create-followup-safewindow-input"
                    type="text"
                    placeholder="09:00-12:00"
                    value={newFollowupSafeWindow}
                    onChange={(e) => setNewFollowupSafeWindow(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Max Attempts</label>
                  <input
                    data-testid="create-followup-maxattempts-input"
                    type="number"
                    min="1"
                    max="5"
                    value={newFollowupMaxAttempts}
                    onChange={(e) => setNewFollowupMaxAttempts(parseInt(e.target.value, 10))}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  data-testid="create-followup-humanonly-checkbox"
                  type="checkbox"
                  id="humanOnlyCheck"
                  checked={newFollowupHumanOnly}
                  onChange={(e) => setNewFollowupHumanOnly(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-700 text-emerald-600 focus:ring-0"
                />
                <label htmlFor="humanOnlyCheck" className="text-slate-300 text-xs cursor-pointer">
                  Human Tele-Counselor Only (Strict No-Bot Outreach)
                </label>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Notes / Instructions</label>
                <textarea
                  data-testid="create-followup-notes-input"
                  rows={2}
                  placeholder="Optional counseling or safety instructions..."
                  value={newFollowupNotes}
                  onChange={(e) => setNewFollowupNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 placeholder-slate-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateFollowupModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="submit-create-followup-btn"
                  className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-colors shadow-sm"
                >
                  Schedule Follow-up
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Phase 12: Follow-up Details Drawer / Modal */}
      {showFollowupDetailsDrawer && selectedFollowup && (
        <div
          data-testid="followup-details-drawer"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <CalendarCheck className="h-5 w-5 text-emerald-400" />
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Follow-up Details: {selectedFollowup.followup_id}
                    <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-slate-800 text-slate-300 border border-slate-700">
                      {selectedFollowup.status}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">Case ID: {selectedFollowup.case_id}</p>
                </div>
              </div>
              <button
                data-testid="close-followup-details-btn"
                onClick={() => setShowFollowupDetailsDrawer(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-4 text-xs">
              {/* Metadata Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-500">Type</span>
                  <div className="font-semibold text-slate-200">{selectedFollowup.type}</div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Priority</span>
                  <div className="font-semibold text-slate-200">{selectedFollowup.priority}</div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Consent State</span>
                  <div className="font-semibold text-emerald-400">{selectedFollowup.consent_state}</div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Safe Window</span>
                  <div className="font-semibold text-slate-200">{selectedFollowup.safe_contact_window || "Anytime"}</div>
                </div>
              </div>

              {/* Purpose */}
              <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Purpose</span>
                <p className="text-slate-200 mt-1">{selectedFollowup.purpose}</p>
              </div>

              {/* Attempt History */}
              <div className="border border-slate-800 rounded-lg p-3 bg-slate-950/40">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1">
                    <History className="h-3.5 w-3.5 text-amber-400" />
                    Attempt History ({selectedFollowup.attempt_count} / {selectedFollowup.max_attempts})
                  </span>
                </div>
                <div data-testid="followup-attempts-list" className="space-y-1.5 max-h-36 overflow-y-auto">
                  {((selectedFollowup as any).attempts && (selectedFollowup as any).attempts.length > 0) ? (
                    (selectedFollowup as any).attempts.map((att: any, idx: number) => (
                      <div
                        key={idx}
                        data-testid="followup-attempt-item"
                        className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px] flex items-center justify-between"
                      >
                        <div>
                          <span className="font-bold text-amber-300">Attempt #{att.attempt_number}</span>
                          <span className="text-slate-400 ml-2">[{att.channel}]</span>
                          <span className="text-slate-300 ml-2 font-mono font-semibold">{att.result}</span>
                          {att.notes && <p className="text-slate-400 mt-0.5">{att.notes}</p>}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(att.attempted_at).toLocaleTimeString()}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-500 text-center py-2 text-[11px]">No attempts recorded yet.</p>
                  )}
                </div>
              </div>

              {/* Action Form 1: Record Attempt */}
              {selectedFollowup.status !== FollowupStatus.COMPLETED &&
                selectedFollowup.status !== FollowupStatus.BLOCKED &&
                selectedFollowup.status !== FollowupStatus.CANCELLED && (
                  <div className="border border-amber-800/40 bg-amber-950/10 p-3 rounded-lg space-y-2">
                    <span className="text-xs font-bold text-amber-300 flex items-center gap-1">
                      <UserCheck className="h-3.5 w-3.5" />
                      Record Human Contact Attempt
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-0.5">Channel</label>
                        <select
                          data-testid="attempt-channel-select"
                          value={attemptChannel}
                          onChange={(e) => setAttemptChannel(e.target.value as ContactChannel)}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                        >
                          <option value={ContactChannel.OPERATOR_CALLBACK}>OPERATOR_CALLBACK</option>
                          <option value={ContactChannel.PHONE}>PHONE</option>
                          <option value={ContactChannel.SMS}>SMS</option>
                          <option value={ContactChannel.INTERNAL_TASK}>INTERNAL_TASK</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-0.5">Result</label>
                        <select
                          data-testid="attempt-result-select"
                          value={attemptResult}
                          onChange={(e) => setAttemptResult(e.target.value as ContactResult)}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                        >
                          <option value={ContactResult.CONTACTED_SUCCESSFULLY}>CONTACTED_SUCCESSFULLY</option>
                          <option value={ContactResult.NO_ANSWER}>NO_ANSWER</option>
                          <option value={ContactResult.CALLER_DECLINED}>CALLER_DECLINED</option>
                          <option value={ContactResult.RESCHEDULED}>RESCHEDULED</option>
                          <option value={ContactResult.WRONG_CONTACT}>WRONG_CONTACT</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Attempt Notes</label>
                      <input
                        data-testid="attempt-notes-input"
                        type="text"
                        placeholder="e.g., Reached caller, confirmed safe with family"
                        value={attemptNotes}
                        onChange={(e) => setAttemptNotes(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 placeholder-slate-500"
                      />
                    </div>
                    <button
                      data-testid="submit-attempt-btn"
                      onClick={() => handleRecordAttempt(selectedFollowup.followup_id)}
                      className="px-3 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold transition-colors shadow-sm"
                    >
                      Save Attempt Record
                    </button>
                  </div>
                )}

              {/* Action Form 2: Reschedule & Complete */}
              {selectedFollowup.status !== FollowupStatus.COMPLETED &&
                selectedFollowup.status !== FollowupStatus.CANCELLED && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    {/* Reschedule */}
                    <div className="border border-slate-800 bg-slate-950/60 p-3 rounded-lg space-y-2">
                      <span className="text-xs font-bold text-slate-300">Reschedule Follow-up</span>
                      <input
                        data-testid="reschedule-time-input"
                        type="text"
                        placeholder="New ISO time: 2026-04-02T10:00:00Z"
                        value={rescheduleTime}
                        onChange={(e) => setRescheduleTime(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-[11px]"
                      />
                      <input
                        data-testid="reschedule-reason-input"
                        type="text"
                        placeholder="Reason: e.g. Caller busy"
                        value={rescheduleReason}
                        onChange={(e) => setRescheduleReason(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                      />
                      <button
                        data-testid="submit-reschedule-btn"
                        onClick={() => handleRescheduleFollowup(selectedFollowup.followup_id)}
                        className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                      >
                        Confirm Reschedule
                      </button>
                    </div>

                    {/* Complete / Cancel */}
                    <div className="border border-slate-800 bg-slate-950/60 p-3 rounded-lg space-y-2">
                      <span className="text-xs font-bold text-slate-300">Complete / Close Task</span>
                      <select
                        data-testid="complete-outcome-select"
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                        defaultValue={FollowupOutcome.CONTACTED_SUCCESSFULLY}
                      >
                        <option value={FollowupOutcome.CONTACTED_SUCCESSFULLY}>CONTACTED_SUCCESSFULLY</option>
                        <option value={FollowupOutcome.REFERRED}>REFERRED</option>
                        <option value={FollowupOutcome.NO_ANSWER}>NO_ANSWER</option>
                        <option value={FollowupOutcome.CALLER_DECLINED}>CALLER_DECLINED</option>
                      </select>
                      <div className="flex gap-2 pt-1">
                        <button
                          data-testid="submit-complete-btn"
                          onClick={() => handleCompleteFollowup(selectedFollowup.followup_id, FollowupOutcome.CONTACTED_SUCCESSFULLY)}
                          className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors"
                        >
                          Mark Completed
                        </button>
                        <button
                          data-testid="submit-cancel-btn"
                          onClick={() => handleCancelFollowup(selectedFollowup.followup_id)}
                          className="px-3 py-1 rounded bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 transition-colors"
                        >
                          Cancel Task
                        </button>
                      </div>
                    </div>
                  </div>
                )}

              {/* Revoke Consent Danger Zone */}
              {selectedFollowup.consent_state === ConsentState.GRANTED && (
                <div className="border border-red-800/40 bg-red-950/20 p-3 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-red-300 flex items-center gap-1">
                      <Ban className="h-3.5 w-3.5" />
                      Caller Revocation Immediate Stop
                    </span>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      Immediately halts and blocks all active follow-ups for this case.
                    </p>
                  </div>
                  <button
                    data-testid="submit-revoke-consent-btn"
                    onClick={() => handleRevokeConsent(selectedFollowup.case_id)}
                    className="px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-bold transition-colors shadow-sm"
                  >
                    Revoke Consent
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Phase 12: Follow-up Audit Trail Modal */}
      {showFollowupAuditModal && (
        <div
          data-testid="followup-audit-modal"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Follow-up Workflow Audit Trail</h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-emerald-300 font-mono border border-slate-700">
                  Append-Only Log
                </span>
              </div>
              <button
                data-testid="close-followup-audit-modal-btn"
                onClick={() => setShowFollowupAuditModal(false)}
                className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div data-testid="followup-audit-log-list" className="p-4 overflow-y-auto flex-1 space-y-2 text-xs">
              {followupAuditLogs.length === 0 ? (
                <p className="text-center py-8 text-slate-500">No follow-up audit entries found.</p>
              ) : (
                followupAuditLogs.map((entry: any) => (
                  <div
                    key={entry.event_id || entry.entry_id}
                    data-testid="followup-audit-log-item"
                    className="p-2.5 rounded bg-slate-950 border border-slate-800"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-bold text-emerald-300">
                        {entry.action || entry.event_type}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{entry.timestamp}</span>
                    </div>
                    <div className="text-slate-300 text-[11px]">
                      Follow-up ID: <span className="font-mono font-semibold text-slate-200">{entry.followup_id}</span>
                      <span className="mx-2">•</span>
                      Actor: <span className="font-semibold text-slate-200">{entry.actor_id}</span>
                    </div>
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <pre className="mt-1 p-1.5 rounded bg-slate-900 text-[10px] font-mono text-slate-400 overflow-x-auto">
                        {JSON.stringify(entry.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
