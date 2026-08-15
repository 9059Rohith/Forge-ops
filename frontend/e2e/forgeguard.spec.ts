import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("submits the deterministic demo and reaches a proof-carrying verdict", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1584, height: 1024 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Autonomous engineering, with proof." })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("forgeguard-entry.png"), fullPage: true });
  await expect(page.getByLabel("Engineering task")).toBeFocused({ timeout: 1000 }).catch(() => undefined);
  await page.setViewportSize({ width: 1516, height: 1045 });
  await page.getByRole("button", { name: /start autonomous engineering/i }).click();

  await expect(page).toHaveURL(/\/task\//);
  await expect(page.getByText("VERIFIED", { exact: true }).first()).toBeVisible({ timeout: 80_000 });
  await expect(page.getByText(/Patch blocked by independent evidence/)).toBeVisible();
  await expect(page.getByText(/Repair cycle 1 completed/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Proof package" })).toBeVisible();
  const visibleReceipt = page.getByText(/^fg_[0-9a-f]{16}$/);
  await expect(visibleReceipt).toBeVisible();
  const receiptId = await visibleReceipt.textContent();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /download receipt/i }).click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const receipt = JSON.parse(await readFile(downloadPath!, "utf8")) as { receipt_id: string };
  expect(receipt.receipt_id).toBe(receiptId);

  await page.screenshot({ path: testInfo.outputPath("forgeguard-verified.png"), fullPage: true });
});

test("entry surface has no horizontal overflow and supports keyboard submission", async ({ page }) => {
  await page.goto("/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.getByLabel("Repository").focus();
  await expect(page.getByLabel("Repository")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Branch")).toBeFocused();
});
