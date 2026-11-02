const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:5174/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  // Switch tabs
  await page.locator('aside').getByRole('button', { name: 'Dashboard' }).click();
  await page.waitForTimeout(500);
  await page.locator('aside').getByRole('button', { name: 'Study Plan' }).click();
  await page.waitForTimeout(500);

  console.log('Reloading...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(500);
    const count = await page.locator('header').count();
    const text = count > 0 ? await page.locator('header').textContent() : 'NO HEADER';
    console.log(`[${i * 0.5}s] count=${count}, text=${JSON.stringify(text)}`);
  }
  await browser.close();
})();

