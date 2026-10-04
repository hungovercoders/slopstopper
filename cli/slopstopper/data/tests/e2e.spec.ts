import { test, expect, type Page } from '@playwright/test';

/**
 * Portable end-to-end journeys for any web site.
 *
 * Smoke proves each page renders; this proves a visitor can get around.
 * From every start path it:
 *
 *   1. clicks each same-origin link in the primary <nav> and asserts the
 *      destination answers, shows a heading and still carries the nav;
 *   2. follows every in-page anchor (href="#…") to an element that exists;
 *   3. opens and closes every <details> disclosure;
 *   4. presses the browser's back button and lands where it started.
 *
 * Each start path must itself answer (status < 400): a path listed in
 * E2E_PAGES that 404s is a failure, not a skip.
 *
 * Nothing here names a selector or a page of a specific site, so the spec
 * runs unchanged on any HTML site. A journey that is specific to yours
 * (log in, add to basket, submit a form) belongs in an ejected copy:
 * `slopstopper templates eject tests/e2e.spec.ts`, then edit `.ss/tests/e2e.spec.ts`.
 *
 * Configuration:
 *   E2E_TEST_URL   — base URL (falls back to SMOKE_TEST_URL / BASE_URL / localhost:8080)
 *   E2E_PAGES      — comma-separated start paths, default '/'
 *   E2E_MAX_LINKS  — nav links followed per start path, default 25
 *
 * Usage:
 *   task ss:reliability:e2e -- https://your-site.example.com
 *   E2E_PAGES='/,/pricing' task ss:reliability:e2e -- https://your-site.example.com
 */

const targetUrl =
  process.env.E2E_TEST_URL ||
  process.env.SMOKE_TEST_URL ||
  process.env.BASE_URL ||
  'http://localhost:8080';

const startPaths = (process.env.E2E_PAGES ?? '/')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

const maxLinks = parseInt(process.env.E2E_MAX_LINKS || '25', 10);

/** Load a start path and fail (not skip) if it doesn't answer: a wrong `pages.e2e` entry is a verdict. */
async function openStart(page: Page, start: string): Promise<void> {
  const response = await page.goto(start);
  expect(response, `${start}: start page should respond`).not.toBeNull();
  expect(response!.status(), `${start}: start page should answer 2xx/3xx, got ${response!.status()}`).toBeLessThan(400);
}

/** Same-origin, navigable hrefs from the page's primary <nav>, in document order, deduped. */
async function navTargets(page: Page): Promise<string[]> {
  const origin = new URL(page.url()).origin;
  const hrefs = await page.locator('nav a[href]').evaluateAll((anchors) =>
    anchors.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''),
  );
  const seen = new Set<string>();
  const out: string[] = [];
  for (const href of hrefs) {
    if (!href || href.startsWith('#') || /^(mailto|tel|javascript):/i.test(href)) continue;
    let url: URL;
    try {
      url = new URL(href, page.url());
    } catch {
      continue;
    }
    if (url.origin !== origin) continue;
    const key = url.pathname + url.search;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(href);
    if (out.length >= maxLinks) break;
  }
  return out;
}

test.describe('E2E Journeys', () => {
  test.use({ baseURL: targetUrl });

  for (const start of startPaths) {
    test(`${start}: primary navigation round trip`, async ({ page }) => {
      const errors: Error[] = [];
      page.on('pageerror', (e) => errors.push(e));

      await openStart(page, start);
      const targets = await navTargets(page);
      test.skip(targets.length === 0, `${start}: no same-origin links inside a <nav>`);

      for (const href of targets) {
        await page.goto(start);
        const link = page.locator(`nav a[href="${href}"]`).first();
        await expect(link, `${start}: nav link ${href} should be visible`).toBeVisible();

        const expected = new URL(href, page.url());
        await Promise.all([
          page.waitForURL((u) => u.pathname === expected.pathname && u.search === expected.search),
          link.click(),
        ]);
        await page.waitForLoadState('domcontentloaded');

        await expect(page.locator('h1').first(), `${href}: page should have a heading`).toBeVisible();
        expect(await page.locator('nav a[href]').count(), `${href}: primary navigation should still be present`)
          .toBeGreaterThan(0);
      }

      expect(errors, `${start}: journey emitted JS errors: ${errors.map((e) => e.message).join('; ')}`)
        .toHaveLength(0);
    });

    test(`${start}: in-page anchors resolve`, async ({ page }) => {
      await openStart(page, start);
      const ids = await page.locator('a[href^="#"]').evaluateAll((anchors) =>
        anchors
          .map((a) => decodeURIComponent((a as HTMLAnchorElement).getAttribute('href') ?? '').slice(1))
          .filter((id) => id.length > 0),
      );
      const unique = [...new Set(ids)];
      test.skip(unique.length === 0, `${start}: no in-page anchors`);

      const missing: string[] = [];
      for (const id of unique) {
        const count = await page.locator(`[id="${id.replace(/"/g, '\\"')}"]`).count();
        if (count === 0) missing.push(`#${id}`);
      }
      expect(missing, `${start}: in-page anchors with no target element: ${missing.join(', ')}`)
        .toHaveLength(0);
    });

    test(`${start}: disclosure widgets open and close`, async ({ page }) => {
      await openStart(page, start);
      const summaries = page.locator('details > summary');
      const total = Math.min(await summaries.count(), maxLinks);
      test.skip(total === 0, `${start}: no <details> on the page`);

      for (let i = 0; i < total; i++) {
        const summary = summaries.nth(i);
        const details = summary.locator('xpath=..');
        await summary.scrollIntoViewIfNeeded();
        await summary.click();
        await expect(details, `${start}: <details> #${i + 1} should open on click`).toHaveAttribute('open', '');
        await summary.click();
        await expect(details, `${start}: <details> #${i + 1} should close on second click`).not.toHaveAttribute('open', '');
      }
    });

    test(`${start}: browser back returns to the start`, async ({ page }) => {
      await openStart(page, start);
      const targets = await navTargets(page);
      const away = targets.find((href) => new URL(href, page.url()).pathname !== new URL(page.url()).pathname);
      test.skip(!away, `${start}: no nav link leads to another page`);

      const startUrl = page.url();
      const expected = new URL(away!, page.url());
      await Promise.all([
        page.waitForURL((u) => u.pathname === expected.pathname),
        page.locator(`nav a[href="${away}"]`).first().click(),
      ]);
      await page.goBack();
      await page.waitForLoadState('domcontentloaded');
      expect(page.url(), `${start}: back button should return to the start page`).toBe(startUrl);
    });
  }
});
