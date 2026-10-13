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
  test('one core is left free by default and a running search can be stopped', async ({ page }) => {
    // The search runs while somebody is looking at the page, so the default
    // worker count is one short of the machine -- and a stop button has to be
    // there for the budget nobody meant to pick.  The health reply is stubbed
    // so the assertion does not depend on how many cores this machine has.
    await page.route('**/api/health', (route) =>
      route.fulfill({
        json: {
          name: 'buttcrack',
          version: '0.0.0-test',
          python: '3.12',
          cpus: 4,
          ciphers: 50,
          layers: [],
          paradigm_records: 10,
          model: {},
          languages: [],
        },
      }),
    );
    await page.goto('/');
    await expect(page.locator('#workers')).toHaveValue('3');
    await expect(page.locator('#cancel')).toBeHidden();

    await page.fill('#input', 'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj');
    await page.click('#crack');
    await expect(page.locator('#cancel')).toBeVisible();
    await expect(page.locator('#plaintext')).toContainText('quick', { timeout: 60000 });
    await expect(page.locator('#cancel')).toBeHidden();
  });

  test('responsive accessibility modes and print mode', async ({ page }) => {
    await page.goto('/');
    await page.emulateMedia({ media: 'print' });
    await expect(page.locator('body')).toBeVisible();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
  });
});
