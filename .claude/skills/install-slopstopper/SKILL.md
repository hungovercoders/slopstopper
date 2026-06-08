---
name: install-slopstopper
description: Install slopstopper into an existing repo. Use when a user asks to add slopstopper, the slopstopper quality suite, or any of its five loops (security, hygiene, reliability, runbooks, deployment) to a project. Walks pre-flight, install, post-install config, a local-first verification loop that closes every check before pushing, and a short maintenance note for when slopstopper itself changes.
---

# Install slopstopper

You're being asked to install slopstopper into an existing repo. Slopstopper is a portable suite of GitHub Actions, Task targets, and analysis scripts that drops a consistent quality pipeline into any repository. This skill walks you through doing that responsibly — and, critically, getting every check green **locally** before pushing, so the first CI run is a confirmation pass rather than a discovery pass.

The install ships ~21 GitHub Actions workflows in one shot, merges devDeps into `package.json`, and creates a `Taskfile.yml` if the target doesn't have one. That's a lot of moving parts. Don't run it blind — work through the pre-flight first, then drive every check to green locally before opening a PR.

## Step 1 — Pre-flight: read the target repo before installing

Before running anything, learn enough about the target to predict where it'll bite you:

1. **Does the target have an existing `Taskfile.yml`?** If yes, the installer prints include instructions instead of overwriting — you (or the user) need to manually add:
   ```yaml
   includes:
     ss:
       taskfile: ./Taskfile.ss.yml
   ```
   to the existing Taskfile.

2. **Does the target already have GitHub Actions workflows?** Slopstopper adds 21 new `ss-*.yml` workflows. They're all `ss-`-prefixed so they group in the Actions UI, but the user should know they're getting that many checks running on every PR.

3. **What `engines.node` does the target need?** Slopstopper workflows pin `node-version: '20'` in their `actions/setup-node` step. If the target needs Node 22+ (Astro 6, recent Next, SvelteKit kit), `npm run build` fails across every reliability/Playwright workflow with `Node.js vXX is not supported`. Predict it from the target's `package.json` `engines.node` and bump the workflows up front. The same edit is wiped by a future `install.sh` re-run, so commit the bump and re-apply if reinstalling.

4. **What's the deploy model and serve story?** Reliability/DAST workflows can target either a deployed URL or a `server.js`-served local build on port 8080. If the target is anything other than a static site (Astro, Next, SvelteKit, a backend app) you'll need either a `server.js` shim or workflows pointed at a deployed environment. Pair this with the deploy model — Cloudflare Workers / Vercel / Netlify / GH Pages each call for a different answer.

5. **How does the target manage security headers?** The CSP-exceptions drift check (`ss-hygiene-csp-exceptions-check.yml`) reads from `worker/headers.json` — slopstopper.dev's pattern. Sites that use an adapter, framework middleware, or platform config to set headers won't have that file and the check has nothing to guard. Flag for deletion if the target doesn't use the worker/headers.json pattern.

6. **Does the target follow the Map Pattern for docs?** Three workflows — `ss-hygiene-docs-accuracy-check.yml`, `ss-hygiene-docs-structure-check.yml`, `ss-hygiene-docs-size-check.yml` — require a `docs/` directory with an `index.md` listing categories (each as a subdirectory with its own `README.md`). Two valid choices: set up the Map Pattern (see Step 5) or delete these three workflows. A half-built `docs/` directory will fail the structure check until the tree matches the index.

7. **Does the target serve a site-wide `/og-image.png` with `Cross-Origin-Resource-Policy: cross-origin`?** The slopstopper Playwright smoke test (`.ss/tests/smoke.spec.ts`) asserts that `/og-image.png` returns 200, has `Content-Type: image/png`, and the CORP header set to `cross-origin` (so social platforms can embed it). Targets that use per-post share images instead won't have it. Either add a 1200×630 `og-image.png` at the site root with CORP configured for that path (Astro/Cloudflare adapter respects `public/_headers`), or restrict the Playwright suite to skip the smoke spec for that target.

8. **Existing `package.json` devDeps that might collide?** Slopstopper merges in `@axe-core/playwright`, `@lhci/cli`, `@playwright/test`, `markdownlint-cli`, `typescript`. Spot collisions ahead of time.

9. **Does the target have its own README/AGENTS/CLAUDE entry files?** The `ss:hygiene:entry-files` check enforces a 1500-word budget on each. Most repos pass, but check if any are bloated.

10. **Is GitHub Advanced Security (or public-repo Dependency Graph) enabled?** The `ss-security-vulnerability-new-check.yml` workflow uses `actions/dependency-review-action`, which requires either GHAS on a private repo or the Dependency Graph setting enabled on a public repo. Otherwise the check errors with `Dependency review is not supported on this repository`. Repo-admin setting — flag to the user.

11. **Does the target already have a `.github/labeler.yml`?** Slopstopper ships the auto-label workflow (`ss-hygiene-auto-label-pr.yml`) but not the config — labels are repo-specific. Without one, the check errors with `The config file was not found`. Plan to ship a labeler config mapping the target's directory structure to labels.

12. **Is the target a private repo?** Some workflows post issues, comments, and PR labels. They need `issues: write`, `pull-requests: write` permissions — usually fine, but flag if the org restricts this.

Report what you found to the user before running the installer. The Node-version question and the deploy-model question together drive the largest chunk of first-PR red checks — call them out specifically.

## Step 2 — Run the installer

From the target repo root, run the canonical one-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

The installer is idempotent. Re-running it pulls newer checks but respects deletions (tracked via `.ss/.workflows-installed`). All slopstopper files live under the `ss` namespace — your repo's existing files are not touched.

If the user prefers to review the script first:
```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
bash install.sh [TARGET_DIR]
```

## Step 3 — What just landed

Sanity-check the install dropped what you expect:

- `Taskfile.ss.yml` — all slopstopper task definitions
- `Taskfile.yml` — created if missing (otherwise: needs manual `includes:` block per Step 1.1)
- `.ss/scripts/` — Python+shell analyzers
- `.ss/tests/` — Playwright specs (smoke, accessibility, broken-links)
- `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`
- `.ss/.workflows-installed` — manifest of installed workflows (tracks deletions on reinstall; commit this)
- `.github/workflows/ss-*.yml` — the curated installer set (~21 files)
- `package.json` — devDeps merged

**Confirm the installed set matches upstream.** `install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. To catch this:

```bash
# inside the target repo, after install
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is a workflow that exists upstream but didn't land. If any look relevant, copy them from slopstopper's repo into `.github/workflows/` directly (and customize like the rest — Node version, URLs, page paths). Also worth flagging the gap upstream as an `install.sh` fix.

The installer's stdout summarises what's active vs what needs config — read it and relay to the user.

## Step 4 — Post-install configuration

### Add slopstopper outputs to `.gitignore`

The installer does NOT add `.ss/reports/` to `.gitignore`. The first time you run any check, it creates `.ss/reports/<check>/...` files. Add this block:

```
# slopstopper local outputs
.ss/reports/
playwright-report/
test-results/
.lighthouseci/
```

### Configure URL env vars for dynamic checks

The reliability checks (smoke, accessibility, Core Web Vitals, SEO, broken-links) and DAST need a URL to test against. Three options, in order of preference:

| Option | Where | Tradeoff |
|---|---|---|
| **GitHub repo variables** | Repo settings → Variables | Persists across reinstalls. Best for shared/public URLs. Requires `gh variable set` or dashboard click-ops. |
| **Hardcode in workflows** | Edit `default:` lines and `echo "url=…"` in `ss-reliability-*.yml` | Works immediately, lives in source control. Gets wiped on every `install.sh` re-run — re-apply after each install. |
| **Leave inert** | Do nothing | Workflows fail loudly on schedule. Fine if you only care about static-analysis checks. |

The URLs each workflow looks for:
- `SMOKE_TEST_URL`, `ACCESSIBILITY_TEST_URL`, `LIGHTHOUSE_URL`, `SEO_TEST_URL`, `BROKEN_LINKS_TEST_URL`, `DAST_TEST_URL`

If the user picks hardcode, edit each workflow in three places:
1. `workflow_dispatch.inputs.url.default:`
2. The `elif [ "$EVENT_NAME" == "schedule" ]` branch's `echo "url=…"`
3. The page list env var (`SMOKE_PAGES` / `ACCESSIBILITY_PAGES` / `SEO_PAGES`) — replace the default slopstopper.dev paths with the target site's actual paths.

## Step 5 — Set up the Map Pattern (if keeping the docs-* checks)

The three docs-* workflows (`docs-accuracy`, `docs-structure`, `docs-size`) validate a `docs/` directory laid out per slopstopper's governance pattern. If you're keeping them, the target needs a `docs/` directory shaped like this:

```
docs/
  index.md                    The map — table of categories, each linked
  <category-a>/README.md      One README per category named in the index
  <category-b>/README.md
  …
```

The structure check parses the table in `docs/index.md` (pattern: `| [category/](category/) | … |`) and fails the build if any listed category lacks a directory or `README.md`, or if there's an undocumented directory inside `docs/`. The directory tree must conform to the index — not the reverse.

**Minimum `docs/index.md`:**

```markdown
# Documentation Index

This file is **the map** — every other entry point in the repo defers to it.

| Category | Purpose | README |
| -------- | ------- | ------ |
| [architecture/](architecture/) | System structure and boundaries | [README](architecture/README.md) |
| [content/](content/) | What this repo produces, and how | [README](content/README.md) |
| [deployment/](deployment/) | How it ships | [README](deployment/README.md) |
| [operations/](operations/) | Runbooks and on-call notes | [README](operations/README.md) |
```

Pick categories that fit the target. Four is usually enough; slopstopper itself uses ten because it ships a tool with many surfaces. A blog/site does fine with three or four.

**Each category README** needs at minimum a heading and a sentence describing the category's scope. Better: short, practical, actually-useful content. The `docs-size` check caps total docs/ size and per-file size — keep each README concise.

**Wire the three entry files to defer to the map.** The Map Pattern is only useful if the entry files actually point at it. Once `docs/index.md` exists, restructure `README.md`, `AGENTS.md` and `CLAUDE.md` as a chain — each thin, each deferring upstream — so a human, an automation tool, or Claude Code all converge on the same canonical map:

- **`README.md`** (humans) — short project intro, install/run commands, pipeline-status badges, then a pointer like `See [docs/index.md](./docs/index.md) for the full documentation map.`
- **`AGENTS.md`** (any automation, [agents.md](https://agents.md) standard) — opens with a Map Pattern callout linking `docs/index.md`. Keeps only what an agent needs up-front: coding conventions (indentation, language, naming patterns), a "where to look for what" table mapping change types to category READMEs, and any non-obvious project-wide rules. Everything else lives in `docs/<category>/README.md`.
- **`CLAUDE.md`** (Claude Code) — a 3-5 line file that names the canonical chain (CLAUDE.md → AGENTS.md → docs/index.md) and uses the `@AGENTS.md` directive to import the agent conventions. Don't duplicate content here; Claude Code resolves the directive automatically.

Example minimal `CLAUDE.md`:

```markdown
# Claude Code — project instructions

The canonical agent conventions for this repo live in [`AGENTS.md`](./AGENTS.md), which in turn defers to the documentation map at [`docs/index.md`](./docs/index.md). Claude Code imports `AGENTS.md` via the directive below — keep this file thin.

@AGENTS.md
```

The `ss:hygiene:entry-files` check enforces a 1500-word budget on each of the three entry files. Aim well under it — the budget is the ceiling, not the target.

**Cross-references in docs:** the `docs-accuracy` check scans for `` `backtick-quoted` `` filenames and broken markdown links. Use full repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) so the checker can resolve them.

If none of this fits the target — short-lived prototype, single-file tool, generated docs only — delete the three workflows instead. `.ss/.workflows-installed` will remember the deletion so re-installs don't bring them back.

## Step 6 — Surface what's installed via README badges

After the workflows are live, surface them in the target's README. One GitHub Actions badge per `ss-*.yml` workflow plus a "powered by slopstopper" advert badge — gives anyone landing on the repo an instant sense of what's being checked and that the gates are real.

Generate the block by listing `ls .github/workflows/ss-*.yml` and grouping by loop prefix (`ss-security-*`, `ss-hygiene-*`, `ss-reliability-*`, operational = `ss-workflow-failure-issue.yml` + `ss-hygiene-doc-updater*`). Use this template — substitute `<OWNER>/<REPO>` with the values from `gh repo view --json nameWithOwner -q .nameWithOwner`:

```markdown
## Pipeline status

[![slopstopper](https://img.shields.io/badge/quality-slopstopper-2c7be5?style=flat-square)](https://slopstopper.dev/)

### 🔒 Security
[![SAST](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-sast-check.yml/badge.svg?branch=main)](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-sast-check.yml)
[![Secrets](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-secrets-check.yml/badge.svg?branch=main)](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-secrets-check.yml)
[![Dependency CVEs](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-vulnerability-all-check.yml/badge.svg?branch=main)](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-security-vulnerability-all-check.yml)

### 🧹 Hygiene
[![Complexity](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-hygiene-complexity-check.yml/badge.svg?branch=main)](https://github.com/<OWNER>/<REPO>/actions/workflows/ss-hygiene-complexity-check.yml)
... (one badge per installed ss-hygiene-* workflow)

### ✅ Reliability
... (one badge per installed ss-reliability-* and ss-playwright-tests.yml)

### 🤖 Operational
... (one badge per installed operational workflow)
```

**Three things to get right:**

1. **Only badge what's actually installed.** Don't paste badges for workflows the user has deleted (the `.ss/.workflows-installed` tracker is the source of truth — but `ls .github/workflows/ss-*.yml` is the simpler check).
2. **Insert position matters.** Most READMEs have a "what this is" intro at the top; the Pipeline status block reads best immediately after that, before the install/usage section — so visitors see what's guarded before they read what it is.
3. **The `?branch=main` parameter is important.** Without it, the badge shows the most recent run on any branch — which during PR work makes the badge flicker red even when `main` is fine.

The "powered by slopstopper" badge uses a static shields.io URL (`https://img.shields.io/badge/quality-slopstopper-2c7be5`). No live status, just an advert — keeps it portable and avoids relying on infra slopstopper doesn't own.

## Step 7 — Drive every check to green locally, **before** pushing

This is the spine of a good install. Every slopstopper check has a local `task ss:*` equivalent. Running them locally in a tight loop — fix, re-run, fix, re-run — is an order of magnitude faster than pushing and waiting on CI for each iteration. The goal of this step is that the first CI run on the target's PR is a **confirmation pass**, not a discovery pass.

**Two passes, in order:**

### Pass A — Static checks (no URL, no build needed, runs in seconds)

Run the two static aggregates first. They cover every static workflow that ships with the install:

```bash
npm install                  # pulls merged devDeps once
task ss:hygiene:test         # complexity + docs-* + entry-files + lint + structure + size
task ss:security:scan        # SAST + secrets + dependency CVEs + DAST (will need URL — skip via SKIP_DAST or run after Pass B)
```

If `task ss:security:scan` complains about a missing DAST URL, run security checks individually instead:

```bash
task ss:security:secrets         # Gitleaks — fast, usually surfaces something
task ss:security:sast            # Semgrep
task ss:security:vulnerability:all  # Trivy (CVE scan of dependencies)
```

For each failure: fix the root cause locally, re-run **just that one task** to confirm, and only move on once green. Anticipated issues during Pass A are listed in the table below.

### Pass B — Dynamic checks (need a URL + a built site)

The reliability and DAST workflows assert behaviour on a running site. The fastest local loop is to build once, serve via a tiny `server.js` shim on `localhost:8080`, then run each dynamic task against `http://localhost:8080`.

```bash
npm run build                                # target's own build
node server.js &                             # static server on :8080 (see "Anticipated issues" below if missing)
SMOKE_TEST_URL=http://localhost:8080 task ss:reliability:smoke
ACCESSIBILITY_TEST_URL=http://localhost:8080 task ss:reliability:accessibility
CWV_URL=http://localhost:8080 task ss:reliability:cwv
SEO_TEST_URL=http://localhost:8080 task ss:reliability:seo
BROKEN_LINKS_TEST_URL=http://localhost:8080 task ss:reliability:links
DAST_TEST_URL=http://localhost:8080 task ss:security:dast    # needs Docker for OWASP ZAP
```

`task ss:security:dast` is the heaviest local check (pulls and runs the OWASP ZAP container) — leave it for last in the loop. Skip it locally if Docker isn't installed and run it on CI only.

Iterate the same way as Pass A: fix root cause locally, re-run the single task, move on once green.

**Only when both passes are clean do you push.** At that point CI is confirming what you already know.

### Anticipated issues during the local loop

These come up reliably on first installs. Handling them locally during Step 7 is what makes the first CI pass green.

| Symptom (where you'll see it locally) | Root cause | Local fix |
|---|---|---|
| `Node.js vXX is not supported by Astro!` (or framework equivalent) on `npm run build` and across every reliability/Playwright workflow | Workflows pin `node-version: '20'`; target needs Node 22+ | Bulk-edit affected workflows to the version matching the target's `engines.node` |
| `task ss:hygiene:complexity` errors with compression-tool usage text instead of cyclomatic output | PATH collision: the `lz4-lizard` compression utility (often Homebrew) shadows the Python `lizard` | `pip install --upgrade lizard`; reorder PATH so Python's wins, or invoke `python3 -m lizard` |
| `task ss:security:secrets` flags an example connection string, sample API key, or emulator config | gitleaks regex matches sample/tutorial content as a generic API key | Real leak → revoke + scrub history. Sample → add a path-scoped allowlist in `.gitleaks.toml`; don't disable globally |
| `task ss:hygiene:docs-accuracy` flags backtick-quoted filenames that don't resolve | Old docs reference renamed/moved files, or use bare filenames the resolver can't find | Fix the link; use full repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) |
| `task ss:hygiene:docs-structure` fails with `❌ docs/ directory not found` (or category mismatch) | Target doesn't follow the Map Pattern, or has an undocumented dir under `docs/` | Set up the Map Pattern (Step 5) or delete the three docs-* workflows. Don't half-build it |
| `task ss:hygiene:csp-exceptions` fails with `worker/headers.json not found` | Target manages headers via adapter/middleware/platform config, not slopstopper.dev's pattern | Delete `ss-hygiene-csp-exceptions-check.yml`; the check has nothing to guard. `.ss/.workflows-installed` remembers the deletion across re-installs |
| `task ss:reliability:smoke` fails: `expected /og-image.png to return 200` or wrong CORP header | Site has no site-wide og-image, or local server isn't applying prod headers | Add a 1200×630 `public/og-image.png`; add `Cross-Origin-Resource-Policy: cross-origin` for that path; make sure the `server.js` shim parses the platform's headers file (e.g. `public/_headers` on Cloudflare) |
| Reliability or DAST tasks fail at "Start local server" / connection refused | No `server.js` at repo root serving the build on port 8080 | (a) add a `server.js` shim that serves the built output and applies the platform's header file per request, OR (b) point each workflow at a deployed URL via the `*_TEST_URL` env vars |
| `task ss:security:dast` reports `Content Security Policy (CSP) Header Not Set`, `X-Frame-Options` missing, etc. | Site has no security headers configured | Add headers via the platform (Cloudflare: `public/_headers`; Vercel: `vercel.json`; Netlify: `_headers` or `netlify.toml`). Baseline for a static site using GTM is in the appendix below |
| `task ss:security:dast` reports a CSP finding on a page that genuinely needs the relaxation (Giscus, GTM, etc.) | Per-path CSP relaxation is real and needs documenting | Document the relaxation in `docs/security/CSP_EXCEPTIONS.md` under `## Exceptions` with a `### /path` heading (glob patterns supported: `/*`, `/blog/*`). The DAST gate swallows CSP findings only on documented paths |
| `task ss:security:dast` reports a ZAP rule that's structurally wrong for the target (SRI on rotating GTM script; SQL Disclosure on blog posts with code blocks) | ZAP heuristic doesn't fit content-heavy sites | Add a `.zap/rules.tsv` with the plugin ID marked `IGNORE` and a `# why` comment. The `dast:analyze` task passes it to ZAP and the gate honours the same allowlist |
| `task ss:reliability:accessibility` reports `color-contrast`, `link-in-text-block`, or `label-title-only` on DOM that belongs to a cookie banner, chat widget, search UI, embedded video | Third-party widget injects its stylesheet at runtime after your CSS — wins on load order. The page owns the violations regardless of authorship | Scope CSS overrides to the widget's root class; use `!important` (runtime-injected styles can't be beaten on specificity alone if loaded last); add `text-decoration: underline` for `link-in-text-block`; add `aria-label` via small post-init script for inputs missing labels |

**Baseline security headers for a static site using GTM** (used in the DAST row above):

```
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://*.googletagmanager.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://*.google-analytics.com https://*.googletagmanager.com; font-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

Tune `script-src` / `connect-src` to the third parties the site actually loads. `'unsafe-inline'` for `script-src` is the pragmatic call when the build tool injects inline scripts (Astro `define:vars`, GTM bootstrap) and you can't easily add nonces; tighten to nonces or hashes if the framework supports them. Document any `'unsafe-inline'` retention in `docs/security/CSP_EXCEPTIONS.md` under `### /*` so the DAST gate swallows the inevitable site-wide CSP finding.

## Step 8 — Push and watch the confirmation pass

After Step 7's local loop is fully green, push to a PR branch. CI should mirror what you saw locally. A few checks are CI-only by design — handle these now rather than locally:

- **`ss-security-vulnerability-new-check.yml` (Dependency Review)** — only runs on `pull_request` and requires either GHAS on a private repo or Dependency Graph enabled on a public repo. If it fails with `Dependency review is not supported on this repository`, toggle the setting in repo Settings → Code security and analysis (admin action), or delete the workflow.
- **`ss-hygiene-auto-label-pr.yml`** — needs a `.github/labeler.yml` in the target. If missing, ship one mapping the target's directory globs to labels using the `actions/labeler@v5` config format. Use the target repo's natural taxonomy (e.g. `blog`, `docs`, `ci`, `deps`).

If anything else is red on CI but was green locally: that's signal there's an environmental delta between local and CI (Node version pin, missing env var, file-permissions, OS-specific tool). Diagnose, fix, and add the difference to the local pre-flight for next time.

## Step 9 — When NOT to install slopstopper

Don't push the user to install if:
- The target already has a competing quality suite they're happy with (don't double up).
- It's a one-file script or library where 21 workflows is overkill.
- The target's CI minutes budget is tight — the dynamic checks (Playwright, Lighthouse CI, ZAP) burn minutes.
- The target's deploy isn't Cloudflare Workers Builds. Slopstopper's deploy story assumes that — the install still works, but the user loses one of its selling points.

In any of those cases: recommend a partial adoption (cherry-pick specific workflows) rather than the full install.

## Step 10 — Maintaining this skill when slopstopper changes

This skill names specific files, env vars, workflow IDs, the `GENERIC_WORKFLOWS` list in `install.sh`, and the local `task ss:*` commands that mirror each workflow. **Any change to slopstopper that touches one of those needs a corresponding update here**, or the skill silently drifts away from reality.

Triggers that require revisiting this skill:

- A workflow is added, removed, or renamed under `slopstopper/.github/workflows/ss-*.yml` → update the workflow count in the intro, Step 1.2, and Step 3; add/remove the matching local-task row in Step 7's table; add/remove the badge example in Step 6.
- The `GENERIC_WORKFLOWS` array in `slopstopper/install.sh` changes → confirm the "What just landed" inventory in Step 3 still matches.
- A `task ss:*` target is renamed in `slopstopper/Taskfile.ss.yml` → update the matching command in Step 7's Pass A or Pass B.
- A new env var is introduced for a dynamic check → add to the URL-defaults list in Step 4 and to the Pass B example in Step 7.
- A new persistent class of finding emerges on a fresh install that can't be resolved by existing guidance → add a row to Step 7's anticipated-issues table (forward-looking phrasing — what the symptom looks like, what the cause is, what the fix is — without citing the install that surfaced it).

The companion to this is `AGENTS.md` in the slopstopper repo: its "When making changes" table flags the skill as a follow-on target whenever a change of the above kind ships. If you're updating slopstopper itself and that table isn't pointing readers back here, fix that first.

## Notes for the agent

- The install is reversible by deleting the slopstopper-added files. Commit the install as its own commit so it's easy to revert.
- Re-running `install.sh` is safe — it tracks deletions in `.ss/.workflows-installed` so workflows the user has deliberately removed don't come back.
- Hardcoded URL edits to `ss-*.yml` workflows are wiped on reinstall. Tell the user this so they're not surprised later.
- Step 7 is the most important part of the install. Don't push until it's green locally — the local loop is faster than CI by an order of magnitude.
- Surface findings, don't auto-fix everything. The user decides what's a real issue vs. a tuning task vs. a deletion candidate.
