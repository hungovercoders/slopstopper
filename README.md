# SlopStopper

**A Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo.** The CLI is `slopstopper-cli`; humans, agents and CI invoke every check through one `task ss:*` surface.

![slopstopper checks list, doctor and a hygiene check going green](./demos/hero.gif)

## Install

```bash
pipx install slopstopper-cli
slopstopper checks list             # what's available
slopstopper run hygiene:docs-size   # run one check (writes .ss/reports/...)
```

The installer puts the full suite into a repo (CLI pinned via [mise](https://mise.jdx.dev), workflows, Taskfile shims, config seed, Claude Code skills). It is idempotent, so re-run it any time to refresh:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

If the repo is an API or a library rather than a website, pass a profile through the same one-liner: `curl -fsSL … | bash -s -- --profile api` (or `library`). Only the checks that apply are then installed.

## Docs

- Adopting it: prerequisites, what gets installed, what each check needs, configure, update → [`docs/runbooks/INSTALL.md`](./docs/runbooks/INSTALL.md)
- Learning it from zero, one check per lesson: [`docs/learn/README.md`](./docs/learn/README.md)
- Working in this repo: [`AGENTS.md`](./AGENTS.md) carries the conventions and commands; [`docs/README.md`](./docs/README.md) routes to everything else
- For Claude Code, `install.sh` lands two skills in `<repo>/.claude/skills/`: `slopstopper-install` and `slopstopper-triage`
- Across an organisation, [slopstopper-steward](https://github.com/hungovercoders/slopstopper-steward) upgrades every adopter and works the issues the suite raised, one PR each

## Dogfooded here on slopstopper.dev

This repo hosts the CLI (under [`cli/`](./cli)) and [slopstopper.dev](https://slopstopper.dev/), a live reference site that runs the same suite it advertises. The badges are this repo's own CI, on every PR and push to `main`.

<!-- badges:begin -->
### 🔒 Security
[![API Headers](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-api-headers-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-api-headers-check.yml)
[![DAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-dast-check.yml)
[![Licences](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-licences-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-licences-check.yml)
[![SAST](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-sast-check.yml)
[![Secrets](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-secrets-check.yml)
[![Dependency CVEs](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-all-check.yml)
[![Dependency Review](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-security-vulnerability-new-check.yml)

### 🧹 Hygiene
[![Auto-label PRs](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-auto-label-pr.yml)
[![Complexity](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-complexity-check.yml)
[![CSP Exceptions](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-csp-exceptions-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-csp-exceptions-check.yml)
[![Docs Accuracy](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-accuracy-check.yml)
[![Docs Size](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-size-check.yml)
[![Docs Structure](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-docs-structure-check.yml)
[![Entry Files](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-entry-files-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-entry-files-check.yml)
[![OpenAPI Drift](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-openapi-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-openapi-check.yml)
[![Privacy Statement](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-privacy-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-privacy-check.yml)

### ✅ Reliability
[![Accessibility](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-accessibility-check.yml)
[![API Health](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-health-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-health-check.yml)
[![API Latency](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-latency-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-api-latency-check.yml)
[![Broken Links](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-broken-links-check.yml)
[![Core Web Vitals](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-core-web-vitals.yml)
[![E2E](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-e2e-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-e2e-check.yml)
[![llms.txt](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-llms-txt-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-llms-txt-check.yml)
[![robots.txt](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-robots-txt-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-robots-txt-check.yml)
[![SEO](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-seo-check.yml)
[![Sitemap](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-sitemap-check.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-sitemap-check.yml)
[![Smoke](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-reliability-smoke-tests.yml)

### 🤖 Operational
[![Deployed Checks](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-cloudflare-deployed.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-cloudflare-deployed.yml)
[![Doc Updater](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-hygiene-doc-updater.lock.yml)
[![Release](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-release.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-release.yml)
[![Workflow Failures](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml/badge.svg?branch=main)](https://github.com/hungovercoders/slopstopper/actions/workflows/ss-workflow-failure-issue.yml)
<!-- badges:end -->

### 🚀 Deployment

slopstopper.dev ships through Cloudflare Workers Builds, which `install.sh` does not set up. See [`docs/deployment/README.md`](./docs/deployment/README.md) to copy the setup.

[![Site](https://img.shields.io/website?url=https%3A%2F%2Fslopstopper.dev&label=slopstopper.dev&up_message=up&down_message=down)](https://slopstopper.dev/)

## License

MIT; the full text is in [LICENSE](./LICENSE). Tool credits and licences are in [`ATTRIBUTIONS.md`](./ATTRIBUTIONS.md).
