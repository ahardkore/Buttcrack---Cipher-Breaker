const {test, expect} = require('@playwright/test');

test('spacing-aware strips count, invalidate, and report errors safely', async ({page}) => {
  await page.goto('/');
  await page.locator('#input').fill(' AB C\n\nXY  Z');
  await page.locator('#strip-column').fill('3');
  await page.locator('#strip-run').click();
  await expect(page.locator('#strip-rows tr')).toHaveCount(2);
  await expect(page.locator('#strip-rows tr').first()).toHaveText(/1\s*3\s*1\s*1\s*1/);
  await expect(page.locator('#strip-status')).toContainText('No outlier or solution');
  await page.locator('#strip-column').fill('4');
  await expect(page.locator('#strip-results')).toBeHidden();
  await page.locator('#strip-run').click();
  await expect(page.locator('#strip-results')).toBeVisible();
  await page.locator('#samples button').first().click();
  await expect(page.locator('#strip-results')).toBeHidden();
  await page.locator('#input').fill('A\tB');
  await page.locator('#strip-run').click();
  await expect(page.locator('#strip-status')).toContainText('tabs are not supported');
  await expect(page.locator('#strip-results')).toBeHidden();
});

test('stale counts are not displayed after edits', async ({page}) => {
  await page.route('**/api/strip-analysis', async route => {
    await page.locator('#input').fill('CHANGED');
    await route.fulfill({json: {guide_column: 1, rows: [{line: 1, letters: 1, before: 0, on: 1, after: 0}]}});
  });
  await page.goto('/');
  await page.locator('#input').fill('A');
  await page.locator('#strip-run').click();
  await expect(page.locator('#strip-status')).toContainText('count again');
  await expect(page.locator('#strip-results')).toBeHidden();
});
