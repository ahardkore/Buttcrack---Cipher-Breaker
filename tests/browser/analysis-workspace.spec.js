const {test, expect} = require('@playwright/test');

const ciphertext = 'LXFOPVEFRNHR';
function report() {
  const first = {plaintext: 'ATTACKATDAWN', cipher: 'vigenere', key: 'LEMON', key_data: 'LEMON', confidence: .9, fitness: -2, steps: []};
  const second = {...first, cipher: 'autokey', key: 'LEMON<img src=x onerror=alert(1)>', key_data: 'LEMON'};
  return {best: first, candidates: [first, second], confidence: .9, solved: false, elapsed: .1, budget: 5, workers: 1, language: 'english', stats: {}, attacks: [], hypotheses: []};
}

test('standalone diagnostics expose frequencies, IC, entropy and bounded repeats', async ({page}) => {
  await page.goto('/');
  await page.locator('#input').fill('ABCXABCYABC');
  await page.locator('#workspace-analyze').click();
  await expect(page.locator('#workspace-data')).toBeVisible();
  await expect(page.locator('.frequency-row')).toHaveCount(26);
  await expect(page.locator('#workspace-metrics')).toContainText('Index of coincidence');
  await expect(page.locator('#workspace-metrics')).toContainText('Entropy (bits / A–Z letter)');
  await expect(page.locator('#workspace-repeats')).toContainText('0, 4, 8');
  await expect(page.locator('#workspace-estimates')).toContainText('Short / unreliable sample');
  await expect(page.locator('#workspace-candidate')).toBeDisabled();
  await expect(page.locator('#workspace-status')).toContainText('No plaintext or key has been recovered');
});

test('candidate alignment uses submitted ciphertext and distinguishes manual hypotheses', async ({page}) => {
  await page.route('**/api/crack', route => route.fulfill({json: {job: 'workspace-test'}}));
  await page.route('**/api/job/workspace-test', async route => {
    await page.locator('#input').fill('EDITED AFTER THE SOLVE STARTED');
    await route.fulfill({json: {done: true, progress: [], report: report()}});
  });
  await page.goto('/');
  await page.locator('#input').fill(ciphertext);
  await page.locator('#crack').click();
  await expect(page.locator('#workspace-data')).toBeVisible();
  await expect(page.locator('#workspace-alignment')).toContainText(ciphertext);
  await expect(page.locator('#workspace-alignment')).toContainText('ATTACKATDAWN');
  await expect(page.locator('#workspace-alignment-note')).toContainText('12 displayed equations checked; 0 mismatches');
  await page.locator('#workspace-key-offset').fill('1');
  await page.locator('#workspace-apply').click();
  await expect(page.locator('#workspace-alignment-note')).toContainText('12 mismatches');
  await page.locator('#workspace-candidate').selectOption('1');
  await expect(page.locator('#workspace-alignment-note')).toContainText('Model: none');
  await expect(page.locator('#workspace-reported-key')).toContainText('<img src=x onerror=alert(1)>');
  await expect(page.locator('#analysis-workspace img')).toHaveCount(0);
  await page.locator('#workspace-alignment-model').selectOption('vigenere');
  await page.locator('#workspace-key').fill('LEMON');
  await page.locator('#workspace-apply').click();
  await expect(page.locator('#workspace-alignment-note')).toContainText('manual convention');
  await expect(page.locator('#workspace-alignment-note')).toContainText('0 mismatches');
  await page.locator('#workspace-analyze').click();
  await expect(page.locator('#workspace-candidate')).toBeDisabled();
  await expect(page.locator('#workspace-status')).toContainText('Ciphertext-only');
  await expect(page.locator('#workspace-key')).toHaveValue('');
});

test('local analysis errors leave solver controls usable and do not render markup', async ({page}) => {
  await page.route('**/api/analysis-workspace', route => route.fulfill({status: 429, json: {error: '<img src=x> busy'}}));
  await page.goto('/');
  await page.locator('#input').fill(ciphertext);
  await page.locator('#workspace-analyze').click();
  await expect(page.locator('#workspace-status')).toContainText('<img src=x> busy');
  await expect(page.locator('#workspace-status img')).toHaveCount(0);
  await expect(page.locator('#workspace-data')).toBeHidden();
  await expect(page.locator('#crack')).toBeEnabled();
});
