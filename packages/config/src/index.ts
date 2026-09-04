/**
 * SAMVED Core Constants & Configuration Definitions
 */

export const APP_MODES = ["DEV", "SIMULATION", "LIVE"] as const;
export type AppMode = (typeof APP_MODES)[number];

export const APP_ENVIRONMENTS = ["development", "staging", "production"] as const;
export type AppEnvironment = (typeof APP_ENVIRONMENTS)[number];

export const SVI_THRESHOLDS = {
  LOW: { min: 0, max: 25, label: "Low Vulnerability" },
  MODERATE: { min: 26, max: 50, label: "Moderate Vulnerability" },
  HIGH: { min: 51, max: 75, label: "High Vulnerability" },
  CRITICAL: { min: 76, max: 100, label: "Critical Vulnerability - Urgent Human Review" }
} as const;

export const SUPPORTED_INDIAN_LANGUAGES = [
  { code: "hi-IN", name: "Hindi" },
  { code: "ta-IN", name: "Tamil" },
  { code: "te-IN", name: "Telugu" },
  { code: "kn-IN", name: "Kannada" },
  { code: "bn-IN", name: "Bengali" },
  { code: "mr-IN", name: "Marathi" },
  { code: "gu-IN", name: "Gujarati" },
  { code: "ml-IN", name: "Malayalam" },
  { code: "pa-IN", name: "Punjabi" },
  { code: "or-IN", name: "Odia" },
  { code: "en-IN", name: "Indian English" }
] as const;

export const HELPLINE_METADATA = {
  name: "National Toll-Free Drug De-Addiction Helpline (NHAA)",
  shortName: "NHAA 14566",
  dialNumber: "14566",
  problemStatement: "26093",
  hackathon: "Smart India Hackathon 2026",
  version: "0.1.0"
} as const;

export const WEBSOCKET_CONFIG = {
  heartbeatIntervalMs: 30000,
  reconnectBaseDelayMs: 1000,
  maxReconnectDelayMs: 30000,
  maxReconnectAttempts: 10
} as const;
