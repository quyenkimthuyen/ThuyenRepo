import { expect, test } from "@playwright/test";

test("learner can move through the core pronunciation loop", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /pronounce new english words/i })).toBeVisible();

  await page.getByRole("link", { name: /start with school/i }).click();
  await expect(page.getByRole("heading", { name: "school" })).toBeVisible();
  await expect(page.getByText("/skuːl/")).toBeVisible();
  await expect(page.getByText("skuul").first()).toBeVisible();
  await expect(page.getByText("Result: skuul")).toBeVisible();

  await page.goto("/game");
  await page.getByRole("button", { name: "skuul" }).click();
  await expect(page.getByText(/\+10 XP/i)).toBeVisible();
});
