import { test, expect, Page } from "@playwright/test";

async function setupMockSimulation(page: Page) {
  // Prevent websocket disconnect flakiness
  await page.route("**/ws/operator", (route) => route.abort());

  // Simulation Status
  await page.route("**/v1/simulation/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "healthy",
        version: "v1.0.0",
        total_scenarios: 24,
        total_drills: 4,
        languages_supported: ["en-IN", "hi-IN", "ta-IN", "te-IN"],
        recent_benchmark_runs: 1,
      }),
    });
  });

  // Scenarios list
  await page.route("**/v1/simulation/scenarios*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          scenario_id: "SCEN-CRIT-001",
          title: "Acute Suicidal Ideation in Despair (Hindi)",
          description: "Caller expressing active suicidal thoughts with feelings of helplessness.",
          language: "hi-IN",
          expected_svi_band: "CRITICAL",
          expected_score_range: [76, 100],
          expected_safety_triggers: ["SELF_HARM"],
          prohibited_safety_triggers: [],
          noise_profile: "CLEAN",
          turns_count: 2,
          tags: ["critical", "self-harm", "hindi", "smoke"],
        },
        {
          scenario_id: "SCEN-CRIT-003",
          title: "Acute Opioid Overdose Emergency (English)",
          description: "Caller reports a family member is unresponsive with blue lips.",
          language: "en-IN",
          expected_svi_band: "CRITICAL",
          expected_score_range: [76, 100],
          expected_safety_triggers: ["MEDICAL_EMERGENCY"],
          prohibited_safety_triggers: [],
          noise_profile: "CLEAN",
          turns_count: 2,
          tags: ["critical", "overdose", "english", "smoke"],
        },
        {
          scenario_id: "SCEN-HIGH-001",
          title: "Severe Opioid Withdrawal & Confinement (Hindi)",
          description: "Caller locked in room with phone taken away.",
          language: "hi-IN",
          expected_svi_band: "HIGH",
          expected_score_range: [51, 75],
          expected_safety_triggers: ["CONFINEMENT"],
          prohibited_safety_triggers: [],
          noise_profile: "CLEAN",
          turns_count: 2,
          tags: ["high", "withdrawal", "hindi", "smoke"],
        },
        {
          scenario_id: "SCEN-MOD-001",
          title: "Alcohol Dependence & Distress (Hindi)",
          description: "Caller realizing their daily drinking is causing severe anxiety.",
          language: "hi-IN",
          expected_svi_band: "MODERATE",
          expected_score_range: [26, 50],
          expected_safety_triggers: [],
          prohibited_safety_triggers: [],
          noise_profile: "CLEAN",
          turns_count: 2,
          tags: ["moderate", "counseling", "hindi", "smoke"],
        },
        {
          scenario_id: "SCEN-LOW-001",
          title: "Government IRCA Center Location Inquiry (Hindi)",
          description: "Caller asking for address and contact details of nearest IRCA center.",
          language: "hi-IN",
          expected_svi_band: "LOW",
          expected_score_range: [0, 25],
          expected_safety_triggers: [],
          prohibited_safety_triggers: [],
          noise_profile: "CLEAN",
          turns_count: 2,
          tags: ["low", "info", "hindi", "smoke"],
        },
      ]),
    });
  });

  // Benchmark runs list & trigger
  const mockBenchmarkRun = {
    run_id: "RUN-E2E-TEST01",
    suite: "SMOKE",
    status: "COMPLETED",
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    total_scenarios: 5,
    passed_scenarios: 5,
    failed_scenarios: 0,
    pass_rate: 1.0,
    mean_wer: 0.025,
    mean_cer: 0.012,
    safety_recall_rate: 1.0,
    svi_band_accuracy: 1.0,
    p95_latency_ms: 12.4,
    critical_safety_passed: true,
    results: [
      {
        scenario_id: "SCEN-CRIT-001",
        passed: true,
        language: "hi-IN",
        expected_svi_band: "CRITICAL",
        actual_svi_band: "CRITICAL",
        svi_score: 88,
        expected_safety_triggers: ["SELF_HARM"],
        actual_safety_triggers: ["SAFETY_SELF_HARM_EXPLICIT_001", "SELF_HARM"],
        safety_recall: 1.0,
        false_negative_hazard: false,
        wer_result: { wer: 0.0, cer: 0.0, substitutions: 0, deletions: 0, insertions: 0, hits: 14, reference_words: 14, hypothesis_words: 14 },
        turn_latencies_ms: [8.5, 9.2],
        p95_latency_ms: 9.2,
      },
      {
        scenario_id: "SCEN-CRIT-003",
        passed: true,
        language: "en-IN",
        expected_svi_band: "CRITICAL",
        actual_svi_band: "CRITICAL",
        svi_score: 92,
        expected_safety_triggers: ["MEDICAL_EMERGENCY"],
        actual_safety_triggers: ["SAFETY_MEDICAL_EMERGENCY_001", "MEDICAL_EMERGENCY"],
        safety_recall: 1.0,
        false_negative_hazard: false,
        wer_result: { wer: 0.0, cer: 0.0, substitutions: 0, deletions: 0, insertions: 0, hits: 16, reference_words: 16, hypothesis_words: 16 },
        turn_latencies_ms: [10.1, 12.4],
        p95_latency_ms: 12.4,
      },
      {
        scenario_id: "SCEN-HIGH-001",
        passed: true,
        language: "hi-IN",
        expected_svi_band: "HIGH",
        actual_svi_band: "HIGH",
        svi_score: 62,
        expected_safety_triggers: ["CONFINEMENT"],
        actual_safety_triggers: ["SAFETY_CONFINEMENT_001", "CONFINEMENT"],
        safety_recall: 1.0,
        false_negative_hazard: false,
        wer_result: { wer: 0.0, cer: 0.0, substitutions: 0, deletions: 0, insertions: 0, hits: 15, reference_words: 15, hypothesis_words: 15 },
        turn_latencies_ms: [6.5, 7.1],
        p95_latency_ms: 7.1,
      },
      {
        scenario_id: "SCEN-MOD-001",
        passed: true,
        language: "hi-IN",
        expected_svi_band: "MODERATE",
        actual_svi_band: "MODERATE",
        svi_score: 36,
        expected_safety_triggers: [],
        actual_safety_triggers: [],
        safety_recall: 1.0,
        false_negative_hazard: false,
        wer_result: { wer: 0.0, cer: 0.0, substitutions: 0, deletions: 0, insertions: 0, hits: 18, reference_words: 18, hypothesis_words: 18 },
        turn_latencies_ms: [5.2, 5.8],
        p95_latency_ms: 5.8,
      },
      {
        scenario_id: "SCEN-LOW-001",
        passed: true,
        language: "hi-IN",
        expected_svi_band: "LOW",
        actual_svi_band: "LOW",
        svi_score: 12,
        expected_safety_triggers: [],
        actual_safety_triggers: [],
        safety_recall: 1.0,
        false_negative_hazard: false,
        wer_result: { wer: 0.0, cer: 0.0, substitutions: 0, deletions: 0, insertions: 0, hits: 12, reference_words: 12, hypothesis_words: 12 },
        turn_latencies_ms: [4.1, 4.5],
        p95_latency_ms: 4.5,
      },
    ],
  };

  await page.route("**/v1/simulation/benchmark/runs*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([mockBenchmarkRun]),
    });
  });

  await page.route("**/v1/simulation/benchmark/run", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockBenchmarkRun),
    });
  });

  // WER evaluation
  await page.route("**/v1/simulation/wer/evaluate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        wer: 0.0714,
        cer: 0.0345,
        substitutions: 0,
        deletions: 1,
        insertions: 0,
        hits: 13,
        reference_words: 14,
        hypothesis_words: 13,
        reference_chars: 82,
        hypothesis_chars: 78,
        normalized_reference: "help my brother overdosed on heroin he is unconscious on the floor and cannot breathe",
        normalized_hypothesis: "help my brother overdosed on heroin he is unconscious on floor and cannot breathe",
        alignment: [
          { ref_token: "help", hyp_token: "help", op: "match" },
          { ref_token: "my", hyp_token: "my", op: "match" },
          { ref_token: "brother", hyp_token: "brother", op: "match" },
          { ref_token: "the", hyp_token: "<eps>", op: "del" },
          { ref_token: "floor", hyp_token: "floor", op: "match" },
        ],
      }),
    });
  });

  // Training drills
  const mockDrills = [
    {
      id: "drill-001",
      drill_key: "DRILL-OVERDOSE-001",
      title: "Critical Opioid Overdose Rapid Intake",
      category: "CRITICAL_TRIAGE",
      difficulty: "EXPERT",
      language: "en-IN",
      description: "Caller reports an unresponsive roommate after heroin use.",
      scenario_context: "Emergency call at 02:15 AM. Roommate unresponsive.",
      expected_competencies: ["Emergency Escalation", "Recovery Position"],
      turns_count: 2,
    },
    {
      id: "drill-002",
      drill_key: "DRILL-WITHDRAWAL-002",
      title: "Acute Opioid Withdrawal & Housing Dislocation",
      category: "WITHDRAWAL_COUNSELING",
      difficulty: "INTERMEDIATE",
      language: "hi-IN",
      description: "Caller undergoing severe chills and tremors.",
      scenario_context: "Street call. Needs immediate detox.",
      expected_competencies: ["Medical Detox Referral", "Empathy"],
      turns_count: 2,
    },
  ];

  await page.route("**/v1/simulation/training/drills*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockDrills),
    });
  });

  // Start training session
  await page.route("**/v1/simulation/training/session/start", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "TRN-MOCK-SESSION-01",
        drill_id: "drill-001",
        trainee_id: "T-OPERATOR-01",
        trainee_name: "Tele-Counselor Trainee",
        status: "ACTIVE",
        started_at: new Date().toISOString(),
        current_turn: 1,
        total_turns: 2,
        evaluated_turns: [],
      }),
    });
  });

  // Submit training turn
  await page.route("**/v1/simulation/training/session/TRN-MOCK-SESSION-01/turn", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        turn_number: 1,
        trainee_input: "Please turn him on his side in recovery position immediately while I coordinate the ambulance.",
        score: 92.0,
        safety_protocol_score: 35.0,
        empathy_score: 22.0,
        de_escalation_score: 18.0,
        statutory_referral_score: 17.0,
        feedback_hints: ["Excellent rapid triage: instructed recovery position and triggered emergency handover."],
        caller_next_turn: "Okay I turned him on his side! When is the ambulance arriving?!",
      }),
    });
  });

  // Get completed training session
  await page.route("**/v1/simulation/training/session/TRN-MOCK-SESSION-01", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "TRN-MOCK-SESSION-01",
        drill_id: "drill-001",
        trainee_id: "T-OPERATOR-01",
        trainee_name: "Tele-Counselor Trainee",
        status: "COMPLETED",
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        current_turn: 2,
        total_turns: 2,
        overall_score: 92.0,
        performance_rating: "EXEMPLARY",
        competency_breakdown: {
          safety_protocol: 35.0,
          empathy_and_listening: 22.0,
          de_escalation_pacing: 18.0,
          referral_accuracy: 17.0,
        },
        recommendations: ["Ready for supervised live calls."],
        evaluated_turns: [
          {
            turn_number: 1,
            trainee_input: "Please turn him on his side in recovery position immediately while I coordinate the ambulance.",
            score: 92.0,
            safety_protocol_score: 35.0,
            empathy_score: 22.0,
            de_escalation_score: 18.0,
            statutory_referral_score: 17.0,
            feedback_hints: ["Excellent rapid triage: instructed recovery position and triggered emergency handover."],
          },
        ],
      }),
    });
  });
}

test.describe("Phase 14 — Scenario Simulation Engine & Operator Training Sandbox E2E", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockSimulation(page);
  });

  test("1. Direct navigation and core UI governance banner", async ({ page }) => {
    await page.goto("/simulation");
    await expect(page.locator("h1")).toContainText("Scenario Simulation Engine & Operator Training Sandbox");
    await expect(page.getByText("SYNTHETIC BENCHMARK ISOLATION:")).toBeVisible();
    await expect(page.getByText("Target: 100% Safety Recall")).toBeVisible();
  });

  test("2. Top KPI Cards show safety recall 100% and metrics", async ({ page }) => {
    await page.goto("/simulation");
    const kpiStrip = page.locator('[data-testid="kpi-strip"]');
    await expect(kpiStrip).toBeVisible();
    await expect(page.locator('[data-testid="kpi-safety-recall"]')).toContainText("Critical Safety Recall");
    await expect(page.locator('[data-testid="kpi-wer"]')).toContainText("Mean Word Error Rate");
    await expect(page.locator('[data-testid="kpi-cer"]')).toContainText("Mean Character Error");
    await expect(page.locator('[data-testid="kpi-svi-accuracy"]')).toContainText("SVI Calibration Accuracy");
    await expect(page.locator('[data-testid="kpi-p95-latency"]')).toContainText("P95 Triage Latency");
    await expect(kpiStrip).toContainText("100%");
  });

  test("3. Benchmark table displays scenarios with pass badges and triggers", async ({ page }) => {
    await page.goto("/simulation");
    const table = page.locator('[data-testid="table-benchmark-results"]');
    await expect(table).toBeVisible();
    await expect(table).toContainText("SCEN-CRIT-001");
    await expect(table).toContainText("PASS");
    await expect(table).toContainText("SELF_HARM");
  });

  test("4. Risk band filter buttons filter benchmark scenario rows", async ({ page }) => {
    await page.goto("/simulation");
    // Click CRITICAL filter
    await page.locator('[data-testid="filter-band-critical"]').click();
    const table = page.locator('[data-testid="table-benchmark-results"]');
    await expect(table).toContainText("SCEN-CRIT-001");
    await expect(table).not.toContainText("SCEN-LOW-001");

    // Click LOW filter
    await page.locator('[data-testid="filter-band-low"]').click();
    await expect(table).toContainText("SCEN-LOW-001");
    await expect(table).not.toContainText("SCEN-CRIT-001");

    // Click ALL filter
    await page.locator('[data-testid="filter-band-all"]').click();
    await expect(table).toContainText("SCEN-CRIT-001");
    await expect(table).toContainText("SCEN-LOW-001");
  });

  test("5. Run Benchmark trigger executes successfully", async ({ page }) => {
    await page.goto("/simulation");
    const runBtn = page.locator('[data-testid="btn-run-benchmark"]');
    await expect(runBtn).toBeVisible();
    await runBtn.click();
    await expect(page.locator('[data-testid="table-benchmark-results"]')).toBeVisible();
  });

  test("6. Indic ASR & WER Lab computes word error rate with token diff", async ({ page }) => {
    await page.goto("/simulation");
    // Switch to WER lab tab
    const tab = page.locator('[data-testid="tab-wer-lab"]');
    await tab.scrollIntoViewIfNeeded();
    await tab.click();

    const computeBtn = page.locator('[data-testid="btn-compute-wer"]');
    await computeBtn.scrollIntoViewIfNeeded();
    await expect(computeBtn).toBeVisible();
    await computeBtn.click();

    // Verify token alignment diff section & metrics panel
    const diffSection = page.locator('[data-testid="wer-diff-section"]');
    await expect(diffSection).toContainText("Token Alignment Diff Visualization");
    const metricsPanel = page.locator('[data-testid="wer-metrics-panel"]');
    await expect(metricsPanel).toContainText("Calculated Metrics");
    await expect(metricsPanel).toContainText("Hits");
  });

  test("7. Operator Training Sandbox drill selection and turn evaluation", async ({ page }) => {
    await page.goto("/simulation");
    // Switch to sandbox tab
    const tab = page.locator('[data-testid="tab-sandbox"]');
    await tab.scrollIntoViewIfNeeded();
    await tab.click();
    await expect(page.getByText("Standard Practice Drills")).toBeVisible();

    // Select first drill
    const drillCard = page.locator('[data-testid="card-drill-DRILL-OVERDOSE-001"]');
    await drillCard.scrollIntoViewIfNeeded();
    await expect(drillCard).toBeVisible();
    await drillCard.click();

    // Wait for active session initiation
    await expect(page.getByText("Session: TRN-MOCK-SESSION-01")).toBeVisible();

    // Trainee input should be visible
    const inputArea = page.locator('[data-testid="input-trainee-response"]');
    await inputArea.scrollIntoViewIfNeeded();
    await expect(inputArea).toBeVisible();

    // Type trainee response
    await inputArea.fill("Please turn him on his side in recovery position immediately while I coordinate the ambulance.");
    const submitBtn = page.locator('[data-testid="btn-submit-turn"]');
    await submitBtn.scrollIntoViewIfNeeded();
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // Verify evaluated turn scorecard pill appears
    const feedbackPill = page.locator('[data-testid="turn-feedback-pill"]');
    await expect(feedbackPill).toContainText("Turn Score:");
    await expect(feedbackPill).toContainText("92/100");
    await expect(feedbackPill).toContainText("Safety: 35/35");
  });

  test("8. Sidebar navigation contains Simulation & Sandbox Phase 14 link", async ({ page }) => {
    await page.goto("/");
    const simLink = page.getByRole("link", { name: /Simulation & Sandbox/i });
    await expect(simLink).toBeVisible();
    await expect(page.getByText("Phase 14")).toBeVisible();
    await simLink.click();
    await expect(page).toHaveURL(/.*simulation/);
  });
});
