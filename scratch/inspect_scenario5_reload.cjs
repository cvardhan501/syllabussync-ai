const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:5174/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: /Continue as Local Guest/i }).click();
  await page.waitForTimeout(1000);

  // Switch to study plan
  await page.locator('aside').getByRole('button', { name: 'Study Plan' }).click();
  await page.waitForTimeout(1000);

  console.log('Reloading...');
  await page.reload();
  await page.waitForTimeout(3000);

  console.log('Current URL:', page.url());
  console.log('Body Text:', (await page.locator('body').textContent()).slice(0, 300));
  console.log('Header Count:', await page.locator('header').count());
  if (await page.locator('header').count() > 0) {
    console.log('Header Text:', await page.locator('header').textContent());
  }
  await browser.close();
})();

