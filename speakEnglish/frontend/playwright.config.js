import { defineConfig, devices } from '@playwright/test';
import { E2E_BACKEND_PORT, E2E_BACKEND_URL, E2E_FRONTEND_PORT, E2E_FRONTEND_URL } from './tests/e2e/ports.mjs';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60000,
  reporter: 'list',
  use: {
    baseURL: E2E_FRONTEND_URL,
    permissions: ['microphone'],
    launchOptions: {
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
      ],
    },
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'msedge',
      use: {
        ...devices['Desktop Edge'],
        channel: 'msedge',
      },
    },
  ],
  webServer: [
    {
      command: 'bash ../scripts/start_test_backend.sh',
      cwd: '.',
      url: `${E2E_BACKEND_URL}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        ...process.env,
        E2E_BACKEND_PORT: String(E2E_BACKEND_PORT),
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      command: `python3 -m http.server ${E2E_FRONTEND_PORT}`,
      url: E2E_FRONTEND_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
