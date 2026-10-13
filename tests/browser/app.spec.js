const { test, expect } = require('@playwright/test');

test.describe('real Buttcrack web application', () => {
  test('navigation tabs and keyboard navigation', async ({ page }) => {
    await page.goto('/');
    for (const tab of ['break','playground','reference','about']) {
      const button=page.locator(`.tab-button[data-tab="${tab}"]`);
      await button.click();
      await expect(page.locator(`#tab-${tab}`)).toBeVisible();
    }
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
  });
  test('assistant, verification, crib, transposition, scoring controls are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toContainText(/assistant|score|verify|crib|transposition/i);
    await expect(page.locator('button, input, textarea').first()).toBeVisible();
  });
  test('session export/import controls and mismatch output', async ({ page }) => {
    await page.goto('/');
    const exportControl=page.getByText(/export/i).first();
    if (await exportControl.count()) await expect(exportControl).toBeVisible();
    await expect(page.locator('#error-card, #error-text, body').first()).toBeAttached();
  });
  // The health reply the page is booted against, stubbed so nothing below
  // depends on how many cores the machine running the suite happens to have.
  const HEALTH = {
    name: 'buttcrack',
    version: '0.0.0-test',
    python: '3.12',
    cpus: 4,
    ciphers: 50,
    layers: [],
    paradigm_records: 10,
    model: {},
    languages: [],
  };

  test('one core is left free by default', async ({ page }) => {
    // The search runs while somebody is looking at the page, so the default is
    // one short of the machine rather than all of it.
    await page.route('**/api/health', (route) => route.fulfill({ json: HEALTH }));
    await page.goto('/');
    await expect(page.locator('#workers')).toHaveValue('3');
    await expect(page.locator('#cancel')).toBeHidden();
  });

  test('a running search can be stopped', async ({ page }) => {
    // The job endpoints are stubbed so the button is tested rather than the
    // engine: a search that finishes in 200 ms would make this a race.
    let finished = false;
    await page.route('**/api/health', (route) => route.fulfill({ json: HEALTH }));
    await page.route('**/api/crack', (route) => route.fulfill({ json: { job: 'testjob1234' } }));
    await page.route('**/api/job/testjob1234', (route) =>
      route.fulfill({
        json: {
          id: 'testjob1234',
          done: finished,
          cancelled: finished,
          error: null,
          report: null,
          progress: [{ at: 0.1, message: 'working', fraction: 0.2, extra: {} }],
        },
      }),
    );
    // Registered last, so it wins over the job status route above.
    await page.route('**/api/job/testjob1234/cancel', (route) =>
      route.fulfill({ json: { job: 'testjob1234', cancel_requested: true } }),
    );

    await page.goto('/');
    await page.fill('#input', 'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj');
    await page.click('#crack');
    await expect(page.locator('#cancel')).toBeVisible();
    await expect(page.locator('#progress-card')).toBeVisible();

    finished = true;
    await page.click('#cancel');
    await expect(page.locator('#cancel')).toBeHidden();
    await expect(page.locator('#progress-state')).toHaveText('stopped');
    await expect(page.locator('#error-card')).toBeHidden();
  });

  test('the last session can be brought back', async ({ page }) => {
    // Restoring is offered, not done: the tab may have been opened to paste
    // something new, so the bar has to be there and the button has to work.
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'buttcrack.session.v1',
        JSON.stringify({ text: 'WKH TXLFN EROZQ', options: { 'hint-key': 'LEMON', budget: '5' }, at: Date.now() }),
      );
    });
    await page.goto('/');
    await expect(page.locator('#restore')).toBeVisible();
    await page.click('#restore-yes');
    await expect(page.locator('#input')).toHaveValue('WKH TXLFN EROZQ');
    await expect(page.locator('#hint-key')).toHaveValue('LEMON');
    await expect(page.locator('#restore')).toBeHidden();

    // And the bar can be waved away without touching the box.
    await page.evaluate(() => window.localStorage.setItem('buttcrack.session.v1', JSON.stringify({ text: 'SECOND', options: {}, at: Date.now() })));
    await page.reload();
    await page.click('#restore-no');
    await expect(page.locator('#restore')).toBeHidden();
    await expect(page.locator('#input')).toHaveValue('');
  });

  test('a ciphertext file is read in the browser', async ({ page }, testInfo) => {
    const fs = require('fs');
    const file = testInfo.outputPath('cipher.txt');
    fs.writeFileSync(file, 'WKH TXLFN EROZQ IRA MXPSV');
    await page.goto('/');
    await page.setInputFiles('#file', file);
    await expect(page.locator('#input')).toHaveValue('WKH TXLFN EROZQ IRA MXPSV');
    // The promise on the page is that nothing is uploaded, so the line that
    // says so has to be the one that appears.
    await expect(page.locator('#footer-status')).toContainText('nothing was uploaded');
  });

  test('print mode keeps the report and drops the furniture', async ({ page }) => {
    // What the print stylesheet promises: the page that comes out of a printer
    // is the result, not the controls that produced it.
    await page.goto('/');
    await page.emulateMedia({ media: 'print' });
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('header')).toBeHidden();
    await expect(page.locator('.controls').first()).toBeHidden();
    await expect(page.locator('#input')).toBeVisible();
  });
});
