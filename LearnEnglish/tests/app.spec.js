import { test, expect } from '@playwright/test';

test.setTimeout(120000);

const BASE_URL = 'http://localhost:8080';

test.describe('Toeic Vocab App UI', () => {
  test.setTimeout(120000);
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('Navigation works', async ({ page }) => {
    await expect(page.locator('.nav-button[data-page="learn"]').first()).toBeVisible();
    await page.click('.nav-button[data-page="quiz"]').then(() => { });
    await expect(page.locator('#quizPage')).not.toHaveClass(/hidden/);
    await page.click('.nav-button[data-page="stats"]').then(() => { });
    await expect(page.locator('#statsPage')).not.toHaveClass(/hidden/);
  });

  test('Theme toggle switches', async ({ page }) => {
    const button = page.locator('#themeButton');
    const initial = await button.textContent();
    await button.click();
    const after = await button.textContent();
    expect(after).not.toBe(initial);
  });

  test('Learning page displays words', async ({ page }) => {
    await page.click('.nav-button[data-page="learn"]');
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('#learnPage article.panel.stack');
      return cards.length > 0 && window.state?.page === 'learn';
    }, null, { timeout: 120000 });
    const cards = page.locator('#learnPage article.panel.stack');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Typing quiz flow', async ({ page }) => {
    await page.click('.nav-button[data-page="quiz"]');
    await page.click('.tab[data-mode="typing"]');
    await page.click('#startQuiz');
    // Wait for the answer input to be rendered
    await page.waitForSelector('#typingAnswer', { timeout: 60000 });
    const prompt = page.locator('.typing-form h3');
    await expect(prompt).toBeVisible();
    const answerInput = page.locator('#typingAnswer');
    await answerInput.fill('test');
    await page.click('#typingForm button[type="submit"]');
    // Wait for feedback element to become visible
    await page.waitForSelector('.feedback', { state: 'visible', timeout: 120000 });
    const feedback = page.locator('.feedback');
    await expect(feedback).toBeVisible();
  });

  test('Hint button reveals hint', async ({ page }) => {
    await page.click('.nav-button[data-page="quiz"]');
    await page.click('.tab[data-mode="typing"]');
    await page.click('#startQuiz');
    await page.click('#quizHint');
    const hint = page.locator('#hintText');
    await expect(hint).not.toHaveClass(/hidden/);
  });

  test('Reset saved state clears data', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('lexirise-vocabulary-store-v3', JSON.stringify({ state: { words: [] } }));
    });
    await page.reload();
    // Navigate to stats page to access the reset button
    await page.click('.nav-button[data-page="stats"]');
    await page.waitForSelector('#resetSavedState');
    await page.click('#resetSavedState');
    // Reload to ensure UI updates after reset
    await page.reload();
    // After reset, the app reloads all words, so total count remains, but known is zero
    const header = await page.locator('#headerStats').textContent();
    expect(header).toMatch(/^0 \//); // matches "0 / <total> known"
  });
});
