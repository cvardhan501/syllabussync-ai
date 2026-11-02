const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:5174');
  await page.waitForTimeout(2000);
  const btns = await page.$$eval('button', els => els.map(e => e.textContent.trim().replace(/\s+/g, ' ')));
  console.log('Buttons on page:', btns);
  const headings = await page.$$eval('h1, h2, h3', els => els.map(e => e.textContent.trim()));
  console.log('Headings:', headings);
  await browser.close();
})();

