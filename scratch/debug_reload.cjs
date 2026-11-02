const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => console.log(`[BROWSER ${msg.type()}]:`, msg.text()));
  page.on('requestfailed', req => console.log(`[FAILED]:`, req.url(), req.failure()?.errorText));

  await page.goto('http://localhost:5174/', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  console.log('Reloading page...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  console.log('Header text:', await page.locator('header').textContent());
  await browser.close();
})();

