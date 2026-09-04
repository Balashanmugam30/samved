import { test, expect } from "@playwright/test";

test.describe("SAMVED Phase 4 Deterministic Safety Engine E2E", () => {
  test("renders safety engine status indicator and navigation triggers", async ({ page }) => {
    await page.goto("/calls");

    // 1. Verify safety engine status badge in header
    const statusBadge = page.getByTestId("safety-engine-status");
    await expect(statusBadge).toBeAttached();
    await expect(statusBadge).toContainText("Safety Engine:");

    // 2. Verify Rules Catalog and Safety Lab action buttons
    const rulesBtn = page.getByRole("button", { name: "Rules Catalog" });
    await expect(rulesBtn).toBeAttached();

    const labBtn = page.getByTestId("open-safety-lab");
    await expect(labBtn).toBeAttached();
  });

  test("opens safety rules catalog modal and displays loaded rules", async ({ page }) => {
    // Intercept rules endpoint
    await page.route("**/v1/safety/rules", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          engine_version: "v1.0.0",
          rules_count: 2,
          rules: [
            {
              rule_id: "RULE_THREAT_001",
              rule_version: "v1.0.0",
              default_severity: "HIGH",
              description: "Detects active physical violence and ongoing bodily harm threats.",
              target_languages: ["en-IN", "ta-IN", "hi-IN"],
              negative_examples: ["I saw an action movie yesterday"],
            },
            {
              rule_id: "RULE_WEAPON_002",
              rule_version: "v1.0.0",
              default_severity: "CRITICAL",
              description: "Detects active presence or threatening possession of lethal weapons.",
              target_languages: ["en-IN", "ta-IN", "hi-IN"],
              negative_examples: ["I am chopping onions with a kitchen knife"],
            },
          ],
        }),
      });
    });

    await page.goto("/calls");

    // Open Rules Catalog
    await page.getByRole("button", { name: "Rules Catalog" }).click();

    // Assert modal header and rules are displayed
    await expect(page.locator("text=Deterministic Safety Rules Catalog")).toBeVisible();
    await expect(page.locator("text=RULE_THREAT_001")).toBeVisible();
    await expect(page.locator("text=RULE_WEAPON_002")).toBeVisible();
    await expect(page.locator("text=Detects active physical violence")).toBeVisible();

    // Close modal
    await page.locator("button:has(svg.lucide-x)").first().click();
    await expect(page.locator("text=Deterministic Safety Rules Catalog")).not.toBeVisible();
  });

  test("runs interactive deterministic safety lab evaluation and displays explainable evidence", async ({
    page,
  }) => {
    // Intercept evaluation endpoint
    await page.route("**/v1/safety/evaluate", async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || "{}");

      if (postData.utterance_text?.includes("knife") && !postData.utterance_text?.includes("no weapon")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            safety_state: "CRITICAL",
            requires_human_review: true,
            deterministic: true,
            evaluated_at: new Date().toISOString(),
            signals: [
              {
                signal_id: "sig-mock-001",
                signal_type: "WEAPON_PRESENCE",
                severity: "CRITICAL",
                evidence: {
                  rule_id: "RULE_WEAPON_002",
                  rule_version: "v1.0.0",
                  matched_phrase: "knife",
                  reason: "Active lethal weapon indicator identified in threat context.",
                  temporal_context: "PRESENT",
                  negated: false,
                },
              },
            ],
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            safety_state: "NONE",
            requires_human_review: false,
            deterministic: true,
            evaluated_at: new Date().toISOString(),
            signals: [],
          }),
        });
      }
    });

    await page.goto("/calls");

    // Open Safety Lab
    await page.getByTestId("open-safety-lab").click();
    await expect(page.getByTestId("safety-lab-modal")).toBeVisible();

    // Select Active Weapon Threat Preset
    await page.getByRole("button", { name: "Active Weapon Threat" }).click();
    await expect(page.getByTestId("safety-lab-input")).toHaveValue(
      "He has a knife and is breaking into my door right now!"
    );

    // Click Evaluate Deterministically
    await page.getByTestId("safety-lab-eval-btn").click();

    // Assert evaluation results
    await expect(page.getByTestId("safety-lab-state")).toHaveText("CRITICAL");
    await expect(page.locator("text=Requires Human Review")).toBeVisible();
    await expect(page.locator("text=WEAPON_PRESENCE")).toBeVisible();
    await expect(page.locator("text=RULE_WEAPON_002")).toBeVisible();
    await expect(page.locator("text=Matched Phrase:")).toBeVisible();

    // Now test Negated Threat Cue
    await page.getByRole("button", { name: "Negated Threat Cue" }).click();
    await page.getByTestId("safety-lab-eval-btn").click();
    await expect(page.getByTestId("safety-lab-state")).toHaveText("NONE");
    await expect(page.locator("text=No safety threats detected")).toBeVisible();

    // Close Safety Lab
    await page.locator("button:has(svg.lucide-x)").first().click();
    await expect(page.getByTestId("safety-lab-modal")).not.toBeVisible();
  });

  test("displays safety oversight banner and enables operator acknowledgment on call with active alerts", async ({
    page,
  }) => {
    const mockCallId = "call-safety-test-01";

    // Prevent background WebSocket from racing or clearing mock state
    await page.route("**/ws/operator", (route) => route.abort());

    // Mock /v1/calls list
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
              safety_state: "CRITICAL",
              safety_signals_count: 1,
            },
          ],
          recent_calls: [],
        }),
      });
    });

    // Mock call details and safety endpoint
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
          safety_state: "CRITICAL",
          safety_signals_count: 1,
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
              text: "He has a weapon and won't let me leave!",
              language: "en-IN",
              safety_flag: true,
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
          safety_state: "CRITICAL",
          requires_human_review: true,
          safety_signals: [
            {
              signal_id: "sig-alert-101",
              signal_type: "ONGOING_THREAT",
              severity: "CRITICAL",
              confidence: 1.0,
              evidence: {
                rule_id: "RULE_THREAT_001",
                rule_version: "v1.0.0",
                matched_category: "THREAT",
                matched_phrase: "won't let me leave",
                reason: "Active confinement and acute threat detected.",
                temporal_context: "PRESENT",
                negated: false,
              },
              rule_id: "RULE_THREAT_001",
              rule_version: "v1.0.0",
              call_id: mockCallId,
              session_id: "sess-101",
              requires_human_review: true,
              acknowledged: false,
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Mock acknowledgment endpoint
    let acknowledgedReceived = false;
    await page.route(`**/v1/safety/calls/${mockCallId}/acknowledge`, async (route) => {
      acknowledgedReceived = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "acknowledged",
          signal_id: "sig-alert-101",
          acknowledged: true,
          acknowledged_at: new Date().toISOString(),
          acknowledged_by: "operator_console",
        }),
      });
    });

    await page.goto("/calls");

    // Click call card to select it
    await page.getByTestId("call-item").first().waitFor({ state: "visible", timeout: 10000 });
    await page.getByTestId("call-item").first().click({ force: true });

    // Verify Safety Engine Oversight Panel
    await expect(page.getByTestId("safety-engine-panel")).toBeVisible();
    await expect(page.getByTestId("safety-state-badge")).toHaveText("CRITICAL");
    await expect(page.locator("text=Requires Human Review").first()).toBeVisible();

    // Verify Active Alert Card and reason
    await expect(page.getByTestId("safety-signal-card")).toBeVisible();
    await expect(page.locator("text=Active confinement and acute threat detected.")).toBeVisible();

    // Verify Transcript safety flag badge
    await expect(page.locator("text=Safety Flagged")).toBeVisible();

    // Click Acknowledge Alert button
    const ackButton = page.getByTestId("acknowledge-safety-alert");
    await expect(ackButton).toBeVisible();
    await ackButton.click({ force: true });

    // Verify acknowledged status badge appears
    await expect(page.locator("text=Acknowledged by operator_console")).toBeVisible();
    expect(acknowledgedReceived).toBe(true);
  });
});
