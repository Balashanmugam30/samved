"use client";

import { useEffect, useState } from "react";

export interface DependencyStatus {
  status: string;
  required_for_mode: boolean;
  details?: string;
  provider?: string;
}

export interface ApiReadinessData {
  ready: boolean;
  mode: string;
  environment: string;
  active_calls_count?: number;
  dependencies: Record<string, DependencyStatus>;
  timestamp: string;
}

export type ConnectionState = "loading" | "connected" | "unavailable" | "error";

export function useApiStatus(pollIntervalMs = 10000) {
  const [state, setState] = useState<ConnectionState>("loading");
  const [data, setData] = useState<ApiReadinessData | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const checkStatus = async () => {
    const startTime = performance.now();
    try {
      const response = await fetch(`${apiUrl}/ready`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      });

      const elapsed = Math.round(performance.now() - startTime);
      setLatencyMs(elapsed);
      setLastChecked(new Date());

      if (response.ok) {
        const json = await response.json();
        setData(json);
        setState("connected");
      } else {
        setState("unavailable");
      }
    } catch {
      setState("unavailable");
      setData(null);
      setLatencyMs(null);
      setLastChecked(new Date());
    }
  };

  useEffect(() => {
    checkStatus();
    const timer = setInterval(checkStatus, pollIntervalMs);
    return () => clearInterval(timer);
  }, [apiUrl, pollIntervalMs]);

  return { state, data, latencyMs, lastChecked, refetch: checkStatus, apiUrl };
}
