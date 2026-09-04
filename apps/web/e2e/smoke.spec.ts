import { test, expect } from "@playwright/test";

test.describe("SAMVED Web Console Smoke Tests", () => {
  test("loads application shell and verifies identity and status panel", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/");

    // 1. Verify title & header branding
    await expect(page).toHaveTitle(/SAMVED/);
    const headerTitle = page.locator("header");
    await expect(headerTitle).toContainText("SAMVED");
    await expect(headerTitle).toContainText("14566");

    // 2. Verify DEV Mode badge is prominently displayed
    const devBadge = page.locator("text=DEV MODE (SAFE)");
    await expect(devBadge).toBeVisible();

    // 3. Verify Operational Status Panel presence
    const statusPanelTitle = page.locator("text=System Operational Status");
    await expect(statusPanelTitle).toBeVisible();
    await expect(page.getByText("FastAPI Backend", { exact: true })).toBeVisible();
    await expect(page.getByText("Realtime Gateway", { exact: true })).toBeVisible();
    await expect(page.getByText("Telephony Ingress", { exact: true })).toBeVisible();

    // 4. Verify no fatal error banner or uncaught exception
    const fatalErrors = consoleErrors.filter(
      (err) =>
        !err.includes("ERR_CONNECTION_REFUSED") &&
        !err.includes("Failed to load resource") &&
        !err.includes("WebSocket connection to")
    );
    expect(fatalErrors).toHaveLength(0);
  });

  test("navigates to telephony console and placeholder pages with phase indications", async ({ page }) => {
    await page.goto("/");

    // Navigate to Live Telephony
    await page.click("text=Live Telephony");
    await expect(page).toHaveURL(/.*\/calls/);
    await expect(page.locator("text=Phase 2 Multilingual AI Voice Conversation Console")).toBeVisible();
    await expect(page.locator("text=Multilingual Voice Pipeline Simulator")).toBeVisible();

    // Verify simulation trigger button is present
    const simButton = page.getByRole("button", { name: "Run Voice Simulation" });
    await expect(simButton).toBeVisible();

    // Navigate to Safety Alerts
    await page.click("text=Safety Alerts");
    await expect(page).toHaveURL(/.*\/alerts/);
    await expect(page.locator("text=Scheduled for Phase 4")).toBeVisible();

    // Navigate back to Overview
    await page.click("text=Overview & Status");
    await expect(page).toHaveURL("/");
  });

  test("renders properly on responsive mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Verify main brand
    await expect(page.locator("header")).toContainText("SAMVED");
    // Verify status section remains visible without horizontal breakage
    await expect(page.locator("text=System Operational Status")).toBeVisible();
  });
});
