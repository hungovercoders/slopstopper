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

3. **What's the deploy model?** Some reliability workflows assume a `server.js`-served static site on `localhost:8080` for their PR/push local-build path. If the target is anything else (Astro, Next, SvelteKit, a backend app), those workflows will fail at "Start local server" with `exit 1` until someone customises the step. This is the #1 first-PR failure on non-trivial sites.

4. **Existing `package.json` devDeps that might collide?** Slopstopper merges in `@axe-core/playwright`, `@lhci/cli`, `@playwright/test`, `markdownlint-cli`, `typescript`. Spot collisions ahead of time.

5. **Does the target have its own README/AGENTS/CLAUDE entry files?** The `ss:hygiene:entry-files` check enforces a 1500-word budget on each. Most repos pass, but check if any are bloated.

6. **Is the target a private repo?** Some workflows post issues, comments, and PR labels. They need `issues: write`, `pull-requests: write` permissions — usually fine, but flag for the user if their org restricts this.

Report what you found to the user before running the installer, especially the deploy-model finding — that's the one that drives whether the dynamic checks need rework.

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
- `.github/workflows/ss-*.yml` — 19 workflows
- `package.json` — devDeps merged

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

## Step 5 — Verify

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

## Step 6 — First-PR triage (from real installs)

Things that have actually broken on first install — check whether they apply here:

### Gitleaks flags a "secret" in old blog/doc content
Tutorial repos and blogs frequently embed example connection strings, sample API keys, or emulator config that gitleaks matches as Generic API Keys. **Triage:**
- If it's a real leaked credential → revoke immediately, scrub history.
- If it's a sample/example → add a `.gitleaks.toml` with a path-specific allowlist. Don't disable gitleaks globally.

### Complexity check fails with "Incorrect parameters"
Symptom: `lizard` runs and errors out with compression-tool usage text. **Cause:** PATH collision with the `lz4-lizard` compression utility (often installed via Homebrew). The Python cyclomatic-complexity `lizard` is being shadowed. **Fix:** `pip install --upgrade lizard` and reorder PATH so the Python one wins, or invoke via `python3 -m lizard`. This is a host/CI environment issue, not a slopstopper bug — but it bites on macOS dev machines and is worth noting in the CI image setup.

### Reliability workflows fail at "Start local server" on PR/push
Symptom: workflow exits with "No server.js — customise this step or set X_TEST_URL." **Cause:** the local-build path of the reliability workflows expects a `server.js` at the repo root serving the built site on port 8080. This works on the slopstopper.dev repo (static site + bundled `server.js`); it does not work on Astro/Next/SvelteKit/backend repos out of the box. **Fix options:**
- (a) Add a tiny `server.js` shim that serves the built output on port 8080 (best for static sites).
- (b) Rewrite the "Start local server" step to use the target's actual dev/serve command (`npm run dev`, etc.).
- (c) Point the workflow at a deployed environment via the `*_TEST_URL` env vars and remove the local-build branch entirely.

### Doc-structure check fails on day one
If the target has its own `docs/` directory not laid out like slopstopper's governance map, `ss:hygiene:docs-structure` will fail. **Fix:** either adopt the map pattern (write a `docs/index.md` that lists categories matching the directory) or disable that workflow if it's not the right fit for the target.

### `ss:hygiene:docs-accuracy` flags broken cross-references
Common in old repos where docs reference renamed/moved files. **Triage:** real findings — fix the links.

## Step 7 — When NOT to install slopstopper

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
