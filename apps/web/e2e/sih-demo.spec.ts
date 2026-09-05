import { test, expect, Page } from "@playwright/test";

async function setupMockDemo(page: Page) {
  await page.route("**/ws/operator", (route) => route.abort());

  await page.route("**/v1/demo/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        demo_mode_enabled: true,
        environment: "development",
        app_mode: "DEV",
        flagship_scenario_id: "DEMO-SCENARIO-TAMIL-ENG-001",
        flagship_scenario_title:
          "Flagship SIH 2026: Tamil/English Code-Switching Acute Domestic Crisis & Rapid Warm Transfer",
        available_scenarios_count: 1,
        replays_conducted_count: 0,
        is_safe_to_reset: true,
      }),
    });
  });

  await page.route("**/v1/demo/flagship/replay", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        execution_id: "SIH-EXEC-8899AABB",
        scenario_id: "DEMO-SCENARIO-TAMIL-ENG-001",
        title: "Flagship SIH 2026: Tamil/English Code-Switching Acute Domestic Crisis & Rapid Warm Transfer",
        language: "ta-IN / en-IN (Code-Switching)",
        duration_total_ms: 182.4,
        svi_score: 88,
        svi_band: "CRITICAL",
        protocol_activated: "P0_EMERGENCY_DISPATCH_ASSIST",
        safety_triggers: ["IMMINENT_VIOLENCE", "WEAPON_INVOLVED", "DOMESTIC_DISTRESS", "CHILD_PRESENT"],
        warm_transfer_ready: true,
        warm_transfer_briefing:
          "1. Barricaded caller (Kavitha, Madurai) with 10-month-old infant in locked bedroom; active forced door entry.\n2. Perpetrator armed with edged weapon (knife); acute panic, acoustic distress score 0.94.\n3. Automated 112 dispatch advisory generated; human confirmation required before emergency vehicle dispatch.",
        rag_citations: [
          {
            statute: "Protection of Women from Domestic Violence Act (PWDVA), 2005",
            section: "Section 12 & 18",
            relevance: "Immediate ex-parte protection orders and residence preservation.",
          },
        ],
        case_entity_id: "CASE-2026-SIH-001",
        followup_window: "T+2 hours post-intervention",
        audit_event_hash: "a9f8b2c4e1d3570298a4bb11cc33ef928174aa9384729012384950ab9c02d184",
        stages: [
          {
            stage_number: 1,
            stage_name: "Multilingual Speech Ingestion & Code-Switching ASR",
            subsystem: "Sarvam / STT Engine",
            status: "SUCCESS",
            duration_ms: 41.2,
            description: "Ingested Tamil/English mixed acoustic stream; detected language pair ta-en.",
            payload: { detected_language: "ta-en" },
            verified_assertions: [
              "Bilingual token recognition active",
              "Acoustic tremor detected in caller voice (score 0.94)",
            ],
          },
          {
            stage_number: 2,
            stage_name: "Crisis Intent & Safety Screening",
            subsystem: "Safety Engine / Guardrails",
            status: "VERIFIED",
            duration_ms: 32.1,
            description: "Zero-latency safety screening flagged compound threat indicators.",
            payload: { imminent_danger: true },
            verified_assertions: ["Immediate escalation rule fired"],
          },
          {
            stage_number: 3,
            stage_name: "Statistical Vulnerability Index (SVI) Assessment",
            subsystem: "SVI Intelligence Engine",
            status: "VERIFIED",
            duration_ms: 35.8,
            description: "Calculated composite vulnerability score of 88/100 (Critical Band).",
            payload: { score: 88, band: "CRITICAL" },
            verified_assertions: ["Composite score = 88 (CRITICAL band >= 75)"],
          },
          {
            stage_number: 4,
            stage_name: "Adaptive Policy Selection",
            subsystem: "Adaptive Conversation Engine",
            status: "SUCCESS",
            duration_ms: 24.3,
            description: "Activated Emergency Protocol P0; configured non-provoking de-escalation tone.",
            payload: { active_protocol: "P0_EMERGENCY_DISPATCH_ASSIST" },
            verified_assertions: ["Policy shifted from standard intake to P0 Emergency"],
          },
          {
            stage_number: 5,
            stage_name: "Tele-Counselor Warm Transfer Synthesis",
            subsystem: "Operator Copilot Subsystem",
            status: "VERIFIED",
            duration_ms: 21.0,
            description: "Generated 3-point factual brief for crisis supervisor handoff.",
            payload: { ready_for_operator: true },
            verified_assertions: ["3-point bulleted briefing synthesized in < 50ms"],
          },
          {
            stage_number: 6,
            stage_name: "Statutory RAG Grounding & Local Referral",
            subsystem: "Knowledge Retrieval Engine",
            status: "SUCCESS",
            duration_ms: 45.1,
            description: "Retrieved statutory protections and Madurai district emergency facilities.",
            payload: { jurisdiction: "Tamil Nadu / Madurai Urban" },
            verified_assertions: ["PWDVA 2005 Section 12 citation retrieved"],
          },
          {
            stage_number: 7,
            stage_name: "Case Intelligence & Entity Graph Linkage",
            subsystem: "Case Intelligence Engine",
            status: "SUCCESS",
            duration_ms: 31.4,
            description: "Constructed incident knowledge graph for case CASE-2026-SIH-001.",
            payload: { case_id: "CASE-2026-SIH-001" },
            verified_assertions: ["Entity graph created with 4 nodes and 2 relational edges"],
          },
          {
            stage_number: 8,
            stage_name: "Cryptographic Audit Seal & Tamper Evident Log",
            subsystem: "Security & Governance Subsystem",
            status: "VERIFIED",
            duration_ms: 19.8,
            description: "Recorded immutable event in SHA-256 Merkle audit chain.",
            payload: { chain_valid: true },
            verified_assertions: ["SHA-256 cryptographic chaining verified"],
          },
        ],
      }),
    });
  });

  await page.route("**/v1/demo/reset", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "RESET_COMPLETE",
        message: "Demo environment reset successfully.",
        demo_mode_enabled: true,
      }),
    });
  });
}

test.describe("Phase 16: SIH 2026 Presentation Demo Hub", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockDemo(page);
    await page.goto("/demo");
    await page.waitForLoadState("networkidle");
  });

  test("renders SIH DEMO synthetic environment banner and scenario overview", async ({ page }) => {
    await expect(page.getByText("SIH DEMO / SYNTHETIC ENVIRONMENT")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Flagship Evaluation Scenario: Tamil\/English Code-Switching Crisis/i })
    ).toBeVisible();
    await expect(page.getByText("Target: SVI 88 (CRITICAL)")).toBeVisible();
    await expect(page.getByText("Turn 1")).toBeVisible();
    await expect(page.getByText("Turn 2")).toBeVisible();
    await expect(page.getByText("Turn 3")).toBeVisible();
  });

  test("triggers flagship scenario replay and displays full 8-stage execution trace", async ({ page }) => {
    const replayBtn = page.getByRole("button", { name: /Replay Flagship Scenario/i });
    await expect(replayBtn).toBeVisible();
    await replayBtn.click();

    // Check summary cards
    await expect(page.getByText("88 / 100")).toBeVisible();
    await expect(page.getByText("P0_EMERGENCY_DISPATCH_ASSIST")).toBeVisible();
    await expect(page.getByText("DISPATCH READY")).toBeVisible();

    // Check 8-stage timeline heading
    await expect(
      page.getByRole("heading", { name: /Multi-Stage Pipeline Execution Trace \(8 Stages\)/i })
    ).toBeVisible();

    // Check specific stages are rendered
    await expect(page.getByText("Multilingual Speech Ingestion & Code-Switching ASR")).toBeVisible();
    await expect(page.getByText("Crisis Intent & Safety Screening")).toBeVisible();
    await expect(page.getByText("Statistical Vulnerability Index (SVI) Assessment")).toBeVisible();
    await expect(page.getByText("Tele-Counselor Warm Transfer Synthesis")).toBeVisible();
    await expect(page.getByText("Cryptographic Audit Seal & Tamper Evident Log")).toBeVisible();

    // Check assertions checklist
    await expect(page.getByText("Bilingual token recognition active")).toBeVisible();
    await expect(page.getByText("Immediate escalation rule fired")).toBeVisible();
  });

  test("triggers safe demo reset", async ({ page }) => {
    const resetBtn = page.getByRole("button", { name: /Reset Environment/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    await expect(page.getByText(/Demo environment reset/i)).toBeVisible();
  });
});
