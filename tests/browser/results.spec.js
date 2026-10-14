const { test, expect } = require('@playwright/test');

function reportFixture(count = 10) {
  const candidates = Array.from({length: count}, (_, index) => ({
    plaintext: `A full candidate reading with historical uncertainty ${index}. ` + 'More than ninety characters of plaintext remain visible. '.repeat(5) + '<img src=x onerror=alert(1)>',
    cipher: 'caesar', cipher_title: 'Caesar (ROT-N)', family: 'shift',
    key: String(index + 1), key_type: 'shift 0–25', key_data: index + 1,
    parameters: {shift: index + 1, alphabet: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'},
    confidence: .9 - index * .002, fitness: -4.2, steps: [], notes: {},
    score: {words: .6, dictionary_assessed: true, sample_size: 120, words_found: ['historical', 'uncertainty'], start_quality: 1, ic: .066, chi_squared: 1.4, segmentation: -.9, confidence: .95},
    statistical_plausibility: {language_score: .95, is_probability: false},
    ranking: {rank: index + 1, gap_to_leader: index * .002, close_peers: [index ? 1 : 2], reasons: ['Language/evidence rank score determines this ordering.', 'Short-text evidence remains limited.']},
    verification: {status: 'not_checked', label: 'Not verified', independent_verification: false, detail: 'Statistical plausibility is not proof of intended plaintext.'},
  }));
  return {best: candidates[0], candidates, solved: true, confidence: .9, elapsed: .1, budget: 5, workers: 1, language: 'english', stats: {}, hypotheses: [], attacks: [], candidate_comparison: {search_mode: 'comparison', close_score_gap: .03, close_ranks: count > 1 ? [2] : []}};
}

async function openReport(page, report) {
  let requests = 0, submitted;
  await page.route('**/api/crack', route => {
    submitted = route.request().postDataJSON();
    requests += 1;
    return route.fulfill({json: {job: 'ranking-fixture'}});
  });
  await page.route('**/api/job/ranking-fixture', route => route.fulfill({json: {done: true, progress: [], report}}));
  await page.goto('/');
  await page.locator('#input').fill('Wklv lv d klvwrulfdo phvvdjh zlwk pdqb srvvleoh uhdglqjv.');
  await page.locator('#crack').click();
  await expect(page.locator('#result-card')).toBeVisible();
  return {requests: () => requests, submitted: () => submitted};
}

test('top ten readings expose evidence, close competitors and full safe plaintext', async ({page}) => {
  const network = await openReport(page, reportFixture());
  await expect(page.locator('.candidate-card')).toHaveCount(10);
  expect(network.submitted().compare).toBe(true);
  expect(network.submitted().candidates).toBe(10);
  await expect(page.locator('#verdict')).toHaveText('statistically strong — not proven');
  await expect(page.locator('#confidence-bar')).not.toHaveClass(/good/);
  await expect(page.locator('#candidate-summary')).toContainText('Close to the leader: #2');
  const first = page.locator('.candidate-card').first();
  await expect(first).toContainText('Family: shift');
  await expect(first).toContainText('Recovered / supplied key');
  await expect(first).toContainText('Why ranked here');
  await expect(first.locator('.candidate-plaintext')).toContainText('<img src=x onerror=alert(1)>');
  await expect(first.locator('img')).toHaveCount(0);
  await first.locator('summary').click();
  await expect(first).toContainText('historical · uncertainty');
  await expect(first).toContainText('"shift":1');
  await page.locator('#candidate-count').selectOption('5');
  await expect(page.locator('.candidate-card')).toHaveCount(5);
  expect(network.requests()).toBe(1);
});

test('a short list is explained and no candidates are fabricated', async ({page}) => {
  await openReport(page, reportFixture(1));
  await expect(page.locator('.candidate-card')).toHaveCount(1);
  await expect(page.locator('#candidate-summary')).toContainText('Fewer than five distinct readings');
  await expect(page.locator('.candidate-badge')).toHaveText('Not verified');
});
