const {test,expect}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../../ventures/cipher-solver-web');
async function openSite(page,url='index.html'){
  const allowed=new Set(fs.readdirSync(root).filter(f=>/\.(html|css|js|svg)$/.test(f)));
  await page.context().route('**/public-app/**',route=>{
    const file=path.basename(new URL(route.request().url()).pathname);
    if(!allowed.has(file))return route.fulfill({status:404,body:'Not found'});
    const type={'.html':'text/html','.css':'text/css','.js':'application/javascript','.svg':'image/svg+xml'}[path.extname(file)];
    return route.fulfill({contentType:type,body:fs.readFileSync(path.join(root,file))});
  });
  await page.route('**/*googlesyndication*',route=>route.abort());
  page.on('dialog',dialog=>dialog.accept());
  await page.goto(`/public-app/${url}`);
}

test('mobile solver is prominent; details stay folded and page has no horizontal overflow',async({page})=>{
  await page.setViewportSize({width:375,height:812});await openSite(page);
  await expect(page.locator('#ciphertext')).toBeVisible();
  const solve=await page.locator('#go').boundingBox();expect(solve.y+solve.height).toBeLessThan(812);expect(solve.height).toBeGreaterThanOrEqual(44);
  expect(await page.locator('#advanced-settings').evaluate(e=>e.open)).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.locator('#ciphertext').fill('Wkh frxqflo ri Yhqlfh kdv ghfuhhg wkdw doo phufkdqw yhvvhov pxvw sdb wkh qhz kduerxu wda ehiruh hqwhulqj wkh odjrrq');
  await page.locator('#go').click();await expect(page.locator('#output > div .plaintext').first()).toContainText(/council/i);
  expect(await page.locator('.candidate-details').first().evaluate(e=>e.open)).toBe(false);
  expect(await page.evaluate(()=>localStorage.getItem('buttcrack.browser.investigations.v1'))).toBeNull();
  await page.locator('.candidate-details summary').first().click();await expect(page.locator('.candidate-details').first()).toContainText('Key');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('wiki action preselects actual method and full worked example without auto-solving',async({page})=>{
  await openSite(page,'playfair-cipher-wiki.html');
  await page.getByRole('link',{name:'Try this cipher →',exact:true}).click();
  await expect(page.locator('#solver-method')).toHaveValue('playfair');
  await expect(page.locator('#ciphertext')).not.toHaveValue('');await expect(page.locator('#output')).toBeEmpty();
  await page.locator('#go').click();await expect(page.locator('#output')).toContainText('Worked example reference — not a new solve');
  await page.locator('#ciphertext').fill('UNRELATED CIPHERTEXT');await page.locator('#go').click();await expect(page.locator('#output')).toContainText('No candidate returned');
});

test('named device-only attempts save explicitly, compare and restore without another search',async({page})=>{
  await openSite(page,'index.html?cipher=caesar&example=caesar#solver');
  await page.locator('#go').click();await expect(page.locator('#save-attempt')).toBeEnabled();
  await page.locator('#local-history > summary').click();await page.locator('#investigation-name').fill('Archive letter <img src=x>');await page.locator('#save-attempt').click();
  await page.locator('#advanced-settings > summary').click();await page.locator('#solver-method').selectOption('atbash');await page.locator('#solver-key').fill('');await page.locator('#go').click();await expect(page.locator('#save-attempt')).toBeEnabled();await page.locator('#save-attempt').click();
  await expect(page.locator('.saved-attempt')).toHaveCount(2);await expect(page.locator('#local-history img')).toHaveCount(0);
  await page.locator('#compare-attempts').click();await expect(page.locator('#attempt-comparison')).toContainText('Attempt B');
  await page.reload();await expect(page.locator('#save-attempt')).toBeDisabled();await page.locator('#local-history > summary').click();await page.locator('#investigation-select').selectOption({index:1});await expect(page.locator('.saved-attempt')).toHaveCount(2);
  await page.locator('.saved-attempt').first().getByRole('button',{name:'Restore text, settings & result'}).click();await expect(page.locator('#output')).toContainText('Restored local snapshot');await expect(page.locator('#stop')).toBeHidden();await expect(page.locator('#solver-method')).toHaveValue('caesar');
});
