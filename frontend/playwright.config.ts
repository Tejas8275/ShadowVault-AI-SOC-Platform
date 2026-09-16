import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/browser', fullyParallel: false, workers: 1,
  reporter: 'list', timeout: 30_000,
  use: { baseURL: 'http://127.0.0.1:5179', channel: 'msedge', headless: true, trace: 'off', screenshot: 'off', video: 'off' },
  webServer: [
    { command: 'npm run dev -- --port 5179 --strictPort', url: 'http://127.0.0.1:5179', reuseExistingServer: false,
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8769/api/v1', VITE_INVESTIGATION_API_BASE_URL: 'http://127.0.0.1:8769/api/v2/investigation' } },
    { command: '"..\\backend\\.venv\\Scripts\\python.exe" "..\\tests\\browser_fixture.py"', url: 'http://127.0.0.1:8769/health', reuseExistingServer: false },
  ],
})
