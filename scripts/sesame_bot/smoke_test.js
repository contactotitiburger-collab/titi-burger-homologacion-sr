import { chromium } from 'playwright';

const SCREENSHOT_PATH = '/tmp/sesame_smoke.png';
const URL = 'https://app.sesametime.com/login';

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    console.log(`Navigating to ${URL}...`);
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
    console.log(`Page title: ${await page.title()}`);
    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
    console.log(`Screenshot saved to ${SCREENSHOT_PATH}`);
  } catch (err) {
    console.error('ERROR:', err.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
