"use client";

import React, { useState, useEffect, useRef } from "react";
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
  CornerDownRight,
  MessageSquare,
} from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { EventEnvelope, EventType } from "@samved/schemas";

interface TelephonySessionItem {
  session_id: string;
  call_id: string;
  provider_call_id: string;
  provider: string;
  caller_masked_number: string;
  state: string;
  conversation_state?: string;
  current_language?: string;
  utterances_count?: number;
  connected_at?: string | null;
  last_activity_at: string;
  inbound_frames_count: number;
  inbound_bytes_count: number;
  sequence_gaps_count: number;
  is_active: boolean;
}

interface TranscriptItem {
  id: string;
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

export default function CallsPage() {
  const [sessions, setSessions] = useState<TelephonySessionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState("tamil_help");
  const [callerPhone, setCallerPhone] = useState("+919876543210");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Conversational state
  const [aiState, setAiState] = useState<string>("IDLE");
  const [currentLanguage, setCurrentLanguage] = useState<string>("ta-IN");
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [partialDraft, setPartialDraft] = useState<string | null>(null);
  const [latencies, setLatencies] = useState<LatencyMetrics>({
    stt_ms: 0,
    llm_ms: 0,
    tts_ms: 0,
    total_ms: 0,
  });

  const transcriptScrollRef = useRef<HTMLDivElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // WebSocket for real-time events broadcasted by backend orchestrator
  useWebSocket({
    onEvent: (envelope: EventEnvelope) => {
      const event_type = envelope.event_type;
      const payload = (envelope.payload || {}) as Record<string, any>;

      switch (event_type) {
        case EventType.CONVERSATION_STATE_CHANGED:
          if (payload.new_state) {
            setAiState(String(payload.new_state));
          }
          break;

        case EventType.LANGUAGE_CHANGED:
          if (payload.new_language) {
            setCurrentLanguage(String(payload.new_language));
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
            setTranscripts((prev) => [
              ...prev,
              {
                id: `caller-${Date.now()}-${Math.random()}`,
                speaker: "caller",
                text: String(payload.text),
                language: payload.language ? String(payload.language) : currentLanguage,
                confidence: typeof payload.confidence === "number" ? payload.confidence : 0.95,
                is_final: true,
                timestamp: new Date().toLocaleTimeString(),
              },
            ]);
          }
          break;

        case EventType.AI_THINKING:
          setAiState("THINKING");
          break;

        case EventType.AI_RESPONSE_STARTED:
          setAiState("SPEAKING");
          if (payload.text) {
            setTranscripts((prev) => [
              ...prev,
              {
                id: `agent-${Date.now()}-${Math.random()}`,
                speaker: "agent",
                text: String(payload.text),
                language: payload.language ? String(payload.language) : currentLanguage,
                intent: payload.intent ? String(payload.intent) : undefined,
                safety_flag: Boolean(payload.safety_flag),
                is_final: true,
                timestamp: new Date().toLocaleTimeString(),
              },
            ]);
          }
          break;

        case EventType.SPEECH_INTERRUPTED:
          setAiState("INTERRUPTED");
          setTranscripts((prev) => [
            ...prev,
            {
              id: `system-interrupt-${Date.now()}`,
              speaker: "system",
              text: `[Barge-in] Caller interrupted agent speech: ${payload.reason || "voice_activity"}. Output audio queue flushed.`,
              timestamp: new Date().toLocaleTimeString(),
            },
          ]);
          break;

        case EventType.TURN_LATENCY:
          setLatencies({
            stt_ms: Number(payload.stt_latency_ms) || 0,
            llm_ms: Number(payload.llm_latency_ms) || 0,
            tts_ms: Number(payload.tts_latency_ms) || 0,
            total_ms: Number(payload.total_turn_ms) || 0,
          });
          break;

        case EventType.AI_RESPONSE_ENDED:
          setAiState("LISTENING");
          break;

        default:
          break;
      }
    },
  });

  // Auto-scroll transcript container
  useEffect(() => {
    if (transcriptScrollRef.current) {
      transcriptScrollRef.current.scrollTop = transcriptScrollRef.current.scrollHeight;
    }
  }, [transcripts, partialDraft]);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/v1/telephony/sessions`, { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error("Failed to fetch active telephony sessions", e);
    } finally {
      setLoading(false);
    }
  };

  const startConversationSimulation = async () => {
    try {
      setSimulating(true);
      setAiState("LISTENING");
      const res = await fetch(`${apiUrl}/v1/telephony/simulate/conversation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: selectedScenario,
          caller_phone: callerPhone,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveSessionId(data.session_id);
        fetchSessions();
      }
    } catch (e) {
      console.error("Failed to trigger conversation simulation", e);
    } finally {
      setSimulating(false);
    }
  };

  const clearTranscripts = () => {
    setTranscripts([]);
    setPartialDraft(null);
    setAiState("IDLE");
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 3000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const getAiStatePill = (state: string) => {
    switch (state) {
      case "LISTENING":
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <Mic className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
            <span>LISTENING (Inbound 8kHz PCM)</span>
          </div>
        );
      case "TRANSCRIBING":
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-300">
            <RefreshCw className="w-3.5 h-3.5 text-amber-600 animate-spin" />
            <span>TRANSCRIBING (Sarvam STT)</span>
          </div>
        );
      case "THINKING":
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-900 border border-purple-300">
            <Cpu className="w-3.5 h-3.5 text-purple-600 animate-pulse" />
            <span>REASONING (Gemini 2.5 Flash)</span>
          </div>
        );
      case "SPEAKING":
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <Volume2 className="w-3.5 h-3.5 text-emerald-600 animate-bounce" />
            <span>SPEAKING (Sarvam Bulbul TTS)</span>
          </div>
        );
      case "INTERRUPTED":
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-900 border border-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            <span>BARGE-IN DETECTED (Audio Cleared)</span>
          </div>
        );
      default:
        return (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-slate-400" />
            <span>PIPELINE READY (IDLE)</span>
          </div>
        );
    }
  };

  const getLanguageLabel = (code: string) => {
    switch (code) {
      case "ta-IN":
        return "Tamil (தமிழ்)";
      case "hi-IN":
        return "Hindi (हिन्दी)";
      case "en-IN":
        return "Indian English";
      default:
        return code;
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Description */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider">
          <Activity className="w-4 h-4" />
          <span>Phase 2 Multilingual AI Voice Conversation Console</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Live AI Voice Helpline Gateway</h1>
        <p className="text-sm text-slate-600 mt-1 max-w-4xl">
          Complete end-to-end voice loop for NHAA 14566. Orchestrates Sarvam Realtime STT (<code>saaras:v3</code>),
          Google Gemini (<code>gemini-2.5-flash</code>), and Sarvam Bulbul TTS (<code>bulbul:v3</code>) directly
          over canonical 8kHz PCM telephony media streams with barge-in interruption.
        </p>
      </div>

      {/* Voice Simulation & Scenario Test Harness */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Multilingual Voice Pipeline Simulator
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            {getAiStatePill(aiState)}
            <div className="inline-flex items-center space-x-1 px-2 py-1 rounded bg-slate-100 text-slate-700 text-xs font-medium">
              <Globe className="w-3.5 h-3.5 text-slate-500" />
              <span>{getLanguageLabel(currentLanguage)}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          <div className="md:col-span-6 space-y-1">
            <label className="text-xs font-semibold text-slate-700">Select Test Scenario:</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="w-full text-xs font-medium px-3 py-2 border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {SCENARIOS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3 space-y-1">
            <label className="text-xs font-semibold text-slate-700">Masked Caller Phone:</label>
            <input
              type="text"
              value={callerPhone}
              onChange={(e) => setCallerPhone(e.target.value)}
              className="w-full text-xs font-mono px-3 py-2 border border-slate-300 rounded bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="md:col-span-3 flex items-end space-x-2 pt-5">
            <button
              onClick={startConversationSimulation}
              disabled={simulating}
              className="flex-1 inline-flex items-center justify-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{simulating ? "Starting..." : "Run Voice Simulation"}</span>
            </button>
            <button
              onClick={clearTranscripts}
              title="Clear transcript history"
              className="px-2.5 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded hover:bg-slate-50 transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 italic">
          {SCENARIOS.find((s) => s.key === selectedScenario)?.desc}
        </p>
      </div>

      {/* Latency Telemetry Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>STT Partial Latency</span>
            <Mic className="w-3.5 h-3.5 text-blue-500" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900 mt-1">
            {latencies.stt_ms ? `${latencies.stt_ms} ms` : "—"}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">Target: &lt; 200 ms</p>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Gemini Reasoning</span>
            <Cpu className="w-3.5 h-3.5 text-purple-500" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900 mt-1">
            {latencies.llm_ms ? `${latencies.llm_ms} ms` : "—"}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">Target: &lt; 400 ms</p>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>TTS First Frame</span>
            <Volume2 className="w-3.5 h-3.5 text-emerald-500" />
          </div>
          <div className="text-lg font-bold font-mono text-slate-900 mt-1">
            {latencies.tts_ms ? `${latencies.tts_ms} ms` : "—"}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">Target: &lt; 200 ms</p>
        </div>

        <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Total Turn Roundtrip</span>
            <Clock className="w-3.5 h-3.5 text-slate-700" />
          </div>
          <div
            className={`text-lg font-bold font-mono mt-1 ${
              latencies.total_ms > 0 && latencies.total_ms < 900
                ? "text-emerald-600"
                : "text-slate-900"
            }`}
          >
            {latencies.total_ms ? `${latencies.total_ms} ms` : "—"}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">Conversational SLA: &lt; 800 ms</p>
        </div>
      </div>

      {/* Live Conversation & Dialogue Transcript Viewer */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[440px]">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-4 h-4 text-slate-700" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Live Multilingual Transcript & AI Dialogue Stream
            </h3>
          </div>
          <div className="text-xs text-slate-500 font-mono">
            {transcripts.length} turns recorded
          </div>
        </div>

        <div
          ref={transcriptScrollRef}
          className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50"
        >
          {transcripts.length === 0 && !partialDraft && (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 text-xs">
              <Mic className="w-8 h-8 mb-2 stroke-1 text-slate-300" />
              <p className="font-medium text-slate-600">No active voice dialogue</p>
              <p className="text-[11px] mt-1 max-w-sm">
                Click &quot;Run Voice Simulation&quot; above or connect an incoming call to observe real-time
                multilingual STT, Gemini reasoning, and speech synthesis.
              </p>
            </div>
          )}

          {transcripts.map((item) => {
            if (item.speaker === "system") {
              return (
                <div
                  key={item.id}
                  className="p-2.5 rounded bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-start space-x-2"
                >
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 font-mono text-[11px] leading-relaxed">
                    {item.text}
                  </div>
                  <span className="text-[10px] text-rose-400">{item.timestamp}</span>
                </div>
              );
            }

            const isCaller = item.speaker === "caller";

            return (
              <div
                key={item.id}
                className={`flex flex-col ${isCaller ? "items-start" : "items-end"}`}
              >
                <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 mb-1 px-1">
                  <span className="font-semibold text-slate-700">
                    {isCaller ? "CALLER" : "SAMVED AI"}
                  </span>
                  {item.language && (
                    <span className="px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 text-[10px]">
                      {item.language}
                    </span>
                  )}
                  {item.intent && (
                    <span className="px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 text-[10px] font-mono">
                      {item.intent}
                    </span>
                  )}
                  {item.safety_flag && (
                    <span className="px-1.5 py-0.2 rounded bg-rose-100 text-rose-800 text-[10px] font-bold">
                      SAFETY_HOOK
                    </span>
                  )}
                  <span className="text-[10px]">{item.timestamp}</span>
                </div>

                <div
                  className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed shadow-sm ${
                    isCaller
                      ? "bg-white text-slate-900 border border-slate-200"
                      : "bg-blue-600 text-white border border-blue-700"
                  }`}
                >
                  {item.text}
                </div>
              </div>
            );
          })}

          {/* Live Typing / Partial STT Draft */}
          {partialDraft && (
            <div className="flex flex-col items-start">
              <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 mb-1 px-1">
                <span className="font-semibold text-amber-700">CALLER (Transcribing...)</span>
              </div>
              <div className="max-w-[85%] rounded-lg p-3 text-xs italic bg-amber-50 text-amber-900 border border-amber-200 shadow-sm animate-pulse">
                {partialDraft} ...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Active Telephony Sessions List */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <PhoneCall className="w-4 h-4 text-slate-700" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Active Telephony Sessions
            </h3>
            <span className="text-xs font-semibold bg-slate-200 text-slate-800 px-2 py-0.5 rounded-full">
              {sessions.length}
            </span>
          </div>
          <button
            onClick={fetchSessions}
            disabled={loading}
            className="inline-flex items-center space-x-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          {sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No active telephony calls currently in progress. Use the simulator above or connect via Exotel webhook.
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-2.5 px-4">Call ID</th>
                  <th className="py-2.5 px-4">Session ID</th>
                  <th className="py-2.5 px-4">Caller (Masked)</th>
                  <th className="py-2.5 px-4">Provider</th>
                  <th className="py-2.5 px-4">Telephony State</th>
                  <th className="py-2.5 px-4">AI State</th>
                  <th className="py-2.5 px-4">Language</th>
                  <th className="py-2.5 px-4">Frames</th>
                  <th className="py-2.5 px-4">Gaps</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((sess) => (
                  <tr key={sess.session_id} className="hover:bg-slate-50 font-mono">
                    <td className="py-2.5 px-4 font-semibold text-slate-900">{sess.call_id}</td>
                    <td className="py-2.5 px-4 text-slate-600">{sess.session_id}</td>
                    <td className="py-2.5 px-4 text-slate-800">{sess.caller_masked_number}</td>
                    <td className="py-2.5 px-4 uppercase text-slate-600">{sess.provider}</td>
                    <td className="py-2.5 px-4">{sess.state}</td>
                    <td className="py-2.5 px-4 font-semibold text-blue-700">
                      {sess.conversation_state || "LISTENING"}
                    </td>
                    <td className="py-2.5 px-4 text-slate-700">
                      {sess.current_language || "ta-IN"}
                    </td>
                    <td className="py-2.5 px-4 text-slate-700">{sess.inbound_frames_count}</td>
                    <td className="py-2.5 px-4">
                      {sess.sequence_gaps_count > 0 ? (
                        <span className="text-amber-600 font-bold">{sess.sequence_gaps_count}</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
