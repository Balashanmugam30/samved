"use client";

import React, { useState } from "react";
import { useApiStatus } from "@/hooks/useApiStatus";
import { useWebSocket } from "@/hooks/useWebSocket";
import { StatusPanel } from "@/components/StatusPanel";
import { EventType } from "@samved/schemas";
import {
  ShieldAlert,
  Terminal,
  Layers,
  ArrowRight,
  Send,
  Check,
} from "lucide-react";

export default function OverviewPage() {
  const { state: apiState, data: apiData, latencyMs, refetch, apiUrl } = useApiStatus();
  const { status: wsStatus, lastEvent, sendEvent, wsUrl } = useWebSocket();
  const [pingSent, setPingSent] = useState(false);

  const handleTestPing = () => {
    const success = sendEvent(EventType.HEARTBEAT_PING, {
      triggered_by: "operator_ui_test",
      timestamp: new Date().toISOString(),
    });
    if (success) {
      setPingSent(true);
      setTimeout(() => setPingSent(false), 3000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Description */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-blue-700 uppercase tracking-wider">
          <Layers className="w-4 h-4" />
          <span>Foundation Stage</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          Operations & Architecture Console
        </h1>
        <p className="text-sm text-slate-600 mt-1 max-w-3xl">
          SAMVED acts as an AI-assisted triage, safety detection, and vulnerability intelligence layer
          for the National Toll-Free Drug De-Addiction Helpline (NHAA 14566).
        </p>
      </div>

      {/* Authoritative Architectural Principles Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-xs text-blue-900 space-y-2">
        <div className="flex items-center space-x-2 font-bold text-blue-950">
          <ShieldAlert className="w-4 h-4 text-blue-600" />
          <span>Core Engineering Principles & Non-Negotiables</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-slate-700">
          <div className="flex items-start space-x-2">
            <span className="font-bold text-blue-700">•</span>
            <span>
              <strong>Real Telephony Ingress:</strong> Final architecture streams live calls from Exotel (14566), not browser microphones.
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-bold text-blue-700">•</span>
            <span>
              <strong>Deterministic Safety:</strong> Safety escalations are governed by auditable rules, not probabilistic LLMs alone.
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-bold text-blue-700">•</span>
            <span>
              <strong>Non-Diagnostic:</strong> SVI and acoustic features provide triage support, never psychiatric or clinical diagnoses.
            </span>
          </div>
          <div className="flex items-start space-x-2">
            <span className="font-bold text-blue-700">•</span>
            <span>
              <strong>Human-in-the-Loop:</strong> Critical risk escalations mandate human tele-counselor verification and override.
            </span>
          </div>
        </div>
      </div>

      {/* Operational Status Panel */}
      <StatusPanel
        apiState={apiState}
        apiData={apiData}
        apiUrl={apiUrl}
        apiLatencyMs={latencyMs}
        wsState={wsStatus}
        wsUrl={wsUrl}
        onRefreshApi={refetch}
      />

      {/* Realtime Event Gateway Tester */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-slate-700" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Realtime WebSocket Event Gateway
            </h3>
          </div>
          <button
            onClick={handleTestPing}
            disabled={wsStatus !== "connected"}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {pingSent ? <Check className="w-3.5 h-3.5" /> : <Send className="w-3.5 h-3.5" />}
            <span>{pingSent ? "Ping Emitted" : "Send Heartbeat Ping"}</span>
          </button>
        </div>

        <div className="mt-4">
          <div className="text-xs font-semibold text-slate-700 mb-1.5">
            Last Received Event Envelope:
          </div>
          <pre className="bg-slate-950 text-emerald-400 p-4 rounded-md text-xs font-mono overflow-x-auto max-h-56">
            {lastEvent
              ? JSON.stringify(lastEvent, null, 2)
              : "// Waiting for incoming WebSocket events or handshake..."}
          </pre>
        </div>
      </div>

      {/* Phase Roadmap Progression */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4">
          Implementation Roadmap Status
        </h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded bg-emerald-50 border border-emerald-200 text-xs">
            <div className="flex items-center space-x-3">
              <span className="font-bold text-emerald-800">Phase 0</span>
              <span className="text-emerald-900 font-medium">
                Engineering Foundation, Monorepo Layout, Contracts, Tests, CI/CD
              </span>
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-200 text-emerald-800">
              COMPLETE
            </span>
          </div>

          <div className="flex items-center justify-between p-3 rounded bg-slate-50 border border-slate-200 text-xs">
            <div className="flex items-center space-x-3">
              <span className="font-bold text-slate-700">Phase 1</span>
              <span className="text-slate-600 font-medium">
                Real Exotel Inbound Telephony Streaming (Mobile → 14566 → Gateway)
              </span>
            </div>
            <div className="flex items-center space-x-1 text-slate-500 text-xs font-medium">
              <span>Next</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded bg-slate-50 border border-slate-200 text-xs">
            <div className="flex items-center space-x-3">
              <span className="font-bold text-slate-700">Phase 2</span>
              <span className="text-slate-600 font-medium">
                Multilingual Speech Loop (Sarvam STT + Gemini Reasoning + Sarvam TTS)
              </span>
            </div>
            <span className="text-[11px] text-slate-400">Scheduled</span>
          </div>
        </div>
      </div>
    </div>
  );
}
