const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8199', headless: true, screenshot: 'only-on-failure' },
  // Not 8080: that is the port the app itself prefers, so on a machine (or a
  // runner) where something already holds it the server quietly takes another
  // port and Playwright waits out its timeout on an address nothing is serving.
  // 8199 is nobody's default, and stdout is piped so a failed start is visible
  // in the job log rather than only as a timeout.
  webServer: {
    command: 'PORT=8199 python3 -m buttcrack.server',
    url: 'http://127.0.0.1:8199',
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe',
    timeout: 60000,
  }
});
