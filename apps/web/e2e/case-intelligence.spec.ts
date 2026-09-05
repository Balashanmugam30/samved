import { test, expect, Page } from "@playwright/test";

interface MockCallParams {
  callId: string;
  callerNumber: string;
}

async function setupMockCallWithCase(
  page: Page,
  primaryCall: MockCallParams = {
    callId: "call-case-test-01",
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
      duration_seconds: 90,
      provider: "exotel",
      is_active: true,
      safety_state: "SAFE",
      safety_signals_count: 0,
      svi_score: 42,
      svi_band: "ELEVATED",
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
        current_language: "en-IN",
        safety_state: "SAFE",
        duration_seconds: 90,
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
            utterance_id: "utt-case-001",
            speaker: "caller",
            text: "My name is Priya and my sister Ananya called me earlier.",
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
            event_id: "ev-case-01",
            session_id: primaryCall.callId,
            call_id: primaryCall.callId,
            event_type: "CASE_CREATED",
            timestamp: new Date().toISOString(),
            payload: {
              case_id: "case-1001",
              case_number: "CAS-2026-001001",
              status: "ACTIVE",
            },
          },
          {
            event_id: "ev-case-02",
            session_id: primaryCall.callId,
            call_id: primaryCall.callId,
            event_type: "CASE_ENTITY_CREATED",
            timestamp: new Date().toISOString(),
            payload: {
              case_id: "case-1001",
              entity_id: "ent-1001",
              label: "Priya",
            },
          },
        ],
      }),
    });
  });

  // Safety, SVI, Acoustic, Adaptive, Orchestration endpoints
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

  await page.route(`**/v1/svi/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, score: 42, band: "ELEVATED", trend: "STABLE" }),
    });
  });

  await page.route(`**/v1/acoustic/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, quality: "GOOD", confidence: 0.95, operational_signals: [] }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, action: "SUPPORTIVE_INQUIRY", priority: "P3" }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ strategies: [] }),
    });
  });

  await page.route(`**/v1/orchestration/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-c-01",
        call_id: primaryCall.callId,
        turn_id: "utt-case-001",
        state: "COMPLETED",
        selected_agents: ["case_graph_extraction_agent", "operator_briefing_agent"],
        completed_agents: ["case_graph_extraction_agent", "operator_briefing_agent"],
        failed_agents: [],
        timed_out_agents: [],
        cancelled_agents: [],
        total_latency_ms: 65,
        briefing: {
          safety_summary: "Caller reported family relocation and shelter inquiry.",
          svi_summary: "SVI 42 (ELEVATED tier).",
          acoustic_summary: "Acoustic audio features stable.",
          adaptive_recommendation: "Establish immediate caller safety.",
          key_facts: ["Priya reported sister Ananya"],
          evidence_refs: ["case:case-1001"],
          confidence: 0.95,
        },
      }),
    });
  });

  await page.route(`**/v1/operator/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        ownership_state: "AI_ASSISTED",
        handoff_status: "AVAILABLE",
        adaptive_paused: false,
      }),
    });
  });

  await page.route(`**/v1/operator/calls/${primaryCall.callId}/notes`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  // Mock Case endpoints
  const mockCaseRecord = {
    case_id: "case-1001",
    case_number: "CAS-2026-001001",
    status: "ACTIVE",
    primary_language: "en-IN",
    svi_score: 42,
    svi_band: "ELEVATED",
    safety_state: "SAFE",
    assigned_operator_id: "operator",
    consent_recorded: true,
    linked_calls: [primaryCall.callId],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const mockCaseGraph = {
    case_id: "case-1001",
    nodes: [
      {
        entity_id: "ent-1001",
        case_id: "case-1001",
        type: "PERSON",
        role: "CALLER",
        label: "Priya",
        claim_status: "REPORTED",
        confidence: 1.0,
        source_refs: [`call:${primaryCall.callId}:turn:1`],
        evidence: [
          {
            link_id: "lnk-1",
            source_type: "CALL_TRANSCRIPT",
            source_id: primaryCall.callId,
            turn_index: 1,
            verbatim_excerpt: "My name is Priya and I need guidance.",
            content_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            confidence: 1.0,
          },
        ],
      },
      {
        entity_id: "ent-1002",
        case_id: "case-1001",
        type: "PERSON",
        role: "SUPPORT_PERSON",
        label: "Ananya",
        claim_status: "REPORTED",
        confidence: 0.9,
        source_refs: [`call:${primaryCall.callId}:turn:2`],
        evidence: [
          {
            link_id: "lnk-2",
            source_type: "CALL_TRANSCRIPT",
            source_id: primaryCall.callId,
            turn_index: 2,
            verbatim_excerpt: "My sister Ananya called me earlier.",
            content_hash: "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
            confidence: 0.9,
          },
        ],
      },
      {
        entity_id: "ent-1003",
        case_id: "case-1001",
        type: "ORGANIZATION",
        label: "Delhi Safe Home",
        claim_status: "VERIFIED",
        confidence: 1.0,
        source_refs: ["org:delhi_safe_home"],
        evidence: [],
      },
      {
        entity_id: "ent-1004",
        case_id: "case-1001",
        type: "DOCUMENT",
        label: "SOP-14566-V3",
        claim_status: "VERIFIED",
        confidence: 1.0,
        source_refs: ["doc:central_policy_en"],
        evidence: [],
      },
    ],
    edges: [
      {
        edge_id: "edge-1001",
        case_id: "case-1001",
        source_entity: "ent-1001",
        relationship_type: "CONNECTED_TO",
        target_entity: "ent-1002",
        claim_status: "REPORTED",
        confidence: 0.95,
        valid_from: new Date().toISOString(),
        evidence: [
          {
            link_id: "lnk-edge-1",
            source_type: "CALL_TRANSCRIPT",
            source_id: primaryCall.callId,
            verbatim_excerpt: "My sister Ananya called me earlier.",
            content_hash: "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
            confidence: 0.95,
          },
        ],
      },
      {
        edge_id: "edge-1002",
        case_id: "case-1001",
        source_entity: "ent-1001",
        relationship_type: "LOCATED_AT",
        target_entity: "ent-1003",
        claim_status: "REPORTED",
        confidence: 0.85,
        valid_from: new Date().toISOString(),
        evidence: [],
      },
    ],
    candidates: [
      {
        candidate_id: "cand-1001",
        case_id: "case-1001",
        source_entity: "ent-1001",
        source_label: "Priya",
        relationship_type: "CONNECTED_TO",
        target_entity: "ent-1002",
        target_label: "Ananya",
        evidence_excerpt: "My sister Ananya called me earlier.",
        confidence: 0.88,
        status: "PENDING",
      },
    ],
    total_nodes: 4,
    total_edges: 2,
    statistics: { depth_applied: 2, as_of: "now" },
  };

  const mockCaseIntegrity = {
    valid: true,
    case_id: "case-1001",
    nodes_count: 4,
    edges_count: 2,
    candidates_count: 1,
    dangling_edges: [],
    temporal_anomalies: [],
    hash_mismatches: [],
    warnings: [],
    checked_at: new Date().toISOString(),
  };

  const mockAuditLogs = [
    {
      entry_id: "aud-001",
      case_id: "case-1001",
      action: "CASE_CREATED",
      actor_id: "system",
      details: { case_number: "CAS-2026-001001", call_id: primaryCall.callId },
      timestamp: new Date().toISOString(),
    },
    {
      entry_id: "aud-002",
      case_id: "case-1001",
      action: "CASE_ENTITY_CREATED",
      actor_id: "operator",
      details: { entity_id: "ent-1001", label: "Priya" },
      timestamp: new Date().toISOString(),
    },
  ];

  await page.route("**/v1/cases/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "READY",
        total_cases: 1,
        active_cases: 1,
        default_case_id: "case-1001",
        epistemic_mode: "EVIDENCE_LINKED_HUMAN_SUPERVISED",
        safety_boundary: "ZERO_CRIMINAL_DETERMINATION_NO_AUTONOMOUS_DISPATCH",
      }),
    });
  });

  await page.route("**/v1/cases/by-call/*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCaseRecord),
    });
  });

  await page.route("**/v1/cases/case-1001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCaseRecord),
    });
  });

  await page.route("**/v1/cases/case-1001/graph*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCaseGraph),
    });
  });

  await page.route("**/v1/cases/case-1001/integrity", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCaseIntegrity),
    });
  });

  await page.route("**/v1/cases/case-1001/audit*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockAuditLogs),
    });
  });

  await page.route("**/v1/cases/case-1001/candidates/*/confirm", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        edge_id: "edge-graduated-01",
        case_id: "case-1001",
        source_entity: "ent-1001",
        relationship_type: "CONNECTED_TO",
        target_entity: "ent-1002",
        claim_status: "REPORTED",
      }),
    });
  });

  await page.route("**/v1/cases/case-1001/candidates/*/reject", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        candidate_id: "cand-1001",
        status: "REJECTED",
      }),
    });
  });
}

test.describe("Phase 11 — Case Intelligence & Knowledge Graph E2E Suite", () => {
  test("TC-CASE-01: Case Intelligence Panel renders with header metadata and epistemic badges", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Verify Case Intelligence Panel is present
    const panel = page.locator('[data-testid="case-intelligence-panel"]');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Verify Case Number and status badges
    await expect(page.locator('[data-testid="case-number-badge"]')).toHaveText("CAS-2026-001001");
    await expect(page.locator('[data-testid="case-status-badge"]')).toHaveText("ACTIVE");
    await expect(page.locator('[data-testid="case-epistemic-mode"]')).toHaveText("HUMAN_SUPERVISED");
    await expect(page.locator('[data-testid="case-integrity-badge"]')).toContainText("INTEGRITY: VALID");
  });

  test("TC-CASE-02: Metrics summary strip displays correct entity, edge, and candidate counts", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    await expect(page.locator('[data-testid="case-entities-count"]')).toHaveText("4", { timeout: 10000 });
    await expect(page.locator('[data-testid="case-edges-count"]')).toHaveText("2");
    await expect(page.locator('[data-testid="case-candidates-count"]')).toHaveText("1");
  });

  test("TC-CASE-03: Graph Visualizer renders entity nodes and directed relationship edges", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    const visualizer = page.locator('[data-testid="case-graph-visualizer"]');
    await expect(visualizer).toBeVisible({ timeout: 10000 });

    // Verify entity nodes rendered
    const nodes = page.locator('[data-testid="case-graph-node"]');
    await expect(nodes).toHaveCount(4);

    // Verify Priya and Ananya labels
    await expect(nodes.filter({ hasText: "Priya" })).toBeVisible();
    await expect(nodes.filter({ hasText: "Ananya" })).toBeVisible();
    await expect(nodes.filter({ hasText: "Delhi Safe Home" })).toBeVisible();

    // Verify relationship edges
    const edges = page.locator('[data-testid="case-graph-edge"]');
    await expect(edges).toHaveCount(2);
    await expect(edges.filter({ hasText: "CONNECTED_TO" })).toBeVisible();
    await expect(edges.filter({ hasText: "LOCATED_AT" })).toBeVisible();
  });

  test("TC-CASE-04: Node Inspector opens and displays entity metadata, claim status, and SHA-256 evidence", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Click on Priya node
    await page.locator('[data-testid="case-graph-node"]').filter({ hasText: "Priya" }).click();

    // Inspector drawer should be visible
    const inspector = page.locator('[data-testid="case-inspector-drawer"]');
    await expect(inspector).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="case-node-inspector"]')).toBeVisible();

    // Check entity fields
    await expect(inspector).toContainText("ent-1001");
    await expect(inspector).toContainText("CALLER");
    await expect(inspector).toContainText("REPORTED");

    // Check SHA-256 evidence hash preview
    await expect(inspector).toContainText("SHA-256");

    // Close inspector
    await page.locator('[data-testid="close-inspector-btn"]').click();
    await expect(inspector).not.toBeVisible();
  });

  test("TC-CASE-05: Edge Inspector opens and displays directed relationship and temporal validity", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Click on CONNECTED_TO edge
    await page.locator('[data-testid="case-graph-edge"]').filter({ hasText: "CONNECTED_TO" }).click();

    const inspector = page.locator('[data-testid="case-inspector-drawer"]');
    await expect(inspector).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="case-edge-inspector"]')).toBeVisible();

    await expect(inspector).toContainText("edge-1001");
    await expect(inspector).toContainText("CONNECTED_TO");
  });

  test("TC-CASE-06: Counselor can confirm candidate relationship to graduate it into active edge", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Verify candidate section is visible
    const candidateSection = page.locator('[data-testid="candidate-confirmations-section"]');
    await expect(candidateSection).toBeVisible({ timeout: 10000 });

    const card = page.locator('[data-testid="candidate-card"]').first();
    await expect(card).toContainText("Priya");
    await expect(card).toContainText("Ananya");
    await expect(card).toContainText("My sister Ananya called me earlier");

    // Click Confirm button
    const confirmBtn = page.locator('[data-testid="confirm-candidate-btn"]').first();
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();
  });

  test("TC-CASE-07: Depth selector allows adjusting graph traversal hops", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    const depthSelect = page.locator('[data-testid="case-depth-select"]');
    await expect(depthSelect).toBeVisible({ timeout: 10000 });
    await depthSelect.selectOption("3");
    await expect(depthSelect).toHaveValue("3");
  });

  test("TC-CASE-08: Audit Trail modal displays immutable case mutation logs", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Click Audit Trail button
    const auditBtn = page.locator('[data-testid="view-case-audit-btn"]');
    await expect(auditBtn).toBeVisible({ timeout: 10000 });
    await auditBtn.click();

    // Modal should be visible
    const modal = page.locator('[data-testid="case-audit-modal"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal).toContainText("CASE_CREATED");
    await expect(modal).toContainText("CASE_ENTITY_CREATED");

    // Close modal
    await modal.locator("button").first().click();
    await expect(modal).not.toBeVisible();
  });

  test("TC-CASE-09: Timeline event stream supports CASE filter category", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    // Verify CASE filter button exists in timeline
    const caseFilterBtn = page.locator('[data-testid="timeline-filter-CASE"]');
    await expect(caseFilterBtn).toBeVisible({ timeout: 10000 });

    // Click CASE filter
    await caseFilterBtn.click();

    // Events stream should display CASE events
    const timelineItems = page.locator('[data-testid="timeline-event-item"]');
    await expect(timelineItems.first()).toContainText("CASE_CREATED");
  });

  test("TC-CASE-10: Epistemic safety disclaimer is displayed", async ({ page }) => {
    await setupMockCallWithCase(page);
    await page.goto("/calls");

    const disclaimer = page.locator('[data-testid="case-safety-disclaimer"]');
    await expect(disclaimer).toBeVisible({ timeout: 10000 });
    await expect(disclaimer).toContainText("No inferences of guilt or criminal determinations");
  });
});
