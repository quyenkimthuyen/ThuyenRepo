import { openApp, expect } from './fixtures.mjs';

/** Mở app với chế độ chấm điểm */
export async function openScoreMode(page, settings = {}) {
  await openApp(page, {
    practiceMode: 'score',
    liveAutoStart: false,
    autoPlaySample: false,
    ...settings,
  });
  await expect(page.locator('#mode-score')).toHaveClass(/active/);
  await expect(page.locator('#score-zone')).toBeVisible();
}

/** Bật micro (fake device — Playwright) */
export async function enableMic(page) {
  await page.locator('#btn-live-toggle').click();
  await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/, {
    timeout: 15000,
  });
}

/** Tắt micro */
export async function disableMic(page) {
  const state = await page.locator('#btn-live-toggle').getAttribute('data-state');
  if (state !== 'off') {
    await page.locator('#btn-live-toggle').click();
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'off', {
      timeout: 10000,
    });
  }
}

export async function getTestState(page) {
  return page.evaluate(() => window.__pronounceLabTest.getState());
}

export async function mockScore(page, score, passed) {
  return page.evaluate(
    ([s, p]) => window.__pronounceLabTest.runMockEvaluate(s, p),
    [score, passed],
  );
}

export async function mockTextPass(page) {
  return page.evaluate(() => window.__pronounceLabTest.simulateTextPass());
}

export async function expectInitUnchanged(page, initBefore) {
  const initAfter = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
  expect(initAfter).toBe(initBefore);
}
