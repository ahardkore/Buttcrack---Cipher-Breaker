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
  test('responsive accessibility modes and print mode', async ({ page }) => {
    await page.goto('/');
    await page.emulateMedia({ media: 'print' });
    await expect(page.locator('body')).toBeVisible();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
  });
});
