import React from "react";

interface ModeBadgeProps {
  mode: string;
}

export const ModeBadge: React.FC<ModeBadgeProps> = ({ mode }) => {
  const normalized = mode.toUpperCase();

  if (normalized === "LIVE") {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
        <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-600 rounded-full animate-pulse" />
        LIVE MODE
      </span>
    );
  }

  if (normalized === "SIMULATION") {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
        <span className="w-1.5 h-1.5 mr-1.5 bg-amber-500 rounded-full" />
        SIMULATION MODE
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-200 text-slate-800 border border-slate-300">
      <span className="w-1.5 h-1.5 mr-1.5 bg-blue-600 rounded-full" />
      DEV MODE (SAFE)
    </span>
  );
};
