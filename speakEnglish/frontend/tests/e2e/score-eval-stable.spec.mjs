import { test, expect, openApp } from './fixtures.mjs';

test.describe('Chế độ Chấm điểm — không reload khi chấm', () => {
  test.beforeEach(async ({ page }) => {
    await openApp(page, {
      practiceMode: 'score',
      liveAutoStart: false,
      autoPlaySample: false,
    });
    await page.locator('#mode-score').click();
    await expect(page.locator('#score-zone')).toBeVisible();
  });

  test('mock evaluate giữ nguyên trang và cập nhật điểm tại chỗ', async ({ page }) => {
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();
    const boxCountBefore = await page.evaluate(() => window.__pronounceLabTest.getPhonemeBoxCount());

    expect(boxCountBefore).toBeGreaterThan(0);

    await page.evaluate(() => window.__pronounceLabTest.runMockEvaluate(62, false));

    await expect(page.locator('#overall-score')).toHaveText('62%');
    await expect(page.locator('#pass-status')).toContainText('Chưa đạt');

    const initAfter = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexAfter = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());

    expect(initAfter).toBe(initBefore);
    expect(indexAfter).toBe(indexBefore);
    await expect(page.locator('#current-word')).toHaveText(wordBefore || '');

    const boxCountAfter = await page.evaluate(() => window.__pronounceLabTest.getPhonemeBoxCount());
    expect(boxCountAfter).toBe(boxCountBefore);
  });

  test('đạt điểm chuyển từ nhẹ — không init lại app', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await page.locator('#btn-live-toggle').click();
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/, {
      timeout: 15000,
    });

    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();

    await page.evaluate(() => window.__pronounceLabTest.runMockEvaluate(92, true));

    const initAfter = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexAfter = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordAfter = await page.locator('#current-word').textContent();

    expect(initAfter).toBe(initBefore);
    expect(indexAfter).toBe(indexBefore + 1);
    expect(wordAfter).not.toBe(wordBefore);
    await expect(page.locator('#overall-score')).toHaveText('—');
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/);
  });

  test('chấm lại cùng từ — phoneme boxes không rebuild', async ({ page }) => {
    await page.evaluate(() => {
      window.__pronounceLabTest.getPhonemeBoxNodes().forEach((node, i) => {
        node.dataset.stableId = `box-${i}`;
      });
    });

    await page.evaluate(() => window.__pronounceLabTest.runMockEvaluate(50, false));
    await expect(page.locator('#overall-score')).toHaveText('50%');

    await page.evaluate(() => window.__pronounceLabTest.runMockEvaluate(70, false));
    await expect(page.locator('#overall-score')).toHaveText('70%');

    const stableIds = await page.evaluate(() =>
      window.__pronounceLabTest.getPhonemeBoxNodes().map((node) => node.dataset.stableId),
    );
    expect(stableIds.length).toBeGreaterThan(0);
    expect(stableIds.every((id) => id?.startsWith('box-'))).toBe(true);
  });
});
