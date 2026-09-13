import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonicalize(item)]),
    );
  }
  return value;
}

test("submits the deterministic demo and reaches a proof-carrying verdict", async ({ page }, testInfo) => {
  if (testInfo.project.name !== "mobile-chromium") {
    await page.setViewportSize({ width: 1584, height: 1024 });
  }
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Autonomous engineering, with proof." })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("forgeguard-entry.png"), fullPage: true });
  await page.getByLabel("Repository").fill("demo");
  await page.getByLabel("Engineering task").fill(
    "Add retry handling with exponential backoff to checkout. Do not change the public API.",
  );
  if (testInfo.project.name !== "mobile-chromium") {
    await page.setViewportSize({ width: 1516, height: 1045 });
  }
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
  const receipt = JSON.parse(await readFile(downloadPath!, "utf8")) as Record<string, unknown> & {
    receipt_id: string;
    integrity: { algorithm: string; digest: string };
  };
  expect(receipt.receipt_id).toBe(receiptId);
  const { receipt_id: _, integrity: __, ...evidence } = receipt;
  const digest = createHash("sha256").update(JSON.stringify(canonicalize(evidence))).digest("hex");
  expect(receipt.integrity).toEqual({ algorithm: "sha256", digest });
  expect(receipt.receipt_id).toBe(`fg_${digest.slice(0, 16)}`);

  if (testInfo.project.name === "mobile-chromium") {
    const graph = page.getByLabel("Live agent verification graph");
    const graphBox = await graph.boundingBox();
    const engineerBox = await graph.getByText("Engineer", { exact: true }).boundingBox();
    const adversarialBox = await graph.getByText("Adversarial", { exact: true }).boundingBox();
    expect(graphBox).not.toBeNull();
    expect(engineerBox).not.toBeNull();
    expect(adversarialBox).not.toBeNull();
    expect(engineerBox!.x).toBeGreaterThanOrEqual(graphBox!.x);
    expect(engineerBox!.x + engineerBox!.width).toBeLessThanOrEqual(
      graphBox!.x + graphBox!.width,
    );
    expect(adversarialBox!.x + adversarialBox!.width).toBeLessThanOrEqual(
      graphBox!.x + graphBox!.width,
    );
  }

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
