# Security

Security scanning and controls: what each check guards, and where its
full guide lives. Read only the doc whose trigger matches.

## Routes

| When you are…                                                        | Do this                                                                 |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| tuning Semgrep rules, suppressing a SAST finding, or moving `security.sast.fail_on` | Read [SAST.md](SAST.md) — the Semgrep check, its suppressions table and knobs |
| configuring or debugging the OWASP ZAP scan (baseline or OpenAPI mode) | Read [DAST.md](DAST.md) — local commands, CI wiring, risk levels, the CSP-exception gate, `api.openapi.spec` |
| fixing a Trivy CVE finding, or when local and CI disagree on one      | Read [DEPENDENCIES.md](DEPENDENCIES.md) — the Trivy scan, the licence gate, local/CI parity |
| handling a Gitleaks finding or allowlisting a false positive          | Read [SECRETS.md](SECRETS.md) — the Gitleaks scan, the allowlist file, what to do when a secret lands |
| adding a third-party script, widget or any external resource to a page | Read [CSP_EXCEPTIONS.md](CSP_EXCEPTIONS.md) first — the strict-default + per-path exception pattern and the live list |
| auditing CORS, HSTS or `nosniff` on a JSON API                        | Read [API_HEADERS.md](API_HEADERS.md) — the findings, the hard-fail split, knobs and commands |

## API Headers & CORS

On a JSON API, CORS — not CSP — decides who may read a response. `security:api-headers` audits that policy, plus HSTS and `nosniff`. The route above holds the detail.

## CSP Exceptions

The site ships a strict `default-src 'self'; script-src 'self'` Content
Security Policy on every path. When a third-party widget is genuinely
required on a single page (e.g. Giscus on `/feedback.html`), we admit it
via a **scoped, documented, SRI-pinned per-path exception** rather than
weakening the site-wide CSP. The
[`ss:hygiene:csp-exceptions`](../../Taskfile.ss.yml) check enforces drift
between `worker/headers.json` and the exceptions doc routed above.

**For adopters:** this is the pattern to reuse the moment your site needs
GTM, Sentry, Intercom or any analytics tag. Copy the schema, drop the
hygiene check via the installer, and your auditors will thank you.

## SAST — Static Application Security Testing

Semgrep scans **your own source code** for vulnerabilities and anti-patterns. Findings at or above `security.sast.fail_on` (default `error`) block the PR; the check fails closed when Semgrep produces no readable report.

## DAST — Dynamic Application Security Testing

OWASP ZAP scans the running app for common web vulnerabilities. Two modes: the
**baseline** scan spiders an HTML site, and the **API** scan reads an OpenAPI
spec and exercises its operations — the only mode that finds anything on a
JSON API.

## Dependency Vulnerability Scanning

Trivy scans the project filesystem for known CVEs; CRITICAL and HIGH block the PR. A companion GitHub-native workflow, `ss-security-vulnerability-new-check.yml`, reviews newly-introduced dependencies on PRs and fails on a denied (copyleft) licence.

## Secrets Detection

Gitleaks scans all files and the full git history for hardcoded credentials. Any finding blocks; the check never writes the credential to disk.

## Running everything

```bash
task ss:security:scan     # SAST + secrets + dependency scan, sequenced
```

Reports land under `.ss/reports/<check>/`.
