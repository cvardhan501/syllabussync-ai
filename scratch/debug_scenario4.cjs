const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => console.log('[CONSOLE]', msg.text()));
  page.on('request', req => {
    if (req.url().includes('health')) console.log('[REQ]', req.url());
  });
  page.on('response', resp => {
    if (resp.url().includes('health')) console.log('[RESP]', resp.url(), resp.status());
  });

  await page.goto('http://localhost:5174/');
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  // Go to settings
  await page.locator('aside').getByRole('button', { name: 'Settings' }).click();
  await page.waitForTimeout(1500);

  console.log('--- Simulating Offline ---');
  await page.route('**/api/health', route => route.abort('failed'));
  await page.getByRole('button', { name: /Refresh Diagnostics/i }).click();
  await page.waitForTimeout(2000);
  console.log('Header text during outage:', await page.locator('header').textContent());

  console.log('--- Unrouting and recovering ---');
  await page.unroute('**/api/health');
  await page.getByRole('button', { name: /Refresh Diagnostics/i }).click();
  for (let i = 1; i <= 5; i++) {
    await page.waitForTimeout(1000);
    console.log(`At ${i}s header text:`, await page.locator('header').textContent());
  }
  await browser.close();
})();

