import { test, expect } from './fixtures.mjs';
import {
  openScoreMode,
  enableMic,
  expectInitUnchanged,
  installMockEvaluateApi,
  simulateScoreReadAndEvaluate,
} from './helpers.mjs';

test.describe('Chế độ Chấm điểm — API evaluate thật (mock response)', () => {
  test.beforeEach(async ({ page }) => {
    await openScoreMode(page, { autoEvaluate: true, silenceSec: 0.35 });
  });

  test('đọc xong → fetch evaluate → fail, không reload trang', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await installMockEvaluateApi(page, () => ({ overallScore: 58, passed: false }));

    await enableMic(page);
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();
    const boxCountBefore = await page.evaluate(() => window.__pronounceLabTest.getPhonemeBoxCount());

    await page.evaluate(() => {
      window.__pronounceLabTest.getPhonemeBoxNodes().forEach((node, i) => {
        node.dataset.stableId = `api-box-${i}`;
      });
    });

    const result = await simulateScoreReadAndEvaluate(page);
    expect(result.error).toBeUndefined();

    await expect(page.locator('#overall-score')).toHaveText('58%', { timeout: 15000 });
    await expect(page.locator('#pass-status')).toContainText(/Chưa đạt/);
    await expect(page.locator('#current-word')).toHaveText(wordBefore || '');

    await expectInitUnchanged(page, initBefore);
    expect(result.before.initCount).toBe(initBefore);
    expect(result.after.initCount).toBe(initBefore);
    expect(result.after.index).toBe(indexBefore);

    const boxCountAfter = await page.evaluate(() => window.__pronounceLabTest.getPhonemeBoxCount());
    expect(boxCountAfter).toBe(boxCountBefore);

    const stableIds = await page.evaluate(() =>
      window.__pronounceLabTest.getPhonemeBoxNodes().map((node) => node.dataset.stableId),
    );
    expect(stableIds.every((id) => id?.startsWith('api-box-'))).toBe(true);
  });

  test('đọc xong → fetch evaluate → đạt, chuyển từ nhẹ không init lại', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await installMockEvaluateApi(page, () => ({ overallScore: 92, passed: true }));

    await enableMic(page);
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();

    await simulateScoreReadAndEvaluate(page);

    await expect(page.locator('#overall-score')).toHaveText('—', { timeout: 15000 });
    await expect(page.locator('#current-word')).not.toHaveText(wordBefore || '', { timeout: 10000 });

    const indexAfter = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    expect(indexAfter).toBe(indexBefore + 1);
    await expectInitUnchanged(page, initBefore);
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/);
  });

  test('chấm lại qua API — phoneme DOM không rebuild', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    let call = 0;
    await installMockEvaluateApi(page, () => {
      call += 1;
      return call === 1
        ? { overallScore: 52, passed: false }
        : { overallScore: 74, passed: false };
    });

    await enableMic(page);

    await page.evaluate(() => {
      window.__pronounceLabTest.getPhonemeBoxNodes().forEach((node, i) => {
        node.dataset.stableId = `live-api-${i}`;
      });
    });

    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());

    await simulateScoreReadAndEvaluate(page);
    await expect(page.locator('#overall-score')).toHaveText('52%', { timeout: 15000 });

    await simulateScoreReadAndEvaluate(page);
    await expect(page.locator('#overall-score')).toHaveText('74%', { timeout: 15000 });

    await expectInitUnchanged(page, initBefore);

    const stableIds = await page.evaluate(() =>
      window.__pronounceLabTest.getPhonemeBoxNodes().map((node) => node.dataset.stableId),
    );
    expect(stableIds.length).toBeGreaterThan(0);
    expect(stableIds.every((id) => id?.startsWith('live-api-'))).toBe(true);
  });
});
