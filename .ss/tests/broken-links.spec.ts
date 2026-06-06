import { test, expect } from '@playwright/test';

const targetUrl =
  process.env.BROKEN_LINKS_TEST_URL ||
  process.env.SMOKE_TEST_URL ||
  process.env.BASE_URL ||
  'http://localhost:8080';

const pagesToScan = (process.env.BROKEN_LINKS_PAGES ?? '/')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

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
        if (/^(#|mailto:|tel:|javascript:|data:|vbscript:)/i.test(href)) {
          continue;
        }

        const resolved = new URL(href, base);
        if (resolved.origin !== base.origin) {
          continue;
        }

        // Fragments do not affect HTTP retrieval, so only pathname+query are checked.
        links.add(`${resolved.pathname}${resolved.search}`);
      }
    }

    const brokenLinks: string[] = [];
    for (const linkPath of links) {
      const response = await request.get(linkPath);
      if (response.status() >= 400) {
        brokenLinks.push(`${linkPath} returned ${response.status()}`);
      }
    }

    expect(brokenLinks, brokenLinks.join('\n')).toEqual([]);
  });
});
