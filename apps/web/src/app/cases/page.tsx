import React from "react";
import { FolderArchive, Clock, Info } from "lucide-react";

export default function CasesPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          <Clock className="w-4 h-4" />
          <span>Scheduled for Phase 11</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">Case Intelligence Records</h1>
        <p className="text-sm text-slate-600 mt-1">
          Longitudinal case tracking, anonymous victim history, and de-addiction referral management.
        </p>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-sm text-slate-800 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-slate-900">
          <Info className="w-5 h-5 text-blue-600" />
          <span>Phase 11 Implementation Boundary</span>
        </div>
        <p className="text-slate-700 leading-relaxed">
          Case management, entity extraction, and multi-session victim timelines will be implemented
          in <strong>Phase 11</strong>.
        </p>
        <div className="bg-white border border-slate-200 rounded p-4 text-xs font-mono text-slate-700 space-y-1">
          <div>Status: <span className="font-semibold text-slate-600">UNAVAILABLE IN PHASE 0</span></div>
          <div>Domain Model: Case, Utterance, ConsentRecord contracts established in @samved/schemas</div>
          <div>Data Persistence: PostgreSQL schema prepared in infra/db/init.sql</div>
        </div>
      </div>
    </div>
  );
}
