import { test, expect, Page } from "@playwright/test";

async function setupMockAnalytics(page: Page) {
  // Prevent websocket disconnect flakiness
  await page.route("**/ws/operator", (route) => route.abort());

  // Calls list for operator console testing
  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: [
          {
            call_id: "call-1001",
            caller_masked_number: "+91******3210",
            state: "STREAMING",
            conversation_state: "LISTENING",
            current_language: "ta-IN",
            duration_seconds: 45,
            provider: "exotel",
            is_active: true,
          },
        ],
        recent_calls: [],
        total_active: 1,
        total_recent: 0,
      }),
    });
  });

  // Analytics Status
  await page.route("**/v1/analytics/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "HEALTHY",
        phase: "PHASE_13",
        service: "District Intelligence & Operational Analytics",
        catalog_version: "v1.0.0",
        predictive_policing_enabled: false,
        surveillance_mode: false,
      }),
    });
  });

  // District Summary (handles role and district)
  await page.route("**/v1/analytics/districts/*/summary*", async (route) => {
    const url = route.request().url();
    const headers = route.request().headers();
    const userRole = headers["x-user-role"] || "DISTRICT_ADMIN";

    if (userRole === "OPERATOR") {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "FORBIDDEN",
            message: "Access denied: OPERATOR role is restricted from macro district intelligence.",
          },
        }),
      });
      return;
    }

    const isSuppressedDistrict = url.includes("PY-KKL");

    if (isSuppressedDistrict) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          summary_id: "sum-py-kkl-day",
          district_code: "PY-KKL",
          district_name: "Karaikal",
          state_code: "PY",
          state_name: "Puducherry",
          period: "DAY",
          period_start: "2026-09-04T00:00:00Z",
          period_end: "2026-09-05T00:00:00Z",
          timezone: "Asia/Kolkata",
          total_calls: { metric_id: "calls_received", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          completed_calls: { metric_id: "calls_completed", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          abandoned_calls: { metric_id: "calls_abandoned", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          unique_cases: { metric_id: "unique_case_count", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          active_followups: { metric_id: "active_followups", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          avg_response_time_sec: { metric_id: "operator_response_time_sec", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          safety_escalations_count: { metric_id: "safety_escalations_count", metric_version: "v1.0.0", display_value: "SUPPRESSED", raw_value: null, status: "SUPPRESSED", suppressed: true, period_start: "", period_end: "" },
          privacy_status: "SUPPRESSED",
          data_quality_status: "HEALTHY",
          metric_version: "v1.0.0",
          computed_at: "2026-09-05T10:00:00Z",
        }),
      });
      return;
    }

    // Default Healthy Summary (TN-CHE, DL-CEN, etc.)
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary_id: "sum-tn-che-day",
        district_code: "TN-CHE",
        district_name: "Chennai",
        state_code: "TN",
        state_name: "Tamil Nadu",
        period: "DAY",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        timezone: "Asia/Kolkata",
        total_calls: { metric_id: "calls_received", metric_version: "v1.0.0", display_value: "142", raw_value: 142, status: "OBSERVED", suppressed: false, trend: "RISING", trend_pct: 8.5, period_start: "", period_end: "" },
        completed_calls: { metric_id: "calls_completed", metric_version: "v1.0.0", display_value: "128", raw_value: 128, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        abandoned_calls: { metric_id: "calls_abandoned", metric_version: "v1.0.0", display_value: "14", raw_value: 14, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        unique_cases: { metric_id: "unique_case_count", metric_version: "v1.0.0", display_value: "85", raw_value: 85, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        active_followups: { metric_id: "active_followups", metric_version: "v1.0.0", display_value: "24", raw_value: 24, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        avg_response_time_sec: { metric_id: "operator_response_time_sec", metric_version: "v1.0.0", display_value: "3.4s", raw_value: 3.4, unit: "s", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        safety_escalations_count: { metric_id: "safety_escalations_count", metric_version: "v1.0.0", display_value: "16", raw_value: 16, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        privacy_status: "PASS",
        data_quality_status: "HEALTHY",
        metric_version: "v1.0.0",
        computed_at: "2026-09-05T10:00:00Z",
      }),
    });
  });

  // Trends
  await page.route("**/v1/analytics/districts/*/trends*", async (route) => {
    const isSuppressedDistrict = route.request().url().includes("PY-KKL");
    const points = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, i) => ({
      label: day,
      period_start: `2026-09-0${i + 1}T00:00:00Z`,
      period_end: `2026-09-0${i + 1}T23:59:59Z`,
      calls_received: {
        metric_id: "calls_received",
        metric_version: "v1.0.0",
        display_value: isSuppressedDistrict ? "SUPPRESSED" : `${120 + i * 5}`,
        raw_value: isSuppressedDistrict ? null : 120 + i * 5,
        status: isSuppressedDistrict ? "SUPPRESSED" : "OBSERVED",
        suppressed: isSuppressedDistrict,
        period_start: "",
        period_end: "",
      },
      calls_completed: {
        metric_id: "calls_completed",
        metric_version: "v1.0.0",
        display_value: isSuppressedDistrict ? "SUPPRESSED" : `${110 + i * 4}`,
        raw_value: isSuppressedDistrict ? null : 110 + i * 4,
        status: isSuppressedDistrict ? "SUPPRESSED" : "OBSERVED",
        suppressed: isSuppressedDistrict,
        period_start: "",
        period_end: "",
      },
      unique_cases: {
        metric_id: "unique_case_count",
        metric_version: "v1.0.0",
        display_value: isSuppressedDistrict ? "SUPPRESSED" : `${70 + i * 3}`,
        raw_value: isSuppressedDistrict ? null : 70 + i * 3,
        status: isSuppressedDistrict ? "SUPPRESSED" : "OBSERVED",
        suppressed: isSuppressedDistrict,
        period_start: "",
        period_end: "",
      },
      safety_escalations: {
        metric_id: "safety_escalations_count",
        metric_version: "v1.0.0",
        display_value: isSuppressedDistrict ? "SUPPRESSED" : `${12 + i}`,
        raw_value: isSuppressedDistrict ? null : 12 + i,
        status: isSuppressedDistrict ? "SUPPRESSED" : "OBSERVED",
        suppressed: isSuppressedDistrict,
        period_start: "",
        period_end: "",
      },
    }));

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: isSuppressedDistrict ? "PY-KKL" : "TN-CHE",
        period: "DAY",
        points,
        overall_trend: isSuppressedDistrict ? "INSUFFICIENT_DATA" : "RISING",
        overall_trend_pct: isSuppressedDistrict ? null : 8.5,
        suppressed: isSuppressedDistrict,
      }),
    });
  });

  // Languages
  await page.route("**/v1/analytics/districts/*/languages*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        items: [
          { language: "hi-IN", language_name: "Hindi", percentage: 45.8, count_display: "65", suppressed: false },
          { language: "ta-IN", language_name: "Tamil", percentage: 31.7, count_display: "45", suppressed: false },
          { language: "en-IN", language_name: "English", percentage: 15.5, count_display: "22", suppressed: false },
          { language: "te-IN", language_name: "Telugu", percentage: 7.0, count_display: "10", suppressed: false },
        ],
        suppressed_count: 0,
        privacy_status: "PASS",
      }),
    });
  });

  // Services
  await page.route("**/v1/analytics/districts/*/services*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        items: [
          { category: "COUNSELING_REFERRAL", category_name: "Counseling Referral", percentage: 36.6, count_display: "52", suppressed: false },
          { category: "SAFETY_SUPPORT", category_name: "Safety Support", percentage: 25.4, count_display: "36", suppressed: false },
          { category: "HEALTH_SUPPORT", category_name: "Health / Medical", percentage: 16.9, count_display: "24", suppressed: false },
          { category: "LEGAL_INFORMATION", category_name: "Legal Information", percentage: 12.7, count_display: "18", suppressed: false },
          { category: "FOLLOW_UP", category_name: "Follow-up Care", percentage: 8.4, count_display: "12", suppressed: false },
        ],
        suppressed_count: 0,
        privacy_status: "PASS",
      }),
    });
  });

  // Safety
  await page.route("**/v1/analytics/districts/*/safety*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        items: [
          { safety_state: "NONE", percentage: 62.0, count_display: "88", suppressed: false },
          { safety_state: "WATCH", percentage: 18.3, count_display: "26", suppressed: false },
          { safety_state: "ELEVATED", percentage: 11.3, count_display: "16", suppressed: false },
          { safety_state: "HIGH", percentage: 6.3, count_display: "9", suppressed: false },
          { safety_state: "CRITICAL", percentage: 2.1, count_display: "3", suppressed: false },
        ],
        suppressed_count: 0,
        privacy_status: "PASS",
      }),
    });
  });

  // SVI
  await page.route("**/v1/analytics/districts/*/svi*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        items: [
          { band: "LOW", percentage: 31.7, count_display: "45", suppressed: false },
          { band: "MODERATE", percentage: 40.8, count_display: "58", suppressed: false },
          { band: "HIGH", percentage: 19.0, count_display: "27", suppressed: false },
          { band: "CRITICAL", percentage: 8.5, count_display: "12", suppressed: false },
        ],
        average_svi: { metric_id: "average_svi", metric_version: "v1.0.0", display_value: "46.5", raw_value: 46.5, status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        suppressed_count: 0,
        privacy_status: "PASS",
      }),
    });
  });

  // Follow-ups
  await page.route("**/v1/analytics/districts/*/followups*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        created_count: { metric_id: "followups_created", metric_version: "v1.0.0", display_value: "34", raw_value: 34, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        completed_count: { metric_id: "followups_completed", metric_version: "v1.0.0", display_value: "28", raw_value: 28, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        missed_count: { metric_id: "followups_missed", metric_version: "v1.0.0", display_value: "4", raw_value: 4, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        blocked_count: { metric_id: "followups_blocked", metric_version: "v1.0.0", display_value: "2", raw_value: 2, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        completion_rate: { metric_id: "followup_completion_rate", metric_version: "v1.0.0", display_value: "87.5%", raw_value: 87.5, unit: "%", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        missed_rate: { metric_id: "followup_missed_rate", metric_version: "v1.0.0", display_value: "12.5%", raw_value: 12.5, unit: "%", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        suppressed: false,
        privacy_status: "PASS",
      }),
    });
  });

  // Operations
  await page.route("**/v1/analytics/districts/*/operations*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        district_code: "TN-CHE",
        period_start: "2026-09-04T00:00:00Z",
        period_end: "2026-09-05T00:00:00Z",
        active_operators_count: { metric_id: "active_operators_count", metric_version: "v1.0.0", display_value: "12", raw_value: 12, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        avg_calls_per_operator: { metric_id: "avg_calls_per_operator", metric_version: "v1.0.0", display_value: "11.8", raw_value: 11.8, status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        takeovers_count: { metric_id: "human_takeovers_count", metric_version: "v1.0.0", display_value: "18", raw_value: 18, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        handoffs_requested: { metric_id: "handoffs_requested", metric_version: "v1.0.0", display_value: "22", raw_value: 22, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        handoffs_confirmed: { metric_id: "handoffs_confirmed", metric_version: "v1.0.0", display_value: "20", raw_value: 20, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        median_response_time_sec: { metric_id: "operator_response_time_sec", metric_version: "v1.0.0", display_value: "3.4s", raw_value: 3.4, unit: "s", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        knowledge_queries: { metric_id: "knowledge_queries", metric_version: "v1.0.0", display_value: "256", raw_value: 256, status: "OBSERVED", suppressed: false, period_start: "", period_end: "" },
        system_latency_ms: { metric_id: "system_api_latency_p95_ms", metric_version: "v1.0.0", display_value: "28ms", raw_value: 28, unit: "ms", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        stt_failure_rate: { metric_id: "system_stt_failure_rate", metric_version: "v1.0.0", display_value: "0.4%", raw_value: 0.4, unit: "%", status: "CALCULATED", suppressed: false, period_start: "", period_end: "" },
        suppressed: false,
        privacy_status: "PASS",
      }),
    });
  });

  // Audit list
  await page.route("**/v1/analytics/audit*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        logs: [
          { audit_id: "aud-01", actor_id: "counselor-01", actor_role: "DISTRICT_ADMIN", endpoint: "/summary/TN-CHE", district_code: "TN-CHE", period: "DAY", privacy_status: "PASS", accessed_at: "2026-09-05T10:15:30Z" },
          { audit_id: "aud-02", actor_id: "supervisor-01", actor_role: "SUPERVISOR", endpoint: "/trends/TN-CHE", district_code: "TN-CHE", period: "DAY", privacy_status: "PASS", accessed_at: "2026-09-05T10:14:20Z" },
        ],
        total_count: 2,
      }),
    });
  });
}

test.describe("Phase 13: District Intelligence & Operational Analytics", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockAnalytics(page);
  });

  test("TC-ANA-01: Analytics dashboard loads with governance watermark", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="analytics-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="governance-watermark"]')).toBeVisible();
    await expect(page.locator('[data-testid="governance-watermark"]')).toContainText("Not a predictive risk score");
  });

  test("TC-ANA-02: Role switcher enforces operator denial", async ({ page }) => {
    await page.goto("/analytics");
    await page.locator('[data-testid="role-selector"]').selectOption("OPERATOR");
    await expect(page.locator('[data-testid="access-denied-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="access-denied-banner"]')).toContainText("Access denied");

    // Switch back to DISTRICT_ADMIN restores view
    await page.locator('[data-testid="role-selector"]').selectOption("DISTRICT_ADMIN");
    await expect(page.locator('[data-testid="access-denied-banner"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="kpi-strip"]')).toBeVisible();
  });

  test("TC-ANA-03: Filter bar allows district and period selection", async ({ page }) => {
    await page.goto("/analytics");
    const districtSelect = page.locator('[data-testid="district-filter"]');
    await expect(districtSelect).toBeVisible();
    await expect(districtSelect).toHaveValue("TN-CHE");

    const periodSelect = page.locator('[data-testid="period-filter"]');
    await expect(periodSelect).toBeVisible();
    await periodSelect.selectOption("WEEK");
    await expect(periodSelect).toHaveValue("WEEK");
  });

  test("TC-ANA-04: KPI strip renders non-predictive operational metrics", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="kpi-total-calls"]')).toBeVisible();
    await expect(page.locator('[data-testid="value-total-calls"]')).toHaveText("142");
    await expect(page.locator('[data-testid="trend-total-calls"]')).toBeVisible();

    await expect(page.locator('[data-testid="kpi-completed-calls"]')).toContainText("128");
    await expect(page.locator('[data-testid="kpi-unique-cases"]')).toContainText("85");
    await expect(page.locator('[data-testid="kpi-active-followups"]')).toContainText("24");
  });

  test("TC-ANA-05: Call volume trends render with table view toggle", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="section-call-volume"]')).toBeVisible();
    await expect(page.locator('[data-testid="volume-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="overall-trend-badge"]')).toContainText("RISING");

    // Toggle to table view
    await page.locator('[data-testid="table-toggle-btn"]').click();
    await expect(page.locator('[data-testid="volume-table"]')).toBeVisible();
    await expect(page.locator('[data-testid="volume-table"]')).toContainText("Calls Received");
  });

  test("TC-ANA-06: Safety and SVI distributions render accurately", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="section-safety-distribution"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-safety-distribution"]')).toContainText("NONE");
    await expect(page.locator('[data-testid="section-safety-distribution"]')).toContainText("CRITICAL");

    await expect(page.locator('[data-testid="section-svi-distribution"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-svi-distribution"]')).toContainText("MODERATE Band");
  });

  test("TC-ANA-07: Multilingual and service demand sections render", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="section-language-demand"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-language-demand"]')).toContainText("Hindi");
    await expect(page.locator('[data-testid="section-language-demand"]')).toContainText("Tamil");

    await expect(page.locator('[data-testid="section-service-demand"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-service-demand"]')).toContainText("Counseling Referral");
  });

  test("TC-ANA-08: Follow-up and operator workload sections render", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.locator('[data-testid="section-followup-workload"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-followup-workload"]')).toContainText("Completion Rate");

    await expect(page.locator('[data-testid="section-operator-workload"]')).toBeVisible();
    await expect(page.locator('[data-testid="section-operator-workload"]')).toContainText("Active Counselors");
  });

  test("TC-ANA-09: Small-cell cohort triggers SUPPRESSED indicators", async ({ page }) => {
    await page.goto("/analytics");
    // Switch to PY-KKL (Karaikal, cohort < 10)
    await page.locator('[data-testid="district-filter"]').selectOption("PY-KKL");
    await expect(page.locator('[data-testid="suppressed-cohort-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="value-total-calls"]')).toHaveText("SUPPRESSED");
    // Ensure no raw counts leak into the card
    await expect(page.locator('[data-testid="kpi-total-calls"]')).not.toContainText("6");
  });

  test("TC-ANA-10: Metric Inspector drawer opens with definition and trust classification", async ({ page }) => {
    await page.goto("/analytics");
    await page.locator('[data-testid="kpi-total-calls"]').click();
    await expect(page.locator('[data-testid="metric-detail-drawer"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-detail-drawer"]')).toContainText("calls_received");
    await expect(page.locator('[data-testid="metric-detail-drawer"]')).toContainText("OBSERVED");
    await expect(page.locator('[data-testid="metric-detail-drawer"]')).toContainText("COUNT(CALL_STARTED events)");

    // Close drawer
    await page.locator('[data-testid="metric-detail-drawer"] button:has-text("Close Inspector")').click();
    await expect(page.locator('[data-testid="metric-detail-drawer"]')).not.toBeVisible();
  });

  test("TC-ANA-11: Operator console header has compact link navigating to analytics", async ({ page }) => {
    await page.goto("/calls");
    const analyticsLink = page.locator('[data-testid="link-operations-analytics"]');
    await expect(analyticsLink).toBeVisible();
    await expect(analyticsLink).toHaveAttribute("href", "/analytics");
  });
});
