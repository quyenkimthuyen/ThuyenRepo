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

/** JSON evaluate giống contract backend */
export function buildEvaluateResponse(wordInfo, overallScore, passed) {
  const phonemes = (wordInfo.phonemes?.length ? wordInfo.phonemes : ['ə']).map((ipa, i) => ({
    ipa,
    score: overallScore / 100,
    label: overallScore >= 80 ? 'ok' : 'mis',
    start: i * 0.1,
    end: (i + 1) * 0.1,
    suggestion: overallScore >= 80 ? '' : 'thử lại',
  }));
  return {
    word: wordInfo.word,
    ipa: wordInfo.ipa,
    overall_score: overallScore,
    passed,
    phonemes,
  };
}

function parseTargetWordFromMultipart(body) {
  const text = body?.toString('utf8') || '';
  const match = text.match(/name="target_word"\r?\n\r?\n([^\r\n]+)/);
  return match?.[1]?.trim() || '';
}

/**
 * Mock POST /api/v1/evaluate — vẫn đi qua fetch trong app.
 * @param {(ctx: { targetWord: string, callIndex: number }) => { overallScore: number, passed: boolean }} scorer
 */
export async function installMockEvaluateApi(page, scorer) {
  let callIndex = 0;
  await page.route('**/api/v1/evaluate', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    const targetWord = parseTargetWordFromMultipart(route.request().postDataBuffer());
    const wordInfo = await page.evaluate((tw) => {
      const cur = window.__pronounceLabTest.getCurrentWord();
      if (cur && (!tw || cur.word === tw)) return cur;
      return { word: tw || cur?.word || 'word', ipa: cur?.ipa || '', phonemes: cur?.phonemes || ['ə'] };
    }, targetWord);

    const { overallScore, passed } = scorer({ targetWord: wordInfo.word, callIndex });
    callIndex += 1;
    const body = buildEvaluateResponse(wordInfo, overallScore, passed);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

/** Bật micro + mô phỏng đọc xong → chờ API evaluate → assert init không đổi */
export async function simulateScoreReadAndEvaluate(page) {
  return page.evaluate(() => window.__pronounceLabTest.simulateScoreReadAndEvaluate());
}

export async function installTestClock(page) {
  await page.clock.install();
}

export async function armScoreSilence(page) {
  return page.evaluate(() => window.__pronounceLabTest.armScoreSilenceEvaluate());
}

export async function flushScoreSilence(page) {
  return page.evaluate(() => window.__pronounceLabTest.flushScoreSilenceTimer());
}

export async function getIdleSampleState(page) {
  return page.evaluate(() => window.__pronounceLabTest.getIdleSampleState());
}
