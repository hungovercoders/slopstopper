# Security

Overview of security scanning and controls for this project.

## Contents

- [SAST — Static Application Security Testing](#sast--static-application-security-testing)
- [DAST — Dynamic Application Security Testing](#dast--dynamic-application-security-testing)
- [Dependency Vulnerability Scanning](#dependency-vulnerability-scanning)
- [Secrets Detection](#secrets-detection)
- [CSP Exceptions](#csp-exceptions) — strict-default + per-path exceptions pattern

---

# CSP Exceptions

The site ships a strict `default-src 'self'; script-src 'self'` Content
Security Policy on every path. When a third-party widget is genuinely
required on a single page (e.g. Giscus on `/feedback.html`), we admit it
via a **scoped, documented, SRI-pinned per-path exception** rather than
weakening the site-wide CSP.

The full pattern — and the live list of exceptions — is in
[`CSP_EXCEPTIONS.md`](./CSP_EXCEPTIONS.md). The
[`ss:hygiene:csp-exceptions`](../../Taskfile.ss.yml) check enforces drift
between `worker/headers.json` and that document.

**For adopters:** this is the pattern to reuse the moment your site needs
GTM, Sentry, Intercom or any analytics tag. Copy the schema, drop the
hygiene check via the installer, and your auditors will thank you.

---

# SAST — Static Application Security Testing

This template includes automated Static Application Security Testing (SAST) using **Semgrep** to detect security bugs and anti-patterns in your own source code. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
task ss:security:sast
```

### What You Get Automatically
- ✅ PR comments with SAST findings report
- ✅ Merge blocking if any ERROR-severity findings exist
- ✅ GitHub issues on main branch for error-severity problems

### Common Issues

| Problem | Solution |
|---------|----------|
| Workflow not triggering? | Check workflow is at `.github/workflows/ss-security-sast-check.yml` |
| Want stricter/looser rules? | Use a custom Semgrep config file (see below) |
| Don't want SAST checks? | Delete `.github/workflows/ss-security-sast-check.yml` |

### Severity Reference

| Severity | Status | Action |
|----------|--------|--------|
| ERROR | 🔴 Blocking | Must be fixed before merge |
| WARNING | ⚠️ Non-blocking | Review recommended |
| INFO | ℹ️ Informational | Awareness only |

### Documented suppressions

Some Semgrep rules are too broad for known-safe patterns. Rather than disable rules globally (which would hurt adopters whose code legitimately needs them), we use narrow inline annotations with a rationale at the call site:

- `# nosemgrep: <full-rule-id>` for Python — placed on the affected statement, with a brief comment explaining why the pattern is safe here
- `<!-- nosemgrep: <full-rule-id> --><rationale>` for HTML — placed on the line directly above the affected element

Both are visible in code review and act as documentation; nothing is silently disabled. Current suppressions in this repo:

| Rule | Where | Why it's safe here |
| ---- | ----- | ------------------ |
| `python.lang.security.audit.dynamic-urllib-use-detected` | `cli/slopstopper/checks/seo.py` (`_fetch` + `_head_ok`) | URL originates from `SEO_TEST_URL` env var (operator-supplied) and `_require_safe_url()` is called before every `urlopen()` to reject any scheme other than `http`/`https`. So `file://`/`ftp://` reads are impossible by construction. |
| `html.security.audit.missing-integrity` | `<link rel="canonical">` in `app/index.html`, `app/features.html`, `app/tools.html`, `app/feedback.html` | Canonical links declare URL identity for search engines. They load no subresource, so Subresource Integrity is structurally inapplicable. The rule fires on any `<link>` without `integrity=` regardless of whether the tag loads anything. |

**For adopters:** when SlopStopper flags noise in your code, prefer this narrow-suppression-with-rationale pattern over disabling a rule globally — it keeps the rule active for real findings while you accept the false positive at the exact site that needs it.

---

## Overview

What SAST checks: **your own source code** for security vulnerabilities and anti-patterns using pattern matching (e.g. dangerous function calls, injection risks, hardcoded secrets).

The SAST workflow:
- ✅ Runs automatically on every PR to `main` and push to `main`
- ✅ Analyses code using Semgrep's auto-configured rule set
- ✅ Posts findings as PR comments
- ✅ Creates GitHub issues when error-severity findings land on `main`
- ✅ Fails PRs with error-severity findings

## Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/ss-security-sast-check.yml` | GitHub Actions workflow |
| `Taskfile.ss.yml` (`sast` task) | Local task runner shim → `slopstopper run security:sast` |
| `cli/slopstopper/checks/sast.py` | Check implementation (subprocess-invokes Semgrep, renders MD report) |
| `.gitignore` | Excludes `.ss/reports/sast/` |

## Key Configuration Points

### Custom Rule Set

By default, Semgrep runs with `--config=auto`. To use a specific ruleset, update the `sast:analyze` task in `Taskfile.yml`:

```yaml
semgrep \
  --config=p/owasp-top-ten \   # ← replace --config=auto
  --json \
  ...
```

### Disable SAST Checking

```bash
# Option A: delete the workflow
rm .github/workflows/ss-security-sast-check.yml

# Option B: disable in GitHub UI → Actions → SAST Analysis → Disable workflow
```

## Running Locally

```bash
# Install Task (one-time)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# Run SAST
task ss:security:sast
```

Reports are saved to `.ss/reports/sast/`.

## For More Information

- **Semgrep Documentation:** https://semgrep.dev/docs/
- **Semgrep Registry:** https://semgrep.dev/r
- **Task Documentation:** https://taskfile.dev

---

# DAST — Dynamic Application Security Testing

This template includes automated Dynamic Application Security Testing (DAST) using **OWASP ZAP** to detect runtime security issues by scanning your running site. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
# Start the site first
task start &
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
task start &

# Run DAST scan (requires Docker)
task ss:security:dast -- http://localhost:8080
```

Reports are saved to `.ss/reports/dast/`.

## For More Information

- **OWASP ZAP Documentation:** https://www.zaproxy.org/docs/
- **ZAP Baseline Scan:** https://www.zaproxy.org/docs/docker/baseline-scan/
- **Task Documentation:** https://taskfile.dev

---

# Dependency Vulnerability Scanning

This template includes automated dependency vulnerability scanning using **Trivy** to detect known CVEs in your project's dependencies. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
task ss:security:vulnerability:all
```

### What You Get Automatically
- ✅ PR comments with vulnerability report
- ✅ Merge blocking if any CRITICAL or HIGH vulnerabilities exist
- ✅ GitHub issues on main branch for blocking vulnerabilities

### Common Issues

| Problem | Solution |
|---------|----------|
| Workflow not triggering? | Check workflow is at `.github/workflows/ss-security-vulnerability-all-check.yml` |
| Want to change blocking threshold? | Edit severity check in `ss-security-vulnerability-all-check.yml` |
| Don't want vulnerability scans? | Delete `.github/workflows/ss-security-vulnerability-all-check.yml` |

### Severity Reference

| Severity | Status | Action |
|----------|--------|--------|
| CRITICAL | 🔴 Blocking | Must be fixed before merge |
| HIGH | 🟠 Blocking | Must be fixed before merge |
| MEDIUM | 🟡 Non-blocking | Review recommended |
| LOW | 🔵 Non-blocking | Update when convenient |

---

## Overview

What dependency scanning checks: **known CVEs in your project's packages** — npm dependencies, lock files, and other supported ecosystems.

The dependency scanning workflow:
- ✅ Runs automatically on every PR to `main` and push to `main`
- ✅ Scans the project filesystem with Trivy
- ✅ Posts vulnerability report as PR comments
- ✅ Creates GitHub issues when CRITICAL/HIGH vulnerabilities land on `main`
- ✅ Fails PRs with CRITICAL or HIGH vulnerabilities

## Local/CI Parity

Trivy is one of the few checks where local and CI can legitimately disagree on the same code — usually as "CI fails on a CVE the local run didn't flag." Treat CI as the canonical verdict when they diverge.

### Why they can disagree

- **24h DB cache.** Trivy caches its vulnerability database (macOS: `~/Library/Caches/trivy/db/`, Linux: `~/.cache/trivy/db/`) and reuses it for ~24 hours before redownloading. CI runs start cacheless and always pull the freshest DB, so your local trivy can be up to a day behind on newly-published CVEs.
- **Binary version.** CI installs trivy via `apt-get install -y trivy` (latest from the aquasecurity Debian repo). Local installs vary (`brew install trivy`, downloaded tarball, etc.). Different binary versions can ship different parsers, default checks, and output schemas — producing dramatic deltas independent of DB state.

### Diagnose

```bash
# Binary version on both sides — compare local against the CI workflow's "Install Trivy" step log
trivy --version

# Local DB age (macOS path; Linux: ~/.cache/trivy/db/metadata.json)
cat ~/Library/Caches/trivy/db/metadata.json | jq .UpdatedAt
```

### Resolve

- **Stale local DB** — clear the cache and rescan so local matches CI's cold-start behaviour:
  ```bash
  trivy clean --vuln-db && task ss:security:vulnerability:all
  ```
- **Binary version drift** — bump local trivy (`brew upgrade trivy` or re-download the release tarball) until `trivy --version` matches the workflow's installed version.

## Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/ss-security-vulnerability-all-check.yml` | GitHub Actions workflow |
| `Taskfile.ss.yml` (`vulnerability:all` task) | Local task runner shim → `slopstopper run security:vulnerability:all` |
| `cli/slopstopper/checks/vulnerability_all.py` | Check implementation (subprocess-invokes Trivy, renders MD report) |
| `.gitignore` | Excludes `.ss/reports/vulnerability-all/` |

## Key Configuration Points

### Change the Blocking Threshold

To block only on CRITICAL (not HIGH), edit the `check-dependencies` step in `ss-security-vulnerability-all-check.yml`:

```bash
# Change this line:
if v.get('Severity', '').upper() in ('CRITICAL', 'HIGH'):
# To:
if v.get('Severity', '').upper() == 'CRITICAL':
```

### Disable Dependency Scanning

```bash
# Option A: delete the workflow
rm .github/workflows/ss-security-vulnerability-all-check.yml

# Option B: disable in GitHub UI → Actions → Dependency Vulnerability Scan → Disable workflow
```

## Running Locally

```bash
# Install Task (one-time)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# Run dependency scan
task ss:security:vulnerability:all
```

Reports are saved to `.ss/reports/dependencies/`.

## For More Information

- **Trivy Documentation:** https://trivy.dev/
- **Task Documentation:** https://taskfile.dev

---

# Secrets Detection

This template includes automated secrets detection using **Gitleaks** to identify hardcoded credentials, API keys, and other sensitive data in your source code and git history. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
task ss:security:secrets
```

### What You Get Automatically
- ✅ PR comments with secrets detection report
- ✅ Merge blocking if any secrets are detected
- ✅ GitHub issues on main branch if secrets land there

### Common Issues

| Problem | Solution |
|---------|----------|
| Workflow not triggering? | Check workflow is at `.github/workflows/ss-security-secrets-check.yml` |
| False positives? | Add a `.gitleaks.toml` allowlist (see below) |
| Don't want secrets checks? | Delete `.github/workflows/ss-security-secrets-check.yml` |

---

## Overview

What secrets detection checks: **hardcoded credentials** — API keys, tokens, passwords, private keys, and other sensitive values in source code files and git history.

The secrets workflow:
- ✅ Runs automatically on every PR to `main` and push to `main`
- ✅ Scans all files and full git history with Gitleaks
- ✅ Posts findings as PR comments
- ✅ Creates GitHub issues when secrets land on `main`
- ✅ Fails PRs whenever secrets are detected (always blocking)

## Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/ss-security-secrets-check.yml` | GitHub Actions workflow |
| `Taskfile.ss.yml` (`secrets` task) | Local task runner shim → `slopstopper run security:secrets` |
| `cli/slopstopper/checks/secrets.py` | Check implementation (subprocess-invokes Gitleaks, renders MD report) |
| `.gitignore` | Excludes `.ss/reports/secrets/` |

## Suppressing False Positives

Create a `.gitleaks.toml` in the project root to allowlist known false positives:

```toml
[allowlist]
description = "Project allowlist"

# Allowlist a specific file
paths = [
  '''tests/fixtures/.*'''
]

# Allowlist a specific pattern (e.g. a test key)
regexes = [
  '''AKIAIOSFODNN7EXAMPLE'''
]

# Allowlist a specific commit
commits = [
  "abc123def456"
]
```

## If Secrets Are Detected

Act immediately:

1. **Revoke** the exposed credential (rotate API keys, invalidate tokens)
2. **Remove** the secret from the codebase
3. **Clean git history** if the secret was committed:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all
   ```
   Or use [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) for a simpler approach.
4. **Force-push** the cleaned history (coordinate with your team)

## Disable Secrets Checking

```bash
# Option A: delete the workflow
rm .github/workflows/ss-security-secrets-check.yml

# Option B: disable in GitHub UI → Actions → Secrets Detection → Disable workflow
```

## Running Locally

```bash
# Install Task (one-time)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# Run secrets detection
task ss:security:secrets
```

Reports are saved to `.ss/reports/secrets/`.
