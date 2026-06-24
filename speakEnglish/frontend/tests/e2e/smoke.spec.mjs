import { test, expect, openApp } from './fixtures.mjs';

test.describe('Smoke — Chrome & Edge', () => {
  test('loads app and first word', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#word-index')).toHaveText(/\d+ \/ \d+/);
    await expect(page.locator('#quiz-info')).toContainText(/từ/);
    await expect(page.locator('#mode-text')).toHaveClass(/active/);
    await expect(page.locator('#live-transcript-placeholder')).toBeVisible();
  });

  test('switches to score mode tab', async ({ page }) => {
    await openApp(page, { practiceMode: 'text' });
    await page.locator('#mode-score').click();
    await expect(page.locator('#mode-score')).toHaveClass(/active/);
    await expect(page.locator('#mode-text')).not.toHaveClass(/active/);
    await expect(page.locator('#phoneme-container')).toBeVisible();
  });

  test('settings panel opens', async ({ page }) => {
    await openApp(page);
    await page.locator('#btn-settings').click();
    await expect(page.locator('#settings-panel')).not.toHaveClass(/hidden/);
    await expect(page.locator('#setting-topic option')).not.toHaveCount(0);
    await page.locator('#btn-close-settings').click();
    await expect(page.locator('#settings-panel')).toHaveClass(/hidden/);
  });
});
