import { test, expect, openApp, BACKEND_URL } from './fixtures.mjs';

test.describe('Chế độ Chỉ text', () => {
  test.beforeEach(async ({ page }) => {
    await openApp(page, { practiceMode: 'text' });
  });

  test('shows text mode status without backend', async ({ page }) => {
    await expect(page.locator('#service-status')).toContainText(/Chế độ text|không cần backend/i);
    await expect(page.locator('#service-status')).toHaveClass(/status-online/);
  });

  test('live toggle starts mic (fake device)', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await page.locator('#btn-live-toggle').click();
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/, {
      timeout: 15000,
    });
    await expect(page.locator('#mic-status-label')).toContainText(/Sẵn sàng|đang nghe/i);
  });

  test('placeholder describes auto-advance', async ({ page }) => {
    await expect(page.locator('#live-transcript-placeholder')).toContainText(/chuyển tiếp/i);
  });
});
