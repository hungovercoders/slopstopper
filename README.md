# SlopStopper

**Portable code-quality suite — security, hygiene, reliability, accessibility, performance, operational automation.** Delivered as a Python CLI (`slopstopper-cli`) plus a small set of GitHub Actions workflows that drive it.

## Install

The CLI alone (most use cases):

```bash
pipx install slopstopper-cli
slopstopper checks list             # see what's available
slopstopper doctor                  # verify the external tools you'll need
slopstopper run hygiene:docs-size   # run a check (writes .ss/reports/...)
```

> Published to PyPI on every release tag. `pipx upgrade slopstopper-cli` pulls the latest. Each release is also attached to [GitHub Releases](https://github.com/hungovercoders/slopstopper/releases/latest) with a Sigstore build-provenance attestation — verify with `gh attestation verify <wheel> --owner hungovercoders`.

The full suite into a repo (CLI + GitHub Actions workflows + Taskfile shim + config seed):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

`install.sh` is idempotent — re-run any time to refresh workflows and `slopstopper-cli`.

## Contents

- [Prerequisites](#prerequisites)
- [What gets installed](#what-gets-installed)
- [What you get](#what-you-get)
- [What each check needs](#what-each-check-needs)
- [Same commands, both loops](#same-commands-both-loops)
- [Configure](#configure)
- [Update](#update)
- [Contribute](#contribute)
- [For agents (Claude, Copilot, Cursor)](#agents)
- [Dogfooded here — slopstopper.dev](#dogfooded-here--slopstopperdev)
- [Acknowledgements](#acknowledgements)
- [License](#license)

> 🗺️ **Documentation map:** [`docs/index.md`](./docs/index.md) is the single index of all project documentation. This README, [`AGENTS.md`](./AGENTS.md) and [`CLAUDE.md`](./CLAUDE.md) are deliberately thin entry points — all three defer to the map.

## Prerequisites

slopstopper-cli itself only needs Python. Each check subprocess-invokes its underlying tool (`semgrep`, `gitleaks`, `trivy`, `lizard`, `docker`, `node`) — deliberate licensing-boundary design. You install only the tools for checks you actually use; `slopstopper doctor` tells you what's installed and what's missing.

- **Python 3.11+** — `pipx` recommended (`brew install pipx`)

Per-check tools (skip if you've disabled the check):

| Tool | Needed by | Install hint |
| ---- | --------- | ------------ |
| `node` 20+ | Reliability checks (Playwright + Lighthouse), `slopstopper serve` | [nodejs.org](https://nodejs.org/) |
| `gh` | `slopstopper emit` (PR comments + issues from CI) | [cli.github.com](https://cli.github.com/) |
| `lizard` | `hygiene:complexity` | `pip install --user lizard` (**not** brew — that's lz4) |
| `semgrep` | `security:sast` | `pip install --user semgrep` |
| `gitleaks` | `security:secrets` | `brew install gitleaks` |
| `trivy` | `security:dependencies` | `brew install aquasecurity/trivy/trivy` |
| `docker` | `security:dast` | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |

Optional: **bash + git** (if using `install.sh`), **Task v3.x** (for the `task ss:*` shim layer).

## What gets installed

Everything SlopStopper owns lives under the `ss` namespace so it can't clash with files you already have.

| Item | Description |
| ---- | ----------- |
| `slopstopper-cli` (Python) | The product — every check runs through this. `pipx upgrade slopstopper-cli` refreshes it. |
| `.github/workflows/ss-*.yml` | Security, hygiene, reliability and operational workflows — all `ss-` prefixed |
| `Taskfile.ss.yml` | Thin `task ss:*` shims that call the CLI — convenient for the local dev loop |
| `Taskfile.yml` | Created if missing (else: prints the include block to paste in) |
| `.slopstopper.yml` | Config seed — URLs, headers, thresholds, page lists (never overwritten on re-run) |
| `.ss/reports/` | Where the CLI writes reports — `.gitignore`d |
| `package.json` | Created (or `devDependencies` merged into an existing file) |

Bundled Playwright specs, lighthouserc dev/prod, and the local-CI static server live inside the wheel — `slopstopper templates eject <name>` copies one into `.ss/` if you want to customise it.

## What you get

Five loops of feedback, all running on every PR and push to `main`:

| Loop | What it does | Tools | Docs |
| ---- | ------------ | ----- | ---- |
| 🔒 **Security** | SAST, DAST, secrets detection, dependency CVE scanning | Semgrep, OWASP ZAP, Gitleaks, Trivy | [Security →](./docs/security/README.md) |
| 🧹 **Hygiene** | Cyclomatic complexity caps, doc structure / accuracy / size checks, auto-labelled PRs | Lizard, Bandit, markdownlint | [Hygiene →](./docs/hygiene/README.md) |
| ✅ **Reliability** | E2E + smoke tests, internal broken-link audits, accessibility (WCAG 2.1 AA), Core Web Vitals, SEO + OpenGraph metatag checks | Playwright, axe-core, Lighthouse CI, stdlib Python | [Reliability →](./docs/reliability/README.md) |
| 🤖 **Runbooks** | Failed workflows auto-raise GitHub issues; an agentic doc updater opens weekly sync PRs | GitHub Actions, gh-aw | [Runbooks →](./docs/runbooks/README.md) |
| 🚀 **Deployment** | Preview deploys per PR, automated production releases, automatic preview cleanup | Cloudflare Workers Builds (Git integration) | [Deployment →](./docs/deployment/README.md) |

## What each check needs

The workflows split into three portability layers. Layer 1 runs the moment you install. Layers 2–3 need a small amount of configuration:

| Layer | Checks | What you provide |
| ----- | ------ | ---------------- |
| **1. Static analysis** (any code) | SAST, Secrets, Trivy, Dependency Review, Complexity, Doc Structure / Accuracy / Size, Auto-label PRs, Workflow-failure tracker | Nothing — works out of the box |
| **2. Web-app dynamic** (need a URL) | Smoke, Broken Links, Accessibility, Core Web Vitals, SEO Metatags, DAST, Playwright | `SMOKE_TEST_URL` · `BROKEN_LINKS_TEST_URL` · `ACCESSIBILITY_TEST_URL` · `LIGHTHOUSE_URL` · `SEO_TEST_URL` · optionally `*_PAGES` env vars |
| **3. Agentic doc-updater** | Weekly doc-sync PRs | `COPILOT_GITHUB_TOKEN` repo secret |

Don't use the doc-updater? Delete its workflows from `.github/workflows/` — re-running the installer respects deletions (tracked in `.ss/.workflows-installed`).

Deploy is intentionally not a layer: connect your repo in the Cloudflare dash (Workers & Pages → Create → Connect to Git) and you get production deploys, PR previews and preview cleanup for free. See [Deployment](./docs/deployment/README.md) for the cutover steps.

## Same commands, both loops

CI runs `slopstopper run <category>:<check>`. You run the same thing locally — same code, same report. The `task ss:*` shims are thin wrappers around the CLI for adopters who already drive their dev loop with `task`.

```bash
slopstopper run hygiene:complexity            # CLI
task ss:reliability:accessibility             # equivalent via the shim
slopstopper run security:sast --quiet         # suppress decorative output (CI logs)
```

## Configure

Most checks work out of the box. Things to wire up if you want the full suite:

**[`.slopstopper.yml`](./.slopstopper.yml.example)** at the repo root is the canonical config carrier. `install.sh` seeds a starter file with `headers.source: null` and empty URLs so the first PR is green; you opt knobs in by editing the file. Survives reinstalls.

**Repo secrets** (under Settings → Secrets and variables → Actions):

- `COPILOT_GITHUB_TOKEN` — for the agentic doc-updater (`ss-hygiene-doc-updater`), a [gh-aw](https://github.github.com/gh-aw/) workflow. Setup guide: [`docs/hygiene/DOC_UPDATER.md`](./docs/hygiene/DOC_UPDATER.md).

No secrets are needed for deploy — Cloudflare Workers Builds is connected via the Cloudflare GitHub App.

**Tuning files** (`.slopstopper.yml` covers most config; these handle the rest):

- Complexity gate — CCN > 10 threshold lives in `.github/workflows/ss-hygiene-complexity-check.yml` (awk filter on the lizard CSV)
- Lighthouse budgets — bundled in `cli/slopstopper/data/lighthouserc{,.prod}.json`; override via `.ss/`
- Doc size thresholds — `hygiene.docs_size.*` keys in [`.slopstopper.yml.example`](./.slopstopper.yml.example) (`max_total_size_kb`, `max_file_size_kb`, `max_files`)

## Update

CLI only:

```bash
pipx upgrade slopstopper-cli
```

Full suite (refreshes CLI + workflows + Taskfile shim — `.slopstopper.yml` and your customisations survive):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

## Contribute

Contributions are welcome. The full contributor guide lives in [`docs/contributing/README.md`](./docs/contributing/README.md) — short version:

- Branch from `main`, keep changes focused
- Run `slopstopper checks list` to see what's available
- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Open a PR; let the SlopStopper checks do their job

## Agents

If an AI agent (Claude, Copilot, Cursor, etc.) is working on this repo, the canonical conventions live in [`AGENTS.md`](./AGENTS.md). [`CLAUDE.md`](./CLAUDE.md) imports `AGENTS.md` so Claude Code picks up the same instructions automatically.

**Using Claude Code?** Install the [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) / [`slopstopper-update`](./.claude/skills/slopstopper-update/SKILL.md) / [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) skill trio once per machine — Claude Code auto-picks the right one per prompt. Runbook: [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md).

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
```

---

## Dogfooded here — slopstopper.dev

This repo hosts both **slopstopper-cli** (the product, under [`cli/`](./cli)) and **[slopstopper.dev](https://slopstopper.dev/)** — a live reference site that runs the same suite it advertises. The badges below are this repo's own CI: proof every check works in production, on every PR and push to `main`. Adopter pipelines will show their own badges in their own README — these are slopstopper.dev's.

### Pipeline status (slopstopper.dev's CI)

#### 🔒 Security
[![SAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml)
[![DAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml)
[![Secrets](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml)
[![Dependency Vulnerabilities](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml)
[![Dependency Review](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml)

#### 🧹 Hygiene
[![Complexity](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml)
[![Docs Accuracy](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml)
[![Docs Size](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml)
[![Docs Structure](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml)
[![Auto Label PRs](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml)

#### ✅ Reliability
[![Smoke Tests](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml)
[![Accessibility](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml)
[![Core Web Vitals](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml)
[![SEO Metatags](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml)
[![Broken Links](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml)

#### 🤖 Operational
[![Doc Auto-Updater](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml)
[![Failure Alerts](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml)

#### 🚀 Deployment
[![Site](https://img.shields.io/website?url=https%3A%2F%2Fslopstopper.dev&label=slopstopper.dev&up_message=up&down_message=down)](https://slopstopper.dev/)

Deployed via [Cloudflare Workers Builds](https://developers.cloudflare.com/workers/ci-cd/) — every push to `main` deploys, every PR gets a preview URL as a commit check.

### See it in action

📍 [**slopstopper.dev**](https://slopstopper.dev/) — live reference site, runs every check in this README on every change. Browse [Features](https://slopstopper.dev/features.html) to see each check's YAML and a mock report, or [Tools](https://slopstopper.dev/tools.html) for the technology stack.

## Acknowledgements

slopstopper-cli ships with no third-party Python dependencies — every check invokes its tool via `subprocess` only. Full credit, licences and upstream links for every tool we drive (Semgrep, Gitleaks, Trivy, Lizard, OWASP ZAP, Playwright, axe-core, Lighthouse CI, markdownlint-cli, Docker, GitHub CLI, Node.js) live in [`ATTRIBUTIONS.md`](./ATTRIBUTIONS.md).

## License

MIT — see [LICENSE](./LICENSE).
