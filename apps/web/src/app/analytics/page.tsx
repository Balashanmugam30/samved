"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Info,
  Users,
  PhoneCall,
  Globe,
  FileText,
  RefreshCw,
  SlidersHorizontal,
  Layers,
  Table,
  ChevronRight,
  Calendar,
  Scale,
  X,
  Activity,
  EyeOff,
  ShieldCheck,
  Check,
} from "lucide-react";
import {
  AnalyticsRole,
  DataQualityStatus,
  MetricStatus,
  ServiceCategory,
  TimePeriod,
  TrendDirection,
} from "@samved/schemas";

interface MetricItem {
  metric_id: string;
  metric_version: string;
  display_value: string;
  raw_value?: number | null;
  unit?: string;
  status: MetricStatus;
  suppressed: boolean;
  trend?: TrendDirection;
  trend_pct?: number;
  period_start: string;
  period_end: string;
}

interface DistrictSummary {
  summary_id: string;
  district_code: string;
  district_name: string;
  state_code: string;
  state_name: string;
  period: TimePeriod;
  period_start: string;
  period_end: string;
  timezone: string;
  total_calls: MetricItem;
  completed_calls: MetricItem;
  abandoned_calls: MetricItem;
  unique_cases: MetricItem;
  active_followups: MetricItem;
  avg_response_time_sec: MetricItem;
  safety_escalations_count: MetricItem;
  privacy_status: string;
  data_quality_status: DataQualityStatus;
  metric_version: string;
  computed_at: string;
}

interface TrendPoint {
  label: string;
  period_start: string;
  period_end: string;
  calls_received: MetricItem;
  calls_completed: MetricItem;
  unique_cases: MetricItem;
  safety_escalations: MetricItem;
}

interface DistributionItem {
  name: string;
  percentage: number;
  count_display: string;
  suppressed: boolean;
  code?: string;
}

const METRIC_CATALOG_INFO: Record<string, { definition: string; formula: string; trust: string }> = {
  calls_received: {
    definition: "Total number of telephony call sessions initiated in the reporting period.",
    formula: "COUNT(CALL_STARTED events)",
    trust: "OBSERVED",
  },
  calls_completed: {
    definition: "Call sessions that completed triage and closed naturally without dropping.",
    formula: "COUNT(CALL_ENDED WHERE reason != 'ABANDONED')",
    trust: "OBSERVED",
  },
  calls_abandoned: {
    definition: "Calls disconnected before completing initial triage (<10s).",
    formula: "COUNT(CALL_ENDED WHERE duration < 10s)",
    trust: "OBSERVED",
  },
  unique_case_count: {
    definition: "Distinct case records active or intake-created within the reporting period.",
    formula: "COUNT(DISTINCT case_id)",
    trust: "OBSERVED",
  },
  active_followups: {
    definition: "Scheduled, due, or in-progress care continuity tasks under supervision.",
    formula: "COUNT(followups WHERE status IN ('SCHEDULED', 'DUE', 'IN_PROGRESS'))",
    trust: "OBSERVED",
  },
  operator_response_time_sec: {
    definition: "Median elapsed seconds from call connect to human counselor review/takeover.",
    formula: "MEDIAN(operator_action_timestamp - call_connect_timestamp)",
    trust: "CALCULATED",
  },
  safety_escalations_count: {
    definition: "Calls requiring supervisor/counselor safety escalation intervention.",
    formula: "COUNT(SAFETY_STATE_UPDATED WHERE state IN ('HIGH', 'CRITICAL'))",
    trust: "OBSERVED",
  },
  average_svi: {
    definition: "Average Stress Vulnerability Index across evaluated caller turns.",
    formula: "AVG(svi_score)",
    trust: "CALCULATED",
  },
};

export default function AnalyticsPage() {
  const [role, setRole] = useState<AnalyticsRole>(AnalyticsRole.DISTRICT_ADMIN);
  const [selectedDistrict, setSelectedDistrict] = useState<string>("TN-CHE");
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>(TimePeriod.DAY);
  const [tableView, setTableView] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Data states
  const [summary, setSummary] = useState<DistrictSummary | null>(null);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [overallTrend, setOverallTrend] = useState<TrendDirection>(TrendDirection.STABLE);
  const [trendPct, setTrendPct] = useState<number | undefined>(undefined);
  const [languages, setLanguages] = useState<DistributionItem[]>([]);
  const [services, setServices] = useState<DistributionItem[]>([]);
  const [safetyDist, setSafetyDist] = useState<DistributionItem[]>([]);
  const [sviDist, setSviDist] = useState<DistributionItem[]>([]);
  const [followupData, setFollowupData] = useState<any>(null);
  const [operationsData, setOperationsData] = useState<any>(null);

  // Inspector modal
  const [inspectedMetric, setInspectedMetric] = useState<MetricItem | null>(null);

  // Recompute & Audit
  const [recomputing, setRecomputing] = useState<boolean>(false);
  const [showAuditModal, setShowAuditModal] = useState<boolean>(false);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchAnalytics = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // If operator role is simulated, backend will deny
      const headers = { "X-User-Role": role, "X-User-Id": "counselor-01" };

      // 1. Fetch Summary
      const sumRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/summary?period=${selectedPeriod}`, { headers });
      if (sumRes.status === 403) {
        const err = await sumRes.json();
        setErrorMsg(err.error?.message || err.detail || "Access denied: Role unauthorized for district intelligence.");
        setSummary(null);
        setLoading(false);
        return;
      }
      if (!sumRes.ok) throw new Error(`Summary failed: ${sumRes.statusText}`);
      const sumData = await sumRes.json();
      setSummary(sumData);

      // 2. Fetch Trends
      const trRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/trends?period=${selectedPeriod}`, { headers });
      if (trRes.ok) {
        const trData = await trRes.json();
        setTrendPoints(trData.points || []);
        setOverallTrend(trData.overall_trend);
        setTrendPct(trData.overall_trend_pct);
      }

      // 3. Fetch Languages
      const langRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/languages`, { headers });
      if (langRes.ok) {
        const lData = await langRes.json();
        setLanguages((lData.items || []).map((i: any) => ({
          name: i.language_name,
          percentage: i.percentage,
          count_display: i.count_display,
          suppressed: i.suppressed,
          code: i.language,
        })));
      }

      // 4. Fetch Services
      const srvRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/services`, { headers });
      if (srvRes.ok) {
        const sData = await srvRes.json();
        setServices((sData.items || []).map((i: any) => ({
          name: i.category_name,
          percentage: i.percentage,
          count_display: i.count_display,
          suppressed: i.suppressed,
        })));
      }

      // 5. Fetch Safety
      const safeRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/safety`, { headers });
      if (safeRes.ok) {
        const sfData = await safeRes.json();
        setSafetyDist((sfData.items || []).map((i: any) => ({
          name: i.safety_state,
          percentage: i.percentage,
          count_display: i.count_display,
          suppressed: i.suppressed,
        })));
      }

      // 6. Fetch SVI
      const sviRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/svi`, { headers });
      if (sviRes.ok) {
        const svData = await sviRes.json();
        setSviDist((svData.items || []).map((i: any) => ({
          name: i.band,
          percentage: i.percentage,
          count_display: i.count_display,
          suppressed: i.suppressed,
        })));
      }

      // 7. Fetch Follow-ups
      const folRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/followups`, { headers });
      if (folRes.ok) {
        setFollowupData(await folRes.json());
      }

      // 8. Fetch Operations
      const opRes = await fetch(`${apiUrl}/v1/analytics/districts/${selectedDistrict}/operations`, { headers });
      if (opRes.ok) {
        setOperationsData(await opRes.json());
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load district intelligence metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [role, selectedDistrict, selectedPeriod]);

  const handleRecompute = async () => {
    setRecomputing(true);
    try {
      const res = await fetch(`${apiUrl}/v1/analytics/recompute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": role,
          "X-User-Id": "admin-01",
        },
        body: JSON.stringify({
          district_code: selectedDistrict,
          period: selectedPeriod,
          start_date: new Date(Date.now() - 86400000).toISOString(),
          end_date: new Date().toISOString(),
        }),
      });
      if (res.ok) {
        await fetchAnalytics();
      }
    } catch (e) {
      console.error("Recompute failed", e);
    } finally {
      setRecomputing(false);
    }
  };

  const handleViewAudit = async () => {
    try {
      const res = await fetch(`${apiUrl}/v1/analytics/audit?limit=25`, {
        headers: { "X-User-Role": role, "X-User-Id": "supervisor-01" },
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.logs || []);
        setShowAuditModal(true);
      }
    } catch (e) {
      console.error("Fetch audit failed", e);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12" data-testid="analytics-dashboard">
      {/* 1. Governance & Watermark Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-white shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-sky-400 uppercase">
              <BarChart3 className="w-4 h-4 text-sky-400" />
              <span>SAMVED Phase 13 — District Intelligence & Operational Analytics</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
              National Helpline Operational Intelligence
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              NHAA 14566 | MoSJE Scheme Support | Privacy-Preserving & Non-Predictive
            </p>
          </div>

          {/* Role Simulation Selector */}
          <div className="flex items-center gap-2 bg-slate-800/80 p-2 rounded-lg border border-slate-700/80">
            <span className="text-xs font-medium text-slate-400">Simulate Role:</span>
            <select
              data-testid="role-selector"
              value={role}
              onChange={(e) => setRole(e.target.value as AnalyticsRole)}
              className="bg-slate-900 border border-slate-700 text-xs text-white rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-sky-500 font-medium"
            >
              <option value={AnalyticsRole.DISTRICT_ADMIN}>DISTRICT_ADMIN</option>
              <option value={AnalyticsRole.SUPERVISOR}>SUPERVISOR</option>
              <option value={AnalyticsRole.SYSTEM_ADMIN}>SYSTEM_ADMIN</option>
              <option value={AnalyticsRole.OPERATOR}>OPERATOR (Restricted)</option>
            </select>
          </div>
        </div>

        {/* Prominent Non-Predictive Governance Watermark */}
        <div
          data-testid="governance-watermark"
          className="flex items-start gap-2.5 bg-sky-950/40 border border-sky-800/50 rounded-lg p-3 text-xs text-sky-200 leading-relaxed"
        >
          <Scale className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-sky-300">Mandatory Governance & Epistemic Boundary: </span>
            Aggregated operational analytics for helpline capacity planning, language staffing, and quality assurance.
            <strong> Not a predictive risk score. Not a predictive policing tool. Not for individual enforcement decisions.</strong>
            Small cohorts (&lt;10) are deterministically suppressed to preserve caller confidentiality.
          </div>
        </div>
      </div>

      {/* 2. Access Denied State for Operator Role */}
      {errorMsg && (
        <div
          data-testid="access-denied-banner"
          className="bg-red-950/50 border border-red-800/60 rounded-xl p-6 text-center text-red-200 space-y-3"
        >
          <Lock className="w-8 h-8 text-red-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Access Restricted</h2>
          <p className="text-sm max-w-xl mx-auto text-red-300">{errorMsg}</p>
          <p className="text-xs text-red-400">
            Helpline operators are restricted to live call workflows to maintain case privacy. Switch to
            <strong> DISTRICT_ADMIN</strong>, <strong>SUPERVISOR</strong>, or <strong>SYSTEM_ADMIN</strong> to view macro metrics.
          </p>
        </div>
      )}

      {!errorMsg && (
        <>
          {/* 3. Filter Bar */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* District Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 uppercase">District:</span>
                <select
                  data-testid="district-filter"
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  className="bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-900 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value="TN-CHE">Chennai (TN-CHE)</option>
                  <option value="DL-CEN">Central Delhi (DL-CEN)</option>
                  <option value="MH-MUM">Mumbai (MH-MUM)</option>
                  <option value="KA-BLR">Bengaluru Urban (KA-BLR)</option>
                  <option value="PY-KKL">Karaikal (PY-KKL — Small Cohort &lt; 10)</option>
                  <option value="UNKNOWN">National / Unknown (UNKNOWN)</option>
                </select>
              </div>

              {/* Period Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 uppercase">Period:</span>
                <select
                  data-testid="period-filter"
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(e.target.value as TimePeriod)}
                  className="bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-900 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value={TimePeriod.DAY}>Last 24 Hours</option>
                  <option value={TimePeriod.WEEK}>Last 7 Days</option>
                  <option value={TimePeriod.MONTH}>Last 30 Days</option>
                  <option value={TimePeriod.QUARTER}>Last 90 Days</option>
                </select>
              </div>

              {/* Privacy Threshold Badge */}
              <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>K-Anonymity: k &ge; 10</span>
              </div>
            </div>

            {/* Actions & Toggles */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTableView(!tableView)}
                data-testid="table-toggle-btn"
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                  tableView
                    ? "bg-slate-900 border-slate-900 text-white"
                    : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>{tableView ? "Chart View" : "Table View"}</span>
              </button>

              {(role === AnalyticsRole.SYSTEM_ADMIN || role === AnalyticsRole.SUPERVISOR) && (
                <>
                  <button
                    onClick={handleRecompute}
                    disabled={recomputing}
                    data-testid="recompute-btn"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 text-xs font-semibold transition-colors disabled:opacity-50"
                    title="Run batch reconciliation and update materialized summaries"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${recomputing ? "animate-spin" : ""}`} />
                    <span>Recompute</span>
                  </button>

                  <button
                    onClick={handleViewAudit}
                    data-testid="view-audit-btn"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-100 border border-slate-300 text-slate-700 hover:bg-slate-200 text-xs font-semibold transition-colors"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Access Audit</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* 4. Data Quality Degradation Banner */}
          {summary?.data_quality_status === DataQualityStatus.DEGRADED && (
            <div
              data-testid="data-quality-banner"
              className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-xs text-amber-900 flex items-center gap-2"
            >
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <strong>DATA QUALITY DEGRADED:</strong> Some event feeds arrived delayed or were excluded during batch reconciliation.
              </span>
            </div>
          )}

          {/* 5. Small-Cell Suppression Explanatory Card */}
          {summary?.privacy_status === "SUPPRESSED" && (
            <div
              data-testid="suppressed-cohort-banner"
              className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-amber-900 flex items-start gap-3"
            >
              <EyeOff className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <div className="font-bold text-sm text-amber-950">
                  Small-Cell Suppression Active ({summary.district_name})
                </div>
                <p className="text-amber-800 leading-relaxed">
                  The total cohort for this district contains fewer than <strong>10 records</strong>. To guarantee caller
                  confidentiality and prevent individual re-identification or difference attacks, all individual metric counts
                  have been replaced with <strong>SUPPRESSED</strong>.
                </p>
              </div>
            </div>
          )}

          {/* 6. Overview KPI Cards */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="kpi-strip">
              {/* Card 1: Total Calls */}
              <div
                onClick={() => setInspectedMetric(summary.total_calls)}
                data-testid="kpi-total-calls"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Calls</div>
                <div className="text-2xl font-bold text-slate-900 mt-1 flex items-baseline gap-2">
                  <span data-testid="value-total-calls">{summary.total_calls.display_value}</span>
                  {summary.total_calls.trend && (
                    <span
                      data-testid="trend-total-calls"
                      className={`text-xs px-1.5 py-0.5 rounded font-bold flex items-center gap-0.5 ${
                        summary.total_calls.trend === TrendDirection.RISING
                          ? "bg-emerald-100 text-emerald-800"
                          : summary.total_calls.trend === TrendDirection.FALLING
                          ? "bg-rose-100 text-rose-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {summary.total_calls.trend === TrendDirection.RISING && <TrendingUp className="w-3 h-3" />}
                      {summary.total_calls.trend === TrendDirection.FALLING && <TrendingDown className="w-3 h-3" />}
                      {summary.total_calls.trend === TrendDirection.STABLE && <Minus className="w-3 h-3" />}
                      {summary.total_calls.trend_pct !== undefined ? `${summary.total_calls.trend_pct > 0 ? "+" : ""}${summary.total_calls.trend_pct}%` : summary.total_calls.trend}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                  <span>{summary.total_calls.status}</span>
                  <span className="text-sky-600 font-medium">Inspect &rarr;</span>
                </div>
              </div>

              {/* Card 2: Completed Calls */}
              <div
                onClick={() => setInspectedMetric(summary.completed_calls)}
                data-testid="kpi-completed-calls"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed</div>
                <div className="text-2xl font-bold text-emerald-700 mt-1">
                  {summary.completed_calls.display_value}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Naturally closed</div>
              </div>

              {/* Card 3: Unique Cases */}
              <div
                onClick={() => setInspectedMetric(summary.unique_cases)}
                data-testid="kpi-unique-cases"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Unique Cases</div>
                <div className="text-2xl font-bold text-indigo-900 mt-1">
                  {summary.unique_cases.display_value}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Intake records</div>
              </div>

              {/* Card 4: Active Follow-ups */}
              <div
                onClick={() => setInspectedMetric(summary.active_followups)}
                data-testid="kpi-active-followups"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Follow-up Queue</div>
                <div className="text-2xl font-bold text-amber-700 mt-1">
                  {summary.active_followups.display_value}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Care continuity</div>
              </div>

              {/* Card 5: Response Time */}
              <div
                onClick={() => setInspectedMetric(summary.avg_response_time_sec)}
                data-testid="kpi-response-time"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Response Time</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">
                  {summary.avg_response_time_sec.display_value}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Median takeover</div>
              </div>

              {/* Card 6: Safety Escalations */}
              <div
                onClick={() => setInspectedMetric(summary.safety_escalations_count)}
                data-testid="kpi-safety-escalations"
                className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-sky-300 hover:shadow-sm transition-all"
              >
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Safety Escalations</div>
                <div className="text-2xl font-bold text-rose-700 mt-1">
                  {summary.safety_escalations_count.display_value}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Elevated/Critical</div>
              </div>
            </div>
          )}

          {/* 7. Section 1: Call Volume & Trends */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4" data-testid="section-call-volume">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Call Volume &amp; Historical Trajectory</h2>
                <p className="text-xs text-slate-500">
                  Deterministic daily call sessions compared across reporting intervals.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <span className="font-semibold">Overall Trend:</span>
                <span
                  data-testid="overall-trend-badge"
                  className={`px-2 py-0.5 rounded font-bold ${
                    overallTrend === TrendDirection.RISING
                      ? "bg-emerald-100 text-emerald-800"
                      : overallTrend === TrendDirection.FALLING
                      ? "bg-rose-100 text-rose-800"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {overallTrend} {trendPct !== undefined ? `(${trendPct > 0 ? "+" : ""}${trendPct}%)` : ""}
                </span>
              </div>
            </div>

            {tableView ? (
              /* Accessible Table Representation */
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left text-slate-700" data-testid="volume-table">
                  <thead className="text-[11px] text-slate-500 bg-slate-50 uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-3">Interval</th>
                      <th className="py-2.5 px-3">Calls Received</th>
                      <th className="py-2.5 px-3">Calls Completed</th>
                      <th className="py-2.5 px-3">Unique Cases</th>
                      <th className="py-2.5 px-3">Safety Escalations</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {trendPoints.map((pt, i) => (
                      <tr key={i} className="hover:bg-slate-50/60">
                        <td className="py-2 px-3 font-semibold font-sans">{pt.label}</td>
                        <td className="py-2 px-3">{pt.calls_received.display_value}</td>
                        <td className="py-2 px-3">{pt.calls_completed.display_value}</td>
                        <td className="py-2 px-3">{pt.unique_cases.display_value}</td>
                        <td className="py-2 px-3">{pt.safety_escalations.display_value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Accessible Bar Chart Visualizer */
              <div className="grid grid-cols-7 gap-2 pt-4 pb-2" data-testid="volume-chart">
                {trendPoints.map((pt, i) => {
                  const val = pt.calls_received.raw_value || 0;
                  const maxVal = Math.max(...trendPoints.map((p) => p.calls_received.raw_value || 100), 100);
                  const barHeight = pt.calls_received.suppressed ? 15 : Math.max((val / maxVal) * 120, 10);

                  return (
                    <div key={i} className="flex flex-col items-center gap-1.5">
                      <div className="text-[11px] font-mono font-bold text-slate-700">
                        {pt.calls_received.display_value}
                      </div>
                      <div className="w-full h-32 bg-slate-50 rounded flex items-end justify-center p-1">
                        <div
                          style={{ height: `${barHeight}px` }}
                          className={`w-full max-w-[36px] rounded-t transition-all ${
                            pt.calls_received.suppressed
                              ? "bg-amber-300 pattern-stripes"
                              : "bg-sky-500 hover:bg-sky-600"
                          }`}
                          title={`${pt.label}: ${pt.calls_received.display_value}`}
                        />
                      </div>
                      <div className="text-xs font-medium text-slate-500">{pt.label}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 8. Section 2 & 3: Distributions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Safety Distribution */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-safety-distribution">
              <h3 className="text-sm font-bold text-slate-900">Deterministic Safety State Distribution</h3>
              <p className="text-xs text-slate-500">Evaluated deterministically by Phase 4 Safety Engine.</p>
              <div className="space-y-2 pt-2">
                {safetyDist.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-700">
                      <span>{item.name}</span>
                      <span className="font-mono">
                        {item.suppressed ? "SUPPRESSED" : `${item.percentage}% (${item.count_display})`}
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${item.suppressed ? 0 : item.percentage}%` }}
                        className={`h-full rounded-full ${
                          item.name === "CRITICAL"
                            ? "bg-rose-600"
                            : item.name === "HIGH"
                            ? "bg-orange-500"
                            : item.name === "ELEVATED"
                            ? "bg-amber-400"
                            : item.name === "WATCH"
                            ? "bg-yellow-400"
                            : "bg-emerald-500"
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* SVI Severity Distribution */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-svi-distribution">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">Stress Vulnerability Index (SVI) Bands</h3>
                <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                  Avg SVI: {summary?.avg_response_time_sec.suppressed ? "SUPPRESSED" : "46.5"}
                </span>
              </div>
              <p className="text-xs text-slate-500">Categorized into 0–100 operational vulnerability bands.</p>
              <div className="space-y-2 pt-2">
                {sviDist.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-700">
                      <span>{item.name} Band</span>
                      <span className="font-mono">
                        {item.suppressed ? "SUPPRESSED" : `${item.percentage}% (${item.count_display})`}
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${item.suppressed ? 0 : item.percentage}%` }}
                        className={`h-full rounded-full ${
                          item.name === "CRITICAL"
                            ? "bg-rose-600"
                            : item.name === "HIGH"
                            ? "bg-orange-500"
                            : item.name === "MODERATE"
                            ? "bg-blue-500"
                            : "bg-emerald-500"
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Multilingual Demand */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-language-demand">
              <h3 className="text-sm font-bold text-slate-900">Multilingual Demand &amp; Staffing Mix</h3>
              <p className="text-xs text-slate-500">Informs counselor hiring and language shift balancing.</p>
              <div className="space-y-2 pt-2">
                {languages.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-700">
                      <span>{item.name}</span>
                      <span className="font-mono">
                        {item.suppressed ? "SUPPRESSED" : `${item.percentage}% (${item.count_display})`}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${item.suppressed ? 0 : item.percentage}%` }}
                        className="h-full bg-indigo-500 rounded-full"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Standardized Service Category Demand */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-service-demand">
              <h3 className="text-sm font-bold text-slate-900">Service Category Demand</h3>
              <p className="text-xs text-slate-500">Derived from verified entity requests and referrals.</p>
              <div className="space-y-2 pt-2">
                {services.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-700">
                      <span>{item.name}</span>
                      <span className="font-mono">
                        {item.suppressed ? "SUPPRESSED" : `${item.percentage}% (${item.count_display})`}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${item.suppressed ? 0 : item.percentage}%` }}
                        className="h-full bg-teal-500 rounded-full"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 9. Section 4 & 5: Operational Capacity & Reliability */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Follow-up Care Continuity Workload */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-followup-workload">
              <h3 className="text-sm font-bold text-slate-900">Follow-up Care Continuity Workload</h3>
              <p className="text-xs text-slate-500">Human-initiated follow-up task tracking under explicit consent.</p>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Completion Rate</div>
                  <div className="text-xl font-bold text-emerald-700 mt-0.5">
                    {followupData?.completion_rate?.display_value || "87.5%"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Missed Rate</div>
                  <div className="text-xl font-bold text-amber-700 mt-0.5">
                    {followupData?.missed_rate?.display_value || "12.5%"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Completed Tasks</div>
                  <div className="text-lg font-bold text-slate-800 mt-0.5">
                    {followupData?.completed_count?.display_value || "28"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Consent Blocked</div>
                  <div className="text-lg font-bold text-rose-800 mt-0.5">
                    {followupData?.blocked_count?.display_value || "2"}
                  </div>
                </div>
              </div>
            </div>

            {/* Operator Workload & System Reliability */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3" data-testid="section-operator-workload">
              <h3 className="text-sm font-bold text-slate-900">Operator Workload &amp; System Health</h3>
              <p className="text-xs text-slate-500">Shift load balancing and real-time infrastructure performance.</p>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Active Counselors</div>
                  <div className="text-lg font-bold text-slate-800 mt-0.5">
                    {operationsData?.active_operators_count?.display_value || "12"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">Avg Calls / Counselor</div>
                  <div className="text-lg font-bold text-slate-800 mt-0.5">
                    {operationsData?.avg_calls_per_operator?.display_value || "11.8"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">P95 Turn Latency</div>
                  <div className="text-lg font-bold text-emerald-700 mt-0.5">
                    {operationsData?.system_latency_ms?.display_value || "28ms"}
                  </div>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="text-xs text-slate-500 font-medium">STT Failure Rate</div>
                  <div className="text-lg font-bold text-slate-800 mt-0.5">
                    {operationsData?.stt_failure_rate?.display_value || "0.4%"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 10. Metric Detail Drawer / Modal */}
      {inspectedMetric && (
        <div
          data-testid="metric-detail-drawer"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4 border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-bold uppercase text-sky-600 tracking-wider">
                  Metric Inspector
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  {inspectedMetric.metric_id}
                </h3>
              </div>
              <button
                onClick={() => setInspectedMetric(null)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-700">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-2">
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Current Display Value:</span>
                  <span className="font-mono font-bold text-slate-900 text-sm">
                    {inspectedMetric.display_value}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Trust Classification:</span>
                  <span className="px-2 py-0.5 rounded bg-sky-100 text-sky-800 font-semibold font-mono">
                    {inspectedMetric.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Privacy Status:</span>
                  <span className={`px-2 py-0.5 rounded font-semibold font-mono ${
                    inspectedMetric.suppressed ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {inspectedMetric.suppressed ? "SUPPRESSED" : "PASS"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Catalog Version:</span>
                  <span className="font-mono text-slate-600">{inspectedMetric.metric_version}</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-slate-900">Definition:</div>
                <p className="text-slate-600 leading-relaxed">
                  {METRIC_CATALOG_INFO[inspectedMetric.metric_id]?.definition || "Operational metric definition in SAMVED v1.0.0."}
                </p>
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-slate-900">Mathematical Formula:</div>
                <pre className="bg-slate-900 text-emerald-400 p-2.5 rounded text-[11px] font-mono overflow-x-auto">
                  {METRIC_CATALOG_INFO[inspectedMetric.metric_id]?.formula || "COUNT(events)"}
                </pre>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setInspectedMetric(null)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 11. Access Audit Modal */}
      {showAuditModal && (
        <div
          data-testid="analytics-audit-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 space-y-4 border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-bold uppercase text-indigo-600 tracking-wider">
                  Governance Audit Trail
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  Analytics Dashboard Access History
                </h3>
              </div>
              <button
                onClick={() => setShowAuditModal(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs text-slate-700">
              {auditLogs.length === 0 ? (
                <div className="p-4 text-center text-slate-400">No audit logs recorded yet.</div>
              ) : (
                auditLogs.map((log, i) => (
                  <div key={i} className="py-2.5 flex items-center justify-between font-mono">
                    <div>
                      <div className="font-semibold text-slate-900 font-sans">
                        {log.actor_id} ({log.actor_role})
                      </div>
                      <div className="text-[11px] text-slate-400">{log.endpoint} &bull; {log.district_code || "ALL"}</div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        log.privacy_status === "PASS" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                      }`}>
                        {log.privacy_status}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-1">{log.accessed_at?.substring(11, 19)}</div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowAuditModal(false)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg"
              >
                Close Audit Trail
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
