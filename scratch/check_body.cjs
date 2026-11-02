const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => console.log('[CONSOLE]', msg.text()));
  page.on('request', req => console.log('[REQ]', req.url()));
  page.on('requestfailed', req => console.log('[REQ FAILED]', req.url(), req.failure()?.errorText));
  page.on('response', resp => console.log('[RESP]', resp.url(), resp.status()));

  await page.goto('http://localhost:5174/');
  await page.waitForTimeout(4000);
  console.log('TEXT:\n', await page.locator('body').textContent());
  await browser.close();
})();
