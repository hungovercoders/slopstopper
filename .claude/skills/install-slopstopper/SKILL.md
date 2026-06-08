---
name: install-slopstopper
description: Install slopstopper into an existing repo. Use when a user asks to add slopstopper, the slopstopper quality suite, or any of its five loops (security, hygiene, reliability, runbooks, deployment) to a project. Walks the agent through pre-flight checks, the install command, post-install URL config, verification, and first-PR triage. Grounded in real installs into non-trivial existing repos, not generic theory.
---

# Install slopstopper

You're being asked to install slopstopper into an existing repo. Slopstopper is a portable suite of GitHub Actions, Task targets, and analysis scripts that drops a consistent quality pipeline into any repository. This skill walks you through doing that responsibly.

The install ships ~19 GitHub Actions workflows in one shot, merges devDeps into `package.json`, and creates a `Taskfile.yml` if the target doesn't have one. That's a lot of moving parts. Don't run it blind — work through the pre-flight first.

## Step 1 — Pre-flight: read the target repo before installing

Before running anything, learn enough about the target to predict where it'll bite you:

1. **Does the target have an existing `Taskfile.yml`?** If yes, the installer prints include instructions instead of overwriting — you (or the user) need to manually add:
   ```yaml
   includes:
     ss:
       taskfile: ./Taskfile.ss.yml
   ```
   to the existing Taskfile.

2. **Does the target already have GitHub Actions workflows?** Slopstopper adds 19 new `ss-*.yml` workflows. They're all `ss-`-prefixed so they group in the Actions UI, but the user should know they're getting that many checks running on every PR.

3. **What `engines.node` does the target need?** Slopstopper workflows pin `node-version: '20'` in their `actions/setup-node` step. If the target needs Node 22+ (Astro 6, recent Next, SvelteKit kit), `npm run build` will fail across every reliability/Playwright workflow with `Node.js vXX is not supported`. This is the **#1 cause of red checks on the first PR** — predict it from the target's `package.json` `engines.node` and plan to bump the workflows.

4. **What's the deploy model and serve story?** Some reliability/DAST workflows assume a `server.js`-served static site on `localhost:8080` for their PR/push local-build path. If the target is anything else (Astro, Next, SvelteKit, a backend app), those workflows fail at "Start local server" with `exit 1` until someone provides a `server.js` shim or rewrites the step. Pair this question with the deploy model — Cloudflare Workers / Vercel / Netlify / GH Pages each call for a different answer.

5. **How does the target manage security headers?** The CSP-exceptions drift check (`ss-hygiene-csp-exceptions-check.yml`) reads from `worker/headers.json` — slopstopper.dev's pattern. Sites that use an adapter, framework middleware, or platform config to set headers won't have that file and the check will fail with `worker/headers.json not found`. If the target doesn't use the worker/headers.json pattern, the check has nothing to guard — flag for deletion.

6. **Does the target follow the Map Pattern for docs?** Three workflows — `ss-hygiene-docs-accuracy-check.yml`, `ss-hygiene-docs-structure-check.yml`, `ss-hygiene-docs-size-check.yml` — require a `docs/` directory with an `index.md` listing categories (each as a subdirectory with its own `README.md`). Without it the checks fail with `❌ docs/ directory not found`. Two valid choices: set up the Map Pattern (see Step 5) or delete these three workflows. Don't leave a half-built `docs/` directory in place — the checks will keep failing until the structure matches the index.

7. **Does the target serve a site-wide `/og-image.png` with `Cross-Origin-Resource-Policy: cross-origin`?** The slopstopper Playwright smoke test (`.ss/tests/smoke.spec.ts`) asserts that `/og-image.png` returns 200, has `Content-Type: image/png`, and the CORP header set to `cross-origin` (so social platforms can embed it). Targets that use per-post share images (e.g. `/assets/<slug>/link.png`) instead of a single site-wide image will fail this test. Plan to either: (a) add a 1200×630 `og-image.png` at the site root and configure CORP for that path (Astro/Cloudflare adapter respects `public/_headers`), or (b) skip the smoke spec via Playwright config if the target genuinely doesn't have a site-wide og-image concept.

8. **Existing `package.json` devDeps that might collide?** Slopstopper merges in `@axe-core/playwright`, `@lhci/cli`, `@playwright/test`, `markdownlint-cli`, `typescript`. Spot collisions ahead of time.

9. **Does the target have its own README/AGENTS/CLAUDE entry files?** The `ss:hygiene:entry-files` check enforces a 1500-word budget on each. Most repos pass, but check if any are bloated.

10. **Is GitHub Advanced Security (or public-repo Dependency Graph) enabled?** The `ss-security-vulnerability-new-check.yml` workflow uses `actions/dependency-review-action` which requires either GHAS on a private repo or the Dependency Graph setting enabled on a public repo. If neither is on, the check fails with `Dependency review is not supported on this repository`. Repo-admin setting, not a code change — flag to the user before install.

11. **Does the target already have a `.github/labeler.yml`?** Slopstopper ships the auto-label workflow (`ss-hygiene-auto-label-pr.yml`) but not the config — labels are by definition repo-specific. If there's no existing `.github/labeler.yml`, the check fails immediately with `The config file was not found`. Plan to ship one mapping the target repo's directory structure to labels.

12. **Is the target a private repo?** Some workflows post issues, comments, and PR labels. They need `issues: write`, `pull-requests: write` permissions — usually fine, but flag for the user if their org restricts this.

Report what you found to the user before running the installer. The Node-version question and the deploy-model question together cause most first-PR red checks — call them out specifically.

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
- `.github/workflows/ss-*.yml` — the curated installer set
- `package.json` — devDeps merged

**Diff what landed vs what slopstopper ships.** `install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. To catch this, run:

```bash
# inside the target repo, after install
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is a workflow that exists upstream but didn't land. If any look relevant, copy them from slopstopper's repo into `.github/workflows/` directly (and customize like the rest — Node version, URLs, page paths). Also worth flagging the gap upstream as an install.sh fix.

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

The reliability checks (smoke, accessibility, Core Web Vitals, SEO) and DAST need a URL to test against. Three options, in order of preference:

| Option | Where | Tradeoff |
|---|---|---|
| **GitHub repo variables** | Repo settings → Variables | Persists across reinstalls. Best for shared/public URLs. Requires `gh variable set` or dashboard click-ops. |
| **Hardcode in workflows** | Edit `default:` lines and `echo "url=…"` in `ss-reliability-*.yml` | Works immediately, lives in source control. **Drift gotcha:** gets wiped on every `install.sh` re-run. |
| **Leave inert** | Do nothing | Workflows fail loudly on schedule. Fine if you only care about static-analysis checks. |

The URLs each workflow looks for:
- `SMOKE_TEST_URL`, `ACCESSIBILITY_TEST_URL`, `LIGHTHOUSE_URL`, `SEO_TEST_URL`, `BROKEN_LINKS_TEST_URL`, `DAST_TEST_URL`

If the user picks hardcode, edit each workflow in three places:
1. `workflow_dispatch.inputs.url.default:`
2. The `elif [ "$EVENT_NAME" == "schedule" ]` branch's `echo "url=…"`
3. The page list env var (`SMOKE_PAGES` / `ACCESSIBILITY_PAGES` / `SEO_PAGES`) — replace the default slopstopper.dev paths (`'/,/features.html,/tools.html,/feedback.html'`) with the target site's actual paths.

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

## Step 7 — Verify

Run, in order, from the target repo:

```bash
npm install                     # pulls merged devDeps
npm run build                   # critical regression check — target's existing build still works
task --list                     # confirms ss:* tasks are wired
task ss:security:secrets        # Gitleaks scan — fast, usually surfaces something
task ss:hygiene:entry-files     # token-budget check on README/AGENTS/CLAUDE
task ss:hygiene:complexity      # Lizard cyclomatic complexity
```

Capture each finding — pass, fail, and why — for the user. Don't fix anything yet; surface the list so the user decides what's a real issue vs. a tuning task.

## Step 8 — First-PR triage

Common first-PR failures and how to handle each. Pre-flight from Step 1 should predict most of these; this section is the recovery playbook when they hit.

### Build fails everywhere with "Node.js vXX is not supported"
**Symptom:** `Core Web Vitals`, `Accessibility`, `SEO`, `Playwright`, and `DAST` workflows all fail at `npm run build` with `Node.js v20.X.X is not supported by Astro!` (or the framework equivalent). **Cause:** the workflows pin `node-version: '20'` in their `actions/setup-node` step. Targets on Astro 6+, recent Next, etc. need Node 22+. **Fix:** bulk-edit the affected workflows to `node-version: '22'` (or whatever matches the target's `engines.node`). One root cause, four-to-five red checks resolved at once. Hardcoded — will be wiped on next `install.sh` re-run.

### Gitleaks flags a "secret" in old blog/doc content
Tutorial repos and blogs frequently embed example connection strings, sample API keys, or emulator config that gitleaks matches as Generic API Keys. **Triage:**
- If it's a real leaked credential → revoke immediately, scrub history.
- If it's a sample/example → add a `.gitleaks.toml` with a path-specific allowlist. Don't disable gitleaks globally.

### Complexity check fails with "Incorrect parameters"
Symptom: `lizard` runs and errors out with compression-tool usage text. **Cause:** PATH collision with the `lz4-lizard` compression utility (often installed via Homebrew). The Python cyclomatic-complexity `lizard` is being shadowed. **Fix:** `pip install --upgrade lizard` and reorder PATH so the Python one wins, or invoke via `python3 -m lizard`. This is a host/CI environment issue, not a slopstopper bug — but it bites on macOS dev machines and is worth noting in the CI image setup.

### Reliability + DAST workflows fail at "Start local server" on PR/push
Symptom: workflow exits with "No server.js — customise this step or set X_TEST_URL." **Cause:** the local-build path of the smoke / accessibility / Core Web Vitals / SEO / Playwright / **DAST** workflows expects a `server.js` at the repo root serving the built site on port 8080 (DAST runs OWASP ZAP via Docker against the same URL). Works on the slopstopper.dev repo (static site + bundled `server.js`); does not work on Astro/Next/SvelteKit/backend repos out of the box. One shim unlocks all six workflows. **Fix options:**
- (a) Add a tiny `server.js` shim that serves the built output on port 8080 (best for static sites). The shim must mirror the deployed Worker's header behavior — for Cloudflare-deployed Astro sites that means parsing `public/_headers` (Cloudflare's per-path header format) and applying matching headers per request, otherwise tests asserting CORP/CSP headers will pass on schedule (against deployed URL) but fail on every PR (against the bare shim).
- (b) Rewrite the "Start local server" step to use the target's actual dev/serve command (`npm run dev`, etc.).
- (c) Point the workflow at a deployed environment via the `*_TEST_URL` env vars and remove the local-build branch entirely.

### Smoke test fails on `/og-image.png` (404 or missing CORP header)
**Symptom:** `.ss/tests/smoke.spec.ts` fails with `expected /og-image.png to return 200 — Expected: 200 Received: 404`, or with `Expected: "cross-origin"` on the `cross-origin-resource-policy` header. **Cause:** the slopstopper smoke test hardcodes a check for a site-wide `/og-image.png` with `Cross-Origin-Resource-Policy: cross-origin` (so social platforms can embed it). Targets that use per-post share images instead of a single site-wide image won't have the file; targets without prod-equivalent header config locally won't have the CORP header on `localhost:8080`. **Fix:**
- Add a 1200×630 `og-image.png` at the site root (e.g. `public/og-image.png` for Astro).
- Configure the CORP header for that path. On Astro/Cloudflare, add to `public/_headers`:
  ```
  /og-image.png
    Cross-Origin-Resource-Policy: cross-origin
  ```
- Ensure your local `server.js` shim applies those headers — see the previous entry.

If the target genuinely has no site-wide og-image concept (per-post images only), the alternative is to grep the spec from the Playwright run via a root-level `playwright.config.js` that extends `.ss/playwright.config.js` with a `grepInvert` pattern. But adding the file is almost always simpler.

### Auto-label workflow fails with "config file was not found"
**Symptom:** `ss-hygiene-auto-label-pr.yml` fails immediately with `HttpError: Not Found` and `The config file was not found at .github/labeler.yml`. **Cause:** slopstopper ships the workflow but not the config — labels are repo-specific. **Fix:** add a `.github/labeler.yml` mapping the target's directory globs to labels. Standard `actions/labeler@v5` format: `{label-name}: [{ changed-files: [{ any-glob-to-any-file: [...] }] }]`. Use the target repo's natural taxonomy (e.g. `blog`, `docs`, `ci`, `deps`).

### Dependency Review fails with "not supported on this repository"
**Symptom:** `ss-security-vulnerability-new-check.yml` errors with `Dependency review is not supported on this repository. Please ensure that Dependency graph is enabled along with GitHub Advanced Security`. **Cause:** the `actions/dependency-review-action` requires GHAS for private repos, or the Dependency Graph setting enabled for public repos. **Fix:** either toggle the setting in repo Settings → Code security and analysis → Dependency graph (admin action, not a code change), or delete the workflow until GHAS is on. There's no in-code workaround.

### CSP-exceptions check fails with "worker/headers.json not found"
**Symptom:** `ss-hygiene-csp-exceptions-check.yml` errors with `❌ worker/headers.json not found`. **Cause:** the check is slopstopper.dev-specific — it guards a single-source-of-truth `worker/headers.json` file used by slopstopper.dev's Cloudflare Worker. Sites that manage headers via an adapter, framework middleware, or platform config don't have this file. **Fix:** delete the workflow. There's no header file to guard, the check has nothing to do. The `.ss/.workflows-installed` tracker will remember the deletion so a re-install doesn't bring it back.

### docs-* checks fail with "docs/ directory not found"
**Symptom:** `ss-hygiene-docs-accuracy-check.yml`, `ss-hygiene-docs-structure-check.yml`, and `ss-hygiene-docs-size-check.yml` all fail with `❌ docs/ directory not found`. **Cause:** these three checks validate slopstopper's Map Pattern, which assumes the target has a `docs/` directory with an `index.md` listing categories. The target has no such directory. **Fix:** either set up the Map Pattern (see Step 5 — `docs/index.md` plus one category README per row in the index table) or delete the three workflows because the target doesn't need them. Don't half-build the structure; the structure check parses every category named in the index and fails on any missing directory or README.

### Doc-structure check fails on day one
If the target has its own `docs/` directory not laid out like slopstopper's governance map, `ss:hygiene:docs-structure` will fail. **Fix:** either adopt the map pattern (write a `docs/index.md` that lists categories matching the directory) or disable that workflow if it's not the right fit for the target.

### `ss:hygiene:docs-accuracy` flags broken cross-references
Common in old repos where docs reference renamed/moved files. **Triage:** real findings — fix the links.

### Accessibility audit fails on DOM injected by third-party widgets
**Symptom:** `ss-reliability-accessibility-check.yml` (or the local `task ss:reliability:accessibility`) reports `color-contrast`, `link-in-text-block`, or `label-title-only` violations and the failing HTML belongs to a cookie banner, chat widget, search UI, embedded video player, or other third-party JS-injected content. **Cause:** widgets like klaro (cookie consent), giscus, intercom, pagefind, etc. inject their own stylesheet at runtime *after* your site's CSS has been parsed, so they win on load order. axe-core scans the rendered DOM and flags their violations as the page's. The page owns them — even if the markup isn't yours, the visitor's accessibility is. **Fix:**
- Scope CSS overrides to the widget's root class (e.g. `.klaro *`, `.giscus *`).
- Use `!important` — runtime-injected styles can't be beaten on specificity alone if they were loaded last.
- For `link-in-text-block` failures, add `text-decoration: underline` so the link is distinguishable from surrounding text by more than colour.
- For inputs missing labels (common with JS-generated search UIs), add an `aria-label` via a small post-init script.

## Step 9 — When NOT to install slopstopper

Don't push the user to install if:
- The target already has a competing quality suite they're happy with (don't double up).
- It's a one-file script or library where 19 workflows is overkill.
- The target's CI minutes budget is tight — the dynamic checks (Playwright, Lighthouse CI, ZAP) burn minutes.
- The target's deploy isn't Cloudflare Workers Builds. Slopstopper's deploy story assumes that — the install still works, but the user loses one of its selling points.

In any of those cases: recommend a partial adoption (cherry-pick specific workflows) rather than the full install.

## Notes for the agent

- The install is reversible by deleting the slopstopper-added files, but commit the install as its own commit so it's easy to revert.
- Re-running `install.sh` is safe — it tracks deletions in `.ss/.workflows-installed` so workflows the user has deliberately removed don't come back.
- Hardcoded URL edits to `ss-*.yml` workflows get wiped on reinstall. Tell the user this explicitly so they're not surprised later.
- Don't fix every finding in the same session as the install — that conflates "is slopstopper working?" with "is our codebase clean?". Install, surface findings, let the user choose.
