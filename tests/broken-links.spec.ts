import { test, expect } from '@playwright/test';

const targetUrl =
  process.env.BROKEN_LINKS_TEST_URL ||
  process.env.SMOKE_TEST_URL ||
  process.env.BASE_URL ||
  'http://localhost:8080';

const pagesToScan = ['/', '/features.html', '/tools.html'];

test.describe('Broken Link Checks', () => {
  test.use({ baseURL: targetUrl });

  test('internal links return successful responses', async ({ page, request, baseURL }) => {
    const base = new URL(baseURL!);
    const links = new Set<string>();

    for (const path of pagesToScan) {
      await page.goto(path);
      const hrefs = await page.locator('a[href]').evaluateAll((anchors) =>
        anchors
          .map((a) => a.getAttribute('href'))
          .filter((href): href is string => Boolean(href)),
      );

      for (const href of hrefs) {
        const normalizedHref = href.toLowerCase();
        if (
          normalizedHref.startsWith('#') ||
          normalizedHref.startsWith('mailto:') ||
          normalizedHref.startsWith('tel:') ||
          normalizedHref.startsWith('javascript:') ||
          normalizedHref.startsWith('data:') ||
          normalizedHref.startsWith('vbscript:')
        ) {
          continue;
        }

        const resolved = new URL(href, base);
        if (resolved.origin !== base.origin) {
          continue;
        }

        links.add(`${resolved.pathname}${resolved.search}`);
      }
    }

    for (const linkPath of links) {
      const response = await request.get(linkPath);
      expect(response.status(), `${linkPath} should not be broken`).toBeLessThan(400);
    }
  });
});
