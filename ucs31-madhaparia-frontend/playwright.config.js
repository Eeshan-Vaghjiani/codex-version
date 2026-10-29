import { defineConfig } from '@playwright/test'

const modelMode = process.env.E2E_MODEL_VERSION || 'v3'

export default defineConfig({
  testDir: './e2e',
  testMatch: modelMode === 'v3' ? '**/consultation-v3.pw.js'
    : modelMode === 'v2' ? '**/research-v2.pw.js' : '**/assessment.pw.js',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  reporter: [['list'], ['json', {
    outputFile: `playwright-results/live-${modelMode}-results.json`,
  }]],
  use: {
    baseURL: process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5173',
    channel: process.env.E2E_BROWSER_CHANNEL || 'msedge',
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    env: { VITE_API_BASE_URL: process.env.E2E_API_URL || 'http://127.0.0.1:8000' },
  },
})
