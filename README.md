# SlopStopper

**A Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo.** The CLI is `slopstopper-cli`; humans, agents and CI invoke every check through one `task ss:*` surface.

## Install

```bash
pipx install slopstopper-cli
slopstopper checks list             # what's available
slopstopper run hygiene:docs-size   # run one check (writes .ss/reports/...)
```

The full suite into a repo (CLI pinned via [mise](https://mise.jdx.dev), workflows, Taskfile shims, config seed, Claude Code skills). Idempotent — re-run to refresh:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

Not a website? `--profile api` or `--profile library` installs only the checks that apply.

## Docs

- Adopting it: prerequisites, what gets installed, what each check needs, configure, update → [`docs/runbooks/INSTALL.md`](./docs/runbooks/INSTALL.md)
- Working in this repo: [`AGENTS.md`](./AGENTS.md) carries the conventions and commands; [`docs/README.md`](./docs/README.md) routes to everything else
- Using Claude Code? `install.sh` lands two skills in `<repo>/.claude/skills/`: `slopstopper-install` and `slopstopper-triage`

## Dogfooded here — slopstopper.dev

This repo hosts the CLI (under [`cli/`](./cli)) and [slopstopper.dev](https://slopstopper.dev/), a live reference site that runs the same suite it advertises. The badges are this repo's own CI, on every PR and push to `main`.

### 🔒 Security

[![SAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml)
[![DAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml)
[![Secrets](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml)
[![Dependency Vulnerabilities](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml)
[![Dependency Review](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml)
[![API Headers](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-api-headers-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-api-headers-check.yml)

### 🧹 Hygiene

[![Complexity](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml)
[![Docs Accuracy](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml)
[![Docs Size](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml)
[![Docs Structure](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml)
[![OpenAPI Drift](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-openapi-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-openapi-check.yml)
[![Auto Label PRs](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml)

### ✅ Reliability

[![Smoke Tests](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml)
[![Accessibility](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml)
[![Core Web Vitals](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml)
[![SEO Metatags](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml)
[![Broken Links](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml)
[![llms.txt](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-llms-txt-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-llms-txt-check.yml)
[![robots.txt](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-robots-txt-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-robots-txt-check.yml)
[![sitemap](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-sitemap-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-sitemap-check.yml)
[![API Health](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-health-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-health-check.yml)
[![API Latency](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-latency-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-latency-check.yml)

### 🤖 Operational

[![Doc Auto-Updater](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml)
[![Failure Alerts](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml)

### 🚀 Deployment

How this site ships (Cloudflare Workers Builds). `install.sh` adds no deploy step — see [`docs/deployment/README.md`](./docs/deployment/README.md) to copy the setup.

[![Site](https://img.shields.io/website?url=https%3A%2F%2Fslopstopper.dev&label=slopstopper.dev&up_message=up&down_message=down)](https://slopstopper.dev/)

## License

MIT — see [LICENSE](./LICENSE). Tool credits and licences: [`ATTRIBUTIONS.md`](./ATTRIBUTIONS.md).
