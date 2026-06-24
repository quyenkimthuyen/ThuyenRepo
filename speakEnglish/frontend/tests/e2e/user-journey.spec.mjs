/**
 * E2E — mô phỏng luồng người dùng trên browser (Playwright + fake micro).
 * Chạy: cd frontend && npx playwright test user-journey --project=chromium
 */
import { test, expect, openApp } from './fixtures.mjs';
import {
  openScoreMode,
  enableMic,
  disableMic,
  getTestState,
  mockScore,
  mockTextPass,
  expectInitUnchanged,
} from './helpers.mjs';

test.describe('Luồng người dùng — khởi động & điều hướng', () => {
  test.beforeEach(async ({ page }) => {
    await openApp(page, { liveAutoStart: false, autoPlaySample: false });
  });

  test('mở app hiển thị từ, quiz info và bảng tổng kết', async ({ page }) => {
    await expect(page.locator('#current-word')).not.toHaveText('—');
    await expect(page.locator('#word-index')).toHaveText(/\d+ \/ \d+/);
    await expect(page.locator('#quiz-info')).toContainText(/Quiz/);
    await expect(page.locator('#quiz-summary')).toBeVisible();
    await expect(page.locator('#quiz-results-body tr')).not.toHaveCount(0);
  });

  test('nút Tiếp / Trước và dropdown đổi từ', async ({ page }) => {
    const word0 = await page.locator('#current-word').textContent();
    const progress0 = await page.locator('#word-index').textContent();

    await page.locator('#btn-next').click();
    const word1 = await page.locator('#current-word').textContent();
    expect(word1).not.toBe(word0);

    await page.locator('#btn-prev').click();
    await expect(page.locator('#current-word')).toHaveText(word0 || '');

    const options = page.locator('#word-select option');
    const count = await options.count();
    test.skip(count < 2, 'Cần ít nhất 2 từ trong bài quiz');

    await page.locator('#word-select').selectOption({ index: 1 });
    await expect(page.locator('#current-word')).not.toHaveText(word0 || '');
    await expect(page.locator('#word-index')).not.toHaveText(progress0 || '');
  });
});

test.describe('Luồng người dùng — chế độ Chỉ text', () => {
  test.beforeEach(async ({ page }) => {
    await openApp(page, {
      practiceMode: 'text',
      liveAutoStart: false,
      autoPlaySample: false,
      textPassScore: 100,
    });
    await expect(page.locator('#mode-text')).toHaveClass(/active/);
  });

  test('đọc đúng từ → tự chuyển từ tiếp + cập nhật bảng quiz', async ({ page }) => {
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const wordBefore = await page.locator('#current-word').textContent();
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());

    const result = await mockTextPass(page);
    expect(result?.before).toBe(indexBefore);
    expect(result?.after).toBe(indexBefore + 1);

    await expect(page.locator('#current-word')).not.toHaveText(wordBefore || '');
    await expectInitUnchanged(page, initBefore);

    const row = await page.evaluate(
      (idx) => window.__pronounceLabTest.getQuizRow(idx),
      indexBefore,
    );
    expect(row?.status).toBe('pass');
    expect(row?.score).toBe(100);
  });

  test('bật/tắt micro không reload app', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    await enableMic(page);
    await expect(page.locator('#mic-status-label')).toContainText(/Sẵn sàng|đang nghe/i);

    await disableMic(page);
    await expect(page.locator('#mic-status-label')).toContainText(/tắt/i);
    await expectInitUnchanged(page, initBefore);
  });

  test('tiêu đề bảng quiz theo chế độ text', async ({ page }) => {
    await expect(page.locator('#quiz-summary-title')).toContainText(/Chỉ text/i);
  });
});

test.describe('Luồng người dùng — chế độ Chấm điểm', () => {
  test.beforeEach(async ({ page }) => {
    await openScoreMode(page);
  });

  test('chấm điểm thất bại → hiện điểm + cập nhật bảng quiz', async ({ page }) => {
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();

    await mockScore(page, 55, false);

    await expect(page.locator('#overall-score')).toHaveText('55%');
    await expect(page.locator('#pass-status')).toContainText(/Chưa đạt/);
    await expect(page.locator('#current-word')).toHaveText(wordBefore || '');
    await expectInitUnchanged(page, initBefore);

    const row = await page.evaluate(
      (idx) => window.__pronounceLabTest.getQuizRow(idx),
      indexBefore,
    );
    expect(row?.status).toBe('fail');
    expect(row?.score).toBe(55);
  });

  test('chấm đạt → chuyển từ + micro vẫn bật', async ({ page, browserName }) => {
    test.skip(browserName === 'firefox', 'Chỉ Chrome/Edge');

    await enableMic(page);
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());
    const indexBefore = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    const wordBefore = await page.locator('#current-word').textContent();

    await mockScore(page, 92, true);

    const state = await getTestState(page);
    expect(state.currentIndex).toBe(indexBefore + 1);
    expect(state.word).not.toBe(wordBefore);
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', /ready|hearing/);
    await expectInitUnchanged(page, initBefore);

    const prevRow = await page.evaluate(
      (idx) => window.__pronounceLabTest.getQuizRow(idx),
      indexBefore,
    );
    expect(prevRow?.status).toBe('pass');
  });

  test('đổi chế độ text ↔ score giữ app ổn định', async ({ page }) => {
    const initBefore = await page.evaluate(() => window.__pronounceLabTest.getInitCount());

    await page.locator('#mode-score').click();
    await expect(page.locator('#phoneme-container')).toBeVisible();
    await expect(page.locator('#quiz-summary-title')).toContainText(/Chấm điểm/i);

    await page.locator('#mode-text').click();
    await expect(page.locator('#mode-text')).toHaveClass(/active/);
    await expect(page.locator('#score-zone')).toBeHidden();
    await expect(page.locator('#quiz-summary-title')).toContainText(/Chỉ text/i);

    await expectInitUnchanged(page, initBefore);
  });

  test('Nghe mẫu không bật micro khi micro tắt', async ({ page }) => {
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'off');
    await page.locator('#btn-play-sample').click();
    await expect(page.locator('#btn-live-toggle')).toHaveAttribute('data-state', 'off');
  });
});

test.describe('Luồng người dùng — Cài đặt', () => {
  test('mở/đóng cài đặt và chỉnh thời gian im lặng', async ({ page }) => {
    await openApp(page, { liveAutoStart: false });

    await page.locator('#btn-settings').click();
    await expect(page.locator('#settings-panel')).not.toHaveClass(/hidden/);
    await expect(page.locator('#setting-topic')).toBeVisible();
    await expect(page.locator('#setting-idle-sample-sec')).toBeVisible();

    await page.locator('#setting-silence-sec').fill('0.5');
    await page.locator('#btn-close-settings').click();
    await expect(page.locator('#settings-panel')).toHaveClass(/hidden/);

    await page.locator('#btn-settings').click();
    await expect(page.locator('#setting-silence-sec')).toHaveValue('0.5');
    await page.locator('#btn-close-settings').click();
  });
});

test.describe('Luồng người dùng — phiên làm bài', () => {
  test('bảng quiz highlight dòng từ hiện tại', async ({ page }) => {
    await openApp(page, { liveAutoStart: false });
    const index = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());

    await page.locator('#btn-next').click();
    const newIndex = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    expect(newIndex).toBe(index + 1);

    const currentRow = page.locator(`#quiz-results-body tr.quiz-row[data-index="${newIndex}"]`);
    await expect(currentRow).toHaveClass(/current/);
  });

  test('click dòng quiz nhảy tới từ', async ({ page }) => {
    await openApp(page, { liveAutoStart: false });
    const options = page.locator('#word-select option');
    const count = await options.count();
    test.skip(count < 3, 'Cần ít nhất 3 từ');

    const targetIndex = 2;
    await page.locator(`#quiz-results-body tr.quiz-row[data-index="${targetIndex}"]`).click();

    const index = await page.evaluate(() => window.__pronounceLabTest.getCurrentIndex());
    expect(index).toBe(targetIndex);

    const wordFromSelect = await page.locator('#word-select').inputValue();
    expect(parseInt(wordFromSelect, 10)).toBe(targetIndex);
  });
});
