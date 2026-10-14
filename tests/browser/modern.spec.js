const { test, expect } = require('@playwright/test');

test.describe('explicit offline crypto labs', () => {
  test('desktop hash opens Crypto Labs and RSA example recovers A', async ({ page }) => {
    await page.goto('/#modern');
    await expect(page.locator('#tab-modern')).toBeVisible();
    await page.locator('#modern-example').click();
    await page.locator('#modern-run').click();
    await expect(page.locator('#modern-status')).toHaveText('weakness found');
    await expect(page.locator('#modern-result')).toContainText('"utf8": "A"');
    await expect(page.locator('#modern-result')).toContainText('"factorization_verified": true');
  });

  test('keystream crib is labelled as a hypothesis and clearing removes inputs', async ({ page }) => {
    await page.goto('/#modern');
    await page.locator('#modern-lab').selectOption('keystream');
    await page.locator('#modern-example').click();
    await page.locator('#modern-run').click();
    await expect(page.locator('#modern-status')).toContainText('reuse is not proven');
    await expect(page.locator('#modern-result')).toContainText('"hypothesis"');
    await page.locator('#modern-clear').click();
    await expect(page.locator('#modern-crib')).toHaveValue('');
    await expect(page.locator('#modern-result')).toBeEmpty();
  });

  test('AES block analysis works without a provider or key', async ({ page }) => {
    await page.goto('/#modern');
    await page.locator('#modern-lab').selectOption('aes');
    await page.locator('#modern-data').fill('ab'.repeat(32));
    await page.locator('#modern-run').click();
    await expect(page.locator('#modern-result')).toContainText('"repeated_blocks"');
    await expect(page.locator('#modern-result')).toContainText('do not prove AES or ECB');
  });

  test('Enigma example matches a known answer', async ({ page }) => {
    await page.goto('/#modern');
    await page.locator('#modern-lab').selectOption('enigma');
    await page.locator('#modern-example').click();
    await page.locator('#modern-run').click();
    await expect(page.locator('#modern-result')).toContainText('"output": "ILBDAAMTAZ"');
    await expect(page.locator('#modern-result')).toContainText('Historical Enigma I');
  });

  test('unsafe RSA JSON numbers are rejected before making a request', async ({ page }) => {
    let requested = false;
    await page.route('**/api/modern', (route) => { requested = true; return route.abort(); });
    await page.goto('/#modern');
    await page.locator('#modern-keys').fill('[{"n": 9007199254740993, "e": 3}]');
    await page.locator('#modern-run').click();
    await expect(page.locator('#modern-status')).toContainText('quote it as a decimal or hex string');
    expect(requested).toBe(false);
  });
});
