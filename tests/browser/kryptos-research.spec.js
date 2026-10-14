const {test,expect}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../../kryptos-app');
// Exercise the actual standalone app on the existing test origin, without
// requiring a second server or a production deployment.
async function openResearch(page){
  const allowed=new Set(['index.html','styles.css','archive.css','research.css','paradigm.js','data.js','research-engine.js','research.js','app.js','unsolved-archive.js','architecture.svg']);
  await page.route('**/research-app/**',route=>{
    const file=path.basename(new URL(route.request().url()).pathname);
    if(!allowed.has(file))return route.fulfill({status:404,body:'Not found'});
    const type={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml'}[path.extname(file)];
    return route.fulfill({contentType:type,body:fs.readFileSync(path.join(root,file))});
  });
  page.on('dialog',dialog=>dialog.accept());
  await page.goto('/research-app/index.html');
  await expect(page.locator('#research-source')).toHaveValue('PK1');
  await expect(page.locator('#research-update-dialog')).toBeVisible();
  await expect(page.locator('#research-update-dialog')).toContainText('21-stage PK10');
  await page.locator('#research-close-updates').click();
}

test('dedicated mode reproduces every PK reference with explicit separate labels',async({page})=>{
  await openResearch(page);
  await expect(page.locator('#research-mode')).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('kryptos.research.notebook.v1'))).toBeNull();
  for(let n=1;n<=10;n++){
    await page.locator('#research-source').selectOption(`PK${n}`);
    await page.locator('#research-run').click();
    await expect(page.locator('#research-corpus')).toContainText(`Verified corpus match · PK${n}`);
    await expect(page.locator('#research-verdict')).toHaveText('Reproduced decryption');
    await expect(page.locator('#research-agreement')).toContainText('100.00%');
  }
  await expect(page.locator('#research-steps > .research-step')).toHaveCount(21);
  await expect(page.locator('#research-intermediates > details')).toHaveCount(21);
  await page.locator('#research-proposed').fill('WRONG');
  await expect(page.locator('#research-verdict')).toBeEmpty();
  await page.locator('#research-run').click();
  await expect(page.locator('#research-verdict')).toHaveText('Research hypothesis');
  await expect(page.locator('#research-corpus')).toContainText('Verified corpus match');
});

test('hypotheses persist only on Save and compare across families with evidence and objections',async({page})=>{
  await openResearch(page);
  await page.locator('#research-save').click();
  await page.locator('#research-name').fill('Alternative <img src=x onerror=alert(1)>');
  await page.locator('#research-proposed').fill(await page.locator('#research-original').inputValue());
  await page.locator('#research-steps [data-field="method"]').selectOption('caesar');
  await page.locator('#research-steps [data-field="key"]').fill('0');
  await page.locator('#research-evidence').fill('Arithmetically reproducible identity transform');
  await page.locator('#research-objections').fill('Not the documented reading; no independent confirmation');
  await page.locator('#research-save').click();
  await expect(page.locator('#research-saved tr')).toHaveCount(2);
  await expect(page.locator('#research-saved img')).toHaveCount(0);
  await expect(page.locator('#research-reference-agreement')).toContainText('does not equal');
  await page.locator('#research-compare').click();
  await expect(page.locator('#research-compare-summary')).toContainText('no independent confirmation');
  await expect(page.locator('#research-compare-summary')).toContainText('Alternative <img');
  await expect(page.locator('#research-comparison tr').first()).toBeVisible();
  await page.reload();
  await expect(page.locator('#research-saved tr')).toHaveCount(2);
  await page.locator('#research-saved tr').last().getByRole('button',{name:'Load',exact:true}).click();
  await expect(page.locator('#research-objections')).toHaveValue('Not the documented reading; no independent confirmation');
});

test('report downloads are reproducible; forged imported statuses cannot upgrade hypotheses',async({page})=>{
  await openResearch(page);
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#research-export').click()]);
  const report=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  expect(report.schema).toBe('kryptos-research-report/v1');
  expect(report.intermediates).toHaveLength(1);
  expect(report.original_text).toBe(report.hypothesis.original);
  expect(report.verification.reproduced).toBe(true);
  report.hypothesis.proposed='FORGED';report.verification={label:'Verified corpus match',reproduced:true};report.intermediates=[{output:'FORGED'}];
  await page.locator('#research-import').setInputFiles({name:'forged.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(report))});
  await expect(page.locator('#research-verdict')).toHaveText('Research hypothesis');
  await expect(page.locator('#research-output')).not.toHaveText('FORGED');
  await expect(page.locator('#research-status')).toContainText('recomputed locally');
});

test('custom K4 input uses clue constraints without a corpus or full-solution claim',async({page})=>{
  await openResearch(page);
  await page.locator('#research-source').selectOption('K4');
  await page.locator('#research-proposed').fill('EASTNORTHEASTBERLINCLOCK');
  await page.locator('#research-run').click();
  await expect(page.locator('#research-verdict')).toHaveText('Research hypothesis');
  await expect(page.locator('#research-corpus')).toContainText('No verified corpus match');
  await expect(page.locator('#research-constraints')).toContainText('does not agree / missing');
  expect(await page.locator('#research-source option[value="K2"]').isDisabled()).toBe(true);
  expect(await page.locator('#research-source option[value="K3"]').isDisabled()).toBe(true);
});
