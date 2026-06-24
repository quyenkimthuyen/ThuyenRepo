import { test, expect, openApp } from './fixtures.mjs';
import {
  openScoreMode,
  enableMic,
  expectInitUnchanged,
  installMockEvaluateApi,
  installTestClock,
  armScoreSilence,
  getIdleSampleState,
} from './helpers.mjs';

test.describe('Timer im lặng → chấm điểm (score mode)', () => {
  test.beforeEach(async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');
    await installTestClock(page);
    await installMockEvaluateApi(page, () => ({ overallScore: 61, passed: false }));
    await openScoreMode(page, { autoEvaluate: true, silenceSec: 0.35 });
  });

  test('SR nghe từ → hangover → processScoreUtterance → API, không reload', async ({ page }) => {
    await enableMic(page);
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();

    const arm = await armScoreSilence(page);
    expect(arm.error).toBeUndefined();
    expect(arm.hasTimer).toBe(true);
    expect(arm.hangMs).toBeGreaterThanOrEqual(300);
    expect(arm.spoken.length).toBeGreaterThan(0);

    await page.clock.fastForward(arm.hangMs + 80);

    await expect(page.locator('#overall-score')).toHaveText('61%', { timeout: 15000 });
    await expect(page.locator('#current-word')).toHaveText(wordBefore || '');
    await expectInitUnchanged(page, initBefore);

    const indexAfter = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    expect(indexAfter).toBe(indexBefore);
  });

  test('flush timer — cùng pipeline processScoreUtterance', async ({ page }) => {
    await enableMic(page);
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());

    const arm = await armScoreSilence(page);
    expect(arm.hasTimer).toBe(true);

    const flushed = await page.evaluate(() => window.__pronounceLabTest.flushScoreSilenceTimer());
    expect(flushed.error).toBeUndefined();
    expect(flushed.unchanged).toBe(true);

    await expect(page.locator('#overall-score')).toHaveText('61%', { timeout: 15000 });
    await expectInitUnchanged(page, initBefore);
  });
});

test.describe('Idle autoplay — tự phát mẫu khi không thao tác', () => {
  test.beforeEach(async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');
    await installTestClock(page);
  });

  test('micro bật + autoplay → sau idleSec phát mẫu (mic vàng/tím)', async ({ page }) => {
    await openApp(page, {
      practiceMode: 'text',
      autoPlaySample: true,
      idleSampleSec: 2,
      liveAutoStart: false,
    });
    await enableMic(page);

    const before = await getIdleSampleState(page);
    expect(before.shouldAutoplay).toBe(true);
    expect(before.armed).toBe(true);
    expect(before.idleSec).toBe(2);

    await page.clock.fastForward(2100);

    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'sample', {
      timeout: 5000,
    });

    const after = await getIdleSampleState(page);
    expect(after.isSamplePlaying).toBe(true);
  });

  test('autoplay tắt → không phát mẫu dù chờ idle', async ({ page }) => {
    await openApp(page, {
      practiceMode: 'text',
      autoPlaySample: false,
      idleSampleSec: 1,
      liveAutoStart: false,
    });
    await enableMic(page);

    const before = await getIdleSampleState(page);
    expect(before.shouldAutoplay).toBe(false);
    expect(before.armed).toBe(false);

    await page.clock.fastForward(1500);

    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/);
    const after = await getIdleSampleState(page);
    expect(after.isSamplePlaying).toBe(false);
  });

  test('micro tắt → idle autoplay không chạy', async ({ page }) => {
    await openApp(page, {
      practiceMode: 'score',
      autoPlaySample: true,
      idleSampleSec: 1,
      liveAutoStart: false,
    });

    const state = await getIdleSampleState(page);
    expect(state.shouldAutoplay).toBe(false);
    expect(state.armed).toBe(false);

    await page.clock.fastForward(1500);

    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'off');
    const after = await getIdleSampleState(page);
    expect(after.isSamplePlaying).toBe(false);
  });

  test('thao tác người dùng → reset timer idle', async ({ page }) => {
    await openApp(page, {
      practiceMode: 'text',
      autoPlaySample: true,
      idleSampleSec: 2,
      liveAutoStart: false,
    });
    await enableMic(page);

    await page.clock.fastForward(1200);
    await page.locator('#btn-next').click();

    await page.clock.fastForward(1200);
    await expect(page.locator('#btn-live-toggle')).not.toHaveAttribute('data-state', 'sample');

    await page.clock.fastForward(1000);
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'sample', {
      timeout: 5000,
    });
  });
});
