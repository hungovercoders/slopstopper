# Security

Security scanning and controls for this project: what each `security:*` check
looks at, how it blocks, and where to tune it. One file per check; this page
is the map.

## Contents

| Check | Tool | Blocks on | Detail |
| ----- | ---- | --------- | ------ |
| `security:sast` | Semgrep | findings at or above `security.sast.fail_on` (default ERROR) in your own code | [SAST.md](SAST.md) |
| `security:dast` | OWASP ZAP | High / Medium alerts on the running site or API | [DAST.md](DAST.md) |
| `security:vulnerability:all` | Trivy | CRITICAL / HIGH CVEs in dependencies | [VULNERABILITY.md](VULNERABILITY.md) |
| `security:secrets` | Gitleaks | any secret, in files or git history | [SECRETS.md](SECRETS.md) |
| `security:api-headers` | stdlib Python | credentialed CORS wildcards, missing HSTS / `nosniff` | [API_HEADERS.md](API_HEADERS.md) |
| `hygiene:csp-exceptions` | stdlib Python | drift between `worker/headers.json` and the exceptions doc | [CSP_EXCEPTIONS.md](CSP_EXCEPTIONS.md) |

Every check follows the same shape: run it locally with
`task ss:security:<check>`, read the report under `.ss/reports/<check>/`,
get a PR comment on pull requests and a GitHub issue when a blocking
finding lands on `main`. Disable one by listing its workflow under
`workflows.disabled` in `.slopstopper.yml` (or by choosing a
[profile](../architecture/README.md) that drops it).

## SAST — Static Application Security Testing

Semgrep pattern-matches **your own source code** for dangerous calls,
injection risks and hardcoded secrets. ERROR blocks; WARNING and INFO are
reported; `security.sast.fail_on` moves that line. Narrow, documented
`nosemgrep` suppressions beat disabling a rule.

→ [SAST.md](SAST.md): quick start, severity table, the suppression pattern
and this repo's current suppressions.

## DAST — Dynamic Application Security Testing

OWASP ZAP scans the running app for common web vulnerabilities. Two modes: the
**baseline** scan spiders an HTML site, and the **API** scan reads an OpenAPI
spec and exercises its operations — the only mode that finds anything on a
JSON API.

→ [DAST.md](DAST.md): local commands, the CI wiring, risk levels, the
CSP-exception gate and the `api.openapi.spec` knob.

## Dependency Vulnerability Scanning

Trivy scans the project filesystem for known CVEs in your packages and lock
files. CRITICAL and HIGH block. A companion GitHub-native workflow
(`ss-security-vulnerability-new-check.yml`) reviews newly-added dependencies
on PRs and fails on denied (copyleft) licences.

→ [VULNERABILITY.md](VULNERABILITY.md): quick start, why local and CI can
disagree (DB cache, binary version) and how to resolve it, the licence gate.

## Secrets Detection

Gitleaks scans all files **and full git history** for credentials, tokens
and private keys. Always blocking. Allowlist known false positives in
`.gitleaks.toml`.

→ [SECRETS.md](SECRETS.md): quick start, the allowlist format, and what to
do the moment a real secret is detected.

## CSP Exceptions

The site ships a strict `default-src 'self'; script-src 'self'` Content
Security Policy on every path. When a third-party widget is genuinely
required on a single page (e.g. Giscus on `/feedback.html`), we admit it
via a **scoped, documented, SRI-pinned per-path exception** rather than
weakening the site-wide CSP. The
[`ss:hygiene:csp-exceptions`](../../Taskfile.ss.yml) check enforces drift
between `worker/headers.json` and that document.

→ [CSP_EXCEPTIONS.md](CSP_EXCEPTIONS.md): the pattern and the live list of
exceptions. **For adopters:** this is the pattern to reuse the moment your
site needs GTM, Sentry, Intercom or any analytics tag.

## API Headers & CORS

On a JSON API, CORS — not CSP — decides who may read a response.
`security:api-headers` audits that policy, plus HSTS and `nosniff`, and
splits findings into hard failures and advisory notes.

→ [API_HEADERS.md](API_HEADERS.md): the findings, the hard-fail split,
knobs and commands.
