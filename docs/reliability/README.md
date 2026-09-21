# Reliability Testing

## Overview

This directory contains documentation for SlopStopper's reliability checks: portable smoke tests, broken-link audits, accessibility audits (see [ACCESSIBILITY.md](ACCESSIBILITY.md)), Core Web Vitals via Lighthouse CI, SEO/social-share metatags (see [SEO.md](SEO.md)), the llms.txt AI-discoverability map (see [LLMS_TXT.md](LLMS_TXT.md)), the robots.txt discoverability + de-index guard (see [ROBOTS_TXT.md](ROBOTS_TXT.md)) the sitemap.xml completeness + drift check (see [SITEMAP.md](SITEMAP.md)), the API health/readiness endpoint audit and the API latency + payload budget audit (both below). These checks are wired against any reachable URL.

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
| `LLMS_TXT_TEST_URL` | (none) | llms.txt check — base URL to audit |
| `LLMS_TXT_PATH` | `/llms.txt` | llms.txt check — path to the file |
| `ROBOTS_TXT_TEST_URL` | (none) | robots.txt check — base URL to audit |
| `ROBOTS_TXT_PATH` | `/robots.txt` | robots.txt check — path to the file |
| `SITEMAP_TEST_URL` | (none) | sitemap check — base URL to crawl + audit |
| `SITEMAP_PATH` | `/sitemap.xml` | sitemap check — path to the sitemap |
| `API_HEALTH_TEST_URL` | (none) | API health check — base URL of the API |
| `API_HEALTH_PATH` | (none — unset skips the check) | API health check — path to the health endpoint |
| `API_LATENCY_TEST_URL` | (none) | API latency check — base URL of the API |
| `API_LATENCY_PATHS` | (none — unset skips the check) | API latency check — comma-separated paths to sample |

## API Health Check

The API-shaped analogue of the smoke test. Smoke drives a browser over HTML pages; this probes the one endpoint an API is expected to expose for exactly this purpose, and asserts the contract around it.

**Why not just point smoke at `/health`:** smoke asserts DOM-shaped things — a `<title>`, a linked stylesheet, a shareable og-image — that a JSON endpoint will never satisfy. And a health endpoint has assertions of its own. `{"status": "degraded"}` returned with HTTP 200 is a **pass** to any reachability probe and a **failure** here, which is the whole reason a health endpoint returns a body at all.

### What it checks

| Assertion | Hard fail? | Knob |
|---|---|---|
| Endpoint reachable | yes | — |
| Status code matches | yes | `api.health.expect_status` (default 200) |
| JSON content-type (`application/json`, `+json` suffixes) | yes | `api.health.require_json` |
| Body parses as JSON and is non-empty | yes | `api.health.require_json` |
| Declared fields present (dot-paths, e.g. `deps.db`) | yes | `api.health.require_fields` |
| Declared fields match an expected value | yes | `api.health.expect_fields` |
| Response time | only with a budget set | `api.health.max_response_ms` |

### Configuration

```yaml
# .slopstopper.yml
api:
  base_path: ''          # prefix the API is served under, e.g. /api/v1
  health:
    path: /health        # unset → the check skips gracefully (exit 0)
    expect_status: 200
    require_json: true
    require_fields: [status, deps.db]
    expect_fields:
      status: ok
    max_response_ms:     # unset → timing reported, never enforced
```

With `api.health.path` unset the check exits 0 with a note — the same contract as [`hygiene:csp-exceptions`](../security/README.md#csp-exceptions) with `headers.source: null`. An unconfigured check is not a failing check, so a fresh install's first PR is green.

### Running locally

```bash
# Pass the base URL positionally (works for any reliability check)
task ss:reliability:api-health -- https://api.example.com

# Override config from the command line
task ss:reliability:api-health -- https://api.example.com \
  --path /readyz --expect-status 204 --require-field status --max-response-ms 500

# Or set the env var
API_HEALTH_TEST_URL=https://api.example.com task ss:reliability:api-health
```

Report: `.ss/reports/api-health/api-health-report.{md,json}`.

### Running in CI

`ss-reliability-api-health-check.yml` audits `urls.preview` on pull requests and `urls.production` on pushes to main, schedules and Cloudflare deployment events. Unlike the browser checks it **never builds and serves the repo locally** — an API isn't a static bundle `slopstopper serve` can host, and guessing a start command would be worse than not guessing. With neither URL configured the PR run emits a notice and skips; the deployed-main and scheduled runs still cover the endpoint.

The check ships under every [project-shape profile](../architecture/README.md#project-shape-profiles) except `library`, and stays inert until configured — so a UI repo with API routes gets it without having to opt in.

## API Latency Check

The API-shaped analogue of Core Web Vitals. There is no rendering on a JSON API, so the equivalent question is narrower and more answerable: how long does the endpoint take to answer, and how much does it send back. Each configured path is sampled several times; the check reports the **median**, the **slowest** sample and the response size.

**Why not p95:** five samples cannot support a 95th percentile, and calling `max()` a percentile would dress up one noisy reading as statistics. Budgets gate on the **median**, which is flake-resistant — one slow sample from a shared CI runner moves the maximum and not the middle. `slowest_ms` is an opt-in tail ceiling for anyone who wants one.

### What it checks

| Assertion | Hard fail? | Knob |
|---|---|---|
| Every sample completes | yes | — |
| Status is 2xx/3xx | yes | — |
| Median response time | only with a budget set | `api.latency.median_ms` |
| Slowest sample | only with a budget set | `api.latency.slowest_ms` |
| Response size | only with a budget set | `api.latency.max_bytes` |

Reachability is the floor and never opt-in: a 500 that answers in 3ms is not fast, and a timing from a connection error is not a measurement. Everything else is advisory until you set a budget.

### Configuration

```yaml
# .slopstopper.yml
api:
  base_path: ''          # prefix the API is served under, e.g. /api/v1
  latency:
    paths: []            # empty → the check skips gracefully (exit 0)
    samples: 5           # measured requests per endpoint
    warmup: 1            # discarded first requests (DNS, TLS, cold start)
    median_ms:           # unset → timings reported, never enforced
    slowest_ms:
    max_bytes:
```

Warmup requests are thrown away rather than averaged in: the first hit pays for DNS, TLS and whatever cold start the platform imposes, none of which is the steady-state latency a budget is about.

**Derive budgets from numbers you have observed, not from numbers that sound right.** A guessed budget on a shared runner is noise, and a check people learn to ignore is worse than no check. Run it with no budgets for a week, read the reports, then set one.

### Running locally

```bash
task ss:reliability:api-latency -- https://api.example.com

# Override config from the command line
task ss:reliability:api-latency -- https://api.example.com \
  --path /v1/items --samples 9 --median-ms 400 --max-bytes 200000

# Or set the env vars
API_LATENCY_TEST_URL=https://api.example.com \
  API_LATENCY_PATHS=/health,/v1/items task ss:reliability:api-latency
```

Report: `.ss/reports/api-latency/api-latency-report.{md,json}`.

### Running in CI

`ss-reliability-api-latency-check.yml` resolves its URL exactly as the API health workflow does — `urls.preview` on pull requests, `urls.production` on main, schedules and deployment events — and never builds or serves the repo locally.

One caveat specific to this check: **timings from a preview environment are not timings from production.** A cold-started preview deploy is slower and noisier. Either set budgets loose enough for it, or leave them unset on PRs and rely on the scheduled production run.

Ships under every [project-shape profile](../architecture/README.md#project-shape-profiles) except `library`, and stays inert until configured.

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
