# Reliability Testing

## Overview

This directory contains documentation for SlopStopper's reliability checks: portable smoke tests, broken-link audits, accessibility audits (see [ACCESSIBILITY.md](ACCESSIBILITY.md)) and Core Web Vitals via Lighthouse CI. These checks are wired against any reachable URL.

## Configuration (env vars)

All reliability checks read their target URL and audit scope from environment variables — no code changes needed.

| Variable | Default | Used by |
|---|---|---|
| `SMOKE_TEST_URL` | (none) | smoke |
| `SMOKE_PAGES` | `/` | smoke — comma-separated paths, e.g. `/,/login,/pricing` |
| `SMOKE_TIMEOUT` | `5000` | smoke — per-request ms |
| `BROKEN_LINKS_TEST_URL` | falls back to `SMOKE_TEST_URL` / `BASE_URL` / `localhost:8080` | broken links |
| `BROKEN_LINKS_PAGES` | `/` | broken links — comma-separated crawl seed paths, e.g. `/,/features.html,/tools.html` |
| `ACCESSIBILITY_TEST_URL` | falls back to `SMOKE_TEST_URL` / `BASE_URL` / `localhost:8080` | accessibility |
| `ACCESSIBILITY_PAGES` | `/` | accessibility — comma-separated paths |
| `ACCESSIBILITY_IMPACT` | `serious` | accessibility — min `critical`/`serious`/`moderate`/`minor` |
| `ACCESSIBILITY_THRESHOLD` | `0` | accessibility — max violations before failing |
| `LIGHTHOUSE_URL` / `CWV_URL` | (none) | Lighthouse CI — URL to audit |
| `SEO_TEST_URL` | (none) | SEO metatag check — base URL to audit |
| `SEO_PAGES` | `/` | SEO metatag check — comma-separated paths, e.g. `/,/features.html` |
| `SEO_REQUIRE_OG_IMAGE` | `1` | SEO metatag check — set `0` to skip og:image presence check |
| `SEO_VERIFY_OG_IMAGE` | `1` | SEO metatag check — set `0` to skip HEAD-fetching og:image |

## Broken Link Checks

The broken-link check can run against any site you provide via `BROKEN_LINKS_TEST_URL`.
It visits each path in `BROKEN_LINKS_PAGES`, collects all anchor links, keeps only same-origin HTTP(S) links, then asserts each destination returns a non-4xx/5xx status.
External links are intentionally skipped to reduce noise from third-party outages,
rate limits, or bot protections outside your control.

### Running broken-link checks locally

```bash
# Pass URL directly
task ss:reliability:broken-links -- https://your-site.example.com

# Or set environment variables
BROKEN_LINKS_TEST_URL=https://your-site.example.com \
BROKEN_LINKS_PAGES="/,/features.html,/tools.html" \
task ss:reliability:broken-links
```

### Running broken-link checks in CI

```bash
BROKEN_LINKS_TEST_URL=https://your-site.example.com \
BROKEN_LINKS_PAGES="/,/features.html,/tools.html" \
task ss:reliability:broken-links -- --ci
```

For live `slopstopper.dev`, the workflow seeds `/,/features.html,/tools.html` so links from the three main pages are validated on every scheduled/deploy/PR run.

## Smoke Tests

Smoke tests are lightweight, critical-path tests that verify a deployed site is functioning correctly. These tests run against live URLs (production or staging) and check for:

- Page availability (200 status codes)
- Core navigation functionality
- Asset loading
- Response times
- Critical content rendering

### Running smoke tests locally

```bash
# Pass URL as a positional argument (works for any reliability check)
task ss:reliability:smoke -- https://your-site.example.com

# Add --ci for retries + HTML report + single worker
task ss:reliability:smoke -- https://your-site.example.com --ci

# Or set the env var (handy when chaining `BROKEN_LINKS_PAGES=… SMOKE_TEST_URL=…`)
SMOKE_TEST_URL=https://your-site.example.com task ss:reliability:smoke
```

`task ss:reliability:smoke` shells through to `slopstopper run reliability:smoke`, which launches the bundled Playwright spec via the config baked into the `slopstopper-cli` wheel — see [`cli/slopstopper/data/playwright.config.js`](../../cli/slopstopper/data/playwright.config.js) and [`cli/slopstopper/data/tests/smoke.spec.ts`](../../cli/slopstopper/data/tests/smoke.spec.ts). Adopters don't vendor those files; the CLI owns them. To customise, run `slopstopper templates eject playwright.config.js` to drop an editable copy into `.ss/`; the CLI picks `.ss/<filename>` up automatically.

### Running in CI

The installer copies a ready-to-run workflow at [`.github/workflows/ss-reliability-smoke-tests.yml`](../../.github/workflows/ss-reliability-smoke-tests.yml) — that's the canonical shape. It runs on PRs, pushes to `main`, an hourly schedule, Cloudflare deployment events, and `workflow_dispatch`; on failure it opens (or updates) a tracking issue, and on recovery it closes it. The job calls:

```yaml
- name: Run smoke tests
  run: task ss:reliability:smoke -- ${{ steps.url.outputs.url }} --ci
```

— same Task command you ran locally, with the positional URL resolved from the trigger context.

### What the Smoke Tests Check

1. **Homepage Availability** - Ensures the main page loads with 200 status
2. **Secondary Pages** - Verifies all critical pages are accessible
3. **Navigation** - Tests basic user navigation flows
4. **Static Assets** - Confirms CSS and JS files load correctly
5. **Performance** - Validates pages load within acceptable timeframes (< 5s)
6. **Error Detection** - Checks for JavaScript console errors

### Test configuration

The portable spec is configured via [`cli/slopstopper/data/playwright.config.js`](../../cli/slopstopper/data/playwright.config.js) — bundled in the `slopstopper-cli` wheel. `testDir: './tests'` resolves to the bundled spec directory so SlopStopper's specs never collide with your own `tests/` directory. To customise, eject an editable copy into your repo's `.ss/` directory:

```bash
slopstopper templates eject playwright.config.js
```

The CLI's template resolver prefers `.ss/<filename>` over the bundled version, so edits to the ejected copy take effect immediately.

### Adding pages to the smoke check

The portable smoke spec at [`cli/slopstopper/data/tests/smoke.spec.ts`](../../cli/slopstopper/data/tests/smoke.spec.ts) iterates over `SMOKE_PAGES`. To add coverage, set the env var — no code changes needed:

```bash
SMOKE_TEST_URL=https://your-site.example.com \
  SMOKE_PAGES="/,/login,/pricing,/about" \
  task ss:reliability:smoke
```

For assertions beyond "page returns 200 and loads cleanly" (e.g. specific element visibility), add your own specs under your repo's own `tests/` directory — those are picked up by a `playwright.config.js` you write in your repo root, not by SlopStopper's bundled config.

### Best Practices

1. **Keep tests fast** - Smoke tests should complete in under 2 minutes
2. **Test critical paths only** - Focus on must-work functionality
3. **Avoid test data dependencies** - Tests should work on any deployment
4. **Set appropriate timeouts** - Allow for network latency in production
5. **Monitor regularly** - Run on a schedule to catch degradation early

### Monitoring Recommendations

- **Frequency**: Run every 15-60 minutes depending on SLA requirements
- **Alerting**: Configure GitHub Actions to notify on failures
- **Retention**: Keep test results for at least 30 days
- **Review**: Regularly review test coverage and update as site evolves

### Troubleshooting

**Tests fail locally but pass in CI (or vice versa):**
- Check `SMOKE_TEST_URL` (or the positional URL) points where you expect
- Verify the target URL is reachable from your network
- The CI workflow installs the Playwright browsers via `npx playwright install --with-deps chromium`; locally, run the same command once before your first invocation (or let the spec install on demand)

**Tests timeout:**
- Check the site is responding (try `curl`/`wget`)
- Verify no network issues or rate limiting
- Bump Playwright's timeout by ejecting the bundled config (`slopstopper templates eject playwright.config.js`) and editing the copy that lands in `.ss/`

**Flaky tests:**
- Add explicit waits (`await page.waitForLoadState('networkidle')`) in any custom specs you add
- Increase the CI retry count by editing the ejected config in `.ss/` (see "Test configuration" above)
- Check for timing-dependent assertions

### Related documentation

- [Playwright testing guide](https://playwright.dev/docs/intro)
- [GitHub Actions documentation](https://docs.github.com/actions)
- [Contributing guidelines](../contributing/README.md)
