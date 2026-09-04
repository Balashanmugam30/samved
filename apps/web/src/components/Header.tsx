import React from "react";
import { ModeBadge } from "./ModeBadge";
import { Shield, PhoneCall } from "lucide-react";

interface HeaderProps {
  mode?: string;
  apiConnected?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ mode = "DEV", apiConnected = false }) => {
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-gov-900 font-bold text-lg tracking-tight">
          <div className="p-1.5 bg-gov-900 text-white rounded">
            <Shield className="w-5 h-5" />
          </div>
          <span>SAMVED</span>
        </div>
        <div className="hidden md:block h-5 w-px bg-slate-300" />
        <div className="hidden md:flex flex-col">
          <span className="text-xs font-semibold text-slate-700">
            NHAA 14566 — National Toll-Free Drug De-Addiction Helpline
          </span>
          <span className="text-[11px] text-slate-500">
            SIH 2026 Problem Statement 26093 | Authorized Operations Console
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 text-xs text-slate-600">
          <PhoneCall className="w-3.5 h-3.5 text-slate-500" />
          <span className="font-mono font-medium">Toll-Free: 14566</span>
        </div>

        <ModeBadge mode={mode} />

        <div className="flex items-center space-x-1.5 pl-2">
          <span
            className={`w-2 h-2 rounded-full ${
              apiConnected ? "bg-emerald-500" : "bg-rose-500"
            }`}
          />
          <span className="text-xs font-medium text-slate-600">
            {apiConnected ? "API Online" : "API Offline"}
          </span>
        </div>
      </div>
    </header>
  );
};
