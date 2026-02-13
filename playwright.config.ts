import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  timeout: 60000,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'on-first-retry',
    extraHTTPHeaders: {
      'x-admin-secret': 'votechain-v3-secret-2026',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'npx http-server . -p 8080',
      port: 8080,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run serve',
      url: 'http://127.0.0.1:3000/api/health',
      reuseExistingServer: !process.env.CI,
      env: {
        ADMIN_SECRET: 'votechain-v3-secret-2026',
        PORT: '3000'
      }
    },
  ],
});
