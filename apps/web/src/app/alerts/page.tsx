import React from "react";
import { AlertTriangle, Clock, Info } from "lucide-react";

export default function AlertsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-rose-700 uppercase tracking-wider">
          <Clock className="w-4 h-4" />
          <span>Scheduled for Phase 4</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Deterministic Safety Alerts</h1>
        <p className="text-sm text-slate-600 mt-1">
          Real-time safety escalations, human-in-the-loop review, and supervisor override queue.
        </p>
      </div>

      <div className="bg-rose-50 border border-rose-200 rounded-lg p-6 text-sm text-rose-950 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-rose-900">
          <Info className="w-5 h-5 text-rose-600" />
          <span>Phase 4 Implementation Boundary</span>
        </div>
        <p className="text-rose-900 leading-relaxed">
          Deterministic safety policies (immediate physical threat, acute withdrawal distress, self-harm signals)
          will be implemented in <strong>Phase 4</strong>.
        </p>
        <div className="bg-white border border-rose-200 rounded p-4 text-xs font-mono text-slate-700 space-y-1">
          <div>Status: <span className="font-semibold text-rose-700">UNAVAILABLE IN PHASE 0</span></div>
          <div>Policy Invariant: LLMs do not act as the final safety authority</div>
          <div>Human Oversight: Mandatory operator confirmation on all critical escalations</div>
        </div>
      </div>
    </div>
  );
}
