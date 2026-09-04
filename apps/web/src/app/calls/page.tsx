import React from "react";
import { PhoneForwarded, Clock, Info } from "lucide-react";

export default function CallsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-amber-700 uppercase tracking-wider">
          <Clock className="w-4 h-4" />
          <span>Scheduled for Phase 1</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Live Telephony Console</h1>
        <p className="text-sm text-slate-600 mt-1">
          Real-time call monitoring and active operator intervention for incoming NHAA 14566 lines.
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-sm text-amber-950 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-amber-900">
          <Info className="w-5 h-5 text-amber-700" />
          <span>Phase 1 Implementation Boundary</span>
        </div>
        <p className="text-amber-900 leading-relaxed">
          Inbound telephone call streaming (Mobile phone → Exotel → SAMVED Realtime Gateway) will be
          implemented in <strong>Phase 1</strong>.
        </p>
        <div className="bg-white border border-amber-200 rounded p-4 text-xs font-mono text-slate-700 space-y-1">
          <div>Status: <span className="font-semibold text-amber-700">UNAVAILABLE IN PHASE 0</span></div>
          <div>Target Provider: Exotel Voice Streaming API (8kHz / 16kHz μ-law)</div>
          <div>Mock Ingress: Available via WebSocket tests and synthetic event envelopes</div>
        </div>
      </div>
    </div>
  );
}
