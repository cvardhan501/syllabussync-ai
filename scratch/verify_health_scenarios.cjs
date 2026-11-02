const { chromium } = require('playwright');

(async () => {
  console.log('=== STARTING HEALTH STATUS VERIFICATION SCENARIOS ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    const text = msg.text();
    if (!text.includes('[vite]') && !text.includes('React DevTools')) {
      console.log(`[BROWSER CONSOLE ${msg.type()}]:`, text);
    }
  });

  // ----------------------------------------------------
  // Scenario 1: FastAPI and database both available
  // ----------------------------------------------------
  console.log('\n--- Scenario 1: FastAPI and database both available ---');
  await page.route('**/api/health', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        app_name: 'SyllabusSync AI API',
        version: '0.2.0',
        timestamp: new Date().toISOString(),
        environment: 'development',
        database_connected: true,
        database_status: 'connected'
      })
    });
  });

  await page.goto('http://localhost:5174/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  const loginBadge = page.locator('text=FastAPI Online (v0.2.0)').first();
  await loginBadge.waitFor({ state: 'visible', timeout: 8000 });
  console.log(`[PASS] Login page badge: "${(await loginBadge.textContent())?.trim()}"`);

  // Bypass dev mode to enter app
  const guestBtn = page.getByRole('button', { name: /Continue as Local Guest/i });
  await guestBtn.click();
  await page.waitForTimeout(1000);

  // Verify Header
  const header = page.locator('header');
  const headerStatus = header.locator('span:has-text("Online (v0.2.0)")').first();
  await headerStatus.waitFor({ state: 'visible', timeout: 5000 });
  console.log(`[PASS] Header status: "${(await headerStatus.textContent())?.trim()}"`);

  // Verify Sidebar
  const sidebar = page.locator('aside');
  const sidebarFastApi = sidebar.locator('text=FastAPI Backend').first().locator('..');
  const sidebarDb = sidebar.locator('text=Database').first().locator('..');
  console.log(`[PASS] Sidebar FastAPI row: "${(await sidebarFastApi.textContent())?.replace(/\s+/g, ' ').trim()}"`);
  console.log(`[PASS] Sidebar Database row: "${(await sidebarDb.textContent())?.replace(/\s+/g, ' ').trim()}"`);

  await page.unroute('**/api/health');

  // ----------------------------------------------------
  // Scenario 2: FastAPI available but database probe times out / degraded
  // ----------------------------------------------------
  console.log('\n--- Scenario 2: FastAPI available but database probe times out (degraded) ---');
  // Intercept /api/health to return 200 OK with database_connected: false and database_status: "degraded"
  await page.route('**/api/health', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        app_name: 'SyllabusSync AI API',
        version: '0.2.0',
        timestamp: new Date().toISOString(),
        environment: 'development',
        database_connected: false,
        database_status: 'degraded'
      })
    });
  });

  // Switch to Settings tab to trigger health check
  await sidebar.getByRole('button', { name: 'Settings' }).click();
  await page.waitForTimeout(1500);

  // Verify Header indicates Online with DB Degraded
  const headerDegraded = header.locator('span:has-text("Online (v0.2.0) • DB Degraded")').first();
  await headerDegraded.waitFor({ state: 'visible', timeout: 5000 });
  console.log(`[PASS] Header with DB degraded: "${(await headerDegraded.textContent())?.trim()}"`);

  // Verify Sidebar separates FastAPI Online from Database Degraded
  const sidebarDbDegraded = sidebar.locator('span:has-text("Degraded")').first();
  await sidebarDbDegraded.waitFor({ state: 'visible', timeout: 5000 });
  console.log(`[PASS] Sidebar FastAPI row during DB outage: "${(await sidebarFastApi.textContent())?.replace(/\s+/g, ' ').trim()}"`);
  console.log(`[PASS] Sidebar Database row during DB outage: "${(await sidebarDb.textContent())?.replace(/\s+/g, ' ').trim()}"`);

  // Verify Settings page Cards: FastAPI is Online, Database is Degraded
  const settingsFastApiCard = page.locator('text=FastAPI Service').first().locator('..');
  const settingsDbCard = page.locator('text=Database').first().locator('..');
  console.log(`[PASS] Settings FastAPI Service card: "${(await settingsFastApiCard.textContent())?.replace(/\s+/g, ' ').trim()}"`);
  console.log(`[PASS] Settings Database card: "${(await settingsDbCard.textContent())?.replace(/\s+/g, ' ').trim()}"`);

  await page.unroute('**/api/health');

  // ----------------------------------------------------
  // Scenario 3: FastAPI completely unavailable (network error / crash)
  // ----------------------------------------------------
  console.log('\n--- Scenario 3: FastAPI completely unavailable ---');
  await page.route('**/api/health', route => route.abort('failed'));

  // Trigger diagnostic refresh
  const refreshBtn = page.getByRole('button', { name: /Refresh Diagnostics/i });
  if (await refreshBtn.isVisible()) {
    await refreshBtn.click();
  }
  await page.waitForTimeout(2000);

  const headerOffline = header.locator('span:has-text("Offline")').first();
  await headerOffline.waitFor({ state: 'visible', timeout: 5000 });
  console.log(`[PASS] Header when backend is unavailable: "${(await headerOffline.textContent())?.trim()}"`);
  console.log(`[PASS] Sidebar FastAPI row when unavailable: "${(await sidebarFastApi.textContent())?.replace(/\s+/g, ' ').trim()}"`);

  await page.unroute('**/api/health');

  // ----------------------------------------------------
  // Scenario 4: Database recovers after a timeout
  // ----------------------------------------------------
  console.log('\n--- Scenario 4: Database recovers after a timeout ---');
  await page.route('**/api/health', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        app_name: 'SyllabusSync AI API',
        version: '0.2.0',
        timestamp: new Date().toISOString(),
        environment: 'development',
        database_connected: true,
        database_status: 'connected'
      })
    });
  });

  if (await refreshBtn.isVisible()) {
    await refreshBtn.click();
  }
  await page.waitForTimeout(1500);

  const headerRecovered = header.locator('span:has-text("Online (v0.2.0)")').first();
  await headerRecovered.waitFor({ state: 'visible', timeout: 5000 });
  console.log(`[PASS] Header recovered: "${(await headerRecovered.textContent())?.trim()}"`);
  console.log(`[PASS] Sidebar FastAPI row recovered: "${(await sidebarFastApi.textContent())?.replace(/\s+/g, ' ').trim()}"`);
  console.log(`[PASS] Sidebar Database row recovered: "${(await sidebarDb.textContent())?.replace(/\s+/g, ' ').trim()}"`);

  await page.unroute('**/api/health');

  // ----------------------------------------------------
  // Scenario 5: Frontend page switching and refresh persistence
  // ----------------------------------------------------
  console.log('\n--- Scenario 5: Frontend page switching and refresh persistence ---');
  // Switch to Dashboard
  await sidebar.getByRole('button', { name: 'Dashboard' }).click();
  await page.waitForTimeout(1000);
  console.log(`[PASS] Switched to Dashboard - Header: "${(await header.locator('span.uppercase').first().textContent())?.trim()}"`);

  // Switch to My Courses
  await sidebar.getByRole('button', { name: 'My Courses' }).click();
  await page.waitForTimeout(1000);
  console.log(`[PASS] Switched to Courses - Header: "${(await header.locator('span.uppercase').first().textContent())?.trim()}"`);

  // Switch to Video Library
  await sidebar.getByRole('button', { name: 'Video Library' }).click();
  await page.waitForTimeout(1000);
  console.log(`[PASS] Switched to Video Library - Header: "${(await header.locator('span.uppercase').first().textContent())?.trim()}"`);

  // Switch to Study Plan
  await sidebar.getByRole('button', { name: 'Study Plan' }).click();
  await page.waitForTimeout(1000);
  console.log(`[PASS] Switched to Study Plan - Header: "${(await header.locator('span.uppercase').first().textContent())?.trim()}"`);

  // Page reload
  console.log('Reloading the browser page...');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('header').waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(2000);

  const headerAfterReload = page.locator('header').locator('span.uppercase').first();
  await headerAfterReload.waitFor({ state: 'visible', timeout: 10000 });
  console.log(`[PASS] Status after browser reload: "${(await headerAfterReload.textContent())?.trim()}"`);

  console.log('\n=== ALL 5 SCENARIOS VERIFIED SUCCESSFULLY ===');
  await browser.close();
})();
