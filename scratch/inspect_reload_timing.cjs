const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => console.log(`[CONSOLE]:`, msg.text()));

  await page.goto('http://localhost:5174/', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  console.log('Reloading...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  for (let i = 1; i <= 6; i++) {
    await page.waitForTimeout(1000);
    const text = await page.locator('header').textContent();
    console.log(`At ${i}s header text:`, text.replace(/\s+/g, ' ').trim());
  }
  await browser.close();
})();

