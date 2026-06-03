# SlopStopper

**Deterministic, automated quality feedback for AI-driven development — drop it into any repo with one command.**

SlopStopper is a portable suite of GitHub Actions workflows, Task targets and
analysis scripts that you install into an existing repository to get a
consistent quality pipeline: security, hygiene, reliability, accessibility,
performance, and operational automation — all running on every pull request
and push to `main`.

📍 **Live reference site:** see [slopstopper.dev](https://slopstopper.dev/) — built with the same suite it advertises.

> 🪞 **Dogfooded here.** Every badge below is real. This repo runs the same suite it ships, on every PR and push to `main`.

> 🗺️ **Documentation map:** [`docs/index.md`](./docs/index.md) is the single index of all project documentation. This README, [`AGENTS.md`](./AGENTS.md) and [`CLAUDE.md`](./CLAUDE.md) are deliberately thin entry points — all three defer to the map so each audience (humans, agents, AI assistants) has one short file to read and one shared place to find the truth. The [hygiene docs-structure check](./docs/hygiene/README.md) enforces that the map stays in sync with the directory tree.

## Pipeline status

Every check below runs on every PR and push to `main` here, and ships to consumers via [`install.sh`](./install.sh). Netlify and Doc-Updater workflows are included by default but are inert until you add their secrets (see [Configure](#configure)).

### 🔒 Security
[![SAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml)
[![DAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml)
[![Secrets](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml)
[![Dependency Vulnerabilities](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml)
[![Dependency Review](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml)

### 🧹 Hygiene
[![Complexity](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml)
[![Docs Accuracy](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml)
[![Docs Size](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml)
[![Docs Structure](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml)
[![Auto Label PRs](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml)

### ✅ Reliability
[![Playwright](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-playwright-tests.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-playwright-tests.yml)
[![Smoke Tests](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml)
[![Accessibility](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml)
[![Core Web Vitals](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml)

### 🤖 Operational
[![Doc Auto-Updater](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml)
[![Failure Alerts](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml)

### 🚀 Deployment
[![Netlify Deploy](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-netlify-deploy.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-netlify-deploy.yml)
[![Preview Cleanup](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-netlify-cleanup-preview.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-netlify-cleanup-preview.yml)

---

## Prerequisites

- **Bash + Git** — installer + workflow runners
- **Node 20+** — Playwright, Lighthouse CI, markdownlint, TypeScript build
- **Python 3.10+** — all analysis scripts (`.ss/scripts/`) are Python
- **Task v3.x** — canonical interface for every check; `curl -sL https://taskfile.dev/install.sh | sh`
- **Docker** — only needed for DAST (OWASP ZAP runs in a container)

## Install

From inside the repo you want to add SlopStopper to:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

Or, if you prefer to review the script first (recommended):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
bash install.sh [TARGET_DIR]
```

The installer is idempotent — re-run any time to pull in new checks.
Everything SlopStopper owns lives under the `ss` namespace so it can't
clash with files you already have, and SlopStopper-owned files
(`Taskfile.ss.yml`, `.ss/`, `.github/workflows/ss-*.yml`) are refreshed on
re-run.

### What gets installed

| Item | Description |
| ---- | ----------- |
| `Taskfile.ss.yml` | All SlopStopper task definitions (always refreshed on re-run) |
| `Taskfile.yml` | Thin root file with `includes: { ss: ./Taskfile.ss.yml }` — created if you don't have one; if you do, the installer prints the block to paste in |
| `.ss/scripts/` | Python/shell analysis scripts (always refreshed) |
| `.ss/reports/` | Generated scan output — `.gitignore`d |
| `.github/workflows/ss-*.yml` | Security, hygiene, reliability and operational workflows — all `ss-` prefixed and named `SlopStopper · …` so they group together in your Actions UI |
| `package.json` | Created (or `devDependencies` merged into an existing file) |

### After installing

```bash
# 1. Install the Task runner (if you don't have it)
curl -sL https://taskfile.dev/install.sh | sh -s -- -b /usr/local/bin

# 2. Install npm dependencies
npm install

# 3. See all available tasks
task --list

# 4. Open a pull request — every check runs automatically
```

**First-run note:** the first time you run any check (e.g. `task ss:hygiene:complexity`), SlopStopper auto-installs the underlying tool (Lizard, Semgrep, Trivy, Gitleaks…) via pip or curl. Expect a one-time delay — subsequent runs are fast.

---

## What you get

Five loops of feedback, all running on every PR and push to `main`:

| Loop | What it does | Tools | Docs |
| ---- | ------------ | ----- | ---- |
| 🔒 **Security** | SAST, DAST, secrets detection, dependency CVE scanning | Semgrep, OWASP ZAP, Gitleaks, Trivy | [Security →](./docs/security/README.md) |
| 🧹 **Hygiene** | Cyclomatic complexity caps, doc structure / accuracy / size checks, auto-labelled PRs | Lizard, Bandit, markdownlint | [Hygiene →](./docs/hygiene/README.md) |
| ✅ **Reliability** | E2E + smoke tests, accessibility audits (WCAG 2.1 AA), Core Web Vitals | Playwright, axe-core, Lighthouse CI | [Reliability →](./docs/reliability/README.md) |
| 🤖 **Operational** | Failed workflows auto-raise GitHub issues; an agentic doc updater opens weekly sync PRs | GitHub Actions, gh-aw | [Runbooks →](./docs/runbooks/README.md) |
| 🚀 **Deployment** | Preview deploys per PR, automated production releases, preview cleanup | Netlify, GitHub Actions | [Deployment →](./docs/deployment/README.md) |

### What each check needs

The 19 workflows split into four portability layers. Layer 1 runs the moment you install. Layers 2–3 need a small amount of configuration:

| Layer | Checks | What you provide |
| ----- | ------ | ---------------- |
| **1. Static analysis** (any code) | SAST, Secrets, Trivy, Dependency Review, Complexity, Doc Structure / Accuracy / Size, Auto-label PRs, Workflow-failure tracker | Nothing — works out of the box |
| **2. Web-app dynamic** (need a URL) | Smoke, Accessibility, Core Web Vitals, DAST, Playwright | `SMOKE_TEST_URL` · `ACCESSIBILITY_TEST_URL` · `LIGHTHOUSE_URL` · optionally `SMOKE_PAGES` / `ACCESSIBILITY_PAGES` |
| **3. Netlify deploy** | Preview deploys, production releases, preview cleanup | `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID` repo secrets |
| **4. Agentic doc-updater** | Weekly doc-sync PRs | `ANTHROPIC_API_KEY` repo secret |

Don't use Netlify or the doc-updater? Delete those workflows from `.github/workflows/` — re-running the installer respects deletions (tracked in `.ss/.workflows-installed`).

### Same commands, both loops

Every check is just a `task ss:<name>` command, defined once in
`Taskfile.ss.yml`. You run it locally for instant feedback. CI runs the
exact same command. No drift between what you ran and what the pipeline
ran — fast inner loop, consistent outer loop, identical behaviour.

```bash
task ss:hygiene:complexity            # locally
task ss:reliability:accessibility     # locally
task ss:security:sast                 # locally
```

The CI workflows call the same `task` targets (or a `:ci` variant that
delegates to the same definition). One source of truth.

---

## Configure

Most checks work out of the box. Things to wire up if you want the full suite:

**Repo secrets** (under your repo's Settings → Secrets and variables → Actions):

- `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID` — for the Netlify deploy + preview cleanup workflows
- `ANTHROPIC_API_KEY` — for the agentic doc-updater (`ss-hygiene-doc-updater`)

**Tunable env vars** (set in workflows or locally):

- `ACCESSIBILITY_TEST_URL` / `SMOKE_TEST_URL` / `LIGHTHOUSE_URL` — point the dynamic checks at your app
- `ACCESSIBILITY_PAGES` / `SMOKE_PAGES` — comma-separated paths to audit (default `/`)
- `ACCESSIBILITY_IMPACT` — `critical` / `serious` / `moderate` / `minor` (default `serious`) — see [`docs/reliability/ACCESSIBILITY.md`](./docs/reliability/ACCESSIBILITY.md)
- `ACCESSIBILITY_THRESHOLD` — max violations before failing (default `0`)

**Files you can edit** for permanent tuning:

- Complexity caps — see [`docs/hygiene/COMPLEXITY_CONFIG.md`](./docs/hygiene/COMPLEXITY_CONFIG.md)
- Lighthouse budgets — `.ss/lighthouserc.json` (PR/dev) and `.ss/lighthouserc.prod.json` (production)
- Doc size thresholds — see [`docs/hygiene/DOCS_SIZE_MONITORING.md`](./docs/hygiene/DOCS_SIZE_MONITORING.md)

---

## Update

Re-run the installer to pull in new checks or updated scripts. Existing files
aren't overwritten, so your customisations are preserved — review the diff
afterwards.

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

---

## Run the demo site locally

This repo also hosts the SlopStopper marketing site (the same set of HTML
pages you'd see at the live URL). To run it yourself:

```bash
npm install
npm run build      # compiles TypeScript
npm start          # serves app/ on http://localhost:8080
```

`server.js` parses `netlify.toml` so local headers match production.

---

## Contribute

Contributions are welcome. The full contributor guide lives in
[`docs/contributing/README.md`](./docs/contributing/README.md) — short
version:

- Branch from `main`, keep changes focused
- Run `task --list` to see check tasks before pushing
- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Open a PR; let the SlopStopper checks do their job

---

## Agents

If an AI agent (Claude, Copilot, Cursor, etc.) is working on this repo, the
canonical conventions and constraints live in [`AGENTS.md`](./AGENTS.md).
[`CLAUDE.md`](./CLAUDE.md) imports `AGENTS.md` so Claude Code picks up the
same instructions automatically.

---

## License

MIT — see [LICENSE](./LICENSE) if present, or the package metadata.
