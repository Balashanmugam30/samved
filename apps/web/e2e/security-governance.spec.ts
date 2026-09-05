import { test, expect, Page } from "@playwright/test";

async function setupMockSecurity(page: Page) {
  // Prevent websocket disconnect flakiness
  await page.route("**/ws/operator", (route) => route.abort());

  // Security status mock
  await page.route("**/v1/security/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        overall_posture: "HEALTHY",
        prototype_notice: "SAMVED Phase 15 prototype security hardening.",
        controls_count: 11,
        controls_operational: 11,
        audit_chain: {
          is_valid: true,
          message: "Cryptographic audit chain verified across all 4 entries.",
          total_records: 4,
        },
        retention_policies_count: 5,
        last_evaluated_at: new Date().toISOString(),
        caller_context: {
          user_id: "usr-supervisor-01",
          role: "SUPERVISOR",
          district: "KOLKATA",
        },
      }),
    });
  });

  // Controls mock
  await page.route("**/v1/security/controls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          control_id: "CTRL-AUTH-001",
          name: "Identity & Context Verification",
          category: "AUTHENTICATION",
          status: "OPERATIONAL",
          description: "Verifies user identity headers, session tokens, and district context.",
          last_verified_at: new Date().toISOString(),
          metrics: { active_identities_tracked: 5 },
        },
        {
          control_id: "CTRL-DATA-001",
          name: "Indian Entity PII Redaction Pipeline",
          category: "DATA_PROTECTION",
          status: "OPERATIONAL",
          description: "High-accuracy regex + heuristic masking for Aadhaar, PAN, Indian phone numbers, emails, and bank accounts.",
          last_verified_at: new Date().toISOString(),
          metrics: { entity_types_covered: ["AADHAAR", "PAN", "PHONE", "EMAIL"] },
        },
        {
          control_id: "CTRL-AUDT-001",
          name: "Cryptographically Chained Audit Trail",
          category: "AUDITABILITY",
          status: "OPERATIONAL",
          description: "Append-only log chained with SHA-256 cryptographic hashes for tamper evidence.",
          last_verified_at: new Date().toISOString(),
          metrics: { total_entries: 4, chain_valid: true },
        },
      ]),
    });
  });

  // PII Redact mock
  await page.route("**/v1/security/pii/redact", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        scrubbed_text: "Caller Mrs. Sharma called from [REDACTED_PHONE:+91-XXXXX-3210] stating her Aadhaar card [REDACTED_AADHAAR:XXXX-XXXX-0123] was retained by in-laws.",
        redactions_count: 2,
        redaction_types: ["PHONE", "AADHAAR"],
        has_pii: true,
      }),
    });
  });

  // Audit verify mock
  await page.route("**/v1/security/audit/verify", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        chain_valid: true,
        verification_message: "Cryptographic SHA-256 audit chain verified across all 4 entries. No tampering detected.",
        entries_verified: 4,
        hash_algorithm: "SHA-256",
        verified_by: "usr-supervisor-01",
      }),
    });
  });
}

test.describe("Security, Privacy & Governance Console (Phase 15)", () => {
  test("loads /security dashboard and verifies posture cards and controls", async ({ page }) => {
    await setupMockSecurity(page);
    await page.goto("/security");

    // Header & Posture
    await expect(page.getByRole("heading", { name: "Security & Governance Console" })).toBeVisible();
    await expect(page.getByText("Phase 15 Security, Privacy & Governance")).toBeVisible();
    await expect(page.getByText("HEALTHY")).toBeVisible();
    await expect(page.getByText("SHA-256 VALID")).toBeVisible();

    // Controls Inventory Tab
    await expect(page.getByText("Identity & Context Verification")).toBeVisible();
    await expect(page.getByText("CTRL-AUTH-001")).toBeVisible();
    await expect(page.getByText("CTRL-DATA-001")).toBeVisible();
  });

  test("interacts with role switcher to change active persona", async ({ page }) => {
    await setupMockSecurity(page);
    await page.goto("/security");

    // Click on DISTRICT_ADMIN
    const daBtn = page.getByRole("button", { name: "DISTRICT_ADMIN" });
    await expect(daBtn).toBeVisible();
    await daBtn.click();
    await expect(daBtn).toHaveClass(/bg-blue-600/);

    // Switch to AUDITOR
    const auditorBtn = page.getByRole("button", { name: "AUDITOR" });
    await auditorBtn.click();
    await expect(auditorBtn).toHaveClass(/bg-blue-600/);
  });

  test("runs Indian PII redaction lab with live scrubbing", async ({ page }) => {
    await setupMockSecurity(page);
    await page.goto("/security");

    // Switch to PII Lab tab
    await page.getByRole("button", { name: "Indian PII Redaction Lab" }).click();
    await expect(page.getByText("Interactive Indian PII Redaction Pipeline")).toBeVisible();

    // Click execute button
    const scrubBtn = page.getByRole("button", { name: "Execute Indian PII Redaction" });
    await expect(scrubBtn).toBeVisible();
    await scrubBtn.click();

    // Verify redacted text appears
    await expect(page.getByText(/REDACTED_AADHAAR/)).toBeVisible();
    await expect(page.getByText("2 Entities Masked")).toBeVisible();
    await expect(page.getByText("AADHAAR", { exact: true })).toBeVisible();
  });

  test("inspects RBAC and IDOR matrix tab", async ({ page }) => {
    await setupMockSecurity(page);
    await page.goto("/security");

    await page.getByRole("button", { name: "RBAC & IDOR Matrix" }).click();
    await expect(page.getByText("Role Permissions Matrix")).toBeVisible();
    await expect(page.getByText("Insecure Direct Object Reference (IDOR) & District Quarantine")).toBeVisible();
  });

  test("navigates to /audit explorer and verifies cryptographic chain", async ({ page }) => {
    await setupMockSecurity(page);
    await page.goto("/audit");

    await expect(page.getByRole("heading", { name: "Governance Audit Explorer" })).toBeVisible();
    await expect(page.getByText("Phase 15 Cryptographic Audit Trail")).toBeVisible();

    // Verify audit log entries exist
    await expect(page.getByText("CALL_INTAKE_CONNECTED")).toBeVisible();

    // Verify Chain button
    const verifyBtn = page.getByRole("button", { name: "Verify SHA-256 Chain" });
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // Check verification banner
    await expect(page.getByText("Cryptographic Hash Chain: VERIFIED INTEGRITY")).toBeVisible();

    // Expand entry row to see details payload
    await page.getByText("CALL_INTAKE_CONNECTED").click();
    await expect(page.getByText("Prev Hash:")).toBeVisible();
    await expect(page.getByText("Entry Hash:")).toBeVisible();
  });
});
