const { chromium } = require('playwright');

async function testDeleteCourseUI() {
  console.log('--- Testing Delete Course in UI without Page Refresh ---');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  const BASE_URL = 'http://localhost:5174';
  const API_URL = 'http://127.0.0.1:8000';

  // 1. Create a course to delete
  const testCourseName = `E2E Deletion Target ${Date.now()}`;
  const createRes = await fetch(`${API_URL}/api/courses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course_name: testCourseName,
      course_code: 'DEL101',
      language: 'English',
      lesson_style: 'In-depth',
      daily_study_availability: '1-2 hours',
      daily_target_minutes: 60
    })
  });
  const createdCourse = await createRes.json();
  console.log(`Created test course: id=${createdCourse.id}, name="${createdCourse.course_name}"`);

  // 2. Open frontend
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  const guestBtn = page.locator('button:has-text("Continue as Local Guest")');
  if (await guestBtn.count() > 0) {
    console.log('Clicking Continue as Local Guest...');
    await guestBtn.click();
    await page.waitForTimeout(1000);
  }

  // 3. Navigate to Courses Page
  console.log('Navigating to My Courses tab...');
  const coursesTab = page.locator('button:has-text("My Courses")').first();
  await coursesTab.waitFor({ state: 'visible', timeout: 5000 });
  await coursesTab.click();
  await page.waitForTimeout(1500);

  // 4. Locate the card with testCourseName
  console.log(`Locating card with title "${testCourseName}"...`);
  const courseCard = page.locator(`text="${testCourseName}"`).locator('xpath=ancestor::div[contains(@class, "rounded-3xl")]').first();
  await courseCard.waitFor({ state: 'visible', timeout: 5000 });
  console.log('✓ Found course card on page.');

  // 5. Click the three dots menu on that card
  const menuButton = courseCard.locator('button[title="Course options"]');
  await menuButton.click();
  await page.waitForTimeout(500);

  // 6. Click "Delete Course"
  const deleteMenuItem = page.locator('button:has-text("Delete Course")');
  await deleteMenuItem.click();
  await page.waitForTimeout(500);

  // 7. Check modal is open
  const modal = page.locator('h3:has-text("Delete Course?")');
  await modal.waitFor({ state: 'visible', timeout: 5000 });
  console.log('✓ Delete Course confirmation modal appeared.');

  // 8. Click "Delete Permanently"
  const deleteBtn = page.locator('button:has-text("Delete Permanently")');
  console.log('Clicking Delete Permanently button...');
  await deleteBtn.click();

  // Wait 3 seconds and print what the button text and modal state is
  await page.waitForTimeout(3000);
  const isModalVisible = await modal.isVisible();
  const btnText = await page.locator('button:has-text("Delete")').allInnerTexts();
  console.log(`Modal visible: ${isModalVisible}, Buttons with 'Delete':`, btnText);

  await browser.close();
}

testDeleteCourseUI().catch((err) => {
  console.error('Test FAILED:', err);
  process.exit(1);
});
