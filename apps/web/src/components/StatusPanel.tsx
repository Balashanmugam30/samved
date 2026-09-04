"use client";

import React from "react";
import { ApiReadinessData, ConnectionState } from "../hooks/useApiStatus";
import { WsStatus } from "../hooks/useWebSocket";
import {
  Server,
  Activity,
  Database,
  Radio,
  Cpu,
  RefreshCw,
  PhoneCall,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";

interface StatusPanelProps {
  apiState: ConnectionState;
  apiData: ApiReadinessData | null;
  apiUrl: string;
  apiLatencyMs: number | null;
  wsState: WsStatus;
  wsUrl: string;
  onRefreshApi: () => void;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({
  apiState,
  apiData,
  apiUrl,
  apiLatencyMs,
  wsState,
  wsUrl,
  onRefreshApi,
}) => {
  const getStatusIcon = (status: "online" | "offline" | "mock" | "loading") => {
    switch (status) {
      case "online":
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      case "mock":
        return <AlertCircle className="w-4 h-4 text-blue-600" />;
      case "loading":
        return <RefreshCw className="w-4 h-4 text-amber-500 animate-spin" />;
      case "offline":
      default:
        return <XCircle className="w-4 h-4 text-rose-500" />;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            System Operational Status
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time telemetry and dependency health for SAMVED Phase 1 (Telephony Ingress)
          </p>
        </div>
        <button
          onClick={onRefreshApi}
          className="inline-flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded hover:bg-slate-100 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* API Backend Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Server className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">FastAPI Backend</span>
            </div>
            {getStatusIcon(
              apiState === "connected"
                ? "online"
                : apiState === "loading"
                ? "loading"
                : "offline"
            )}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Endpoint:</span>
              <span className="font-mono text-slate-800">{apiUrl}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Status:</span>
              <span
                className={`font-semibold ${
                  apiState === "connected" ? "text-emerald-700" : "text-rose-600"
                }`}
              >
                {apiState.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Latency:</span>
              <span className="text-slate-800 font-mono">
                {apiLatencyMs ? `${apiLatencyMs} ms` : "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Realtime Gateway Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">Realtime Gateway</span>
            </div>
            {getStatusIcon(
              wsState === "connected"
                ? "online"
                : wsState === "connecting" || wsState === "reconnecting"
                ? "loading"
                : "offline"
            )}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Route:</span>
              <span className="font-mono text-slate-800">{wsUrl}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Connection:</span>
              <span
                className={`font-semibold ${
                  wsState === "connected" ? "text-emerald-700" : "text-slate-600"
                }`}
              >
                {wsState.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Envelope:</span>
              <span className="text-slate-800 font-mono">v1.0 (Typed)</span>
            </div>
          </div>
        </div>

        {/* Telephony Integration Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <PhoneCall className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">Telephony Ingress</span>
            </div>
            {getStatusIcon("online")}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Provider:</span>
              <span className="text-slate-800 font-medium">
                {apiData?.dependencies?.telephony?.provider || "Exotel Adapter"}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Active Calls:</span>
              <span className="text-emerald-700 font-bold font-mono">
                {apiData?.active_calls_count ?? 0}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Streaming:</span>
              <span className="text-slate-700 font-medium">8kHz PCM s16le (WS)</span>
            </div>
          </div>
        </div>

        {/* Speech Recognition & Synthesis Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Radio className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">Speech (STT / TTS)</span>
            </div>
            {getStatusIcon("online")}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Provider:</span>
              <span className="text-slate-800 font-medium">
                {apiData?.dependencies?.speech?.provider || "Sarvam AI"}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Engine:</span>
              <span className="text-slate-700">saaras:v3 & bulbul:v3</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Pipeline:</span>
              <span className="text-emerald-700 font-semibold">Phase 2 Active</span>
            </div>
          </div>
        </div>

        {/* LLM Reasoning Provider Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">LLM Reasoning</span>
            </div>
            {getStatusIcon("online")}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Provider:</span>
              <span className="text-slate-800 font-medium">
                {apiData?.dependencies?.llm?.provider || "Gemini"}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Model:</span>
              <span className="text-slate-700">Gemini 2.5 Flash</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Pipeline:</span>
              <span className="text-emerald-700 font-semibold">Phase 2 Active</span>
            </div>
          </div>
        </div>

        {/* Database & State Persistence Card */}
        <div className="p-4 rounded-md border border-slate-200 bg-slate-50 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-4 h-4 text-slate-700" />
              <span className="text-xs font-semibold text-slate-900">Data Persistence</span>
            </div>
            {getStatusIcon("mock")}
          </div>
          <div className="mt-3 text-xs space-y-1">
            <div className="flex justify-between text-slate-500">
              <span>Database:</span>
              <span className="text-slate-800 font-medium">PostgreSQL (DEV Mode)</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Redis:</span>
              <span className="text-slate-800 font-medium">In-Memory Gateway</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Migration:</span>
              <span className="text-emerald-700 font-medium">Alembic / SQL Ready</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
