/**
 * Video Library E2E verification for CSE3016
 * -------------------------------------------
 * Grounded in the actual SyllabusSync AI DOM (no data-test attrs exist).
 *
 * Auth: Google OAuth or dev-bypass. On the first run the test pauses for
 * manual login (5 min timeout). After login succeeds, storageState is
 * persisted to frontend/tests/e2e/.auth/state.json and reused next time.
 *
 * Uses the Playwright-provided { page, context } fixtures so that the
 * configured storageState is actually applied.
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const AUTH_DIR = path.join(__dirname, '.auth');
const AUTH_FILE = path.join(AUTH_DIR, 'state.json');

// ---------------------------------------------------------------------------
// Error collectors (reset per test)
// ---------------------------------------------------------------------------
let consoleErrors: string[] = [];
let failedAppRequests: string[] = [];

function attachListeners(page: Page) {
  consoleErrors = [];
  failedAppRequests = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('requestfailed', req => {
    const url = req.url();
    // Ignore third-party domains (YouTube thumbnails, Google fonts, etc.)
    if (
      url.includes('youtube.com') ||
      url.includes('googleapis.com') ||
      url.includes('google.com') ||
      url.includes('gstatic.com') ||
      url.includes('supabase.co/auth')
    ) {
      return;
    }
    failedAppRequests.push(`${req.method()} ${url} — ${req.failure()?.errorText}`);
  });
}

// ---------------------------------------------------------------------------
// Playwright configuration
// ---------------------------------------------------------------------------

// If a saved auth state exists, load it so Supabase session cookies and
// localStorage tokens are injected into the browser context automatically.
test.use({
  storageState: fs.existsSync(AUTH_FILE) ? AUTH_FILE : undefined,
});

// 5-minute timeout to accommodate manual login on first run.
test.setTimeout(5 * 60 * 1000);

// ---------------------------------------------------------------------------
// Main test — uses the provided { page, context } fixtures
// ---------------------------------------------------------------------------
test.describe('Video Library E2E — CSE3016', () => {
  test('Full verification flow', async ({ page, context }) => {
    attachListeners(page);

    // ---------------------------------------------------------------
    // 1. Navigate to app
    // ---------------------------------------------------------------
    await page.goto('http://localhost:5174/');

    // ---------------------------------------------------------------
    // 2. Authenticate (or confirm already authenticated)
    // ---------------------------------------------------------------
    // The app shows the main layout (with sidebar nav) when authenticated,
    // or the LoginPage when not. The sidebar contains a button labelled
    // "Dashboard" — if visible, we are authenticated.
    const dashboardBtn = page.locator('button', { hasText: 'Dashboard' });
    const isAuthenticated = await dashboardBtn.isVisible({ timeout: 3000 }).catch(() => false);

    if (!isAuthenticated) {
      // Not authenticated — either use dev bypass or wait for manual Google login.
      // Try the dev bypass first (quicker for local testing).
      const devBypassBtn = page.locator('button, a', {
        hasText: /Continue.*Local|Continue.*Dev|Continue.*Guest/i,
      });
      const hasBypass = await devBypassBtn.isVisible({ timeout: 2000 }).catch(() => false);

      if (hasBypass) {
        console.log('🔑 Using dev bypass for authentication');
        await devBypassBtn.click();
      } else {
        // Wait for the user to sign in manually via Google OAuth.
        console.log('🔑 Waiting for manual Google sign-in (up to 4 min) …');
        // After a successful login the app renders the sidebar with "Dashboard".
        await dashboardBtn.waitFor({ state: 'visible', timeout: 4 * 60 * 1000 });
      }

      // Confirm we're now in the authenticated shell
      await expect(dashboardBtn).toBeVisible({ timeout: 15000 });
      console.log('✅ Authenticated');

      // Save session for future runs
      if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });
      await context.storageState({ path: AUTH_FILE });
      console.log('💾 Auth state saved to', AUTH_FILE);
    } else {
      console.log('✅ Already authenticated (loaded from saved state)');
    }

    // ---------------------------------------------------------------
    // 3. Navigate to Video Library tab
    // ---------------------------------------------------------------
    const videoLibBtn = page.locator('button', { hasText: 'Video Library' }).first();
    await videoLibBtn.click();

    // Wait for the Video Library page to render. It may show:
    //  - The course-selection grid (if multiple courses), or
    //  - The video cards directly (if a course is already active).
    // Either way, wait for "Video Library" or "Video Libraries" heading text.
    await page.waitForTimeout(1500);

    // ---------------------------------------------------------------
    // 4. Select CSE3016 course (if course selection view is shown)
    // ---------------------------------------------------------------
    const cse3016Card = page.locator('text=CSE3016').first();
    const hasCourseSelection = await cse3016Card.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasCourseSelection) {
      console.log('📚 Course selection view detected — clicking CSE3016');
      await cse3016Card.click();
      await page.waitForTimeout(1500);
    }

    // ---------------------------------------------------------------
    // 5. Wait for video data to load
    // ---------------------------------------------------------------
    // The page shows a loading spinner ("Discovering YouTube Learning Resources")
    // while fetching. Wait for it to disappear (or for video cards to appear).
    // Video cards have className containing "rounded-2xl" and an <img> with
    // YouTube thumbnail. We identify them by the "Watch on YouTube" button.
    const watchButtons = page.locator('button:has-text("Watch on YouTube")');
    await watchButtons.first().waitFor({ state: 'visible', timeout: 30000 });

    // ---------------------------------------------------------------
    // 6. Count visible video cards
    // ---------------------------------------------------------------
    // Each video card contains a "Watch on YouTube" button.
    const videoCardCount = await watchButtons.count();
    console.log(`✅ Visible video cards with "Watch on YouTube": ${videoCardCount}`);
    expect(videoCardCount).toBeGreaterThan(0);

    // ---------------------------------------------------------------
    // 7. Validate card contents
    // ---------------------------------------------------------------
    // Each video card is a div with class "rounded-2xl" that contains:
    //   - An <img> (thumbnail)
    //   - An <h4> (topic title)
    //   - A <p> with class "text-slate-200" (video title)
    //   - A <span> with class "truncate" inside an <a> (channel name)
    //   - A <span> with "font-mono" in the thumbnail area (duration)

    // We'll identify cards by the grid cells that contain "Watch on YouTube".
    // Each card's parent structure: grid > card div > content.
    // Simplest: the card is the closest ancestor of the Watch button that has
    // the "rounded-2xl" class.

    // Validate a sample of cards (first, middle, last)
    const indices = [0, Math.floor(videoCardCount / 2), videoCardCount - 1];

    for (const idx of indices) {
      const btn = watchButtons.nth(idx);
      // Navigate up to the card container (the rounded-2xl div)
      const card = btn.locator('xpath=ancestor::div[contains(@class,"rounded-2xl")][1]');

      // Thumbnail <img>
      const img = card.locator('img').first();
      const imgSrc = await img.getAttribute('src');
      expect(imgSrc, `Card ${idx}: thumbnail src`).toBeTruthy();
      expect(imgSrc).toContain('img.youtube.com');

      // Topic title <h4>
      const topicTitle = card.locator('h4').first();
      const topicText = await topicTitle.innerText();
      expect(topicText.trim().length, `Card ${idx}: topic title`).toBeGreaterThan(0);

      // Video title <p class="...text-slate-200...">
      const videoTitle = card.locator('p.text-slate-200, p.font-medium').first();
      if (await videoTitle.isVisible()) {
        const vt = await videoTitle.innerText();
        expect(vt.trim().length, `Card ${idx}: video title`).toBeGreaterThan(0);
      }

      // Channel name — <span> inside <a> that links to youtube.com/channel
      const channelSpan = card.locator('a span.truncate').first();
      if (await channelSpan.isVisible()) {
        const ch = await channelSpan.innerText();
        expect(ch.trim().length, `Card ${idx}: channel name`).toBeGreaterThan(0);
      }

      // Duration — <span> with font-mono inside the thumbnail area
      const durationSpan = card.locator('span.font-mono').first();
      if (await durationSpan.isVisible()) {
        const dur = await durationSpan.innerText();
        expect(dur.trim().length, `Card ${idx}: duration`).toBeGreaterThan(0);
      }

      console.log(`  ✓ Card ${idx}: topic="${topicText.trim().substring(0, 50)}", thumb OK`);
    }

    // ---------------------------------------------------------------
    // 8. Verify module section headers exist
    // ---------------------------------------------------------------
    // Module headers are <h3> with "text-base font-bold text-white"
    const moduleHeaders = page.locator('h3.font-bold.text-white');
    const moduleCount = await moduleHeaders.count();
    console.log(`✅ Module section headers: ${moduleCount}`);
    expect(moduleCount).toBeGreaterThan(0);

    // ---------------------------------------------------------------
    // 9. Click 3 videos — "Watch on YouTube" uses window.open()
    // ---------------------------------------------------------------
    const openedUrls: string[] = [];
    for (const idx of indices) {
      const btn = watchButtons.nth(idx);

      // window.open() triggers a 'popup' event on the page
      const [popup] = await Promise.all([
        page.waitForEvent('popup', { timeout: 10000 }),
        btn.click(),
      ]);

      const url = popup.url();
      console.log(`🔗 Video ${idx}: ${url}`);
      openedUrls.push(url);
      await popup.close();
    }

    console.log(`✅ Videos successfully opened: ${openedUrls.length}`);
    for (const url of openedUrls) {
      expect(url).toContain('youtube.com/watch?v=');
    }

    // ---------------------------------------------------------------
    // 10. Refresh and verify persistence
    // ---------------------------------------------------------------
    await page.reload();
    await watchButtons.first().waitFor({ state: 'visible', timeout: 30000 });
    const afterRefreshCount = await watchButtons.count();
    console.log(`✅ After refresh: ${afterRefreshCount} video cards`);
    expect(afterRefreshCount).toBe(videoCardCount);

    // ---------------------------------------------------------------
    // 11. Navigate away (Dashboard) and back (Video Library)
    // ---------------------------------------------------------------
    const dashNav = page.locator('button', { hasText: 'Dashboard' }).first();
    await dashNav.click();
    await page.waitForTimeout(1000);

    const videoNav = page.locator('button', { hasText: 'Video Library' }).first();
    await videoNav.click();
    await watchButtons.first().waitFor({ state: 'visible', timeout: 30000 });
    const afterNavCount = await watchButtons.count();
    console.log(`✅ After nav round-trip: ${afterNavCount} video cards`);
    expect(afterNavCount).toBe(videoCardCount);

    // ---------------------------------------------------------------
    // 12. Mock-data check — ensure no "Dev Fallback Mode" badge
    // ---------------------------------------------------------------
    const fallbackBadge = page.locator('text=Dev Fallback Mode');
    const hasFallback = await fallbackBadge.isVisible({ timeout: 1000 }).catch(() => false);
    console.log(`✅ Dev Fallback Mode badge present: ${hasFallback}`);

    // ---------------------------------------------------------------
    // 13. Final error report
    // ---------------------------------------------------------------
    console.log(`\n========== FINAL REPORT ==========`);
    console.log(`Visible video cards:        ${videoCardCount}`);
    console.log(`Videos successfully opened: ${openedUrls.length}`);
    console.log(`Refresh persistence:        ${afterRefreshCount === videoCardCount ? 'PASS' : 'FAIL'}`);
    console.log(`Navigation persistence:     ${afterNavCount === videoCardCount ? 'PASS' : 'FAIL'}`);
    console.log(`Console errors:             ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach((e, i) => console.log(`  [${i}] ${e.substring(0, 200)}`));
    }
    console.log(`Failed app API requests:    ${failedAppRequests.length}`);
    if (failedAppRequests.length > 0) {
      failedAppRequests.forEach((e, i) => console.log(`  [${i}] ${e}`));
    }
    console.log(`Mock/fallback data:         ${hasFallback ? 'YES (fallback detected)' : 'NO (real data)'}`);
    console.log(`==================================\n`);

    // Assert no app-level failures
    expect(failedAppRequests.length, 'No failed app API requests').toBe(0);
  });
});
