# Adopting SlopStopper

Everything an adopter needs once: prerequisites, what `install.sh` writes,
what each check needs from you, how to run the suite, configure it and
move the CLI pin. The [README](../../README.md) holds the two install
commands; this is the rest.

## Prerequisites

mise pins + installs `slopstopper-cli`; each check subprocess-invokes its own tool (`semgrep`, `gitleaks`, `trivy`, `docker`, `node`). `slopstopper doctor` reports what's missing.

- **[mise](https://mise.jdx.dev)** — required; installs the pinned `slopstopper-cli` + `task`, activated per-directory (CI uses `jdx/mise-action`)
- **Python 3.11+** — mise's pipx backend needs it on PATH

Per-check tools (skip any check your profile drops):

| Tool | Needed by | Install hint |
| ---- | --------- | ------------ |
| `node` 20+ | Reliability checks (Playwright + Lighthouse), `slopstopper serve` | [nodejs.org](https://nodejs.org/) |
| `gh` | `slopstopper emit` (PR comments + issues from CI) | [cli.github.com](https://cli.github.com/) |
| `semgrep` | `security:sast` | `pip install --user semgrep` |
| `gitleaks` | `security:secrets` | `brew install gitleaks` |
| `trivy` | `security:vulnerability:all` | `brew install aquasecurity/trivy/trivy` |
| `docker` | `security:dast` | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |

Optional: **bash + git** (if using `install.sh`), **Task v3.x** (for the `task ss:*` shim layer).

## What gets installed

Everything SlopStopper owns lives under the `ss` namespace so it can't clash with files you already have.

| Item | Description |
| ---- | ----------- |
| `slopstopper-cli` (Python) | The product — every check runs through this. Pinned per-repo in `mise.toml` (`"pipx:slopstopper-cli"`) and installed via mise. |
| `.github/workflows/ss-*.yml` | Security, hygiene, reliability and operational workflows |
| `.github/actions/ss-*/` | Composite steps the workflows share (setup, URL resolution); replaced on refresh |
| `Taskfile.ss.yml` | Thin `task ss:*` shims that call the CLI — convenient for the local dev loop |
| `Taskfile.yml` | Created if missing (else: prints the include block to paste in) |
| `.githooks/pre-push` | Pre-push hygiene gate (`--no-hooks` opts out; defers to husky/lefthook/pre-commit) |
| `mise.toml` | Toolchain pin (`slopstopper-cli`, `task`), read locally and in CI; moved by `--upgrade-cli`/`--cli-version` |
| `.slopstopper.yml` | Config starter — profile, URLs, headers, page lists (never overwritten) |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/README.md` | AGENTS.md-first entry-file scaffolds, seeded only when absent |
| `.claude/skills/slopstopper-*/` | The `slopstopper-install` and `slopstopper-triage` Claude Code skills (`--no-skills` opts out) |
| `.ss/reports/` | Where the CLI writes reports — `.gitignore`d |
| `package.json` | Created (or `devDependencies` merged into an existing file) |

Bundled Playwright specs, lighthouserc dev/prod, and the local-CI static server live inside the wheel — `slopstopper templates eject <name>` copies one into `.ss/` to customise.

## What you get

Five loops of feedback, all running on every PR and push to `main`:

| Loop | What it does | Tools | Docs |
| ---- | ------------ | ----- | ---- |
| 🔒 **Security** | SAST, DAST, secrets detection, dependency CVEs, API header + CORS audit | Semgrep, OWASP ZAP, Gitleaks, Trivy | [Security →](../security/README.md) |
| 🧹 **Hygiene** | Complexity caps, docs structure/accuracy/size and entry-file checks, OpenAPI drift, auto-labelled PRs | Lizard, stdlib Python | [Hygiene →](../hygiene/README.md) |
| ✅ **Reliability** | E2E + smoke tests, broken-link audits, accessibility (WCAG 2.1 AA), Core Web Vitals, SEO metatags, llms.txt, robots.txt, sitemap.xml, API health + latency | Playwright, axe-core, Lighthouse CI, stdlib Python | [Reliability →](../reliability/README.md) |
| 🤖 **Runbooks** | One rolling PR comment summarises every check; failed workflows auto-raise issues; an agentic doc updater opens weekly sync PRs | GitHub Actions, gh-aw | [Runbooks →](./README.md) |
| 🚀 **Deployment** | Preview deploys per PR, automated production releases, automatic preview cleanup | Cloudflare Workers Builds (Git integration) | [Deployment →](../deployment/README.md) |

## What each check needs

Three portability layers. Layer 1 runs on install; layers 2–3 need a little config:

| Layer | Checks | What you provide |
| ----- | ------ | ---------------- |
| **1. Static analysis** (any code) | SAST, Secrets, Trivy, Dependency Review, Complexity, Doc Structure/Accuracy/Size, Entry Files, Auto-label PRs, Workflow-failure tracker | Nothing — works out of the box |
| **2. Deployed surface** (need a URL) | Smoke, Broken Links, Accessibility, Core Web Vitals, SEO Metatags, llms.txt, robots.txt, sitemap.xml, DAST, Playwright, API Health/Latency/Headers, OpenAPI Drift | `urls.production` / `urls.preview` in `.slopstopper.yml` ([per-check env vars](../reliability/README.md) also work) |
| **3. Agentic doc-updater** | Weekly doc-sync PRs | `COPILOT_GITHUB_TOKEN` repo secret |

Don't use a check? Delete its workflow or list it under `workflows.disabled` — re-runs respect both. Not a website? `--profile api` (or `library`) installs only the applicable checks — see [Profiles](../architecture/PROFILES.md).

Deploy is intentionally not a layer: connect your repo in the Cloudflare dash for production deploys, PR previews and preview cleanup. See [Deployment](../deployment/README.md).

## Same commands, both loops

`task ss:<category>:<check>` is the canonical interface — humans, agents and CI all go through it, so the suite shares one invocation surface with the rest of your codebase. The shims call `slopstopper-cli` under the hood; pass `--no-task` to `install.sh` to skip Task and have workflows call the CLI directly.

```bash
task ss:hygiene:complexity                    # the canonical form
task ss:reliability:accessibility -- http://localhost:8080
task ss:security:sast                         # CI runs the same line
slopstopper run hygiene:complexity            # underlying CLI if you skip Task
```

## Configure

Most checks work out of the box. To wire up the full suite:

**[`.slopstopper.yml`](../../.slopstopper.yml.example)** at the repo root is the config file. `install.sh` seeds a starter (`profile`, URLs, page lists, `headers.source: null`) so the first PR is green; the link is the full schema. Survives reinstalls.

**Repo secrets** (under Settings → Secrets and variables → Actions):

- `COPILOT_GITHUB_TOKEN` — for the agentic doc-updater, a [gh-aw](https://github.github.com/gh-aw/) workflow. Setup: [`docs/hygiene/DOC_UPDATER.md`](../hygiene/DOC_UPDATER.md).

Deploy needs no secrets — Cloudflare Workers Builds connects via the GitHub App.

**Thresholds** — complexity ceiling, doc size, entry-file token budgets and the rest are keys in [`.slopstopper.yml.example`](../../.slopstopper.yml.example). Lighthouse budgets ship inside the wheel; override via `.ss/`.

**Docs layout** — the docs checks enforce AGENTS.md-first: `AGENTS.md` under ~2k tokens with explicit routes, `CLAUDE.md` exactly `@AGENTS.md`, a `docs/README.md` map, every doc routed. A fresh install seeds the scaffolds; an existing repo gets paste-ready fixes in the `entry-files` report.

## Update

Refresh workflows + shims and reinstall the **pinned** `slopstopper-cli` (config + customisations survive):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

Move the pin when ready (rewrites `mise.toml`; commit so CI matches). See [UPGRADE_CLI.md](./UPGRADE_CLI.md):

```bash
bash install.sh --upgrade-cli        # latest
bash install.sh --cli-version X.Y.Z  # exact
```

Refresh only the Claude Code skills: `curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash` — see [INSTALL_SKILLS.md](./INSTALL_SKILLS.md).

## Releases and provenance

Published to PyPI on every release tag. Each release is also attached to [GitHub Releases](https://github.com/hungovercoders/slopstopper/releases/latest) with a Sigstore build-provenance attestation — verify with `gh attestation verify <wheel> --owner hungovercoders`. The CLI ships with no third-party Python dependencies; every check invokes its tool via `subprocess` only. Credits and licences for every tool live in [`ATTRIBUTIONS.md`](../../ATTRIBUTIONS.md).

## See it in action

[slopstopper.dev](https://slopstopper.dev/) runs every check on every change. Browse [Features](https://slopstopper.dev/features.html) for each check's YAML and a mock report, or [Tools](https://slopstopper.dev/tools.html) for the technology stack.
