import { test, expect, Page } from "@playwright/test";

async function setupMockCallWithAdaptive(page: Page, mockCallId = "call-adaptive-test-01") {
  // Prevent background WebSocket from racing
  await page.route("**/ws/operator", (route) => route.abort());

  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: [
          {
            call_id: mockCallId,
            caller_masked_number: "+91******4321",
            state: "STREAMING",
            conversation_state: "LISTENING",
            current_language: "ta-IN",
            duration_seconds: 45,
            provider: "exotel",
            is_active: true,
            safety_state: "NONE",
            safety_signals_count: 0,
            svi_score: 35,
            svi_band: "MODERATE",
            acoustic_quality: "GOOD",
            acoustic_confidence: 0.95,
            acoustic_signals_count: 0,
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
        caller_masked_number: "+91******4321",
        state: "STREAMING",
        conversation_state: "LISTENING",
        current_language: "ta-IN",
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
            utterance_id: "utt-ad-001",
            speaker: "caller",
            text: "வணக்கம், எனக்கு உதவி வேண்டும்.",
            language: "ta-IN",
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

  await page.route(`**/v1/safety/status`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "healthy", active_rules: 24 }),
    });
  });

  await page.route(`**/v1/safety/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        safety_state: "NONE",
        safety_signals: [],
      }),
    });
  });

  await page.route(`**/v1/svi/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        score: 35,
        band: "MODERATE",
        trend: "INITIAL",
        delta: 0,
        assessment_completeness: 0.5,
        top_contributors: ["DISCLOSURE_ELEVATION"],
        protective_factor_reduction: 0,
        critical_override_applied: false,
        requires_human_review: false,
      }),
    });
  });

  await page.route(`**/v1/acoustic/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        quality: "GOOD",
        confidence: 0.95,
        voice_activity: { speech_activity_ratio: 0.55, silence_ratio: 0.45 },
        pause_metrics: { longest_pause_ms: 800, pause_count: 2 },
        interruption_metrics: { interruption_count: 0 },
        energy_metrics: { energy_variability: 0.2, mean_energy_rms: 400 },
        pitch_metrics: { median_f0_hz: 180 },
        operational_signals: [],
      }),
    });
  });

  // Adaptive Strategy Mock
  await page.route(`**/v1/adaptive/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        action: "ASK_SUPPORT",
        priority: "P4",
        target_information_gap: "support_domain",
        reason_codes: ["INFORMATION_GAP"],
        evidence_used: ["caller_turn_1"],
        confidence: 0.95,
        operator_override_applied: false,
        operator_override_reason: null,
        fallback_response_text: "What type of support do you need right now?",
        evaluated_at: new Date().toISOString(),
      }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${mockCallId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        total_strategies: 2,
        strategies: [
          {
            action: "SAFETY_CHECK",
            priority: "P1",
            target_information_gap: "immediate_danger",
            reason_codes: ["INTENT_UNCERTAIN"],
            evaluated_at: new Date().toISOString(),
          },
          {
            action: "ASK_SUPPORT",
            priority: "P4",
            target_information_gap: "support_domain",
            reason_codes: ["INFORMATION_GAP"],
            evaluated_at: new Date().toISOString(),
          },
        ],
        active_override: null,
      }),
    });
  });
}

test.describe("Phase 7: Adaptive Conversation Engine", () => {
  test("1. Renders Adaptive Conversation Panel with policy, priority, and reason chips", async ({
    page,
  }) => {
    const mockCallId = "call-adaptive-test-01";
    await setupMockCallWithAdaptive(page, mockCallId);

    await page.goto("/calls");

    // Wait for the main panel to render
    const panel = page.locator('[data-testid="adaptive-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Verify Action Badge
    const strategyBadge = page.locator('[data-testid="adaptive-strategy"]');
    await expect(strategyBadge).toBeVisible();
    await expect(strategyBadge).toHaveText("ASK_SUPPORT");

    // Verify Priority Badge
    const priorityBadge = page.locator('[data-testid="adaptive-priority"]');
    await expect(priorityBadge).toBeVisible();
    await expect(priorityBadge).toHaveText("P4");

    // Verify Target Gap
    const targetGap = page.locator('[data-testid="adaptive-target"]');
    await expect(targetGap).toBeVisible();
    await expect(targetGap).toContainText("support_domain");

    // Verify Confidence
    const conf = page.locator('[data-testid="adaptive-confidence"]');
    await expect(conf).toBeVisible();
    await expect(conf).toContainText("95%");

    // Verify Reason Codes
    const reasonsContainer = page.locator('[data-testid="adaptive-reasons"]');
    await expect(reasonsContainer).toBeVisible();
    const reasonChip = page.locator('[data-testid="adaptive-reason-chip"]');
    await expect(reasonChip.first()).toBeVisible();
    await expect(reasonChip.first()).toContainText("INFORMATION_GAP");

    // Verify Structured Evidence
    const evidenceContainer = page.locator('[data-testid="adaptive-evidence"]');
    await expect(evidenceContainer).toBeVisible();
    const evChip = page.locator('[data-testid="adaptive-evidence-chip"]');
    await expect(evChip.first()).toBeVisible();
    await expect(evChip.first()).toContainText("caller_turn_1");

    // Verify Strategy History Trajectory
    const historyContainer = page.locator('[data-testid="adaptive-history"]');
    await expect(historyContainer).toBeVisible();
    const histItems = page.locator('[data-testid="adaptive-history-item"]');
    expect(await histItems.count()).toBeGreaterThanOrEqual(2);

    // Verify Non-clinical disclaimer
    const disclaimer = page.locator('[data-testid="adaptive-disclaimer"]');
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toContainText("Non-clinical");
  });

  test("2. Operator Override Controls trigger proper REST calls and update UI state", async ({
    page,
  }) => {
    const mockCallId = "call-adaptive-test-02";
    await setupMockCallWithAdaptive(page, mockCallId);

    let overridePayload: any = null;
    await page.route(`**/v1/adaptive/calls/${mockCallId}/override`, async (route) => {
      overridePayload = JSON.parse(route.request().postData() || "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          override_id: "ovr-001",
          call_id: mockCallId,
          action: overridePayload.action,
          reason: overridePayload.reason,
          operator_id: "operator_console_1",
          applied_at: new Date().toISOString(),
          active: true,
        }),
      });
    });

    // Mock the updated strategy after override
    await page.route(`**/v1/adaptive/calls/${mockCallId}`, async (route) => {
      if (overridePayload && overridePayload.action === "operator_force_human") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            action: "HUMAN_HANDOFF",
            priority: "P0",
            target_information_gap: "human_counselor_escalation",
            reason_codes: ["OPERATOR_FORCE_HUMAN_OVERRIDE"],
            evidence_used: ["operator_override"],
            confidence: 1.0,
            operator_override_applied: true,
            operator_override_reason: "Operator escalation to human agent",
            fallback_response_text: "Connecting you to an emergency counselor immediately.",
            evaluated_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            action: "ASK_SUPPORT",
            priority: "P4",
            target_information_gap: "support_domain",
            reason_codes: ["INFORMATION_GAP"],
            evidence_used: [],
            confidence: 0.95,
            operator_override_applied: false,
            operator_override_reason: null,
            fallback_response_text: "What support do you need?",
            evaluated_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.goto("/calls");

    // Click call card to select it
    await page.getByTestId("call-item").first().waitFor({ state: "visible", timeout: 10000 });
    await page.getByTestId("call-item").first().click({ force: true });

    // Click Force Human
    const forceHumanBtn = page.locator('[data-testid="btn-override-human"]');
    await expect(forceHumanBtn).toBeVisible({ timeout: 10000 });
    await forceHumanBtn.click();

    // Verify UI displays the updated P0 and HUMAN_HANDOFF strategy (polling until network response arrives)
    const priorityBadge = page.locator('[data-testid="adaptive-priority"]');
    await expect(priorityBadge).toHaveText("P0", { timeout: 10000 });
    const strategyBadge = page.locator('[data-testid="adaptive-strategy"]');
    await expect(strategyBadge).toHaveText("HUMAN_HANDOFF");

    // Verify REST call was executed
    expect(overridePayload).not.toBeNull();
    expect(overridePayload.action).toBe("operator_force_human");

    // Verify override badge is active
    const overrideBadge = page.locator('[data-testid="adaptive-override-badge"]');
    await expect(overrideBadge).toBeVisible();
    await expect(overrideBadge).toContainText("OVERRIDE ACTIVE");
  });

  test("3. Adaptive Simulation Lab opens, accepts presets, and executes live evaluation", async ({
    page,
  }) => {
    const mockCallId = "call-adaptive-test-03";
    await setupMockCallWithAdaptive(page, mockCallId);

    // Mock simulation plan endpoint
    await page.route("**/v1/adaptive/plan", async (route) => {
      const body = JSON.parse(route.request().postData() || "{}");
      let action = "ASK_SUPPORT";
      let priority = "P4";
      let target = "support_domain";
      let reasons = ["INFORMATION_GAP"];

      if (body.safety_state === "CRITICAL") {
        action = "SAFETY_CHECK";
        priority = "P0";
        target = "immediate_danger_clarification";
        reasons = ["CRITICAL_THREAT_PRESENT"];
      } else if (body.acoustic_quality === "POOR") {
        action = "CLARIFY_AUDIO";
        priority = "P3";
        target = "audio_channel_clarification";
        reasons = ["POOR_AUDIO_QUALITY"];
      } else if (body.svi_score >= 76) {
        action = "SAFETY_CHECK";
        priority = "P2";
        target = "high_vulnerability_stabilization";
        reasons = ["HIGH_SVI_SCORE"];
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action,
          priority,
          target_information_gap: target,
          reason_codes: reasons,
          evidence_used: ["simulated_input"],
          confidence: 0.98,
          fallback_response_text: `Deterministic fallback response for ${action}`,
          disclaimer: "Deterministic conversational strategy layer. Non-clinical.",
          evaluated_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/calls");

    // Open Adaptive Simulation Lab modal
    const openLabBtn = page.locator('[data-testid="open-adaptive-lab"]');
    await expect(openLabBtn).toBeVisible();
    await openLabBtn.click();

    // Verify modal is open
    const modal = page.locator('[data-testid="adaptive-lab-modal"]');
    await expect(modal).toBeVisible();

    // Select Critical Threat Preset
    const critPreset = page.locator('[data-testid="preset-danger-unknown"]');
    await expect(critPreset).toBeVisible();
    await critPreset.click();

    // Run Evaluation
    const evalBtn = page.locator('[data-testid="run-adaptive-eval"]');
    await expect(evalBtn).toBeVisible();
    await evalBtn.click();

    // Verify Result Container shows P0 Critical Threat
    const resultBox = page.locator('[data-testid="adaptive-lab-result"]');
    await expect(resultBox).toBeVisible();
    await expect(resultBox).toContainText("SAFETY_CHECK");
    await expect(resultBox).toContainText("P0");
    await expect(resultBox).toContainText("CRITICAL_THREAT_PRESENT");

    // Select Degraded Audio Preset
    const audioPreset = page.locator('[data-testid="preset-poor-audio"]');
    await audioPreset.click();
    await evalBtn.click();

    // Verify Result Container shows P3 Audio Clarification
    await expect(resultBox).toContainText("CLARIFY_AUDIO");
    await expect(resultBox).toContainText("P3");
    await expect(resultBox).toContainText("POOR_AUDIO_QUALITY");

    // Close Modal
    const closeBtn = page.locator('[data-testid="close-adaptive-lab"]');
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
    await expect(modal).not.toBeVisible();
  });
});
