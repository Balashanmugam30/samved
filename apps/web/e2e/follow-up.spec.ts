import { test, expect, Page } from "@playwright/test";

interface MockCallParams {
  callId: string;
  callerNumber: string;
}

async function setupMockCallWithFollowups(
  page: Page,
  primaryCall: MockCallParams = {
    callId: "call-fol-test-01",
    callerNumber: "+91******1001",
  }
) {
  // Prevent background WebSocket from racing or disconnecting
  await page.route("**/ws/operator", (route) => route.abort());

  const activeCalls = [
    {
      call_id: primaryCall.callId,
      caller_masked_number: primaryCall.callerNumber,
      state: "STREAMING",
      conversation_state: "LISTENING",
      current_language: "en-IN",
      duration_seconds: 120,
      provider: "exotel",
      is_active: true,
      safety_state: "SAFE",
      safety_signals_count: 0,
      svi_score: 35,
      svi_band: "MODERATE",
      ownership_state: "AI_ASSISTED",
      notes_count: 0,
    },
  ];

  // Active calls list
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

  // Call detail
  await page.route(`**/v1/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        caller_masked_number: primaryCall.callerNumber,
        state: "STREAMING",
        conversation_state: "LISTENING",
        current_language: "en-IN",
        safety_state: "SAFE",
        duration_seconds: 120,
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
            utterance_id: "utt-fol-001",
            speaker: "caller",
            text: "Please check in with me tomorrow morning between 9 and 12.",
            language: "en-IN",
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
            event_id: "ev-fol-01",
            session_id: primaryCall.callId,
            call_id: primaryCall.callId,
            event_type: "FOLLOWUP_SCHEDULED",
            timestamp: new Date().toISOString(),
            payload: {
              followup_id: "fol-1001",
              case_id: "case-1001",
              status: "SCHEDULED",
              priority: "NORMAL",
            },
          },
          {
            event_id: "ev-fol-02",
            session_id: primaryCall.callId,
            call_id: primaryCall.callId,
            event_type: "FOLLOWUP_STARTED",
            timestamp: new Date().toISOString(),
            payload: {
              followup_id: "fol-1002",
              case_id: "case-1001",
              status: "IN_PROGRESS",
              priority: "HIGH",
            },
          },
        ],
      }),
    });
  });

  // Safety status
  await page.route("**/v1/safety/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "READY",
        engine_version: "2.0.0",
        total_rules: 15,
        rules: [],
      }),
    });
  });

  await page.route(`**/v1/safety/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, safety_state: "SAFE", safety_signals: [] }),
    });
  });

  // Case endpoints
  await page.route("**/v1/cases/case-1001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        case_id: "case-1001",
        case_number: "CAS-2026-001001",
        status: "ACTIVE",
        assigned_operator_id: "operator_1",
        primary_language: "en-IN",
        linked_calls: [primaryCall.callId],
      }),
    });
  });

  await page.route("**/v1/cases/case-1001/graph*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        case_id: "case-1001",
        nodes: [{ id: "case-1001", label: "CAS-2026-001001", type: "CASE" }],
        edges: [],
        total_nodes: 1,
        total_edges: 0,
      }),
    });
  });

  await page.route("**/v1/cases/case-1001/integrity", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ valid: true, issues: [] }),
    });
  });

  // Phase 12 Follow-up Mock Data
  const mockFollowups = [
    {
      followup_id: "fol-1001",
      case_id: "case-1001",
      call_id: primaryCall.callId,
      created_by: "operator_1",
      assigned_to: "operator_1",
      type: "CHECK_IN",
      status: "SCHEDULED",
      priority: "NORMAL",
      requested_at: "2026-03-31T10:00:00Z",
      scheduled_for: "2026-04-01T10:00:00Z",
      due_at: "2026-04-02T10:00:00Z",
      consent_state: "GRANTED",
      contact_preferences: {
        preferred_channel: "OPERATOR_CALLBACK",
        safe_to_contact: true,
        human_only: true,
        preferred_time_window: "09:00-12:00",
        no_voicemail: true,
        no_text: false,
      },
      safe_contact_window: "09:00-12:00",
      channel: "OPERATOR_CALLBACK",
      purpose: "Safety check-in regarding overnight shelter arrangement",
      attempt_count: 0,
      max_attempts: 3,
      policy_version: "2026.03.v1",
      created_at: "2026-03-31T10:00:00Z",
      updated_at: "2026-03-31T10:00:00Z",
      attempts: [],
    },
    {
      followup_id: "fol-1002",
      case_id: "case-1001",
      call_id: primaryCall.callId,
      created_by: "operator_1",
      assigned_to: "operator_1",
      type: "RESOURCE_FOLLOW_UP",
      status: "READY",
      priority: "HIGH",
      requested_at: "2026-03-31T09:00:00Z",
      scheduled_for: "2026-03-31T15:00:00Z",
      due_at: "2026-04-01T18:00:00Z",
      consent_state: "GRANTED",
      contact_preferences: {
        preferred_channel: "PHONE",
        safe_to_contact: true,
        human_only: true,
        preferred_time_window: "14:00-18:00",
        no_voicemail: true,
        no_text: false,
      },
      safe_contact_window: "14:00-18:00",
      channel: "PHONE",
      purpose: "Provide verified legal aid contact number for Protection Officer",
      attempt_count: 1,
      max_attempts: 3,
      policy_version: "2026.03.v1",
      created_at: "2026-03-31T09:00:00Z",
      updated_at: "2026-03-31T15:00:00Z",
      attempts: [
        {
          attempt_number: 1,
          attempted_at: "2026-03-31T15:10:00Z",
          operator_id: "operator_1",
          channel: "PHONE",
          result: "NO_ANSWER",
          notes: "Line rang with no answer; left no message per safe contact policy.",
        },
      ],
    },
    {
      followup_id: "fol-1003",
      case_id: "case-1001",
      call_id: primaryCall.callId,
      created_by: "operator_1",
      assigned_to: "operator_1",
      type: "OPERATOR_REVIEW",
      status: "IN_PROGRESS",
      priority: "CRITICAL_REVIEW",
      requested_at: "2026-03-31T08:00:00Z",
      scheduled_for: "2026-03-31T08:30:00Z",
      due_at: "2026-03-31T12:00:00Z",
      consent_state: "GRANTED",
      contact_preferences: {
        preferred_channel: "INTERNAL_TASK",
        safe_to_contact: true,
        human_only: true,
        no_voicemail: true,
        no_text: false,
      },
      safe_contact_window: "09:00-17:00",
      channel: "INTERNAL_TASK",
      purpose: "Supervisor review of high-risk acoustic distress cues",
      attempt_count: 0,
      max_attempts: 2,
      policy_version: "2026.03.v1",
      created_at: "2026-03-31T08:00:00Z",
      updated_at: "2026-03-31T08:30:00Z",
      attempts: [],
    },
  ];

  // Workqueue Summary
  await page.route("**/v1/followups/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total_active: 3,
        due_today: 2,
        overdue: 0,
        blocked: 0,
        completed_today: 0,
      }),
    });
  });

  // Followups list endpoints
  await page.route("**/v1/followups", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: mockFollowups,
          total: mockFollowups.length,
          page: 1,
          limit: 50,
        }),
      });
    }
  });

  await page.route("**/v1/cases/case-1001/followups", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: mockFollowups,
          total: mockFollowups.length,
          page: 1,
          limit: 50,
        }),
      });
    } else if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      const newFol = {
        followup_id: "fol-new-999",
        case_id: "case-1001",
        call_id: primaryCall.callId,
        created_by: body.created_by || "operator_1",
        type: body.type || "CHECK_IN",
        status: "SCHEDULED",
        priority: body.priority || "NORMAL",
        purpose: body.purpose,
        channel: body.channel || "OPERATOR_CALLBACK",
        scheduled_for: body.scheduled_for,
        due_at: body.due_at,
        safe_contact_window: body.safe_contact_window || "09:00-12:00",
        consent_state: body.consent_state || "GRANTED",
        contact_preferences: body.contact_preferences || {
          preferred_channel: "OPERATOR_CALLBACK",
          safe_to_contact: true,
          human_only: true,
          no_voicemail: true,
          no_text: false,
        },
        attempt_count: 0,
        max_attempts: body.max_attempts || 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(newFol),
      });
    }
  });

  // Action routes
  await page.route("**/v1/followups/*/start", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockFollowups[0],
        status: "IN_PROGRESS",
      }),
    });
  });

  await page.route("**/v1/followups/*/attempt", async (route) => {
    const postData = route.request().postDataJSON() || {};
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockFollowups[1],
        attempt_count: 2,
        attempts: [
          ...mockFollowups[1].attempts,
          {
            attempt_number: 2,
            attempted_at: new Date().toISOString(),
            operator_id: postData.operator_id || "operator_1",
            channel: postData.channel || "PHONE",
            result: postData.result || "CONTACTED_SUCCESSFULLY",
            notes: postData.notes || "Attempt recorded successfully",
          },
        ],
      }),
    });
  });

  await page.route("**/v1/followups/*/complete", async (route) => {
    const postData = route.request().postDataJSON() || {};
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockFollowups[2],
        status: "COMPLETED",
        outcome: postData.outcome || "CONTACTED_SUCCESSFULLY",
        completed_at: new Date().toISOString(),
      }),
    });
  });

  await page.route("**/v1/followups/*/reschedule", async (route) => {
    const postData = route.request().postDataJSON() || {};
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockFollowups[0],
        status: "SCHEDULED",
        scheduled_for: postData.new_scheduled_for || "2026-04-03T10:00:00Z",
      }),
    });
  });

  await page.route("**/v1/followups/*/cancel", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...mockFollowups[0],
        status: "CANCELLED",
        cancelled_at: new Date().toISOString(),
      }),
    });
  });

  await page.route("**/v1/cases/*/followups/revoke-consent", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        revoked_count: 3,
        status: "REVOKED",
        message: "Consent revoked for all active follow-ups under case",
      }),
    });
  });

  await page.route("**/v1/followups/*/audit*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            event_id: "aud-fol-001",
            action: "FOLLOWUP_CREATED",
            followup_id: "fol-1001",
            actor_id: "operator_1",
            timestamp: "2026-03-31T10:00:00Z",
            details: { type: "CHECK_IN", priority: "NORMAL", channel: "OPERATOR_CALLBACK" },
          },
          {
            event_id: "aud-fol-002",
            action: "FOLLOWUP_SCHEDULED",
            followup_id: "fol-1001",
            actor_id: "scheduler",
            timestamp: "2026-03-31T10:00:05Z",
            details: { scheduled_for: "2026-04-01T10:00:00Z", safe_contact_window: "09:00-12:00" },
          },
          {
            event_id: "aud-fol-003",
            action: "FOLLOWUP_ATTEMPTED",
            followup_id: "fol-1002",
            actor_id: "operator_1",
            timestamp: "2026-03-31T15:10:00Z",
            details: { attempt_number: 1, result: "NO_ANSWER" },
          },
        ],
        total: 3,
      }),
    });
  });
}

test.describe("SAMVED Phase 12: Follow-up Workflow & Continuity Engine E2E", () => {
  test("TC-FOL-01: Workqueue Panel renders with KPI metrics strip and governance badges", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    // Panel presence
    const panel = page.locator('[data-testid="followup-workqueue-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Governance badges
    await expect(page.locator('[data-testid="followup-supervised-badge"]')).toHaveText("HUMAN_SUPERVISED");
    await expect(page.locator('[data-testid="followup-consent-guarded-badge"]')).toHaveText("CONSENT_GUARDED");

    // KPI Metrics strip
    await expect(page.locator('[data-testid="workqueue-stat-active"]')).toContainText("3");
    await expect(page.locator('[data-testid="workqueue-stat-due"]')).toContainText("2");
    await expect(page.locator('[data-testid="workqueue-stat-overdue"]')).toContainText("0");
    await expect(page.locator('[data-testid="workqueue-stat-blocked"]')).toContainText("0");
    await expect(page.locator('[data-testid="workqueue-stat-completed"]')).toContainText("0");
  });

  test("TC-FOL-02: Follow-up task cards render with correct attributes and safe contact windows", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const fol1001 = page.locator('[data-testid="followup-card-fol-1001"]');
    await expect(fol1001).toBeVisible({ timeout: 10000 });
    await expect(fol1001.locator('[data-testid="followup-id"]')).toHaveText("fol-1001");
    await expect(fol1001.locator('[data-testid="followup-type-badge"]')).toHaveText("CHECK_IN");
    await expect(fol1001.locator('[data-testid="followup-status-badge"]')).toHaveText("SCHEDULED");
    await expect(fol1001.locator('[data-testid="followup-priority-badge"]')).toHaveText("NORMAL");
    await expect(fol1001.locator('[data-testid="followup-consent-badge"]')).toContainText("GRANTED");
    await expect(fol1001.locator('[data-testid="followup-channel-badge"]')).toHaveText("OPERATOR_CALLBACK");
    await expect(fol1001.locator('[data-testid="followup-safe-window"]')).toHaveText("09:00-12:00");
    await expect(fol1001.locator('[data-testid="followup-purpose"]')).toContainText("Safety check-in");

    const fol1002 = page.locator('[data-testid="followup-card-fol-1002"]');
    await expect(fol1002).toBeVisible();
    await expect(fol1002.locator('[data-testid="followup-status-badge"]')).toHaveText("READY");
    await expect(fol1002.locator('[data-testid="followup-safe-window"]')).toHaveText("14:00-18:00");
  });

  test("TC-FOL-03: Workqueue filter pills filter tasks by lifecycle status", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    // Click SCHEDULED filter
    await page.locator('[data-testid="followup-filter-scheduled"]').click();
    await expect(page.locator('[data-testid="followup-card-fol-1001"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="followup-card-fol-1002"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="followup-card-fol-1003"]')).not.toBeVisible();

    // Click READY filter
    await page.locator('[data-testid="followup-filter-ready"]').click();
    await expect(page.locator('[data-testid="followup-card-fol-1002"]')).toBeVisible();
    await expect(page.locator('[data-testid="followup-card-fol-1001"]')).not.toBeVisible();

    // Click IN_PROGRESS filter
    await page.locator('[data-testid="followup-filter-inprogress"]').click();
    await expect(page.locator('[data-testid="followup-card-fol-1003"]')).toBeVisible();
    await expect(page.locator('[data-testid="followup-card-fol-1001"]')).not.toBeVisible();

    // Click All Tasks filter
    await page.locator('[data-testid="followup-filter-all"]').click();
    await expect(page.locator('[data-testid="followup-card-fol-1001"]')).toBeVisible();
    await expect(page.locator('[data-testid="followup-card-fol-1002"]')).toBeVisible();
    await expect(page.locator('[data-testid="followup-card-fol-1003"]')).toBeVisible();
  });

  test("TC-FOL-04: Tele-counselor can schedule new follow-up via Create Follow-up Modal", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    // Open Modal
    const createBtn = page.locator('[data-testid="create-followup-btn"]');
    await expect(createBtn).toBeVisible({ timeout: 10000 });
    await createBtn.click();

    // Modal should be visible
    const modal = page.locator('[data-testid="create-followup-modal"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Fill form
    await page.locator('[data-testid="create-followup-type-select"]').selectOption("RESOURCE_FOLLOW_UP");
    await page.locator('[data-testid="create-followup-priority-select"]').selectOption("HIGH");
    await page.locator('[data-testid="create-followup-purpose-input"]').fill("Check victim shelter admittance with PO");
    await page.locator('[data-testid="create-followup-channel-select"]').selectOption("OPERATOR_CALLBACK");
    await page.locator('[data-testid="create-followup-scheduled-input"]').fill("2026-04-02T10:00:00Z");
    await page.locator('[data-testid="create-followup-due-input"]').fill("2026-04-03T10:00:00Z");
    await page.locator('[data-testid="create-followup-safewindow-input"]').fill("10:00-13:00");
    await page.locator('[data-testid="create-followup-notes-input"]').fill("Follow up specifically with counselor Meera.");

    // Submit
    await page.locator('[data-testid="submit-create-followup-btn"]').click();

    // Modal closes
    await expect(modal).not.toBeVisible({ timeout: 10000 });
  });

  test("TC-FOL-05: Counselor can transition task to IN_PROGRESS via Start Task", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const fol1001 = page.locator('[data-testid="followup-card-fol-1001"]');
    await expect(fol1001).toBeVisible({ timeout: 10000 });

    const startBtn = fol1001.locator('[data-testid="start-followup-btn"]');
    await expect(startBtn).toBeVisible();
    await startBtn.click();
  });

  test("TC-FOL-06: Counselor can record contact attempt with notes and result", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    // Open details for fol-1002
    const fol1002 = page.locator('[data-testid="followup-card-fol-1002"]');
    await expect(fol1002).toBeVisible({ timeout: 10000 });
    await fol1002.locator('[data-testid="view-followup-details-btn"]').click();

    const drawer = page.locator('[data-testid="followup-details-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 10000 });

    // Verify existing attempt history
    const attemptsList = drawer.locator('[data-testid="followup-attempts-list"]');
    await expect(attemptsList).toContainText("Attempt #1");
    await expect(attemptsList).toContainText("NO_ANSWER");

    // Fill attempt form
    await drawer.locator('[data-testid="attempt-result-select"]').selectOption("CONTACTED_SUCCESSFULLY");
    await drawer.locator('[data-testid="attempt-notes-input"]').fill("Spoke with caller, confirmed safe.");
    await drawer.locator('[data-testid="submit-attempt-btn"]').click();

    // Close drawer
    await drawer.locator('[data-testid="close-followup-details-btn"]').click();
    await expect(drawer).not.toBeVisible();
  });

  test("TC-FOL-07: Counselor can reschedule follow-up with reason", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const fol1001 = page.locator('[data-testid="followup-card-fol-1001"]');
    await expect(fol1001).toBeVisible({ timeout: 10000 });
    await fol1001.locator('[data-testid="reschedule-followup-btn"]').click();

    const drawer = page.locator('[data-testid="followup-details-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 10000 });

    await drawer.locator('[data-testid="reschedule-time-input"]').fill("2026-04-03T10:00:00Z");
    await drawer.locator('[data-testid="reschedule-reason-input"]').fill("Caller requested morning callback Friday.");
    await drawer.locator('[data-testid="submit-reschedule-btn"]').click();
  });

  test("TC-FOL-08: Counselor can mark follow-up completed with clinical outcome", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const fol1003 = page.locator('[data-testid="followup-card-fol-1003"]');
    await expect(fol1003).toBeVisible({ timeout: 10000 });

    const completeBtn = fol1003.locator('[data-testid="complete-followup-btn"]');
    await expect(completeBtn).toBeVisible();
    await completeBtn.click();
  });

  test("TC-FOL-09: Caller consent revocation halts and blocks contact workflow", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const fol1001 = page.locator('[data-testid="followup-card-fol-1001"]');
    await expect(fol1001).toBeVisible({ timeout: 10000 });

    const revokeBtn = fol1001.locator('[data-testid="revoke-consent-btn"]');
    await expect(revokeBtn).toBeVisible();
    await revokeBtn.click();
  });

  test("TC-FOL-10: Audit trail modal displays append-only immutable event logs", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    // Click Audit Trail button in Workqueue header
    const auditBtn = page.locator('[data-testid="view-all-followup-audit-btn"]');
    await expect(auditBtn).toBeVisible({ timeout: 10000 });
    await auditBtn.click();

    // Modal should be visible
    const modal = page.locator('[data-testid="followup-audit-modal"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify entries
    const logList = page.locator('[data-testid="followup-audit-log-list"]');
    await expect(logList).toContainText("FOLLOWUP_CREATED");
    await expect(logList).toContainText("FOLLOWUP_SCHEDULED");
    await expect(logList).toContainText("FOLLOWUP_ATTEMPTED");
    await expect(logList).toContainText("operator_1");

    // Close modal
    await page.locator('[data-testid="close-followup-audit-modal-btn"]').click();
    await expect(modal).not.toBeVisible();
  });

  test("TC-FOL-11: Case Intelligence panel displays linked follow-ups badge", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const caseBadge = page.locator('[data-testid="case-followup-count"]');
    await expect(caseBadge).toBeVisible({ timeout: 10000 });
    await expect(caseBadge).toContainText("Active");
  });

  test("TC-FOL-12: Event stream timeline supports FOLLOWUP filter category", async ({ page }) => {
    await setupMockCallWithFollowups(page);
    await page.goto("/calls");

    const followupFilterBtn = page.locator('[data-testid="timeline-filter-FOLLOWUP"]');
    await expect(followupFilterBtn).toBeVisible({ timeout: 10000 });
    await followupFilterBtn.click();

    const timelineItems = page.locator('[data-testid="timeline-event-item"]');
    await expect(timelineItems.first()).toContainText("FOLLOWUP_");
  });
});
