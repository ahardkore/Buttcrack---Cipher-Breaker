const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8080', headless: true, screenshot: 'only-on-failure' },
  webServer: { command: 'PORT=8080 python3 -m buttcrack.server', url: 'http://127.0.0.1:8080', reuseExistingServer: false, timeout: 30000 }
});
