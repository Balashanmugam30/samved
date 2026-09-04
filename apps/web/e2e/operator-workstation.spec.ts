import { test, expect, Page } from "@playwright/test";

interface MockCallParams {
  callId: string;
  callerNumber: string;
  ownershipState: string;
  handoffStatus: string;
  adaptivePaused: boolean;
  safetyState: string;
  sviBand: string;
  notesCount: number;
}

async function setupWorkstationMocks(
  page: Page,
  primaryCall: MockCallParams = {
    callId: "call-op-test-01",
    callerNumber: "+91******3210",
    ownershipState: "AI_ASSISTED",
    handoffStatus: "AVAILABLE",
    adaptivePaused: false,
    safetyState: "ELEVATED",
    sviBand: "MODERATE",
    notesCount: 1,
  },
  secondaryCall?: MockCallParams
) {
  // Prevent background WebSocket from racing or disconnecting
  await page.route("**/ws/operator", (route) => route.abort());

  const activeCalls = [
    {
      call_id: primaryCall.callId,
      caller_masked_number: primaryCall.callerNumber,
      state: "STREAMING",
      conversation_state: "LISTENING",
      current_language: "ta-IN",
      duration_seconds: 62,
      provider: "exotel",
      is_active: true,
      safety_state: primaryCall.safetyState,
      safety_signals_count: primaryCall.safetyState !== "NONE" ? 1 : 0,
      svi_score: 52,
      svi_band: primaryCall.sviBand,
      ownership_state: primaryCall.ownershipState,
      notes_count: primaryCall.notesCount,
    },
  ];

  if (secondaryCall) {
    activeCalls.push({
      call_id: secondaryCall.callId,
      caller_masked_number: secondaryCall.callerNumber,
      state: "STREAMING",
      conversation_state: "LISTENING",
      current_language: "hi-IN",
      duration_seconds: 24,
      provider: "exotel",
      is_active: true,
      safety_state: secondaryCall.safetyState,
      safety_signals_count: secondaryCall.safetyState !== "NONE" ? 2 : 0,
      svi_score: 84,
      svi_band: secondaryCall.sviBand,
      ownership_state: secondaryCall.ownershipState,
      notes_count: secondaryCall.notesCount,
    });
  }

  // Calls list
  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: activeCalls,
        recent_calls: [],
      }),
    });
  });

  // Call detail for primary
  await page.route(`**/v1/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        caller_masked_number: primaryCall.callerNumber,
        state: "STREAMING",
        conversation_state: "LISTENING",
        current_language: "ta-IN",
        safety_state: primaryCall.safetyState,
        duration_seconds: 62,
        provider: "exotel",
        is_active: true,
      }),
    });
  });

  await page.route(`**/v1/calls/${primaryCall.callId}/transcript`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        utterances: [
          {
            utterance_id: "utt-op-001",
            speaker: "caller",
            text: "வணக்கம், நான் மிகுந்த அச்சத்தில் உள்ளேன்.",
            language: "ta-IN",
            safety_flag: false,
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  await page.route(`**/v1/calls/${primaryCall.callId}/events`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        events: [
          {
            event_id: "ev-01",
            call_id: primaryCall.callId,
            event_type: "OPERATOR_STATE_CHANGED",
            timestamp: new Date().toISOString(),
            payload: { ownership_state: primaryCall.ownershipState },
          },
          {
            event_id: "ev-02",
            call_id: primaryCall.callId,
            event_type: "SAFETY_SIGNAL_TRIGGERED",
            timestamp: new Date().toISOString(),
            payload: { signal: "THREAT_EVALUATED", severity: "ELEVATED" },
          },
          {
            event_id: "ev-03",
            call_id: primaryCall.callId,
            event_type: "SVI_UPDATED",
            timestamp: new Date().toISOString(),
            payload: { score: 52, band: primaryCall.sviBand },
          },
        ],
      }),
    });
  });

  // Safety endpoints
  await page.route("**/v1/safety/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "healthy", engine_version: "1.0.0", rules_loaded_count: 12 }),
    });
  });

  await page.route(`**/v1/safety/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        safety_state: primaryCall.safetyState,
        safety_signals: [
          {
            signal_id: "sig-op-01",
            rule_id: "RULE_DISTRESS_01",
            severity: "ELEVATED",
            description: "Elevated verbal distress cues detected",
            acknowledged: false,
            evidence: {
              reason: "Elevated verbal distress cues detected",
              temporal_context: "PRESENT",
              matched_phrase: "அச்சத்தில்",
            },
          },
        ],
      }),
    });
  });

  // SVI endpoints
  await page.route(`**/v1/svi/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        score: 52,
        band: primaryCall.sviBand,
        trend: "STABLE",
        delta: 2,
        assessment_completeness: 0.7,
        top_contributors: ["FEAR_DISCLOSURE"],
        protective_factor_reduction: 5,
        critical_override_applied: false,
        requires_human_review: false,
      }),
    });
  });

  // Acoustic endpoints
  await page.route(`**/v1/acoustic/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        quality: "GOOD",
        confidence: 0.94,
        voice_activity: { speech_activity_ratio: 0.6, silence_ratio: 0.4 },
        pause_metrics: { longest_pause_ms: 650, pause_count: 3 },
        interruption_metrics: { interruption_count: 0 },
        energy_metrics: { energy_variability: 0.22, mean_energy_rms: 380 },
        pitch_metrics: { median_f0_hz: 195 },
        operational_signals: [],
      }),
    });
  });

  // Adaptive endpoints
  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        action: "DEESCALATE_AND_GROUND",
        priority: "P2",
        target_information_gap: "immediate_safety",
        confidence: 0.91,
        reason_codes: ["ELEVATED_DISTRESS"],
        evidence_used: ["caller_fear_statement"],
        operator_override_applied: false,
        operator_override_reason: null,
      }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ strategies: [] }),
    });
  });

  // Operator snapshot & notes endpoints
  await page.route(`**/v1/operator/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        ownership_state: primaryCall.ownershipState,
        handoff_status: primaryCall.handoffStatus,
        adaptive_paused: primaryCall.adaptivePaused,
        active_operator_id: "operator_1",
      }),
    });
  });

  await page.route(`**/v1/operator/calls/${primaryCall.callId}/notes`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        notes: [
          {
            note_id: "note-001",
            call_id: primaryCall.callId,
            operator_id: "supervisor_1",
            category: "SAFETY",
            text: "Initial triage note: Caller expresses heightened anxiety.",
            timestamp: new Date().toISOString(),
            is_structured: true,
          },
        ],
      }),
    });
  });

  // Secondary call routes if present
  if (secondaryCall) {
    await page.route(`**/v1/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          caller_masked_number: secondaryCall.callerNumber,
          state: "STREAMING",
          conversation_state: "LISTENING",
          current_language: "hi-IN",
          safety_state: secondaryCall.safetyState,
          duration_seconds: 24,
          provider: "exotel",
          is_active: true,
        }),
      });
    });

    await page.route(`**/v1/calls/${secondaryCall.callId}/transcript`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          utterances: [
            {
              utterance_id: "utt-op-002",
              speaker: "caller",
              text: "मुझे तुरंत मदद चाहिए।",
              language: "hi-IN",
              safety_flag: true,
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    await page.route(`**/v1/calls/${secondaryCall.callId}/events`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          events: [],
        }),
      });
    });

    await page.route(`**/v1/safety/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          safety_state: secondaryCall.safetyState,
          safety_signals: [],
        }),
      });
    });

    await page.route(`**/v1/svi/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          score: 84,
          band: secondaryCall.sviBand,
          trend: "ESCALATING",
          delta: 12,
          assessment_completeness: 0.8,
          top_contributors: ["DIRECT_THREAT"],
          protective_factor_reduction: 0,
          critical_override_applied: true,
          requires_human_review: true,
        }),
      });
    });

    await page.route(`**/v1/acoustic/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          quality: "GOOD",
          confidence: 0.9,
          voice_activity: { speech_activity_ratio: 0.7, silence_ratio: 0.3 },
          pause_metrics: { longest_pause_ms: 400, pause_count: 1 },
          interruption_metrics: { interruption_count: 1 },
          energy_metrics: { energy_variability: 0.35, mean_energy_rms: 550 },
          pitch_metrics: { median_f0_hz: 230 },
          operational_signals: [],
        }),
      });
    });

    await page.route(`**/v1/adaptive/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action: "ROUTE_CRISIS_SUPPORT",
          priority: "P0",
          target_information_gap: "immediate_safety",
          confidence: 0.99,
          reason_codes: ["CRITICAL_SAFETY_THREAT"],
          evidence_used: ["threat_verbalized"],
          operator_override_applied: false,
          operator_override_reason: null,
        }),
      });
    });

    await page.route(`**/v1/adaptive/calls/${secondaryCall.callId}/history`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ strategies: [] }),
      });
    });

    await page.route(`**/v1/operator/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          ownership_state: secondaryCall.ownershipState,
          handoff_status: secondaryCall.handoffStatus,
          adaptive_paused: secondaryCall.adaptivePaused,
          active_operator_id: "operator_2",
        }),
      });
    });

    await page.route(`**/v1/operator/calls/${secondaryCall.callId}/notes`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ notes: [] }),
      });
    });
  }
}

test.describe("Phase 8 Human Operator Console & Tele-Counselor Workstation E2E", () => {
  test.beforeEach(async ({ page }) => {
    page.on("pageerror", (err) => console.log(">>> BROWSER EXCEPTION:", err.message, err.stack));
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.log(">>> BROWSER CONSOLE ERROR:", msg.text());
      }
    });
  });

  test("renders workstation layout, active call header, and ownership badge", async ({ page }) => {
    await setupWorkstationMocks(page);
    await page.goto("/calls");

    // 1. Root Workstation Container
    await expect(page.locator('[data-testid="operator-workstation"]')).toBeVisible();

    // 2. Active Call Header & Masked Phone
    await expect(page.locator('[data-testid="active-call-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="active-call-header"]')).toContainText("+91******3210");

    // 3. Ownership Badge (AI_ASSISTED default)
    const ownershipBadge = page.locator('[data-testid="ownership-badge"]');
    await expect(ownershipBadge).toBeVisible();
    await expect(ownershipBadge).toContainText("AI_ASSISTED");

    // 4. Simulation Mode Badge
    await expect(page.locator('[data-testid="simulation-mode-badge"]')).toBeVisible();
  });

  test("renders unified call triage summary with 5 operational dimensions and disclaimer", async ({ page }) => {
    await setupWorkstationMocks(page);
    await page.goto("/calls");

    // 1. Unified Triage Summary Container
    const summary = page.locator('[data-testid="unified-triage-summary"]');
    await expect(summary).toBeVisible();

    // 2. Safety State Dimension
    await expect(page.locator('[data-testid="safety-summary"]')).toContainText("ELEVATED");

    // 3. SVI Distress Dimension
    await expect(page.locator('[data-testid="svi-summary"]')).toContainText("52");
    await expect(page.locator('[data-testid="svi-summary"]')).toContainText("MODERATE");

    // 4. Acoustic Signal Dimension
    await expect(page.locator('[data-testid="acoustic-summary"]')).toContainText("GOOD");

    // 5. Adaptive Strategy Dimension
    await expect(page.locator('[data-testid="adaptive-summary"]')).toContainText("DEESCALATE_AND_GROUND");

    // 6. Human Authority Dimension
    await expect(page.locator('[data-testid="human-summary"]')).toContainText("AI_ASSISTED");

    // 7. Non-Clinical Disclaimer
    await expect(summary).toContainText("Strictly advisory & supervisory. Not a clinical diagnosis");
  });

  test("filters calls by queue filter pills in Master Call List", async ({ page }) => {
    await setupWorkstationMocks(
      page,
      {
        callId: "call-01",
        callerNumber: "+91******1111",
        ownershipState: "AI_ASSISTED",
        handoffStatus: "AVAILABLE",
        adaptivePaused: false,
        safetyState: "ELEVATED",
        sviBand: "MODERATE",
        notesCount: 0,
      },
      {
        callId: "call-02",
        callerNumber: "+91******2222",
        ownershipState: "HUMAN_ACTIVE",
        handoffStatus: "AVAILABLE",
        adaptivePaused: false,
        safetyState: "CRITICAL",
        sviBand: "CRITICAL",
        notesCount: 2,
      }
    );
    await page.goto("/calls");

    const callList = page.locator('[data-testid="call-list"]');
    await expect(callList).toBeVisible();

    // Initial ALL shows both
    await expect(callList).toContainText("+91******1111");
    await expect(callList).toContainText("+91******2222");

    // Click Critical filter -> only call-02 shown
    await page.getByRole("button", { name: "Critical", exact: true }).click();
    await expect(callList).toContainText("+91******2222");
    await expect(callList).not.toContainText("+91******1111");

    // Click Takeover filter -> only call-02 shown (HUMAN_ACTIVE)
    await page.getByRole("button", { name: "Takeover", exact: true }).click();
    await expect(callList).toContainText("+91******2222");
    await expect(callList).not.toContainText("+91******1111");

    // Click Elevated filter -> only call-01 shown
    await page.getByRole("button", { name: "Elevated", exact: true }).click();
    await expect(callList).toContainText("+91******1111");
    await expect(callList).not.toContainText("+91******2222");

    // Reset to All
    await page.getByRole("button", { name: "All", exact: true }).click();
    await expect(callList).toContainText("+91******1111");
    await expect(callList).toContainText("+91******2222");
  });

  test("executes operator takeover and updates ownership badge to HUMAN_ACTIVE", async ({ page }) => {
    await setupWorkstationMocks(page);

    // Mock takeover endpoint
    await page.route("**/v1/operator/calls/call-op-test-01/takeover", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-takeover-01",
          call_id: "call-op-test-01",
          action_type: "TAKEOVER",
          operator_id: "operator_1",
          reason: "Operator initiated human takeover",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.goto("/calls");

    // Initial state: Take Over button visible
    const takeoverBtn = page.locator('[data-testid="takeover-button"]');
    await expect(takeoverBtn).toBeVisible();

    // Click Take Over
    await takeoverBtn.click();

    // Ownership badge transitions to HUMAN_ACTIVE
    const ownershipBadge = page.locator('[data-testid="ownership-badge"]');
    await expect(ownershipBadge).toContainText("HUMAN_ACTIVE");

    // Alert banner informs operator of takeover
    await expect(page.locator('[data-testid="operator-alert-banner"]')).toContainText("Operator Takeover");
  });

  test("executes pause and resume adaptive AI controls", async ({ page }) => {
    await setupWorkstationMocks(page);

    await page.route("**/v1/operator/calls/call-op-test-01/pause", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-pause-01",
          call_id: "call-op-test-01",
          action_type: "PAUSE_ADAPTIVE",
          operator_id: "operator_1",
          reason: "Operator paused adaptive AI",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.route("**/v1/operator/calls/call-op-test-01/resume", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-resume-01",
          call_id: "call-op-test-01",
          action_type: "RESUME_ADAPTIVE",
          operator_id: "operator_1",
          reason: "Operator resumed adaptive AI",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.goto("/calls");

    // Click Pause Adaptive
    const pauseBtn = page.locator('[data-testid="pause-adaptive-button"]');
    await expect(pauseBtn).toBeVisible();
    await pauseBtn.click();

    // Verify AI Paused indicator and Resume button appear
    await expect(page.locator("text=AI Paused")).toBeVisible();
    const resumeBtn = page.locator('[data-testid="resume-adaptive-button"]');
    await expect(resumeBtn).toBeVisible();

    // Click Resume Adaptive
    await resumeBtn.click();
    await expect(page.locator('[data-testid="pause-adaptive-button"]')).toBeVisible();
  });

  test("manages handoff lifecycle: request -> confirm modal -> confirmed", async ({ page }) => {
    await setupWorkstationMocks(page);

    await page.route("**/v1/operator/calls/call-op-test-01/handoff", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-handoff-req-01",
          call_id: "call-op-test-01",
          action_type: "HANDOFF_REQUEST",
          operator_id: "operator_1",
          reason: "Operator requested handoff",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.route("**/v1/operator/calls/call-op-test-01/handoff/confirm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-handoff-conf-01",
          call_id: "call-op-test-01",
          action_type: "HANDOFF_CONFIRM",
          operator_id: "supervisor_01",
          reason: "Supervisor confirmed handoff",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.goto("/calls");

    // 1. Request Handoff
    const handoffBtn = page.locator('[data-testid="handoff-button"]');
    await expect(handoffBtn).toBeVisible();
    await handoffBtn.click();

    // Handoff Requested badge and action buttons appear
    await expect(page.locator("text=Handoff Requested")).toBeVisible();
    const confirmHandoffBtn = page.locator('[data-testid="handoff-confirm-button"]');
    const cancelHandoffBtn = page.locator('[data-testid="handoff-cancel-button"]');
    await expect(confirmHandoffBtn).toBeVisible();
    await expect(cancelHandoffBtn).toBeVisible();

    // 2. Click Confirm Handoff -> opens Confirmation Modal
    await confirmHandoffBtn.click();
    const modal = page.locator('[data-testid="confirmation-modal"]');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("Confirm Handoff");

    // 3. Confirm in modal
    await page.locator('[data-testid="confirm-action-button"]').click();
    await expect(modal).not.toBeVisible();

    // Handoff Confirmed badge appears
    await expect(page.locator("text=Handoff Confirmed")).toBeVisible();
  });

  test("adds structured operator note and verifies it displays in notes panel", async ({ page }) => {
    await setupWorkstationMocks(page);

    await page.route("**/v1/operator/calls/call-op-test-01/notes", async (route) => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            note_id: "note-new-002",
            call_id: "call-op-test-01",
            operator_id: body.operator_id || "operator_1",
            category: body.category || "SAFETY",
            text: body.text,
            timestamp: new Date().toISOString(),
            is_structured: true,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            notes: [
              {
                note_id: "note-001",
                call_id: "call-op-test-01",
                operator_id: "supervisor_1",
                category: "SAFETY",
                text: "Initial triage note: Caller expresses heightened anxiety.",
                timestamp: new Date().toISOString(),
                is_structured: true,
              },
            ],
          }),
        });
      }
    });

    await page.goto("/calls");

    // Open Notes Modal
    const addNoteBtn = page.locator('[data-testid="add-note-button"]');
    await expect(addNoteBtn).toBeVisible();
    await addNoteBtn.click();

    const notesModal = page.locator('[data-testid="operator-notes-panel"]');
    await expect(notesModal).toBeVisible();

    // Verify existing note
    await expect(notesModal).toContainText("Initial triage note: Caller expresses heightened anxiety.");

    // Fill new note
    await page.locator('[data-testid="note-category-select"]').selectOption("SAFETY");
    await page.locator('[data-testid="note-text-input"]').fill("Caller verified in secure room. Contacting district coordinator.");

    // Submit Note
    await page.locator('[data-testid="submit-note-button"]').click();

    // Verify new note appears in notes list
    await expect(notesModal).toContainText("Caller verified in secure room. Contacting district coordinator.");
  });

  test("confirms call termination through confirmation modal", async ({ page }) => {
    await setupWorkstationMocks(page);

    await page.route("**/v1/operator/calls/call-op-test-01/end", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          action_id: "act-end-01",
          call_id: "call-op-test-01",
          action_type: "END_CALL",
          operator_id: "operator_1",
          reason: "Operator concluded call from workstation",
          timestamp: new Date().toISOString(),
          status: "SUCCESS",
        }),
      });
    });

    await page.goto("/calls");

    // Click End Call
    await page.locator('[data-testid="end-call-button"]').click();

    // Verify Confirmation Modal
    const modal = page.locator('[data-testid="confirmation-modal"]');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("End Active Call");

    // Click Confirm
    await page.locator('[data-testid="confirm-action-button"]').click();
    await expect(modal).not.toBeVisible();

    // Ownership badge transitions to ENDED
    await expect(page.locator('[data-testid="ownership-badge"]')).toContainText("ENDED");
  });

  test("verifies event timeline filtering for OPERATOR, SAFETY, SVI categories", async ({ page }) => {
    await setupWorkstationMocks(page);
    await page.goto("/calls");

    const timeline = page.locator('[data-testid="event-timeline"]');
    await expect(timeline).toBeVisible();

    // Check filter pills presence
    await expect(page.getByRole("button", { name: "OPERATOR", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "SAFETY", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "SVI", exact: true })).toBeVisible();

    // Click OPERATOR filter -> only OPERATOR_STATE_CHANGED visible
    await page.getByRole("button", { name: "OPERATOR", exact: true }).click();
    await expect(timeline).toContainText("OPERATOR_STATE_CHANGED");
    await expect(timeline).not.toContainText("SAFETY_SIGNAL_TRIGGERED");

    // Click SAFETY filter -> only SAFETY_SIGNAL_TRIGGERED visible
    await page.getByRole("button", { name: "SAFETY", exact: true }).click();
    await expect(timeline).toContainText("SAFETY_SIGNAL_TRIGGERED");
    await expect(timeline).not.toContainText("OPERATOR_STATE_CHANGED");

    // Click SVI filter -> SVI_UPDATED visible
    await page.getByRole("button", { name: "SVI", exact: true }).click();
    await expect(timeline).toContainText("SVI_UPDATED");
  });

  test("maintains multi-call state isolation when switching calls", async ({ page }) => {
    await setupWorkstationMocks(
      page,
      {
        callId: "call-alpha",
        callerNumber: "+91******1111",
        ownershipState: "AI_ASSISTED",
        handoffStatus: "AVAILABLE",
        adaptivePaused: false,
        safetyState: "NONE",
        sviBand: "LOW",
        notesCount: 1,
      },
      {
        callId: "call-beta",
        callerNumber: "+91******2222",
        ownershipState: "HUMAN_ACTIVE",
        handoffStatus: "REQUESTED",
        adaptivePaused: true,
        safetyState: "CRITICAL",
        sviBand: "CRITICAL",
        notesCount: 0,
      }
    );

    await page.goto("/calls");

    // Call Alpha selected initially
    await expect(page.locator('[data-testid="active-call-header"]')).toContainText("+91******1111");
    await expect(page.locator('[data-testid="ownership-badge"]')).toContainText("AI_ASSISTED");

    // Switch to Call Beta
    const callBetaItem = page.locator('[data-testid="call-item"]').filter({ hasText: "+91******2222" });
    await callBetaItem.click();

    // Verify Call Beta state is completely isolated
    await expect(page.locator('[data-testid="active-call-header"]')).toContainText("+91******2222");
    await expect(page.locator('[data-testid="ownership-badge"]')).toContainText("HUMAN_ACTIVE");
    await expect(page.locator('[data-testid="safety-summary"]')).toContainText("CRITICAL");
    await expect(page.locator('[data-testid="svi-summary"]')).toContainText("CRITICAL");
  });
});
