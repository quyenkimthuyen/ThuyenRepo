import { expect, test } from "@playwright/test";

test("learner can move through the core pronunciation loop", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /nhìn từ tiếng anh/i })).toBeVisible();

  await page.getByRole("link", { name: /bắt đầu học 1 từ/i }).click();
  await expect(page.getByRole("heading", { name: "see" })).toBeVisible();
  await expect(page.getByText("/siː/")).toBeVisible();
  await expect(page.getByText("sii").first()).toBeVisible();
  await expect(page.getByText("Result: sii")).toBeVisible();

  await page.goto("/game");
  await page.getByRole("button", { name: "skuul" }).click();
  await expect(page.getByText(/\+10 XP/i)).toBeVisible();
});
