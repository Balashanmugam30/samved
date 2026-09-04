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
} from "lucide-react";
import { useOperatorWebSocket } from "@/hooks/useOperatorWebSocket";
import { EventEnvelope, EventType } from "@samved/schemas";

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
    key: "interruption",
    name: "Barge-in / Caller Interruption Test",
    lang: "Barge-in",
    desc: "Caller speaks while agent is speaking. Orchestrator halts TTS and flushes outbound queue immediately.",
  },
];

type EventFilterCategory = "ALL" | "TRANSCRIPT" | "CONVERSATION" | "ERRORS" | "LATENCY";

export default function OperatorCallsPage() {
  // Call lists
  const [activeCalls, setActiveCalls] = useState<CallSummaryItem[]>([]);
  const [recentCalls, setRecentCalls] = useState<CallSummaryItem[]>([]);
  const [activeTab, setActiveTab] = useState<"ACTIVE" | "RECENT">("ACTIVE");
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);

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
        setActiveCalls(snapshotPayload.active_calls);
      }
      if (snapshotPayload.recent_calls) {
        setRecentCalls(snapshotPayload.recent_calls);
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
        setTranscripts(remoteTurns);
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

        case EventType.TURN_LATENCY:
          setLatencies({
            stt_ms: Number(payload.stt_ms || 0),
            llm_ms: Number(payload.llm_ms || 0),
            tts_ms: Number(payload.tts_ms || 0),
            total_ms: Number(payload.total_turn_ms || 0),
          });
          break;
      }
    },
  });

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

  useEffect(() => {
    fetchCalls();
    const interval = setInterval(fetchCalls, 8000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  // Handle Call Selection
  const selectCall = async (callId: string) => {
    setSelectedCallId(callId);
    setPartialDraft(null);
    subscribeCall(callId);

    // Fetch call details and transcripts via REST snapshot
    try {
      const [trRes, evRes] = await Promise.all([
        fetch(`${apiUrl}/v1/calls/${callId}/transcript`),
        fetch(`${apiUrl}/v1/calls/${callId}/events`),
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
        setTranscripts(formatted);
      } else {
        setTranscripts([]);
      }

      if (evRes.ok) {
        const evData = await evRes.json();
        setCallEvents(evData.events || []);
      } else {
        setCallEvents([]);
      }
    } catch (err) {
      console.error("Error loading call snapshot:", err);
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
      if (eventFilter === "ERRORS") {
        return type.includes("ERROR") || type.includes("SIGNAL");
      }
      if (eventFilter === "LATENCY") {
        return type.includes("LATENCY");
      }
      return true;
    });
  }, [callEvents, eventFilter]);

  // Language display helper
  const getLanguageLabel = (langCode?: string) => {
    if (!langCode) return "Unknown";
    if (langCode.includes("ta")) return "Tamil (ta-IN)";
    if (langCode.includes("hi")) return "Hindi (hi-IN)";
    if (langCode.includes("en")) return "English (en-IN)";
    return langCode;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/60 backdrop-blur shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Radio className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white flex items-center gap-2">
              SAMVED Operator Console
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                Phase 3: Realtime Observation
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
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
      <div className="flex flex-1 overflow-hidden">
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

          {/* Calls List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {(activeTab === "ACTIVE" ? activeCalls : recentCalls).length === 0 ? (
              <div className="text-center py-12 px-4">
                <PhoneCall className="h-8 w-8 text-slate-600 mx-auto mb-2 opacity-50" />
                <p className="text-xs text-slate-500">
                  {activeTab === "ACTIVE" ? "No active telephony calls." : "No recent calls recorded."}
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
              (activeTab === "ACTIVE" ? activeCalls : recentCalls).map((call) => {
                const isSelected = call.call_id === selectedCallId;
                return (
                  <div
                    key={call.call_id}
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

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="truncate max-w-[120px] font-mono text-slate-500">
                        {call.call_id}
                      </span>
                      <span>{call.duration_seconds}s</span>
                    </div>

                    <div className="mt-2 flex items-center justify-between pt-2 border-t border-slate-800/60">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300">
                        {getLanguageLabel(call.current_language)}
                      </span>
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
        <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden border-r border-slate-800">
          {selectedCall ? (
            <>
              {/* Selected Call Header */}
              <div className="border-b border-slate-800 bg-slate-900/30 p-4 shrink-0">
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
        <aside className="w-96 bg-slate-900/50 flex flex-col shrink-0">
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
              {(["ALL", "TRANSCRIPT", "CONVERSATION", "ERRORS", "LATENCY"] as EventFilterCategory[]).map(
                (f) => (
                  <button
                    key={f}
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

                return (
                  <div
                    key={ev.event_id || `${type}-${idx}`}
                    className={`p-2.5 rounded-md border text-xs transition-colors hover:bg-slate-800/80 ${
                      isError
                        ? "bg-rose-950/20 border-rose-800/50"
                        : isLatency
                        ? "bg-cyan-950/20 border-cyan-800/50"
                        : isTts
                        ? "bg-purple-950/20 border-purple-800/50"
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
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
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

            <div className="p-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Evaluation Scenario:
                </label>
                <div className="space-y-2">
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
    </div>
  );
}
