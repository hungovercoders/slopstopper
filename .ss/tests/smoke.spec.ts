import { test, expect } from '@playwright/test';

/**
 * Smoke Tests for Production/Staging Reliability
 *
 * These tests verify critical functionality on live environments.
 * Run with: SMOKE_TEST_URL=https://your-site.netlify.app npm run test:smoke
 *
 * Or via task: task ss:reliability:smoke -- https://your-site.netlify.app
 */

const targetUrl = process.env.SMOKE_TEST_URL || process.env.BASE_URL || 'http://localhost:8080';

test.describe('Smoke Tests', () => {
  test.use({ baseURL: targetUrl });

  test('homepage loads successfully', async ({ page }) => {
    const response = await page.goto('/');

    expect(response!.status()).toBe(200);

    await expect(page).toHaveTitle('SlopStopper');
  });

  test('features page loads successfully', async ({ page }) => {
    const response = await page.goto('/features.html');

    expect(response!.status()).toBe(200);
    await expect(page).toHaveTitle('Features');
  });

  test('tools page loads successfully', async ({ page }) => {
    const response = await page.goto('/tools.html');

    expect(response!.status()).toBe(200);
    await expect(page).toHaveTitle('Tools');
  });

  test('basic navigation works', async ({ page }) => {
    await page.goto('/');

    const featuresLink = page.locator('#nav-features');
    const toolsLink = page.locator('#nav-tools');

    await expect(featuresLink).toBeVisible();
    await expect(toolsLink).toBeVisible();

    await featuresLink.click();
    await expect(page).toHaveURL(/.*features(\.html)?/);
    await expect(page).toHaveTitle('Features');
  });

  test('static assets load correctly', async ({ page }) => {
    await page.goto('/');

    const stylesheets = await page.locator('link[rel="stylesheet"]').count();
    expect(stylesheets).toBeGreaterThan(0);

    const errors: Error[] = [];
    page.on('pageerror', error => errors.push(error));

    await page.waitForLoadState('networkidle');
    expect(errors.length).toBe(0);
  });

  test('site responds within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    const response = await page.goto('/');
    const loadTime = Date.now() - startTime;

    expect(loadTime).toBeLessThan(5000);
    expect(response!.status()).toBe(200);
  });

  test('all critical pages return 200 status', async ({ page }) => {
    const criticalPages = [
      '/',
      '/features.html',
      '/tools.html',
    ];

    for (const pagePath of criticalPages) {
      const response = await page.goto(pagePath);
      expect(response!.status(), `${pagePath} should return 200`).toBe(200);
    }
  });
});
