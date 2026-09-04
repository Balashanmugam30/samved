"use client";

import React, { useState, useEffect } from "react";
import {
  PhoneCall,
  Activity,
  Play,
  CheckCircle2,
  RefreshCw,
  Radio,
  Server,
  Terminal,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";

interface TelephonySessionItem {
  session_id: string;
  call_id: string;
  provider_call_id: string;
  provider: string;
  caller_masked_number: string;
  state: string;
  connected_at?: string | null;
  last_activity_at: string;
  inbound_frames_count: number;
  inbound_bytes_count: number;
  sequence_gaps_count: number;
  is_active: boolean;
}

export default function CallsPage() {
  const [sessions, setSessions] = useState<TelephonySessionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [testPhone, setTestPhone] = useState("+919876543210");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

  const startSimulation = async () => {
    try {
      setSimulating(true);
      const res = await fetch(`${apiUrl}/v1/telephony/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caller_phone: testPhone,
          duration_frames: 15,
          frame_interval_ms: 60,
          simulate_gap: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimulationResult(data);
        // Refresh session list
        fetchSessions();
      }
    } catch (e) {
      console.error("Failed to trigger simulation", e);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 4000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const getStateBadge = (state: string) => {
    switch (state) {
      case "STREAMING":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-600 rounded-full animate-pulse" />
            STREAMING
          </span>
        );
      case "CONNECTING":
      case "RINGING":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <span className="w-1.5 h-1.5 mr-1.5 bg-amber-500 rounded-full" />
            {state}
          </span>
        );
      case "ENDED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-200 text-slate-700">
            ENDED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
            {state}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Description */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider">
          <Activity className="w-4 h-4" />
          <span>Phase 1 Telephony Ingress Console</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Live Telephony Gateway</h1>
        <p className="text-sm text-slate-600 mt-1 max-w-3xl">
          Real-time telephone call ingress for NHAA 14566. Manages bidirectional audio streaming between
          Exotel media streams and SAMVED's canonical 8kHz PCM audio gateway.
        </p>
      </div>

      {/* Gateway Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center space-x-2 text-slate-900 font-semibold text-xs">
            <Server className="w-4 h-4 text-blue-600" />
            <span>Inbound Webhook Route</span>
          </div>
          <div className="mt-2">
            <div className="font-mono text-xs text-slate-800 bg-slate-50 p-2 rounded border border-slate-200 truncate">
              POST /v1/telephony/exotel/inbound
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Passthru call intake & session provisioning
            </p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center space-x-2 text-slate-900 font-semibold text-xs">
            <Radio className="w-4 h-4 text-emerald-600" />
            <span>Audio Streaming Route</span>
          </div>
          <div className="mt-2">
            <div className="font-mono text-xs text-slate-800 bg-slate-50 p-2 rounded border border-slate-200 truncate">
              WS /ws/telephony/exotel/&#123;session_id&#125;
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Bidirectional 16-bit 8000Hz PCM audio
            </p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center space-x-2 text-slate-900 font-semibold text-xs">
            <ShieldCheck className="w-4 h-4 text-slate-700" />
            <span>Privacy Guard</span>
          </div>
          <div className="mt-2 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span>Caller Masking:</span>
              <span className="font-semibold text-emerald-700">Active</span>
            </div>
            <div className="flex justify-between">
              <span>Raw Audio Blob:</span>
              <span className="font-semibold text-slate-700">Ephemeral (Zero disk)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Synthetic Call Simulation Test Harness */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-slate-700" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Synthetic Call Simulator & Ingress Harness
            </h3>
          </div>
          <div className="flex items-center space-x-3">
            <input
              type="text"
              value={testPhone}
              onChange={(e) => setTestPhone(e.target.value)}
              placeholder="+919876543210"
              className="text-xs font-mono px-3 py-1.5 border border-slate-300 rounded bg-slate-50 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={startSimulation}
              disabled={simulating}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{simulating ? "Simulating..." : "Start Simulation Call"}</span>
            </button>
          </div>
        </div>

        {simulationResult && (
          <div className="mt-4 p-4 rounded bg-blue-50 border border-blue-200 text-xs text-blue-900 space-y-2">
            <div className="flex items-center space-x-2 font-bold text-blue-950">
              <CheckCircle2 className="w-4 h-4 text-blue-600" />
              <span>Simulation Ingress Established Successfully</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px] text-slate-700">
              <div>Call ID: <strong>{simulationResult.call_id}</strong></div>
              <div>Session ID: <strong>{simulationResult.session_id}</strong></div>
              <div>Masked Number: <strong>{simulationResult.masked_caller_number}</strong></div>
              <div>Scheduled Frames: <strong>{simulationResult.frames_scheduled}</strong></div>
            </div>
          </div>
        )}
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
                  <th className="py-2.5 px-4">State</th>
                  <th className="py-2.5 px-4">Frames</th>
                  <th className="py-2.5 px-4">Bytes</th>
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
                    <td className="py-2.5 px-4">{getStateBadge(sess.state)}</td>
                    <td className="py-2.5 px-4 text-slate-700">{sess.inbound_frames_count}</td>
                    <td className="py-2.5 px-4 text-slate-700">{sess.inbound_bytes_count} B</td>
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
