# Security

Security scanning and controls for this project: what each `security:*` check
looks at, how it blocks, and where to tune it. One file per check; this page
is the map, so read only the doc whose trigger matches.

## Routes

| When you are…                                                        | Do this                                                                 |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| tuning what SAST blocks, or suppressing a Semgrep finding            | Read [SAST.md](SAST.md) for the quick start, severity table, `security.sast.fail_on`, the suppression pattern and this repo's suppressions |
| configuring or debugging the OWASP ZAP scan (baseline or OpenAPI mode) | Read [DAST.md](DAST.md) for local commands, CI wiring, risk levels, the CSP-exception gate and `api.openapi.spec` |
| fixing a Trivy CVE finding, or when local and CI disagree on one      | Read [VULNERABILITY.md](VULNERABILITY.md) for the Trivy scan, the licence gate and local/CI parity (DB cache, binary version) |
| handling a Gitleaks finding or allowlisting a false positive          | Read [SECRETS.md](SECRETS.md) for the quick start, the allowlist format and what to do the moment a real secret is detected |
| adding a third-party script, widget or any external resource to a page | Read [CSP_EXCEPTIONS.md](CSP_EXCEPTIONS.md) first for the strict-default + per-path exception pattern and the live list |
| auditing CORS, HSTS or `nosniff` on a JSON API                        | Read [API_HEADERS.md](API_HEADERS.md) for the findings, the hard-fail split, knobs and commands |

| Check | Tool | Blocks on |
| ----- | ---- | --------- |
| `security:sast` | Semgrep | findings at or above `security.sast.fail_on` (default ERROR) in your own code |
| `security:dast` | OWASP ZAP | High / Medium alerts on the running site or API |
| `security:vulnerability:all` | Trivy | CRITICAL / HIGH CVEs in dependencies |
| `security:secrets` | Gitleaks | any secret, in files or git history |
| `security:api-headers` | stdlib Python | credentialed CORS wildcards, missing HSTS / `nosniff` |
| `hygiene:csp-exceptions` | stdlib Python | drift between `worker/headers.json` and the exceptions doc |

Every check follows the same shape: run it locally with the `task`
target named after it (`task ss:security:sast`,
`task ss:hygiene:csp-exceptions`), read the report its page names under
`.ss/reports/`, get a PR comment on pull requests and a GitHub issue when a
blocking finding lands on `main`. Disable one by listing its workflow under
`workflows.disabled` in `.slopstopper.yml` (or by choosing a
[profile](../architecture/PROFILES.md) that drops it). `task ss:security:scan`
runs SAST, secrets and the dependency scan in sequence.

## Static Application Security Testing (SAST)

Semgrep pattern-matches **your own source code** for dangerous calls,
injection risks and hardcoded secrets. ERROR blocks; WARNING and INFO are
reported; `security.sast.fail_on` moves that line. Narrow, documented
`nosemgrep` suppressions beat disabling a rule.

## Dynamic Application Security Testing (DAST)

OWASP ZAP scans the running app for common web vulnerabilities. It has two
modes. The **baseline** scan spiders an HTML site, and the **API** scan reads
an OpenAPI spec and exercises its operations. Only the API scan finds
anything on a JSON API.

## Dependency Vulnerability Scanning

Trivy scans the project filesystem for known CVEs in your packages and lock
files. CRITICAL and HIGH block. A companion GitHub-native workflow
(`ss-security-vulnerability-new-check.yml`) reviews newly-added dependencies
on PRs and fails on denied (copyleft) licences.

## Secrets Detection

Gitleaks scans all files **and full git history** for credentials, tokens
and private keys. Always blocking; the check never writes the credential to
disk. Allowlist known false positives in the file SECRETS.md describes.

## CSP Exceptions

The site ships a strict `default-src 'self'; script-src 'self'` Content
Security Policy on every path. When a third-party widget is genuinely
required on a single page (e.g. Giscus on `/feedback.html`), we admit it
via a **scoped, documented, SRI-pinned per-path exception** rather than
weakening the site-wide CSP. The
[`ss:hygiene:csp-exceptions`](../../Taskfile.ss.yml) check enforces drift
between `worker/headers.json` and the exceptions doc routed above. **For
adopters:** this is the pattern to reuse the moment your site needs GTM,
Sentry, Intercom or any analytics tag.

## API Headers & CORS

On a JSON API, CORS rather than CSP decides who may read a response.
`security:api-headers` audits that policy, plus HSTS and `nosniff`, and
splits findings into hard failures and advisory notes.
