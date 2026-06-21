import { test as base, expect } from '@playwright/test';
import { E2E_BACKEND_URL } from './ports.mjs';

/**
 * @param {Page} page
 * @param {object} settings
 */
export async function seedSettings(page, settings = {}) {
  const defaults = {
    liveAutoStart: false,
    autoPlaySample: false,
    autoEvaluate: true,
    silenceSec: 0.35,
    apiBaseUrl: E2E_BACKEND_URL,
    practiceMode: 'text',
  };
  const merged = { ...defaults, ...settings };
  await page.addInitScript((data) => {
    localStorage.setItem('pronouncelab_settings', JSON.stringify(data));
  }, merged);
}

export async function openApp(page, settings = {}) {
  await seedSettings(page, settings);
  await page.goto('/');
  await expect(page.locator('#current-word')).not.toHaveText('—', { timeout: 15000 });
}

export { expect, E2E_BACKEND_URL as BACKEND_URL };

export const test = base;
