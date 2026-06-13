#!/usr/bin/env node
// Render SVG source assets to PNG using Playwright (already a devDep).
// Outputs are committed; re-run when the SVG sources change:
//   task ss:contributing:assets
//
// Add a new target by appending an entry to TARGETS below.

const path = require('node:path');
const fs = require('node:fs/promises');
const { chromium } = require('@playwright/test');

const APP = path.join(__dirname, '..', '..', 'app');

const TARGETS = [
  { svg: 'og-image.svg',          png: 'og-image.png',          width: 1200, height: 630 },
  { svg: 'apple-touch-icon.svg',  png: 'apple-touch-icon.png',  width: 180,  height: 180 },
];

async function render(browser, { svg, png, width, height }) {
  const svgPath = path.join(APP, svg);
  const outPath = path.join(APP, png);
  const svgBody = await fs.readFile(svgPath, 'utf8');

  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;padding:0;background:transparent}
    svg{display:block;width:${width}px;height:${height}px}
  </style></head><body>${svgBody}</body></html>`;

  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  const element = await page.locator('svg').first();
  await element.screenshot({ path: outPath, omitBackground: false, scale: 'device' });
  await context.close();
  console.log(`  ${svg} -> ${png} (${width}x${height} @2x)`);
}

(async () => {
  console.log('Rendering static assets via Playwright...');
  const browser = await chromium.launch();
  try {
    for (const t of TARGETS) {
      await render(browser, t);
    }
  } finally {
    await browser.close();
  }
  console.log('Done.');
})();
