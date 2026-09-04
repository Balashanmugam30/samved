import React from "react";
import { BarChart3, Clock, Info } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          <Clock className="w-4 h-4" />
          <span>Scheduled for Phase 13</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Helpline Analytics & Intelligence</h1>
        <p className="text-sm text-slate-600 mt-1">
          Aggregated call volumes, language distribution, geographic trends, and SVI severity indices.
        </p>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-sm text-slate-800 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-slate-900">
          <Info className="w-5 h-5 text-blue-600" />
          <span>Phase 13 Implementation Boundary</span>
        </div>
        <p className="text-slate-700 leading-relaxed">
          Aggregated reporting, SVI distribution heatmaps, and MoSJE administrative dashboards
          will be implemented in <strong>Phase 13</strong>.
        </p>
        <div className="bg-white border border-slate-200 rounded p-4 text-xs font-mono text-slate-700 space-y-1">
          <div>Status: <span className="font-semibold text-slate-600">UNAVAILABLE IN PHASE 0</span></div>
          <div>Telemetry Principle: No manufactured metrics or fake charts in production view</div>
        </div>
      </div>
    </div>
  );
}
