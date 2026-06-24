import { test, expect, openApp, BACKEND_URL } from './fixtures.mjs';

test.describe('Chế độ Chấm điểm + backend', () => {
  test.beforeEach(async ({ page }) => {
    await openApp(page, {
      practiceMode: 'score',
      apiBaseUrl: BACKEND_URL,
      autoEvaluate: true,
    });
    await page.locator('#mode-score').click();
  });

  test('footer shows backend online', async ({ page }) => {
    await expect(page.locator('#service-status')).toHaveClass(/status-online/, {
      timeout: 15000,
    });
    await expect(page.locator('#service-status')).toContainText(/online/i);
  });

  test('score zone and quiz summary visible in score mode', async ({ page }) => {
    await expect(page.locator('#score-zone')).toBeVisible();
    await expect(page.locator('#phoneme-container')).toBeVisible();
    await expect(page.locator('#quiz-results-table')).toBeVisible();
    await expect(page.locator('#phoneme-container .phoneme-char').first()).toBeVisible();
    await expect(page.locator('#score-section')).toBeVisible();
  });

  test('evaluate API reachable from page context (CORS)', async ({ page }) => {
    const result = await page.evaluate(async (apiBase) => {
      const res = await fetch(`${apiBase}/api/v1/health`);
      const data = await res.json();
      return { ok: res.ok, status: data.status };
    }, BACKEND_URL);

    expect(result.ok).toBe(true);
    expect(result.status).toBe('ok');
  });

  test('live mic auto-score hint in score mode', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await page.locator('#btn-live-toggle').click();
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/, {
      timeout: 10000,
    });
    await expect(page.locator('#live-transcript-placeholder')).toContainText(/chấm IPA/i);
  });

  test('settings API URL matches test backend', async ({ page }) => {
    await page.locator('#btn-settings').click();
    await expect(page.locator('#setting-api-url')).toHaveValue(BACKEND_URL);
  });
});

test.describe('Score mode — backend offline message', () => {
  test('shows offline when API unreachable', async ({ page, context }) => {
    await openApp(page, {
      practiceMode: 'score',
      apiBaseUrl: 'http://127.0.0.1:19999',
    });
    await page.locator('#mode-score').click();
    await expect(page.locator('#service-status')).toHaveClass(/status-offline/, {
      timeout: 15000,
    });
  });
});
