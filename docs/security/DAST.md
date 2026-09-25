# DAST — Dynamic Application Security Testing

This template includes automated Dynamic Application Security Testing (DAST) using **OWASP ZAP** to detect runtime security issues by scanning your running site. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
# Start the site first
task contributing:run &
# Run DAST scan against it
task ss:security:dast -- http://localhost:8080
```

### What You Get Automatically
- ✅ PR comments with DAST findings report
- ✅ Merge blocking if any High or Medium alerts exist
- ✅ GitHub issues on main branch for blocking alerts
- ✅ Documented CSP exceptions surfaced separately and **not** blocking (see below)

### Common Issues

| Problem | Solution |
|---------|----------|
| Workflow not triggering? | Check workflow is at `.github/workflows/ss-security-dast-check.yml` |
| ZAP not available? | The workflow uses Docker to run ZAP — no installation needed in CI |
| Don't want DAST checks? | Delete `.github/workflows/ss-security-dast-check.yml` |
| All my PRs fail DAST because I had to embed GTM / Intercom / etc.? | Document the CSP relaxation in [`CSP_EXCEPTIONS.md`](./CSP_EXCEPTIONS.md). The gate will swallow CSP-class findings on documented paths. See "DAST + CSP exceptions" below. |

### Risk Level Reference

| Risk Level | riskcode | Status | Action |
|------------|----------|--------|--------|
| High | 3 | 🔴 Blocking | Must be fixed before merge — blocks even on documented exception paths |
| Medium | 2 | 🟡 Blocking by default | Blocks unless the finding is a CSP issue on a path documented in `CSP_EXCEPTIONS.md` |
| Low | 1 | 🔵 Non-blocking | Review when time allows |
| Informational | 0 | ℹ️ Non-blocking | Awareness only |

### DAST + CSP exceptions

The DAST gate in this template (driven by [`cli/slopstopper/dast_gate.py`](../../cli/slopstopper/dast_gate.py)) consults [`docs/security/CSP_EXCEPTIONS.md`](./CSP_EXCEPTIONS.md) on every run:

- **No `CSP_EXCEPTIONS.md` file?** Gate behaves exactly like a vanilla riskcode ≥ 2 cutoff — nothing changes for you. Adopters with no third-party scripts can ignore this section entirely.
- **You added a third-party widget (GTM, Sentry, Intercom, Giscus…)?** Add a per-path entry to `worker/headers.json` for the affected path, *and* document it under `## Exceptions` in `CSP_EXCEPTIONS.md` using the schema in that file. Once it's documented, ZAP's CSP findings on that exact path stop blocking the build. They still appear in the PR comment under a separate "🛡 Documented CSP exceptions" section so they stay visible in review.
- **What still blocks even with an exception?** Any non-CSP finding (XSS, missing other headers, CSRF, etc.) on the same path; any finding at all on a non-documented path; any High-severity (riskcode 3) finding anywhere — including CSP High on a documented path. The exception only relaxes the *Medium-CSP-on-this-path* case; the rest of DAST coverage is unchanged.

The companion check `ss:hygiene:csp-exceptions` (workflow `ss-hygiene-csp-exceptions-check.yml`) keeps `worker/headers.json` and `CSP_EXCEPTIONS.md` in sync — if either side drifts, the build fails before DAST even runs.

---

## Overview

What DAST checks: **your running application** for HTTP-level security vulnerabilities — missing security headers, injection vectors, exposed sensitive endpoints, and other issues that only appear at runtime.

The DAST workflow:
- ✅ Starts a local http-server for the static site
- ✅ Runs OWASP ZAP baseline scan against it
- ✅ Posts findings as PR comments
- ✅ Creates GitHub issues when High/Medium alerts land on `main`
- ✅ Fails PRs with High or Medium alerts

## Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/ss-security-dast-check.yml` | GitHub Actions workflow |
| `Taskfile.ss.yml` (`dast` task) | Local task runner shim → `slopstopper run security:dast` |
| `cli/slopstopper/checks/dast.py` | Check implementation (subprocess-invokes Docker + OWASP ZAP, renders MD report) |
| `cli/slopstopper/dast_gate.py` | Pass/fail gate — filters documented CSP exceptions from the blocker count |
| `docs/security/CSP_EXCEPTIONS.md` | Single source of truth for per-path CSP relaxations (optional — gate handles absence) |
| `.gitignore` | Excludes `.ss/reports/dast/` |

## Key Configuration Points

### Change the Target URL

In `Taskfile.yml`, the `dast` task accepts the target URL as an argument:

```bash
task ss:security:dast -- http://your-site-url
```

In `ss-security-dast-check.yml`, the CI workflow starts a local server and passes `http://localhost:8080`. To scan a deployed preview instead, update that step with your preview URL.

### Change the Blocking Threshold

To block only on High (not Medium), edit `ss-security-dast-check.yml`:

```python
# Change this line:
if int(alert.get('riskcode', 0)) >= 2:
# To:
if int(alert.get('riskcode', 0)) >= 3:
```

### Disable DAST Checking

```bash
# Option A: delete the workflow
rm .github/workflows/ss-security-dast-check.yml

# Option B: disable in GitHub UI → Actions → DAST Analysis → Disable workflow
```

## Running Locally

```bash
# Install Task (one-time)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# Start the site
task contributing:run &

# Run DAST scan (requires Docker)
task ss:security:dast -- http://localhost:8080
```

Reports are saved to `.ss/reports/dast/`.

## For More Information

- **OWASP ZAP Documentation:** https://www.zaproxy.org/docs/
- **ZAP Baseline Scan:** https://www.zaproxy.org/docs/docker/baseline-scan/
- **Task Documentation:** https://taskfile.dev

---

## Scanning an API (ZAP OpenAPI mode)

The default scan above is ZAP's **baseline**, which spiders the site from the
URL you pass. That is right for an HTML surface and useless against a JSON
API — there are no links to crawl, so the scan reports next to nothing.

Point the check at an OpenAPI spec and it switches to ZAP's **API scan**,
which reads the spec and exercises the operations it declares:

```yaml
# .slopstopper.yml
api:
  openapi:
    spec: https://api.example.com/openapi.json   # URL or repo-relative file
    host_override: true                          # pass the scanned URL as ZAP's -O
```

```bash
task ss:security:dast -- https://api-preview.example.com
task ss:security:dast -- https://api-preview.example.com --spec openapi.yaml
```

| | Baseline | API scan |
|---|---|---|
| Trigger | `api.openapi.spec` unset | `api.openapi.spec` (or `--spec`) set |
| ZAP entry point | baseline scan | API scan (`-f openapi`) |
| What it drives from | spidering a root URL | the operations in the spec |
| ZAP's `-t` | the site URL | the spec |
| The URL you pass | the scan target | ZAP's `-O` host override |

**`host_override`** exists because a spec's `servers` block usually names
production. Passing the scanned URL as `-O` points the same operations at
whatever environment you are actually testing. Set it to `false` if your spec
already names the right host.

**A local spec file** is staged into ZAP's mounted report directory for the
run and removed afterwards — the container only sees `/zap/wrk/`, so a
repo-relative path can't be handed to it directly.

**Unconfigured is not failing.** With no spec the check keeps its baseline
behaviour, and on an `api`-profile repo the workflow skips rather than
scanning nothing — the same contract as `reliability:api-health` and
`security:api-headers`. So an `api` repo carries the DAST workflow but gets
no dynamic scanning until a spec is set; that is the one step to take if you
want API security coverage.

**In CI**, `ss-security-dast-check.yml` branches on the same key: with a spec
it audits `urls.preview` on pull requests and `urls.production` on main and
schedules; without one it keeps building the repo and serving it on
`localhost:8080`.
