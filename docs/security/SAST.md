# SAST — Static Application Security Testing

This template includes automated Static Application Security Testing (SAST) using **Semgrep** to detect security bugs and anti-patterns in your own source code. This guide explains how to customise and use this feature.

## Quick Start

### Run Analysis Locally
```bash
task ss:security:sast
```

### What You Get Automatically
- ✅ PR comments with SAST findings report
- ✅ Merge blocking on findings at or above `security.sast.fail_on` (default: ERROR)
- ✅ GitHub issues on main branch when blocking findings land

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
- ✅ Creates GitHub issues when blocking findings land on `main` (a scan that couldn't run fails the job but opens no issue)
- ✅ Fails PRs with blocking findings, and fails closed when Semgrep produces no readable report or exits with an error

## Files Involved

| File | Purpose |
|------|---------|
| `.github/workflows/ss-security-sast-check.yml` | GitHub Actions workflow |
| `Taskfile.ss.yml` (`sast` task) | Local task runner shim → `slopstopper run security:sast` |
| `cli/slopstopper/checks/sast.py` | Check implementation (subprocess-invokes Semgrep, renders MD report) |
| `.gitignore` | Excludes `.ss/reports/sast/` |

## Key Configuration Points

### Rule set

The check runs Semgrep with `--config=auto` (Semgrep picks rules from the languages it detects). The flag is set in `cli/slopstopper/checks/sast.py`, not in a task or workflow, and there is no `.slopstopper.yml` knob for it today — tune individual rules with the inline `nosemgrep` suppressions above, or open an issue if you need a project-wide ruleset such as `p/owasp-top-ten`.

### Failure threshold

Semgrep reports findings at ERROR, WARNING and INFO severity. By default only ERROR fails the check; the rest are reported. `security.sast.fail_on` in `.slopstopper.yml` moves the line — `warning` makes warnings block too, `none` reports without ever failing. The check's exit code is the verdict; the workflow no longer re-counts findings in a separate step.

```yaml
security:
  sast:
    fail_on: error   # error | warning | info | none
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
