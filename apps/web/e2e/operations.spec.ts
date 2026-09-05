import { test, expect, Page } from "@playwright/test";

async function setupMockOperations(page: Page) {
  await page.route("**/ws/operator", (route) => route.abort());

  await page.route("**/v1/operations/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        service: "samved-api",
        version: "1.0.0-sih2026",
        environment: "development",
        mode: "DEV",
        uptime_seconds: 7200,
        uptime_formatted: "2h 0m 0s",
        telephony: { active_calls: 0, provider: "MockTelephony" },
        realtime_websockets: { connected_operators: 1, gateway_status: "OPERATIONAL" },
        security_governance: { posture: "HEALTHY", active_controls: 11, audit_chain_valid: true },
        circuit_breakers: [
          {
            name: "sarvam-stt",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 5,
            last_failure_time: 0,
            recovery_timeout_seconds: 30,
          },
          {
            name: "sarvam-tts",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 5,
            last_failure_time: 0,
            recovery_timeout_seconds: 30,
          },
          {
            name: "gemini-llm",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 5,
            last_failure_time: 0,
            recovery_timeout_seconds: 30,
          },
          {
            name: "exotel-telephony",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 5,
            last_failure_time: 0,
            recovery_timeout_seconds: 30,
          },
          {
            name: "database",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 3,
            last_failure_time: 0,
            recovery_timeout_seconds: 15,
          },
          {
            name: "redis",
            state: "CLOSED",
            failure_count: 0,
            failure_threshold: 3,
            last_failure_time: 0,
            recovery_timeout_seconds: 15,
          },
        ],
        timestamp: new Date().toISOString(),
      }),
    });
  });

  await page.route("**/v1/operations/circuits/*/reset", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ message: "Circuit reset to CLOSED" }),
    });
  });

  await page.route("**/v1/operations/circuits/reset-all", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ message: "All circuits reset to operational CLOSED state." }),
    });
  });
}

test.describe("Phase 16: Operations & Reliability Console", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockOperations(page);
    await page.goto("/operations");
    await page.waitForLoadState("networkidle");
  });

  test("renders console header with Phase 16 badge and core telemetry KPIs", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Operational Reliability & Observability Console/i })).toBeVisible();
    await expect(page.getByText("Phase 16 SIH Final")).toBeVisible();

    // Check KPI cards
    await expect(page.getByText("Service & Runtime")).toBeVisible();
    await expect(page.getByText("Telephony Subsystem")).toBeVisible();
    await expect(page.getByText("Operator Gateway")).toBeVisible();
    await expect(page.getByText("Governance & Cryptography")).toBeVisible();
  });

  test("displays all registered circuit breakers with CLOSED state badges", async ({ page }) => {
    await expect(page.getByText("Circuit Breakers & Provider Fault Isolation")).toBeVisible();
    await expect(page.getByText("sarvam-stt")).toBeVisible();
    await expect(page.getByText("gemini-llm")).toBeVisible();
    await expect(page.getByText("exotel-telephony")).toBeVisible();
  });

  test("triggers reset all circuit breakers with confirmation banner", async ({ page }) => {
    const resetBtn = page.getByRole("button", { name: /Reset All Circuit Breakers/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    await expect(
      page.getByText(/All circuit breakers restored to operational CLOSED state/i)
    ).toBeVisible();
  });

  test("renders Kubernetes probes and degradation architecture sections", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Kubernetes & Orchestration Probes/i })).toBeVisible();
    await expect(page.getByText("GET /healthz & /health/live")).toBeVisible();
    await expect(page.getByText("GET /ready & /health/ready")).toBeVisible();
    await expect(page.getByText("GET /health/startup")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Graceful Degradation Architecture/i })).toBeVisible();
  });
});
