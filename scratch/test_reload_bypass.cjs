const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:5174/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(500);

  console.log('dev_bypass after click:', await page.evaluate(() => localStorage.getItem('syllabussync_dev_bypass')));

  console.log('Reloading...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  console.log('dev_bypass after reload:', await page.evaluate(() => localStorage.getItem('syllabussync_dev_bypass')));
  console.log('Page has header:', await page.locator('header').count());
  console.log('Page has guest button:', await page.getByRole('button', { name: /Continue as Local Guest/i }).count());
  await browser.close();
})();

