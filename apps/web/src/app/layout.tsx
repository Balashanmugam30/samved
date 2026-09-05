import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "SAMVED — AI-Assisted Victim Triage Layer | NHAA 14566",
  description:
    "National Toll-Free Drug De-Addiction Helpline (NHAA 14566) Operational Console - SIH 2026 Problem Statement 26093",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-100 text-slate-900 min-h-screen flex flex-col antialiased">
        <Header mode="DEV" apiConnected={true} />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-3 sm:p-6 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full min-w-0">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
