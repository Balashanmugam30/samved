"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PhoneForwarded,
  FolderArchive,
  AlertTriangle,
  BarChart3,
  FlaskConical,
  FileCheck,
  LifeBuoy,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  phaseBadge?: string;
  activeInPhase0?: boolean;
}

const navItems: NavItem[] = [
  {
    label: "Overview & Status",
    href: "/",
    icon: LayoutDashboard,
    activeInPhase0: true,
  },
  {
    label: "Live Telephony",
    href: "/calls",
    icon: PhoneForwarded,
    phaseBadge: "Active",
  },
  {
    label: "Case Intelligence",
    href: "/cases",
    icon: FolderArchive,
    phaseBadge: "Phase 11",
  },
  {
    label: "Safety Alerts",
    href: "/alerts",
    icon: AlertTriangle,
    phaseBadge: "Phase 4",
  },
  {
    label: "Analytics & Trends",
    href: "/analytics",
    icon: BarChart3,
    phaseBadge: "Phase 13",
  },
  {
    label: "Simulation & Sandbox",
    href: "/simulation",
    icon: FlaskConical,
    phaseBadge: "Phase 14",
  },
  {
    label: "Audit Trail",
    href: "/audit",
    icon: FileCheck,
    phaseBadge: "Phase 15",
  },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 border-r border-slate-800 min-h-screen">
      <div className="p-4 border-b border-slate-800">
        <div className="text-xs uppercase tracking-wider font-semibold text-slate-400">
          Navigation
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2 rounded text-xs font-medium transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Icon className="w-4 h-4 text-slate-400" />
                <span>{item.label}</span>
              </div>
              {item.phaseBadge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {item.phaseBadge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950 text-xs text-slate-400 space-y-2">
        <div className="flex items-center space-x-2">
          <LifeBuoy className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">Phase 2 AI Voice Active</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Sarvam STT, Gemini 2.5 Flash reasoning, and Sarvam Bulbul TTS real-time pipeline operational.
        </p>
      </div>
    </aside>
  );
};
