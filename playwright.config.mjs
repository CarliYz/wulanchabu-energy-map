import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './qa/e2e',
  timeout: 45000,
  expect: { timeout: 12000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    baseURL: process.env.ENERGY_QA_URL || 'http://127.0.0.1:8766',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  webServer: {
    command: 'python3 -m http.server 8766 --bind 127.0.0.1 --directory web/map-viewer',
    url: 'http://127.0.0.1:8766',
    reuseExistingServer: true,
    timeout: 10000
  }
});
