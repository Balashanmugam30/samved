import { test, expect, Page } from "@playwright/test";

async function setupMockCallWithOrchestration(
  page: Page,
  mockCallId = "call-orch-test-01",
  orchestrationState = "COMPLETED"
) {
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
            orchestration_state: orchestrationState,
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
            utterance_id: "utt-01",
            speaker: "caller",
            text: "Enakku udhavi thevai, aabathu irukku.",
            language: "ta-IN",
            confidence: 0.96,
            is_final: true,
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
        events: [
          {
            event_id: "ev-orch-1",
            call_id: mockCallId,
            event_type: "ORCHESTRATION_STARTED",
            payload: {
              turn_id: "utt-01",
              selected_agents: [
                "safety_context_agent",
                "acoustic_context_agent",
                "language_context_agent",
                "conversation_context_agent",
                "support_options_agent",
                "operator_briefing_agent",
              ],
            },
            timestamp: new Date().toISOString(),
          },
          {
            event_id: "ev-orch-2",
            call_id: mockCallId,
            event_type: "ORCHESTRATION_COMPLETED",
            payload: {
              turn_id: "utt-01",
              state: orchestrationState,
              total_latency_ms: 135.5,
              completed_agents: [
                "safety_context_agent",
                "acoustic_context_agent",
                "language_context_agent",
                "conversation_context_agent",
                "support_options_agent",
                "operator_briefing_agent",
              ],
            },
            timestamp: new Date().toISOString(),
          },
        ],
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
        operational_signals: [],
      }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        action: "CONFIRM_SAFETY",
        priority: "P1",
      }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${mockCallId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ strategies: [] }),
    });
  });

  await page.route(`**/v1/operator/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        ownership_state: "AI_ASSISTED",
        handoff_status: "AVAILABLE",
        adaptive_paused: false,
      }),
    });
  });

  await page.route(`**/v1/operator/calls/${mockCallId}/notes`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ notes: [] }),
    });
  });

  // Orchestration call detail endpoint
  await page.route(`**/v1/orchestration/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-123",
        call_id: mockCallId,
        turn_id: "utt-01",
        state: orchestrationState,
        selected_agents: [
          "safety_context_agent",
          "acoustic_context_agent",
          "language_context_agent",
          "conversation_context_agent",
          "support_options_agent",
          "operator_briefing_agent",
        ],
        completed_agents: [
          "safety_context_agent",
          "acoustic_context_agent",
          "language_context_agent",
          "conversation_context_agent",
          "support_options_agent",
          "operator_briefing_agent",
        ],
        failed_agents: [],
        timed_out_agents: [],
        cancelled_agents: [],
        total_latency_ms: 135.5,
        briefing: {
          safety_summary: "No immediate lethal threat cues. Standard triage.",
          svi_summary: "SVI 35 (MODERATE tier). Contributing factors: emotional distress.",
          acoustic_summary: "Acoustic audio features stable. SNR 18 dB.",
          adaptive_recommendation: "Establish immediate safety and confirm location.",
          key_facts: ["Caller reports distress in Chennai"],
          evidence_refs: ["turn:utt-01", "rule:BASELINE"],
          confidence: 0.95,
        },
        agent_outputs: {
          safety_context_agent: { status: "SUCCESS", latency_ms: 12, confidence: 1.0 },
          acoustic_context_agent: { status: "SUCCESS", latency_ms: 15, confidence: 0.95 },
          language_context_agent: { status: "SUCCESS", latency_ms: 18, confidence: 0.9 },
          conversation_context_agent: { status: "SUCCESS", latency_ms: 55, confidence: 0.85 },
          support_options_agent: { status: "SUCCESS", latency_ms: 8, confidence: 1.0 },
          operator_briefing_agent: { status: "SUCCESS", latency_ms: 25, confidence: 0.95 },
        },
      }),
    });
  });

  // Orchestration refresh endpoint
  await page.route(`**/v1/orchestration/calls/${mockCallId}/refresh`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-refreshed",
        call_id: mockCallId,
        turn_id: "refresh-turn-01",
        state: "COMPLETED",
        total_latency_ms: 142.0,
        completed_agents: [
          "safety_context_agent",
          "acoustic_context_agent",
          "language_context_agent",
          "conversation_context_agent",
          "support_options_agent",
          "operator_briefing_agent",
        ],
        briefing: {
          safety_summary: "Refreshed safety context: stable.",
          svi_summary: "Refreshed SVI: 35 (MODERATE tier).",
          acoustic_summary: "Refreshed acoustic telemetry: normal speech rate.",
          adaptive_recommendation: "Continue supportive inquiry.",
          key_facts: ["Caller reports distress in Chennai", "Refresh verified"],
          evidence_refs: ["turn:refresh-turn-01"],
          confidence: 0.98,
        },
        agent_outputs: {
          safety_context_agent: { status: "SUCCESS", latency_ms: 10, confidence: 1.0 },
          acoustic_context_agent: { status: "SUCCESS", latency_ms: 12, confidence: 0.95 },
          language_context_agent: { status: "SUCCESS", latency_ms: 14, confidence: 0.9 },
          conversation_context_agent: { status: "SUCCESS", latency_ms: 50, confidence: 0.85 },
          support_options_agent: { status: "SUCCESS", latency_ms: 6, confidence: 1.0 },
          operator_briefing_agent: { status: "SUCCESS", latency_ms: 20, confidence: 0.95 },
        },
      }),
    });
  });
}

test.describe("Phase 9: Multi-Agent Orchestration & Specialized AI Coordination Layer", () => {
  test("renders multi-agent panel, state badge, workers grid, and operator briefing card", async ({
    page,
  }) => {
    await setupMockCallWithOrchestration(page, "call-orch-01");
    await page.goto("/calls");

    // Select the call
    await page.click('[data-testid="call-item"]');

    // 1. Unified triage summary 6th card (orchestration-summary)
    const orchSummary = page.locator('[data-testid="orchestration-summary"]');
    await expect(orchSummary).toBeVisible();
    await expect(orchSummary).toContainText("Multi-Agent");

    // 2. Multi-agent panel
    const multiAgentPanel = page.locator('[data-testid="multi-agent-panel"]');
    await expect(multiAgentPanel).toBeVisible();
    await expect(multiAgentPanel).toContainText("Multi-Agent Orchestration & Specialized AI Layer");

    // 3. Orchestration state badge
    const stateBadge = page.locator('[data-testid="orchestration-state-badge"]');
    await expect(stateBadge).toBeVisible();
    await expect(stateBadge).toContainText("COMPLETED");

    // 4. Workers grid
    const workersGrid = page.locator('[data-testid="workers-grid"]');
    await expect(workersGrid).toBeVisible();
    const workerChips = page.locator('[data-testid="worker-chip"]');
    await expect(workerChips).toHaveCount(6);

    // Verify all 6 workers are represented
    await expect(workersGrid).toContainText("Safety Adapter");
    await expect(workersGrid).toContainText("Acoustic Telemetry");
    await expect(workersGrid).toContainText("Language & Dialect");
    await expect(workersGrid).toContainText("Facts & Gaps");
    await expect(workersGrid).toContainText("Support Stub");
    await expect(workersGrid).toContainText("Briefing Formatter");

    // 5. Operator Briefing Card
    const briefingCard = page.locator('[data-testid="operator-briefing-card"]');
    await expect(briefingCard).toBeVisible();
    await expect(briefingCard).toContainText("Operator Briefing Card");

    // Check specific briefing sections
    await expect(page.locator('[data-testid="briefing-safety-summary"]')).toContainText("No immediate lethal threat");
    await expect(page.locator('[data-testid="briefing-svi-summary"]')).toContainText("SVI 35");
    await expect(page.locator('[data-testid="briefing-acoustic-summary"]')).toContainText("SNR 18 dB");
    await expect(page.locator('[data-testid="briefing-adaptive-recommendation"]')).toContainText("Establish immediate safety");
    await expect(page.locator('[data-testid="briefing-key-facts"]')).toContainText("Caller reports distress in Chennai");
    await expect(page.locator('[data-testid="briefing-evidence-chips"]')).toContainText("turn:utt-01");
  });

  test("refresh orchestration button triggers manual refresh and updates briefing", async ({
    page,
  }) => {
    await setupMockCallWithOrchestration(page, "call-orch-refresh");
    await page.goto("/calls");
    await page.click('[data-testid="call-item"]');

    const refreshBtn = page.locator('[data-testid="refresh-orchestration-button"]');
    await expect(refreshBtn).toBeVisible();

    const [response] = await Promise.all([
      page.waitForResponse((resp) => resp.url().includes("/refresh")),
      refreshBtn.click(),
    ]);
    expect(response.status()).toBe(200);

    // Verify briefing was updated with refreshed data
    await expect(page.locator('[data-testid="briefing-safety-summary"]')).toContainText("Refreshed safety context");
    await expect(page.locator('[data-testid="briefing-key-facts"]')).toContainText("Refresh verified");
  });

  test("supports DEGRADED state badge and resilience display", async ({ page }) => {
    await setupMockCallWithOrchestration(page, "call-orch-degraded", "DEGRADED");
    await page.goto("/calls");
    await page.click('[data-testid="call-item"]');

    const stateBadge = page.locator('[data-testid="orchestration-state-badge"]');
    await expect(stateBadge).toBeVisible();
    await expect(stateBadge).toContainText("DEGRADED");
  });

  test("filters timeline events by ORCHESTRATION category", async ({ page }) => {
    await setupMockCallWithOrchestration(page, "call-orch-events");
    await page.goto("/calls");
    await page.click('[data-testid="call-item"]');

    // Click the ORCHESTRATION filter pill in event timeline
    const orchFilterPill = page.getByRole("button", { name: "ORCHESTRATION" });
    await expect(orchFilterPill).toBeVisible();
    await orchFilterPill.click();

    // Verify timeline events displayed match orchestration
    const timelineItems = page.locator('[data-testid="timeline-event-item"]');
    const count = await timelineItems.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const text = await timelineItems.nth(i).innerText();
      expect(text).toMatch(/ORCHESTRATION|AGENT_|BRIEFING/);
    }
  });
});
