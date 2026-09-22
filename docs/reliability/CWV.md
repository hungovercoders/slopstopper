# Core Web Vitals

`reliability:cwv` runs [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) against a URL and fails the build when a page's performance falls below budget. It is the browser-side speed check; [API Latency](README.md#api-latency-check) is its analogue for a JSON API.

## What it measures

Lighthouse loads the page three times (`numberOfRuns: 3`). Neither bundled config sets `assert.aggregationMethod`, so Lighthouse CI's default `optimistic` aggregation applies: each assertion is judged on the **best** of the three runs, which is what keeps one slow run on a noisy CI runner from failing the build. The headline metrics and their default budgets:

| Metric | Budget | Fails? |
|---|---|---|
| Performance score | ≥ 70 / 100 | yes |
| SEO score | ≥ 90 / 100 | yes |
| Largest Contentful Paint (LCP) | ≤ 4 s | yes |
| Total Blocking Time (TBT) | ≤ 600 ms | yes |
| Cumulative Layout Shift (CLS) | ≤ 0.25 | yes |
| First Contentful Paint (FCP) | ≤ 3 s | warn only |

The production config (`--prod`) keeps those and adds advisory warnings for Accessibility and Best Practices scores (≥ 80), Speed Index (≤ 5.8 s) and Time to Interactive (≤ 7.3 s). Warnings appear in the report and never fail the run.

These are deliberately loose — a static site should clear them easily, and a budget that fires on CI-runner noise is worse than none. Tighten them once you have a few weeks of numbers.

## Configuration

The budgets live in Lighthouse's own config, not `.slopstopper.yml`. The CLI ships two — `cli/slopstopper/data/lighthouserc.json` (dev) and `cli/slopstopper/data/lighthouserc.prod.json` — inside the wheel. To change a budget, eject the one you want and edit the copy:

```bash
slopstopper templates eject lighthouserc.json        # → .ss/lighthouserc.json
slopstopper templates eject lighthouserc.prod.json   # → .ss/lighthouserc.prod.json
```

The check resolves `.ss/lighthouserc[.prod].json` first and falls back to the bundled copy, so an ejected file is picked up automatically. `--config <path>` overrides both.

## Running locally

```bash
task ss:reliability:cwv -- http://localhost:8080          # dev budgets
task ss:reliability:cwv -- https://example.com --prod      # production budgets
CWV_URL=http://localhost:8080 task ss:reliability:cwv
```

Needs `node` (Lighthouse runs in headless Chrome via `npx lhci`). The check generates `cwv-report.md` under `.ss/reports/cwv/` — the threshold table with pass/fail per metric, plus a link to the full Lighthouse HTML report on Lighthouse's temporary public storage. Raw Lighthouse output lands in `.lighthouseci/` (gitignored; the workflow uploads it as an artifact).

## Running in CI

`ss-reliability-core-web-vitals.yml` picks the URL and the budget set from the event, in its `Determine audit URL` step:

| Event | URL audited | Budgets |
|---|---|---|
| `pull_request`, `push` | the site built and served on `localhost:8080` | dev |
| `workflow_dispatch` | the `url` input, else `urls.production` | dev |
| `deployment_status` (e.g. a Cloudflare deploy) | that deployment's own `target_url` — a preview deploy audits the preview | `--prod` |
| `schedule` (daily) | `urls.production` | `--prod` |

It posts the rolling PR comment, opens a tracking issue when `main` regresses, and closes that issue automatically on the next green run.

## Reading a failure

- **Performance score under 70 with LCP over budget** — almost always an unoptimised hero image or a render-blocking stylesheet. Lighthouse's HTML report (linked from the check's report) names the resource.
- **CLS over 0.25** — an image or embed without explicit `width`/`height`, or a web font swapping in late.
- **TBT over 600 ms** — long JavaScript tasks on load. On a static site this usually means a third-party script.
- **Everything passes locally, fails in CI** — the CI runner is slower and noisier than your laptop. Look at all three runs in the Lighthouse output before touching a budget — the gate passes on the best one, so a failure means every run missed; if the numbers are consistently near the line, the budget is telling you something.

Dropped by `--profile api` and `--profile library`; there is no page to render.
