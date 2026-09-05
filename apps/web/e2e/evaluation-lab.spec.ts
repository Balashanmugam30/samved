import { test, expect, Page } from "@playwright/test";

async function setupMockEvaluation(page: Page) {
  // Prevent websocket disconnect flakiness
  await page.route("**/ws/operator", (route) => route.abort());

  // Status mock
  await page.route("**/v1/evaluation/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        engine_version: "1.0.0",
        scenarios_count: 19,
        baselines_count: 5,
        runs_count: 12,
        supported_modes: ["OFFLINE", "INTEGRATED"],
        supported_suites: ["smoke", "safety", "multilingual", "full"],
        disclaimer: "SYNTHETIC EVALUATION ENVIRONMENT",
      }),
    });
  });

  // Scenarios mock
  await page.route("**/v1/evaluation/scenarios*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 2,
        scenarios: [
          {
            scenario_id: "SCEN-GEN-001",
            scenario_version: "1.0",
            title: "General IRCA Facility Information Inquiry (English)",
            description: "Caller inquiring about nearest Integrated Rehabilitation Centre for Addicts (IRCA) operating hours.",
            locale: "en-IN",
            channel: "PSTN_8KHZ",
            difficulty: "BEGINNER",
            tags: ["general", "info", "irca", "smoke"],
            synthetic_disclaimer: "SYNTHETIC BENCHMARK ISOLATION: Purely synthetic scenario.",
            caller_profile: { caller_id: "SYNTHETIC-CALLER-GEN-01", prior_contact_history: false },
            turns: [
              { turn_number: 1, speaker: "caller", text: "Hello, I am calling to find out about rehab facilities." },
            ],
            expected: {
              expected_safety_state: "SAFE",
              expected_svi_band: "LOW",
              expected_svi_score_range: [0, 25],
              expected_required_human_review: false,
              expected_language: "en-IN",
              expected_adaptive_policy: "PROVIDE_INFORMATION",
              max_p95_latency_ms: 1200.0,
            },
          },
          {
            scenario_id: "SCEN-THREAT-001",
            scenario_version: "1.0",
            title: "Active Physical Threat by Trafficker Outside Residence (Hindi)",
            description: "Caller reports an armed substance supplier attempting forced entry.",
            locale: "hi-IN",
            channel: "PSTN_8KHZ",
            difficulty: "EXPERT",
            tags: ["active_threat", "violence", "critical", "safety", "smoke"],
            synthetic_disclaimer: "SYNTHETIC BENCHMARK ISOLATION: Purely synthetic scenario.",
            caller_profile: { caller_id: "SYNTHETIC-CALLER-THREAT-01", prior_contact_history: false },
            turns: [
              { turn_number: 1, speaker: "caller", text: "Bachao! Woh aadmi darwaze ke bahar hai, darwaza tod raha hai!" },
            ],
            expected: {
              expected_safety_state: "CRITICAL",
              expected_svi_band: "CRITICAL",
              expected_svi_score_range: [76, 100],
              expected_required_human_review: true,
              expected_language: "hi-IN",
              expected_adaptive_policy: "SAFETY_FIRST",
              max_p95_latency_ms: 1200.0,
            },
          },
        ],
      }),
    });
  });

  // Baselines mock
  await page.route("**/v1/evaluation/baselines*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 1,
        baselines: [
          {
            baseline_id: "BASE-SCEN-GEN-001-v1",
            scenario_id: "SCEN-GEN-001",
            scenario_version: "1.0",
            evaluation_version: "1.0",
            seed: 42,
            status: "PASS",
            metrics: {
              safety: { state: "SAFE", highest_severity: "NONE" },
              svi: { score: 10, band: "LOW" },
              adaptive: { policy: "PROVIDE_INFORMATION" },
              acoustic: { frames_analyzed: 1 },
              orchestration: { dag_execution_successful: true },
              rag: { citations: [] },
              case_intelligence: { handoff_state: "NOT_REQUIRED" },
              followup: { followup_state: "NOT_SCHEDULED", autonomous_dispatch: false },
              analytics_isolation: { isolated_from_analytics: true },
              latency: { total_ms: 15.2, p95_ms: 3.1, min_ms: 2.1, median_ms: 3.1, max_ms: 3.1, stage_breakdown: {} },
            },
            captured_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  // Runs trigger mock
  await page.route("**/v1/evaluation/runs*", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: "RUN-EVAL-TEST-001",
          scenario_id: "SCEN-GEN-001",
          scenario_version: "1.0",
          mode: "OFFLINE",
          seed: 42,
          execution_status: "COMPLETED",
          evaluation_status: "PASS",
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          duration_ms: 18.5,
          synthetic_marker: "SYNTHETIC_EVALUATION",
          assertions: [
            {
              assertion_id: "ASSERT-SAFETY-STATE-SCEN-GEN-001",
              category: "safety",
              description: "Safety state must match expected 'SAFE'",
              passed: true,
              expected: "SAFE",
              actual: "SAFE",
            },
          ],
          findings: [
            {
              finding_id: "FND-001",
              scenario_id: "SCEN-GEN-001",
              subsystem: "safety",
              severity: "PASS",
              message: "Safety state verified: SAFE",
              details: { actual: "SAFE" },
              timestamp: new Date().toISOString(),
            },
          ],
          metrics: {
            safety: { state: "SAFE", highest_severity: "NONE", signals_count: 0, human_review_required: false, rules_evaluated: 14 },
            svi: { score: 12, band: "LOW", critical_floor_applied: false },
            adaptive: { policy: "PROVIDE_INFORMATION", language: "en-IN", channel: "PSTN_8KHZ" },
            acoustic: { frames_analyzed: 1, degraded_audio_detected: false, prolonged_silence_count: 0 },
            orchestration: { fault_injected: "NONE", dag_execution_successful: true, events_count: 4 },
            rag: { citations: [], retrieval_success: true },
            case_intelligence: { handoff_state: "NOT_REQUIRED", synthetic_case_created: false },
            followup: { followup_state: "NOT_SCHEDULED", autonomous_dispatch: false },
            analytics_isolation: { isolated_from_analytics: true, synthetic_marker: "SYNTHETIC_EVALUATION" },
            latency: {
              total_ms: 18.5,
              p95_ms: 3.4,
              min_ms: 2.1,
              median_ms: 3.0,
              max_ms: 3.4,
              stage_breakdown: { safety: 0.8, svi: 0.9, adaptive: 0.5 },
            },
          },
          events_count: 4,
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, runs: [] }),
      });
    }
  });

  // Diff mock
  await page.route("**/v1/evaluation/diff", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        baseline_id: "BASE-SCEN-GEN-001-v1",
        current_run_id: "RUN-EVAL-TEST-001",
        scenario_id: "SCEN-GEN-001",
        status: "IDENTICAL",
        has_regression: false,
        differences: [
          {
            field: "safety_state",
            subsystem: "safety",
            baseline_value: "SAFE",
            current_value: "SAFE",
            is_regression: false,
            message: "Safety state identical",
          },
        ],
      }),
    });
  });
}

test.describe("Phase 14: Scenario Simulator & Evaluation Lab", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockEvaluation(page);
  });

  test("renders prominent synthetic governance banner and safety guarantees", async ({ page }) => {
    await page.goto("/evaluation");

    // Mandatory banner checks
    await expect(page.locator("text=Synthetic Evaluation Environment")).toBeVisible();
    await expect(page.locator("text=AUTONOMOUS DISPATCH: FALSE")).toBeVisible();
    await expect(page.locator("text=ISOLATED SANDBOX")).toBeVisible();
  });

  test("sidebar navigation links to Evaluation Lab", async ({ page }) => {
    await page.goto("/");
    const navLink = page.locator("a[href='/evaluation']");
    await expect(navLink).toBeVisible();
    await navLink.click();
    await expect(page).toHaveURL(/.*\/evaluation/);
  });

  test("scenario library displays calibrated benchmark cards and search filters", async ({ page }) => {
    await page.goto("/evaluation");

    // Scenarios visible
    await expect(page.locator("text=SCEN-GEN-001").first()).toBeVisible();

    // Inspect drawer
    const inspectBtn = page.locator("button:has-text('Inspect Spec')").first();
    await inspectBtn.click();

    // Drawer should appear
    await expect(page.locator("text=Scenario Narrative")).toBeVisible();
    await expect(page.locator("text=Machine-Checkable Expectations")).toBeVisible();

    // Close drawer
    const closeBtn = page.locator("button:has-text('Close')").first();
    await closeBtn.click();
  });

  test("executes an evaluation run and displays telemetry & assertions", async ({ page }) => {
    await page.goto("/evaluation");

    // Click run on first scenario
    const runBtn = page.locator("[data-testid='run-scenario-btn']").first();
    await runBtn.scrollIntoViewIfNeeded();
    await runBtn.click();

    // Switches to analysis view
    await expect(page.locator("[data-testid='run-status-badge']")).toContainText("STATUS: PASS");
    await expect(page.locator("text=Safety Classification")).toBeVisible();
    await expect(page.locator("text=P95 Replay Latency")).toBeVisible();

    // Sub-tab navigation: Assertions
    const assertionsTab = page.locator("[data-testid='subtab-assertions']");
    await assertionsTab.scrollIntoViewIfNeeded();
    await assertionsTab.click();
    await expect(page.locator("text=Machine-Checkable Golden Expectations")).toBeVisible();

    // Sub-tab navigation: Subsystem Telemetry
    const subsystemsTab = page.locator("[data-testid='subtab-subsystems']");
    await subsystemsTab.scrollIntoViewIfNeeded();
    await subsystemsTab.click();
    await expect(page.locator("text=Deterministic Safety")).toBeVisible();
    await expect(page.locator("text=Explainable SVI")).toBeVisible();

    // Sub-tab navigation: Baseline Regression Diff
    const diffTab = page.locator("[data-testid='subtab-diff']");
    await diffTab.scrollIntoViewIfNeeded();
    await diffTab.click();
    const computeDiffBtn = page.locator("[data-testid='btn-compute-diff']");
    await computeDiffBtn.scrollIntoViewIfNeeded();
    await computeDiffBtn.click();
    await expect(page.locator("text=NO REGRESSION")).toBeVisible();
  });

  test("suite runner allows selecting and executing benchmark suites", async ({ page }) => {
    await page.goto("/evaluation");

    // Switch to suites tab
    const suiteTab = page.locator("[data-testid='tab-suites']");
    await suiteTab.scrollIntoViewIfNeeded();
    await suiteTab.click();

    const controls = page.locator("[data-testid='suite-controls']");
    await controls.scrollIntoViewIfNeeded();
    await expect(controls).toBeVisible();

    const targets = page.locator("text=Suite Benchmark Targets");
    await expect(targets).toBeAttached();

    const executeBtn = page.locator("button:has-text('Execute')");
    await expect(executeBtn).toBeAttached();
  });
});
