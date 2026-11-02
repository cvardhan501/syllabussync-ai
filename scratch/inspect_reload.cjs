const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('http://localhost:5174/', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  // Switch to study plan
  await page.locator('aside').getByRole('button', { name: 'Study Plan' }).click();
  await page.waitForTimeout(1000);

  console.log('Reloading...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  console.log('URL after reload:', page.url());
  console.log('Has header:', await page.locator('header').count());
  if (await page.locator('header').count() > 0) {
    console.log('Header text:', await page.locator('header').textContent());
  } else {
    console.log('Body text snippet:', (await page.locator('body').textContent()).slice(0, 300));
  }
  await browser.close();
})();

