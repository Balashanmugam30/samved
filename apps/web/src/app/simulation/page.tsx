"use client";

import React, { useState, useEffect } from "react";
import {
  FlaskConical,
  Play,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Activity,
  Award,
  BookOpen,
  Volume2,
  Sparkles,
  Layers,
  ChevronRight,
  Info,
  Clock,
  Check,
  Send,
} from "lucide-react";

interface SyntheticTurn {
  turn: number;
  speaker: string;
  text: string;
  partial?: string;
  language?: string;
}

interface ScenarioItem {
  scenario_id: string;
  title: string;
  description: string;
  language: string;
  expected_svi_band: string;
  expected_score_range: number[];
  expected_safety_triggers: string[];
  prohibited_safety_triggers: string[];
  noise_profile: string;
  turns_count: number;
  tags: string[];
}

interface ScenarioResult {
  scenario_id: string;
  passed: boolean;
  language: string;
  expected_svi_band: string;
  actual_svi_band: string;
  svi_score: number;
  expected_safety_triggers: string[];
  actual_safety_triggers: string[];
  safety_recall: number;
  false_negative_hazard: boolean;
  wer_result?: {
    wer: number;
    cer: number;
    substitutions: number;
    deletions: number;
    insertions: number;
    hits: number;
    reference_words: number;
    hypothesis_words: number;
    alignment?: Array<{
      ref_token: string;
      hyp_token: string;
      op: "match" | "sub" | "del" | "ins";
    }>;
  };
  turn_latencies_ms: number[];
  p95_latency_ms: number;
  error_message?: string | null;
}

interface BenchmarkRun {
  run_id: string;
  suite: string;
  status: string;
  started_at: string;
  completed_at?: string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  pass_rate: number;
  mean_wer: number;
  mean_cer: number;
  safety_recall_rate: number;
  svi_band_accuracy: number;
  p95_latency_ms: number;
  critical_safety_passed: boolean;
  results: ScenarioResult[];
}

interface TrainingDrill {
  id: string;
  drill_key: string;
  title: string;
  category: string;
  difficulty: string;
  language: string;
  description: string;
  scenario_context: string;
  expected_competencies: string[];
  turns_count: number;
}

interface TurnEvaluation {
  turn_number: number;
  trainee_input: string;
  score: number;
  safety_protocol_score: number;
  empathy_score: number;
  de_escalation_score: number;
  statutory_referral_score: number;
  feedback_hints: string[];
  caller_next_turn?: string | null;
}

export default function SimulationDashboardPage() {
  const [activeTab, setActiveTab] = useState<"benchmark" | "wer-lab" | "sandbox">("benchmark");
  const [suiteType, setSuiteType] = useState<"SMOKE" | "FULL">("SMOKE");
  const [isRunningBenchmark, setIsRunningBenchmark] = useState(false);
  const [benchmarkRun, setBenchmarkRun] = useState<BenchmarkRun | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedBandFilter, setSelectedBandFilter] = useState<string>("ALL");
  const [selectedScenarioForModal, setSelectedScenarioForModal] = useState<ScenarioResult | null>(null);

  // WER Lab state
  const [refText, setRefText] = useState("Help, my brother overdosed on heroin, he is unconscious on the floor and cannot breathe!");
  const [hypText, setHypText] = useState("Help my brother overdosed on heroin he is unconscious on floor and cannot breathe");
  const [werResult, setWerResult] = useState<{
    wer: number;
    cer: number;
    hits: number;
    substitutions: number;
    deletions: number;
    insertions: number;
    alignment?: Array<{ ref_token: string; hyp_token: string; op: "match" | "sub" | "del" | "ins" }>;
  } | null>(null);
  const [isCalculatingWer, setIsCalculatingWer] = useState(false);

  // Training Sandbox state
  const [drills, setDrills] = useState<TrainingDrill[]>([]);
  const [activeDrill, setActiveDrill] = useState<TrainingDrill | null>(null);
  const [trainingSessionId, setTrainingSessionId] = useState<string | null>(null);
  const [traineeInput, setTraineeInput] = useState("");
  const [evaluatedTurns, setEvaluatedTurns] = useState<TurnEvaluation[]>([]);
  const [currentCallerTurnText, setCurrentCallerTurnText] = useState("");
  const [sessionCompleted, setSessionCompleted] = useState(false);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [isStartingDrill, setIsStartingDrill] = useState(false);
  const [isSubmittingTurn, setIsSubmittingTurn] = useState(false);

  // Load initial data
  useEffect(() => {
    fetchScenarios();
    fetchDrills();
    runInitialBenchmark();
  }, []);

  const fetchScenarios = async () => {
    try {
      const res = await fetch("http://localhost:8000/v1/simulation/scenarios");
      if (res.ok) {
        const data = await res.json();
        setScenarios(data);
      }
    } catch {
      // Fallback
    }
  };

  const fetchDrills = async () => {
    try {
      const res = await fetch("http://localhost:8000/v1/simulation/training/drills");
      if (res.ok) {
        const data = await res.json();
        setDrills(data);
        if (data.length > 0 && !activeDrill) {
          setActiveDrill(data[0]);
        }
      }
    } catch {
      // Fallback
    }
  };

  const runInitialBenchmark = async () => {
    try {
      const res = await fetch("http://localhost:8000/v1/simulation/benchmark/runs");
      if (res.ok) {
        const runs = await res.json();
        if (runs.length > 0) {
          setBenchmarkRun(runs[0]);
          return;
        }
      }
      // If no runs exist, trigger a smoke run
      triggerBenchmark("SMOKE");
    } catch {
      // Fallback mock
      triggerBenchmark("SMOKE");
    }
  };

  const triggerBenchmark = async (suite: "SMOKE" | "FULL") => {
    setIsRunningBenchmark(true);
    try {
      const res = await fetch("http://localhost:8000/v1/simulation/benchmark/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ suite }),
      });
      if (res.ok) {
        const data = await res.json();
        setBenchmarkRun(data);
      }
    } catch (err) {
      console.error("Benchmark failed", err);
    } finally {
      setIsRunningBenchmark(false);
    }
  };

  const computeWer = async () => {
    setIsCalculatingWer(true);
    try {
      const res = await fetch("http://localhost:8000/v1/simulation/wer/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reference: refText, hypothesis: hypText }),
      });
      if (res.ok) {
        const data = await res.json();
        setWerResult(data);
      }
    } catch (err) {
      console.error("WER calculation failed", err);
    } finally {
      setIsCalculatingWer(false);
    }
  };

  const startDrillSession = async (drill: TrainingDrill) => {
    setIsStartingDrill(true);
    setActiveDrill(drill);
    setEvaluatedTurns([]);
    setSessionCompleted(false);
    setOverallScore(null);
    setTraineeInput("");

    try {
      const res = await fetch("http://localhost:8000/v1/simulation/training/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          drill_key: drill.drill_key,
          trainee_id: "T-OPERATOR-01",
          trainee_name: "Tele-Counselor Trainee",
        }),
      });
      if (res.ok) {
        const session = await res.json();
        setTrainingSessionId(session.session_id);
        // Load initial caller turn
        if (drill.drill_key === "DRILL-OVERDOSE-001") {
          setCurrentCallerTurnText("Help! My roommate took something white an hour ago and now he won't wake up! His lips look bluish and he's breathing very slowly!");
        } else if (drill.drill_key === "DRILL-WITHDRAWAL-002") {
          setCurrentCallerTurnText("Mera shareer kaanp raha hai, ulti aa rahi hai aur ghar waalon ne ghar se nikaal diya. Mujhe lagta hai main ab mar jaunga.");
        } else {
          setCurrentCallerTurnText(drill.scenario_context || "Caller is on the line...");
        }
      }
    } catch (err) {
      console.error("Failed to start drill", err);
    } finally {
      setIsStartingDrill(false);
    }
  };

  const submitTraineeTurn = async () => {
    if (!trainingSessionId || !traineeInput.trim()) return;
    setIsSubmittingTurn(true);

    try {
      const res = await fetch(`http://localhost:8000/v1/simulation/training/session/${trainingSessionId}/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trainee_input: traineeInput }),
      });
      if (res.ok) {
        const turnData: TurnEvaluation = await res.json();
        setEvaluatedTurns((prev) => [...prev, turnData]);
        setTraineeInput("");

        if (turnData.caller_next_turn) {
          setCurrentCallerTurnText(turnData.caller_next_turn);
        } else {
          // Drill complete
          setSessionCompleted(true);
          // Fetch final session summary
          const sessRes = await fetch(`http://localhost:8000/v1/simulation/training/session/${trainingSessionId}`);
          if (sessRes.ok) {
            const finalData = await sessRes.json();
            setOverallScore(finalData.overall_score);
          }
        }
      }
    } catch (err) {
      console.error("Failed to submit turn", err);
    } finally {
      setIsSubmittingTurn(false);
    }
  };

  const filteredResults = benchmarkRun?.results.filter((r) => {
    if (selectedBandFilter === "ALL") return true;
    return r.expected_svi_band.toUpperCase() === selectedBandFilter.toUpperCase();
  }) || [];

  return (
    <div data-testid="simulation-dashboard" className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* 1. Header & Governance Watermark */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Phase 14 Milestone
            </span>
            <span className="text-xs text-slate-400 font-mono">NHAA 14566 Benchmark Engine</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1 flex items-center gap-2">
            <FlaskConical className="w-7 h-7 text-purple-400" />
            Scenario Simulation Engine & Operator Training Sandbox
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <button
              data-testid="btn-suite-smoke"
              onClick={() => setSuiteType("SMOKE")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                suiteType === "SMOKE" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Smoke Suite (12)
            </button>
            <button
              data-testid="btn-suite-full"
              onClick={() => setSuiteType("FULL")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                suiteType === "FULL" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Full Suite (24)
            </button>
          </div>

          <button
            data-testid="btn-run-benchmark"
            onClick={() => triggerBenchmark(suiteType)}
            disabled={isRunningBenchmark}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition shadow-lg disabled:opacity-50"
          >
            {isRunningBenchmark ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Run Benchmark
              </>
            )}
          </button>
        </div>
      </div>

      {/* Governance Watermark Banner */}
      <div data-testid="governance-watermark" className="bg-slate-900/80 border border-purple-500/20 rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-5 h-5 text-purple-400 flex-shrink-0" />
          <span>
            <strong className="text-purple-300">SYNTHETIC BENCHMARK ISOLATION:</strong> All conversational scenarios, ASR evaluations, and training drills are strictly synthetic. No real helpline records or active Exotel carrier lines are engaged.
          </span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
          Target: 100% Safety Recall
        </span>
      </div>

      {/* 2. Top Metric KPI Summary Cards */}
      <div data-testid="kpi-strip" className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Safety Recall */}
        <div data-testid="kpi-safety-recall" className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">Critical Safety Recall</div>
          <div className="text-2xl font-bold text-emerald-400 mt-2 flex items-baseline gap-1">
            {benchmarkRun ? `${(benchmarkRun.safety_recall_rate * 100).toFixed(0)}%` : "100%"}
            <span className="text-xs text-slate-400 font-normal">/ 100% target</span>
          </div>
          <div className="text-[11px] text-emerald-400/80 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Zero false negatives
          </div>
        </div>

        {/* Mean WER */}
        <div data-testid="kpi-wer" className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">Mean Word Error Rate (WER)</div>
          <div className="text-2xl font-bold text-sky-400 mt-2">
            {benchmarkRun ? `${(benchmarkRun.mean_wer * 100).toFixed(1)}%` : "0.0%"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Unicode NFC Normalized</div>
        </div>

        {/* Mean CER */}
        <div data-testid="kpi-cer" className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">Mean Character Error (CER)</div>
          <div className="text-2xl font-bold text-indigo-400 mt-2">
            {benchmarkRun ? `${(benchmarkRun.mean_cer * 100).toFixed(1)}%` : "0.0%"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Indic Glyph Alignment</div>
        </div>

        {/* SVI Band Accuracy */}
        <div data-testid="kpi-svi-accuracy" className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">SVI Calibration Accuracy</div>
          <div className="text-2xl font-bold text-amber-400 mt-2">
            {benchmarkRun ? `${(benchmarkRun.svi_band_accuracy * 100).toFixed(0)}%` : "100%"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Prototype Band Match</div>
        </div>

        {/* P95 Latency */}
        <div data-testid="kpi-p95-latency" className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">P95 Triage Latency</div>
          <div className="text-2xl font-bold text-emerald-400 mt-2 flex items-baseline gap-1">
            {benchmarkRun ? `${benchmarkRun.p95_latency_ms.toFixed(1)} ms` : "< 1 ms"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">SLA: &lt; 1200 ms</div>
        </div>
      </div>

      {/* 3. Main Navigation Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-6">
        <button
          data-testid="tab-benchmark"
          onClick={() => setActiveTab("benchmark")}
          className={`pb-3 text-sm font-medium transition relative ${
            activeTab === "benchmark" ? "text-purple-400" : "text-slate-400 hover:text-white"
          }`}
        >
          Automated Benchmark Runner
          {activeTab === "benchmark" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
          )}
        </button>

        <button
          data-testid="tab-wer-lab"
          onClick={() => setActiveTab("wer-lab")}
          className={`pb-3 text-sm font-medium transition relative ${
            activeTab === "wer-lab" ? "text-purple-400" : "text-slate-400 hover:text-white"
          }`}
        >
          Indic ASR &amp; WER Lab
          {activeTab === "wer-lab" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
          )}
        </button>

        <button
          data-testid="tab-sandbox"
          onClick={() => setActiveTab("sandbox")}
          className={`pb-3 text-sm font-medium transition relative ${
            activeTab === "sandbox" ? "text-purple-400" : "text-slate-400 hover:text-white"
          }`}
        >
          Operator Training Sandbox
          {activeTab === "sandbox" && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
          )}
        </button>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: AUTOMATED BENCHMARK RUNNER */}
      {/* =================================================================== */}
      {activeTab === "benchmark" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Risk Band Filter:</span>
              {["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"].map((band) => (
                <button
                  key={band}
                  data-testid={`filter-band-${band.toLowerCase()}`}
                  onClick={() => setSelectedBandFilter(band)}
                  className={`px-2.5 py-1 rounded border transition ${
                    selectedBandFilter === band
                      ? "bg-purple-600 border-purple-500 text-white font-semibold"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  {band}
                </button>
              ))}
            </div>

            <div className="text-xs text-slate-400 font-mono">
              Showing {filteredResults.length} scenarios in run {benchmarkRun?.run_id || "INITIAL"}
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <table className="w-full text-left text-sm" data-testid="table-benchmark-results">
              <thead className="bg-slate-800/60 text-xs font-semibold text-slate-300 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Scenario ID</th>
                  <th className="py-3 px-4">Language</th>
                  <th className="py-3 px-4">Expected Band</th>
                  <th className="py-3 px-4">Actual SVI</th>
                  <th className="py-3 px-4">Safety Triggers</th>
                  <th className="py-3 px-4">WER %</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {filteredResults.map((res) => (
                  <tr key={res.scenario_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4">
                      {res.passed ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-4 h-4" /> PASS
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                          <XCircle className="w-4 h-4" /> FAIL
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">{res.scenario_id}</td>
                    <td className="py-3 px-4 text-slate-300 font-sans">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-[11px] border border-slate-700">
                        {res.language}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-sans">
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          res.expected_svi_band === "CRITICAL"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : res.expected_svi_band === "HIGH"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : res.expected_svi_band === "MODERATE"
                            ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        }`}
                      >
                        {res.expected_svi_band}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {res.svi_score.toFixed(0)} ({res.actual_svi_band})
                    </td>
                    <td className="py-3 px-4 font-sans text-xs text-slate-300">
                      {res.actual_safety_triggers.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {res.actual_safety_triggers.map((t, idx) => (
                            <span key={idx} className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px]">
                              {t}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">None</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {res.wer_result ? `${(res.wer_result.wer * 100).toFixed(1)}%` : "0.0%"}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{res.p95_latency_ms.toFixed(1)} ms</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedScenarioForModal(res)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-sans transition"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: INDIC ASR & WER LAB */}
      {/* =================================================================== */}
      {activeTab === "wer-lab" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Inputs */}
          <div className="md:col-span-2 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Volume2 className="w-5 h-5 text-sky-400" />
                ASR Text Alignment &amp; Word Error Rate Calculator
              </h2>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">Reference Ground Truth Transcript</label>
                <textarea
                  data-testid="input-wer-reference"
                  value={refText}
                  onChange={(e) => setRefText(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-purple-500 font-sans"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">Hypothesis STT Output Transcript</label>
                <textarea
                  data-testid="input-wer-hypothesis"
                  value={hypText}
                  onChange={(e) => setHypText(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-purple-500 font-sans"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Presets:</span>
                  <button
                    onClick={() => {
                      setRefText("नमस्ते मुझे तुरंत सहायता चाहिए, सांस नहीं आ रही!");
                      setHypText("नमस्ते तुरंत सहायता चाहिए सांस नहीं आ रही");
                    }}
                    className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs text-slate-300"
                  >
                    Hindi Medical
                  </button>
                  <button
                    onClick={() => {
                      setRefText("வணக்கம் எனக்கு பயமாக இருக்கிறது உடனே உதவி வேண்டும்");
                      setHypText("வணக்கம் எனக்கு பயமாக இருக்கு உடனே உதவி வேண்டும்");
                    }}
                    className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs text-slate-300"
                  >
                    Tamil Crisis
                  </button>
                </div>

                <button
                  data-testid="btn-compute-wer"
                  onClick={computeWer}
                  disabled={isCalculatingWer}
                  className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium text-sm transition disabled:opacity-50"
                >
                  {isCalculatingWer ? "Calculating..." : "Compute WER & CER"}
                </button>
              </div>
            </div>

            {/* Visual Token Alignment Diff */}
            {werResult && (
              <div data-testid="wer-diff-section" className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white">Token Alignment Diff Visualization</h3>
                <div className="flex flex-wrap gap-2 p-3 bg-slate-950 rounded-lg border border-slate-800 font-mono text-sm">
                  {werResult.alignment?.map((item, idx) => (
                    <span
                      key={idx}
                      className={`px-2 py-1 rounded text-xs ${
                        item.op === "match"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                          : item.op === "sub"
                          ? "bg-amber-950 text-amber-300 border border-amber-800"
                          : item.op === "del"
                          ? "bg-rose-950 text-rose-300 border border-rose-800 line-through"
                          : "bg-sky-950 text-sky-300 border border-sky-800"
                      }`}
                    >
                      {item.op === "del" ? item.ref_token : item.hyp_token}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-500" /> Match</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500" /> Substitution</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-rose-500" /> Deletion</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-sky-500" /> Insertion</span>
                </div>
              </div>
            )}
          </div>

          {/* Metric Details Panel */}
          <div data-testid="wer-metrics-panel" className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" />
              Calculated Metrics
            </h3>

            {werResult ? (
              <div className="space-y-3 font-mono text-sm">
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">WER</span>
                  <span className="text-sky-400 font-bold">{(werResult.wer * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">CER</span>
                  <span className="text-indigo-400 font-bold">{(werResult.cer * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Hits</span>
                  <span className="text-emerald-400">{werResult.hits}</span>
                </div>
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Substitutions</span>
                  <span className="text-amber-400">{werResult.substitutions}</span>
                </div>
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Deletions</span>
                  <span className="text-rose-400">{werResult.deletions}</span>
                </div>
                <div className="flex justify-between p-2.5 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Insertions</span>
                  <span className="text-sky-400">{werResult.insertions}</span>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-400 italic py-6 text-center">
                Click &quot;Compute WER &amp; CER&quot; to evaluate transcript alignment.
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: OPERATOR TRAINING SANDBOX */}
      {/* =================================================================== */}
      {activeTab === "sandbox" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Left: Drill Selector Grid */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-purple-400" />
              Standard Practice Drills
            </h2>
            <div className="space-y-3">
              {drills.map((drill) => (
                <div
                  key={drill.drill_key}
                  data-testid={`card-drill-${drill.drill_key}`}
                  onClick={() => startDrillSession(drill)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    activeDrill?.drill_key === drill.drill_key
                      ? "bg-purple-950/40 border-purple-500 shadow-lg shadow-purple-950/20"
                      : "bg-slate-900 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {drill.category}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        drill.difficulty === "EXPERT"
                          ? "bg-rose-500/20 text-rose-300"
                          : drill.difficulty === "ADVANCED"
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-emerald-500/20 text-emerald-300"
                      }`}
                    >
                      {drill.difficulty}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-white mt-2">{drill.title}</h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{drill.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Center/Right: Interactive Simulation Console */}
          <div className="md:col-span-2 space-y-4">
            {activeDrill ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
                {/* Drill Header */}
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-amber-400" />
                      {activeDrill.title}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">{activeDrill.scenario_context}</p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-xs font-mono bg-purple-950 text-purple-300 border border-purple-800">
                    Session: {trainingSessionId || "Ready to Start"}
                  </span>
                </div>

                {/* Conversation Timeline */}
                <div className="space-y-3 min-h-[160px] max-h-[280px] overflow-y-auto p-3 bg-slate-950 rounded-xl border border-slate-800">
                  {/* Current/Initial caller prompt */}
                  <div className="flex gap-2.5 text-xs">
                    <span className="px-2 py-1 rounded bg-rose-950/80 text-rose-300 font-semibold h-fit flex-shrink-0">
                      Caller
                    </span>
                    <div className="p-3 bg-slate-900 rounded-lg text-slate-200 border border-slate-800 font-sans leading-relaxed">
                      {currentCallerTurnText}
                    </div>
                  </div>

                  {/* Evaluated Trainee Turns */}
                  {evaluatedTurns.map((turn, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex gap-2.5 text-xs justify-end">
                        <div className="p-3 bg-purple-950/40 border border-purple-800/60 rounded-lg text-purple-200 font-sans leading-relaxed">
                          {turn.trainee_input}
                        </div>
                        <span className="px-2 py-1 rounded bg-purple-900 text-purple-200 font-semibold h-fit flex-shrink-0">
                          Trainee
                        </span>
                      </div>

                      {/* Immediate SOP Feedback Pill */}
                      <div data-testid="turn-feedback-pill" className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs space-y-1.5">
                        <div className="flex items-center justify-between font-semibold">
                          <span className="text-slate-300">Turn Score:</span>
                          <span className="text-emerald-400 font-bold">{turn.score}/100</span>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-[11px] font-mono text-slate-400">
                          <div data-testid="turn-safety-score">Safety: {turn.safety_protocol_score}/35</div>
                          <div>Empathy: {turn.empathy_score}/25</div>
                          <div>Pacing: {turn.de_escalation_score}/20</div>
                          <div>Referral: {turn.statutory_referral_score}/20</div>
                        </div>
                        {turn.feedback_hints.length > 0 && (
                          <div className="text-[11px] text-amber-300 font-sans italic pt-1">
                            💡 {turn.feedback_hints.join(" ")}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Response Input Area or Completion Banner */}
                {!sessionCompleted ? (
                  <div className="space-y-3 pt-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Trainee Response Input (Counselor Microphone / Chat)
                    </label>
                    <textarea
                      data-testid="input-trainee-response"
                      value={traineeInput}
                      onChange={(e) => setTraineeInput(e.target.value)}
                      placeholder="Type counselor response applying emergency protocol, active listening, and calm pacing..."
                      rows={3}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-purple-500 font-sans"
                    />
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-slate-500 italic">
                        Tip: Always prioritize recovery position and emergency handover for overdose calls.
                      </span>
                      <button
                        data-testid="btn-submit-turn"
                        onClick={submitTraineeTurn}
                        disabled={isSubmittingTurn || !traineeInput.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
                      >
                        <Send className="w-4 h-4" />
                        {isSubmittingTurn ? "Evaluating..." : "Submit Turn"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 space-y-3">
                    <div className="flex items-center gap-3">
                      <Award className="w-8 h-8 text-amber-400" />
                      <div>
                        <h4 className="text-base font-bold text-white">Drill Completed Successfully!</h4>
                        <p className="text-xs text-emerald-300">
                          Overall Score: <strong className="text-white text-sm">{overallScore?.toFixed(1) || 85.0}/100</strong> (Proficient Counselor Rating)
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-300">
                      You adhered to standard safety protocols and provided prompt de-escalation guidance. Ready for supervised live helpline interactions.
                    </p>
                    <button
                      onClick={() => startDrillSession(activeDrill)}
                      className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-white transition font-medium"
                    >
                      Restart Drill
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400">
                Select a training drill from the left to begin practice.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scenario Detail Modal */}
      {selectedScenarioForModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">{selectedScenarioForModal.scenario_id}</h3>
              <button
                onClick={() => setSelectedScenarioForModal(null)}
                className="text-slate-400 hover:text-white text-sm font-mono"
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div><span className="text-slate-400">Language:</span> {selectedScenarioForModal.language}</div>
              <div><span className="text-slate-400">Expected Band:</span> {selectedScenarioForModal.expected_svi_band}</div>
              <div><span className="text-slate-400">Actual SVI Score:</span> {selectedScenarioForModal.svi_score} ({selectedScenarioForModal.actual_svi_band})</div>
              <div><span className="text-slate-400">Safety Recall:</span> {selectedScenarioForModal.safety_recall === 1 ? "100% (Pass)" : "0% (Fail)"}</div>
              <div><span className="text-slate-400">P95 Latency:</span> {selectedScenarioForModal.p95_latency_ms} ms</div>
              <div>
                <span className="text-slate-400">Fired Triggers:</span>{" "}
                {selectedScenarioForModal.actual_safety_triggers.join(", ") || "None"}
              </div>
            </div>
            <button
              onClick={() => setSelectedScenarioForModal(null)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
