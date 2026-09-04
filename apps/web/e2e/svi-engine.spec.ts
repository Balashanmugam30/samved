import { test, expect, Page } from "@playwright/test";

async function setupMockCall(page: Page, mockCallId = "call-svi-test-01") {
  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: [
          {
            call_id: mockCallId,
            caller_masked_number: "+91******3210",
            state: "STREAMING",
            conversation_state: "SPEAKING",
            current_language: "en-IN",
            duration_seconds: 45,
            provider: "exotel",
            is_active: true,
            safety_state: "NONE",
            safety_signals_count: 0,
            svi_score: 15,
            svi_band: "LOW",
          },
        ],
        recent_calls: [],
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        caller_masked_number: "+91******3210",
        state: "STREAMING",
        conversation_state: "SPEAKING",
        current_language: "en-IN",
        safety_state: "NONE",
        safety_signals_count: 0,
        duration_seconds: 45,
        provider: "exotel",
        is_active: true,
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}/transcript`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        utterances: [
          {
            utterance_id: "utt-001",
            speaker: "caller",
            text: "Hello, I need some information about your services.",
            language: "en-IN",
            safety_flag: false,
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}/events`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        events: [],
      }),
    });
  });

  await page.route(`**/v1/safety/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        safety_state: "NONE",
        active_signals: [],
        acknowledged_signals: [],
        escalation_history: [],
      }),
    });
  });

  await page.route(`**/v1/svi/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assessment_id: "svi-mock-001",
        call_id: mockCallId,
        session_id: "sess-mock-001",
        turn_index: 1,
        score: 15,
        band: "LOW",
        trend: "INITIAL",
        delta: 0,
        assessment_completeness: 0.35,
        features: [],
        top_contributors: [],
        protective_factor_reduction: 0,
        critical_override_applied: false,
        acoustic_evidence_available: false,
        acoustic_evidence_note: "Acoustic evidence: Not available in current phase (Phase 6 deferred)",
        requires_human_review: false,
        disclaimer: "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
        evaluated_at: new Date().toISOString(),
        svi_version: "v1",
      }),
    });
  });
}

test.describe("SAMVED Phase 5 SVI Engine E2E", () => {
  test("renders SVI panel with score gauge, band badge, trend indicator, and acoustic notice", async ({ page }) => {
    await setupMockCall(page);
    await page.goto("/calls");

    // 1. Verify SVI panel exists
    const sviPanel = page.getByTestId("svi-panel");
    await expect(sviPanel).toBeVisible({ timeout: 10000 });

    // 2. Verify SVI band badge
    const bandBadge = page.getByTestId("svi-band-badge");
    await expect(bandBadge).toBeAttached();
    await expect(bandBadge).toContainText("LOW");

    // 3. Verify SVI trend indicator
    const trendIndicator = page.getByTestId("svi-trend-indicator");
    await expect(trendIndicator).toBeAttached();
    await expect(trendIndicator).toContainText("INITIAL");

    // 4. Verify completeness bar
    const completenessBar = page.getByTestId("svi-completeness-bar");
    await expect(completenessBar).toBeAttached();

    // 5. Verify acoustic deferral notice
    const acousticNotice = page.getByTestId("svi-acoustic-notice");
    await expect(acousticNotice).toBeAttached();
    await expect(acousticNotice).toContainText("Phase 6 deferred");
  });

  test("renders SVI Lab button and opens SVI Simulation Lab modal", async ({ page }) => {
    await page.goto("/calls");

    // 1. Verify SVI Lab button in header
    const sviLabBtn = page.getByTestId("open-svi-lab");
    await expect(sviLabBtn).toBeAttached();
    await expect(sviLabBtn).toContainText("SVI Lab");

    // 2. Click to open modal
    await sviLabBtn.click();

    // 3. Verify modal header
    await expect(page.locator("text=SVI Scoring Simulation Lab")).toBeVisible();

    // 4. Verify disclaimer text
    await expect(page.locator("text=Operational Prototype Priority Indicator")).toBeVisible();

    // 5. Verify preset scenario buttons exist
    await expect(page.locator("text=Active Danger")).toBeVisible();
    await expect(page.locator("text=Coercive Control")).toBeVisible();
    await expect(page.locator("text=Tamil Distress")).toBeVisible();
    await expect(page.locator("text=Protective Buffer")).toBeVisible();
    await expect(page.locator("text=Historical Only")).toBeVisible();

    // 6. Verify language selector
    const langSelect = page.getByTestId("svi-lab-lang");
    await expect(langSelect).toBeAttached();

    // 7. Verify input textarea
    const inputTextarea = page.getByTestId("svi-lab-input");
    await expect(inputTextarea).toBeAttached();

    // 8. Verify evaluate button
    const evalBtn = page.getByTestId("svi-lab-evaluate");
    await expect(evalBtn).toBeAttached();
    await expect(evalBtn).toContainText("Evaluate SVI Score");
  });

  test("evaluates SVI in simulation lab and displays deterministic result", async ({ page }) => {
    // Intercept SVI evaluate endpoint
    await page.route("**/v1/svi/evaluate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          assessment_id: "test-assessment-001",
          call_id: "sim-call-01",
          session_id: "sim-sess-01",
          turn_index: 1,
          score: 42,
          band: "MODERATE",
          trend: "INITIAL",
          delta: 0,
          assessment_completeness: 0.55,
          features: [
            {
              category: "coercion_control",
              feature_name: "Coercion Control: 'locked me'",
              raw_score: 12.0,
              recency: "PRESENT",
              recency_weight: 1.0,
              weighted_score: 12.0,
              matched_phrase: "locked me",
              rule_id: "svi_coercion_control",
              description: "Matched keyword 'locked me' under coercion_control with PRESENT recency.",
            },
            {
              category: "distress_overwhelm",
              feature_name: "Distress Overwhelm: 'panicking'",
              raw_score: 10.0,
              recency: "PRESENT",
              recency_weight: 1.0,
              weighted_score: 10.0,
              matched_phrase: "panicking",
              rule_id: "svi_distress_overwhelm",
              description: "Matched keyword 'panicking' under distress_overwhelm with PRESENT recency.",
            },
          ],
          top_contributors: ["Coercion Control: 'locked me' (+12 pts)", "Distress Overwhelm: 'panicking' (+10 pts)"],
          protective_factor_reduction: 0,
          critical_override_applied: false,
          acoustic_evidence_available: false,
          acoustic_evidence_note: "Acoustic evidence: Not available in current phase (Phase 6 deferred)",
          requires_human_review: false,
          disclaimer: "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
          evaluated_at: new Date().toISOString(),
          svi_version: "v1",
        }),
      });
    });

    await page.goto("/calls");

    // Open SVI Lab
    await page.getByTestId("open-svi-lab").click();
    await expect(page.locator("text=SVI Scoring Simulation Lab")).toBeVisible();

    // Click Active Danger preset
    await page.locator("text=Active Danger").click();

    // Click Evaluate
    await page.getByTestId("svi-lab-evaluate").click();

    // Wait for result
    const labResult = page.getByTestId("svi-lab-result");
    await expect(labResult).toBeVisible({ timeout: 5000 });

    // Verify score and band are displayed
    await expect(labResult.locator("text=42")).toBeVisible();
    await expect(labResult.locator("text=MODERATE")).toBeVisible();

    // Verify feature attribution
    await expect(labResult.locator("text=Feature Attribution")).toBeVisible();
    await expect(labResult.locator("text=Coercion Control")).toBeVisible();

    // Verify acoustic notice
    await expect(labResult.locator("text=Phase 6 deferred")).toBeVisible();
  });

  test("SVI panel shows NOT clinical disclaimer", async ({ page }) => {
    await setupMockCall(page);
    await page.goto("/calls");

    const sviPanel = page.getByTestId("svi-panel");
    await expect(sviPanel).toBeVisible({ timeout: 10000 });
    await expect(sviPanel).toContainText("NOT a clinical, medical, or diagnostic score");
  });
});
