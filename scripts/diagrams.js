#!/usr/bin/env node
// Render the docs' Mermaid diagrams to SVG, one file per theme.
//
// The site's CSP allows no script and no inline style, so a diagram
// cannot render in the visitor's browser. scripts/docsite.py writes each
// `mermaid` fence it meets to app/assets/docs/diagrams/<digest>.mmd and
// puts an <img> per theme on the page; this script turns every .mmd
// there into <digest>-light.svg and <digest>-dark.svg with the site's
// palette, and the SVGs are committed like the hero recording.
//
//   task contributing:docs:diagrams     # renders, then re-runs docsite.py
//
// Mermaid is not a devDependency (package.json is the suite's manifest,
// merged into every adopter's), so it is installed on first use into
// .ss/mermaid/, which is gitignored, at the version pinned below. The
// library runs in Playwright's Chromium, the one `task contributing:setup`
// installs; MERMAID_CHROMIUM overrides the binary.

const path = require('node:path');
const fs = require('node:fs');
const { execSync } = require('node:child_process');
const { chromium } = require('@playwright/test');

const ROOT = path.join(__dirname, '..');
const DIAGRAMS = path.join(ROOT, 'app', 'assets', 'docs', 'diagrams');
const CACHE = path.join(ROOT, '.ss', 'mermaid');
const MERMAID_VERSION = '12.3.0';
const ORIGIN = 'https://mermaid.local';

// The site's palette (app/shared.css), light then dark: every colour in
// the SVG is a token's value, so a diagram sits in the page like a card.
const THEMES = {
  light: {
    primaryColor: '#FFE9D4', primaryTextColor: '#2A2118', primaryBorderColor: '#2A2118',
    secondaryColor: '#FFD9B8', tertiaryColor: '#FBF5EC', lineColor: '#6B5B47',
    textColor: '#2A2118', clusterBkg: '#FBF5EC', clusterBorder: '#6B5B47',
    edgeLabelBackground: '#FBF5EC', background: '#FBF5EC',
  },
  dark: {
    primaryColor: '#3A2E27', primaryTextColor: '#EFE7DC', primaryBorderColor: '#AEA192',
    secondaryColor: '#231D19', tertiaryColor: '#1C1815', lineColor: '#AEA192',
    textColor: '#EFE7DC', clusterBkg: '#1C1815', clusterBorder: '#AEA192',
    edgeLabelBackground: '#131110', background: '#131110',
  },
};
const FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif';

const TYPES = { '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css' };

function ensureMermaid() {
  const pkg = path.join(CACHE, 'node_modules', 'mermaid', 'package.json');
  if (fs.existsSync(pkg) && JSON.parse(fs.readFileSync(pkg, 'utf8')).version === MERMAID_VERSION) return;
  console.log(`Installing mermaid@${MERMAID_VERSION} into ${path.relative(ROOT, CACHE)}/ ...`);
  fs.mkdirSync(CACHE, { recursive: true });
  execSync(`npm install --no-save --no-audit --no-fund --no-package-lock --prefix "${CACHE}" mermaid@${MERMAID_VERSION}`, { stdio: 'inherit' });
}

// Serve the cache directory under a fake origin: a module script cannot
// import its chunks over file://, and nothing here may touch the network
// once mermaid is installed.
async function serveCache(page) {
  await page.route(`${ORIGIN}/**`, (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/') {
      const body = `<!doctype html><meta charset="utf-8"><script type="module">
        import mermaid from '/node_modules/mermaid/dist/mermaid.esm.min.mjs';
        window.mermaid = mermaid;
      </script>`;
      return route.fulfill({ status: 200, contentType: 'text/html', body });
    }
    const file = path.join(CACHE, decodeURIComponent(url.pathname));
    if (!file.startsWith(CACHE) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: '' });
    return route.fulfill({ status: 200, contentType: TYPES[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
}

async function renderAll(page, sources) {
  let count = 0;
  for (const [digest, source] of sources) {
    for (const [theme, themeVariables] of Object.entries(THEMES)) {
      const svg = await page.evaluate(async ({ id, source, themeVariables, fontFamily }) => {
        // SVG-only labels (no <foreignObject> HTML), and an XML serialisation:
        // the file is loaded as an <img>, where it is parsed as XML and
        // HTML labels are unreliable across browsers.
        window.mermaid.initialize({
          startOnLoad: false, theme: 'base', themeVariables: { ...themeVariables, fontFamily }, fontFamily,
          flowchart: { htmlLabels: false }, htmlLabels: false, securityLevel: 'strict',
        });
        const { svg } = await window.mermaid.render(id, source);
        const holder = document.createElement('div');
        holder.innerHTML = svg;
        const el = holder.querySelector('svg');
        el.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        return new XMLSerializer().serializeToString(el);
      }, { id: `d${digest}${theme}`, source, themeVariables, fontFamily: FONT });
      fs.writeFileSync(path.join(DIAGRAMS, `${digest}-${theme}.svg`), svg + '\n');
      count += 1;
    }
    console.log(`  ${digest}: light + dark`);
  }
  return count;
}

(async () => {
  if (!fs.existsSync(DIAGRAMS)) {
    console.error(`diagrams: ${path.relative(ROOT, DIAGRAMS)} does not exist; run \`task contributing:docs:site\` first`);
    process.exit(2);
  }
  const sources = fs.readdirSync(DIAGRAMS).filter((f) => f.endsWith('.mmd')).sort()
    .map((f) => [f.slice(0, -4), fs.readFileSync(path.join(DIAGRAMS, f), 'utf8')]);
  if (sources.length === 0) {
    console.error('diagrams: no .mmd sources to render');
    process.exit(2);
  }
  ensureMermaid();
  const launch = process.env.MERMAID_CHROMIUM ? { executablePath: process.env.MERMAID_CHROMIUM } : {};
  const browser = await chromium.launch(launch);
  try {
    const page = await browser.newPage();
    const pageErrors = [];
    page.on('pageerror', (e) => pageErrors.push(e));
    await serveCache(page);
    await page.goto(`${ORIGIN}/`, { waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(window.mermaid), null, { timeout: 15000 });
    const count = await renderAll(page, sources);
    if (pageErrors.length) throw new Error(`the page reported ${pageErrors.length} error(s): ${pageErrors.map((e) => e.message).join('; ')}`);
    console.log(`diagrams: ${count} SVG(s) written for ${sources.length} diagram(s)`);
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(`diagrams: ${err.message || err}`);
  process.exit(1);
});
