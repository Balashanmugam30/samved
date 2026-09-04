import { test, expect } from "@playwright/test";

test.describe("SAMVED Phase 3 Operator Console E2E", () => {
  test("renders operator console layout, tabs, and filters", async ({ page }) => {
    await page.goto("/calls");

    // 1. Verify header title & branding
    await expect(page.locator("text=SAMVED Operator Console")).toBeVisible();
    await expect(page.locator("text=Phase 3: Realtime Observation")).toBeVisible();

    // 2. Verify Mode pill
    await expect(page.locator("text=Mode:")).toBeVisible();

    // 3. Verify Master Call List tabs
    await expect(page.getByRole("button", { name: /^Active/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Recent/ })).toBeVisible();

    // 4. Verify Event timeline filter pills
    await expect(page.getByRole("button", { name: "ALL", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "TRANSCRIPT", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "CONVERSATION", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "ERRORS", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "LATENCY", exact: true })).toBeVisible();
  });

  test("opens simulation modal with scenarios and allows canceling", async ({ page }) => {
    await page.goto("/calls");

    // Click Launch Simulation button
    await page.getByRole("button", { name: "Launch Simulation", exact: true }).click();

    // Verify modal is visible
    await expect(page.locator("text=Launch Multi-turn Conversation Simulation")).toBeVisible();
    await expect(page.locator("text=Tamil Distress & Safety Verification")).toBeVisible();
    await expect(page.locator("text=Hindi Assistance & De-addiction Inquiry")).toBeVisible();
    await expect(page.locator("text=Indian English Support Request")).toBeVisible();
    await expect(page.locator("text=Code-Switching Resilience")).toBeVisible();
    await expect(page.locator("text=Barge-in / Caller Interruption Test")).toBeVisible();

    // Click Cancel
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.locator("text=Launch Multi-turn Conversation Simulation")).not.toBeVisible();
  });

  test("renders properly on responsive mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/calls");

    // Verify header title
    await expect(page.locator("text=SAMVED Operator Console")).toBeVisible();
    // Verify simulation button is present
    await expect(page.getByRole("button", { name: "Launch Simulation", exact: true })).toBeVisible();
  });
});
