---
name: slopstopper-install
description: Install slopstopper into a repo for the first time OR refresh an existing slopstopper install. Use when a user asks to add slopstopper, install the slopstopper quality suite, refresh slopstopper, upgrade slopstopper, pull in new slopstopper checks, or see what's new in slopstopper. Covers pre-flight, install command, idempotent re-run on existing installs, post-install URL config, Map Pattern setup, README badges, customizations that get wiped on refresh, new-knob discovery, and a local-first verification loop that closes every check before pushing. For per-check failure diagnosis use the slopstopper-triage skill.
---

# Install or refresh slopstopper

You're being asked to install slopstopper into a repo, or refresh an existing slopstopper install. Both flows live here: the steps are mostly the same (install.sh is idempotent), with a couple of refresh-only sections for diffing upstream and re-applying customizations that get wiped on re-run.

## Mode detection — first install or refresh?

Check the target repo before doing anything else:

```bash
ls .slopstopper.yml .ss/.workflows-installed 2>/dev/null
```

- **Both files exist** → this is a **refresh**. The mechanical part is "re-run install.sh"; the value-add is diffing upstream for new workflows, re-applying customizations the installer wipes, and surfacing new tunable knobs in `.slopstopper.yml.example`. Skim Steps 1, 4-6 (already done last time) and focus on Step 2 (idempotent re-run), the new **Refresh-only** section between Steps 6 and 7, and Step 7 (local verify) before pushing.
- **Neither exists** → this is a **first install**. Walk every step in order: pre-flight → install → post-install config → Map Pattern → badges → local verify → push.
- **Only one exists** (rare) → partial state. Stop and ask the user what happened — usually means a previous install was interrupted or partially reverted.

Slopstopper is a portable suite of GitHub Actions plus a `slopstopper-cli` Python package that owns every check's logic. The install drops a consistent quality pipeline into any repository. This skill walks you through doing that responsibly — and, critically, getting every check green **locally** before pushing, so the first CI run is a confirmation pass rather than a discovery pass.

The install ships ~21 GitHub Actions workflows in one shot, pins + installs `slopstopper-cli` via **mise** (`mise.toml` `[tools]` "pipx:slopstopper-cli"), merges devDeps into `package.json`, and creates a `Taskfile.yml` if the target doesn't have one. That's a lot of moving parts. Don't run it blind — work through the pre-flight first, then drive every check to green locally before opening a PR.

**The CLI is the single source of truth for every check.** Every workflow boils down to two CLI commands: `slopstopper run <category>:<check>` (executes the check, writes reports under `.ss/reports/`) and `slopstopper emit <category>:<check> --target {pr-comment,issue} [--on-pass=close]` (posts the report to GitHub on failure, or closes any prior issue when the check now passes on `main`). Reliability checks also use `slopstopper discover <check> --event=<event>` (resolves which pages to audit) and the installer itself uses `slopstopper config get <key>` to read `.slopstopper.yml`. No bash scripts under `.ss/scripts/` any more — pure Python, one package, one upgrade path.

## Step 1 — Pre-flight: read the target repo before installing

Before running anything, learn enough about the target to predict where it'll bite you:

0. **Are `mise` and `python3` available?** Both hard prereqs — `install.sh` errors out without them. mise is the toolchain manager: it pins `slopstopper-cli` (and `task`) in `mise.toml` and installs them, activating the pinned versions per-directory so the active `slopstopper` follows the repo (this is what stops a single global binary from drifting between repos). mise's pipx backend needs `python3` on PATH. The CLI runs every check, so no mise/Python = no slopstopper. Make sure mise is [activated](https://mise.jdx.dev/getting-started.html) in the shell so the pinned binary lands on `$PATH` (CI handles this via `jdx/mise-action`).

1. **Does the target have an existing `Taskfile.yml`?** If yes, the installer prints include instructions instead of overwriting — you (or the user) need to manually add:
   ```yaml
   includes:
     ss:
       taskfile: ./Taskfile.ss.yml
   ```
   to the existing Taskfile.

2. **Does the target already have GitHub Actions workflows?** Slopstopper adds 21 new `ss-*.yml` workflows. They're all `ss-`-prefixed so they group in the Actions UI, but the user should know they're getting that many checks running on every PR.

3. **What `engines.node` does the target need?** Slopstopper workflows read `${{ vars.SLOPSTOPPER_NODE_VERSION || '20' }}` for their `actions/setup-node` step. If the target needs Node 22+ (Astro 6, recent Next, SvelteKit kit), set `node_version:` in `.slopstopper.yml` AND run `gh variable set SLOPSTOPPER_NODE_VERSION --body 22` to push it into the repo variable that workflows read. One source of truth; survives `install.sh` re-runs.

4. **What's the deploy model and serve story?** Reliability/DAST workflows can target either a deployed URL or a `server.js`-served local build on port 8080. If the target is anything other than a static site (Astro, Next, SvelteKit, a backend app) you'll need either a `server.js` shim or workflows pointed at a deployed environment. Pair this with the deploy model — Cloudflare Workers / Vercel / Netlify / GH Pages each call for a different answer.

5. **How does the target manage security headers?** The CSP-exceptions drift check reads from whatever you name in `.slopstopper.yml` `headers.source` (with `headers.format`). Shipped adapters: `json` (for `[{for, values}]` JSON files like slopstopper.dev's `worker/headers.json`), `cloudflare-text` (Cloudflare/Netlify native `_headers` text format), `auto` (infer from extension). Set `source: null` to skip the check entirely — adopters managing headers via framework middleware / `vercel.json` / etc. do this. The installer seeds `.slopstopper.yml` with `source: null` so first-PR is green even before you configure anything; you opt the check in by pointing it at your real headers file.

6. **Does the target follow the Map Pattern for docs?** Three workflows — `ss-hygiene-docs-accuracy-check.yml`, `ss-hygiene-docs-structure-check.yml`, `ss-hygiene-docs-size-check.yml` — require a `docs/` directory with an `index.md` listing categories (each as a subdirectory with its own `README.md`). A fourth — `ss-hygiene-entry-files-check.yml` — also enforces the pointer side of the pattern: README.md and AGENTS.md must link to `docs/index.md`, CLAUDE.md must be a thin pointer to AGENTS.md, and `docs/index.md` itself must exist (unless `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml`). Two valid choices: set up the Map Pattern (see Step 5) or disable both halves (`workflows.disabled` the three docs-* workflows AND set `require_map_pointer: false`). A half-built `docs/` directory will fail the structure check until the tree matches the index; a docs/ directory with no pointers from the entry files will fail the entry-files check.

7. **Does the target serve a site-wide `/og-image.png` with `Cross-Origin-Resource-Policy: cross-origin`?** The slopstopper Playwright smoke test (`.ss/tests/smoke.spec.ts`, or the bundled `cli/slopstopper/data/tests/smoke.spec.ts` when no `.ss/` override is present) asserts that `/og-image.png` returns 200, has `Content-Type: image/png`, and the CORP header set to `cross-origin` (so social platforms can embed it). Targets that use per-post share images instead won't have it. Either add a 1200×630 `og-image.png` at the site root with CORP configured for that path (Astro/Cloudflare adapter respects `public/_headers`), or set `smoke.og_image_path: ''` in `.slopstopper.yml` to skip the assertion.

8. **Existing `package.json` devDeps that might collide?** Slopstopper merges in `@axe-core/playwright`, `@lhci/cli`, `@playwright/test`, `markdownlint-cli`, `typescript`. Spot collisions ahead of time.

9. **Does the target have its own README/AGENTS/CLAUDE entry files?** The `ss:hygiene:entry-files` check enforces two things: a 1500-word budget on each, AND the Map Pattern pointer rule (README.md + AGENTS.md link to `docs/index.md`; CLAUDE.md is a thin pointer to AGENTS.md). If any of the three are missing, `install.sh` seeds a minimal pointer-shaped scaffold from `cli/slopstopper/data/templates/entry-files/` (never overwrites existing files). If they exist but don't link the map, the check's report at `.ss/reports/entry-files/entry-file-size-report.md` emits a paste-ready snippet for each violation — apply it during the Step 7 local loop. Most repos with existing entry files need 1-3 small additions; flag any that are bloated or that lack the pointer up-front.

10. **Is GitHub Advanced Security (or public-repo Dependency Graph) enabled?** The `ss-security-vulnerability-new-check.yml` workflow uses `actions/dependency-review-action`, which requires either GHAS on a private repo or the Dependency Graph setting enabled on a public repo. Otherwise the check errors with `Dependency review is not supported on this repository`. Repo-admin setting — flag to the user.

11. **Does the target already have a `.github/labeler.yml`?** Slopstopper ships the auto-label workflow (`ss-hygiene-auto-label-pr.yml`) but not the config — labels are repo-specific. Without one, the check errors with `The config file was not found`. Plan to ship a labeler config mapping the target's directory structure to labels.

12. **Is the target a private repo?** Two things to flag, not one. First, some workflows post issues, comments, and PR labels — they need `issues: write`, `pull-requests: write` permissions, usually fine but check if the org restricts this. Second, and more important: **GitHub Actions minutes are free on public repos but billed on private ones.** The full suite runs ~18 checks on every PR, and the scheduled reliability/smoke runs add recurring minutes on top of that — the heavier dynamic checks (Playwright, Lighthouse CI, ZAP-in-Docker) are the expensive ones. On a public repo this is a non-issue; on a private repo with a tight minutes budget, slopstopper may not be a good fit as-is. Call the cost out explicitly during pre-flight so the user decides with eyes open — and consider a partial adoption (Step 9) rather than the full suite.

Report what you found to the user before running the installer. The Node-version question and the deploy-model question together drive the largest chunk of first-PR red checks — call them out specifically.

## Step 2 — Run the installer

Before running anything, ensure you're on a clean branch:

```bash
git status                              # must show clean
git checkout -b chore/slopstopper-install   # or chore/slopstopper-refresh for a refresh
```

`install.sh` adds ~21 workflow files, a `Taskfile.ss.yml`, and `.ss/server.js` to the repo in one shot. On `main` that's an awkward 25+-file commit; on a dedicated branch the diff is reviewable and the rollback is `git checkout main && git branch -D <branch>`. If `git status` is dirty, stop and reconcile first — the installer doesn't ask before writing into `ss-*.yml` or `Taskfile.ss.yml`. On a refresh, the wipe-and-replace behaviour will clobber anything sitting in the tracked files it rewrites — commit or stash first.

From the target repo root, download-review-run in two steps:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
bash install.sh                                # default Task mode
```

**Lead with the two-step form when you're an agent.** The piped one-liner
(`curl … | bash`) is what the human-facing README advertises, but Claude Code's
auto-mode classifier (and most agent security sandboxes) reject piping external
code straight into `bash`, so it stalls on a permission prompt mid-install. The
two-step form lands the script on disk first — reviewable, and it clears the
sandbox. The piped form remains the canonical convenience command for humans:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

The installer is idempotent. Re-running it pulls newer checks but respects deletions (tracked via `.ss/.workflows-installed`). It does **not** bump `slopstopper-cli`: the CLI is pinned per-repo in `mise.toml` (`[tools]` "pipx:slopstopper-cli"), and a plain re-run honours that pin via `mise use` (which installs exactly that version). A breaking upstream release therefore can't reach the repo until someone moves the pin with `install.sh --upgrade-cli` (latest) or `install.sh --cli-version X.Y.Z` (exact). An older install that pinned `cli_version` in `.slopstopper.yml` is migrated into `mise.toml` and the dead key stripped on the next run. All slopstopper files live under the `ss` namespace — your repo's existing files are not touched. If a pre-CLI install left a `.ss/scripts/` directory behind, the installer scrubs it on first run.

**`install.sh` also installs the SlopStopper Claude Code skills at project level** — `<target>/.claude/skills/slopstopper-{install,triage}/SKILL.md` — so every contributor that clones the repo picks them up automatically (Claude Code auto-discovers project-level skills). Commit the resulting files alongside the workflows. Pass `--no-skills` or set `SLOPSTOPPER_NO_SKILLS=1` to disable. To refresh just the skills later without re-running the whole installer, use `install-skill.sh` from inside the repo. If you've previously run an older version of `install-skill.sh` that wrote to `~/.claude/skills/slopstopper-*`, the installer warns you so you can clean up the user-level copies before they shadow the project-level ones.

### What `install.sh` writes (and leaves alone)

Three categories of write, in order of "how much trust to extend on re-run":

**Always overwritten — slopstopper-owned, safe to clobber:**

- `Taskfile.ss.yml`, `.ss/server.js`, `.ss/.workflows-installed`
- Workflows under `.github/workflows/ss-*.yml` that are in `GENERIC_WORKFLOWS` and not listed in `.slopstopper.yml` `workflows.disabled`
- `mise.toml` — the `"pipx:slopstopper-cli"` + `task` pins (written via `mise use`); `slopstopper-cli` itself is installed/activated by mise at the **pinned** version. A plain re-run never bumps it; `--upgrade-cli` / `--cli-version` do
- `<repo>/.claude/skills/slopstopper-install/SKILL.md` and `<repo>/.claude/skills/slopstopper-triage/SKILL.md` (project level — opt out with `--no-skills`)

**Seeded only if missing — adopter-owned, NEVER overwritten on re-run:**

- `.slopstopper.yml` (config; once it exists `install.sh` never touches it — **except** stripping a legacy `cli_version` pin line, migrated into `mise.toml` once). The CLI pin now lives in `mise.toml`, which the installer writes on first install and rewrites only when you pass `--upgrade-cli` / `--cli-version`
- `.github/labeler.yml`, `.zap/rules.tsv`, `.markdownlint.json`
- Root `Taskfile.yml` — only if absent; otherwise install.sh prints the `includes:` block to paste in
- `package.json` — only if absent (otherwise see below)
- Map Pattern entry files (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/index.md`) — seeded from `cli/slopstopper/data/templates/entry-files/` when absent; never overwritten. If they exist but don't link the map, the `ss:hygiene:entry-files` check fails with a paste-ready snippet in its report — apply it manually rather than re-seeding

**Conservatively additive on shared files — adopter content preserved:**

- `package.json` devDeps merge: adds missing keys; existing keys are kept on version conflict (warning printed, not error).
- `.gitignore`: appends a `# slopstopper begin` / `# slopstopper end` marker-bracketed block exactly once. Re-runs detect the marker and skip; adopter's existing lines are never edited.
- `public/_headers` (only if `public/` exists): appends a commented-out security-headers baseline inside `# slopstopper security headers begin/end` markers. Same idempotent skip on re-run.

**Everything else is left alone** — source code, build outputs, custom workflows under `.github/workflows/` outside the `ss-*` namespace, generic configs (`.eslintrc`, `tsconfig.json`, etc.), and anything under `app/`, `src/`, `worker/`, etc.

**One risk worth flagging:** inline customisations to `ss-*.yml` workflow body content (bespoke `gh issue create` blocks, extra steps, custom env vars beyond what `.slopstopper.yml` covers) get wiped on the next `install.sh` re-run because workflow files are wholesale-replaced. Push bespoke wording into the check's META in `slopstopper-cli` upstream rather than hand-editing the YAML locally. See the **Refresh-only** section below for how to diff and re-apply on refresh.

By default the installer ships **Task-driven workflows** — every check runs via `task ss:<category>:<check>` so the suite shares one invocation surface with `task build`, `task deploy`, etc. The workflows install the toolchain via `jdx/mise-action`, which reads `mise.toml` and installs both the pinned `slopstopper-cli` and `task`, so adopters don't need either in their CI runners by hand. If the adopter explicitly doesn't want Task in their CI, install with `--no-task`:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash -s -- --no-task
```

`--no-task` post-processes each shipped workflow at install time to rewrite `task ss:<X>` lines to `slopstopper run <X>` — same execution path, just without the Task layer. (The `jdx/mise-action` step stays; mise still installs the pinned CLI, and `task` simply goes unused.) Default mode is the right choice for most adopters; `--no-task` is the escape hatch.

Full two-step variants (all flags, optional explicit target dir):
```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
bash install.sh [TARGET_DIR]                   # default Task mode
bash install.sh --no-task [TARGET_DIR]         # CLI-direct mode
```

## Step 3 — What just landed

Sanity-check the install dropped what you expect:

- `slopstopper-cli` — installed and activated by **mise**, **pinned in `mise.toml`** (`[tools]` "pipx:slopstopper-cli"). Confirm with `slopstopper --version` (must equal the pin; ensure mise is activated in your shell). Every check runs through this. First install records the latest published version as the pin; it never moves on a plain re-run.
- `mise.toml` — the per-repo toolchain pin (`"pipx:slopstopper-cli"` + `task`). Both `install.sh` (local) and the `ss-*.yml` workflows (`jdx/mise-action`) read it, so local and CI run the same version. Commit it. Move the CLI pin deliberately with `install.sh --upgrade-cli` or `install.sh --cli-version X.Y.Z` (both wrap `mise use`). A legacy `cli_version` in `.slopstopper.yml` is migrated here and removed on the next run.
- `Taskfile.ss.yml` — thin `task ss:*` shims that each call `slopstopper run <category>:<check>` under the covers. Useful for adopters who already drive their dev loop with `task`.
- `Taskfile.yml` — created if missing (otherwise: needs manual `includes:` block per Step 1.1).
- `.ss/server.js` — tiny static-server shim for serving the built site on `:8080` during the local loop. The **only** file the installer seeds into `.ss/` for a fresh adopter — every other CLI-managed file (Playwright specs, Playwright config, lighthouserc dev + prod) lives inside the slopstopper-cli wheel and only lands in `.ss/` if you opt in by writing a same-named override there.
- `.ss/.workflows-installed` — manifest of installed workflows (tracks deletions on reinstall; commit this).
- `.github/workflows/ss-*.yml` — the curated installer set (~21 files). Each workflow body is now ~8 lines: install CLI, `slopstopper run …`, `slopstopper emit … --target pr-comment|issue`.
- `package.json` — devDeps merged.
- `.claude/skills/slopstopper-install/SKILL.md` + `.claude/skills/slopstopper-triage/SKILL.md` — the project-level Claude Code playbooks. Auto-discovered by Claude Code for any contributor working in this repo. Commit them.

**What's NOT there any more** (if you're updating from a pre-CLI install): `.ss/scripts/` (every Python/bash script lives in `slopstopper-cli`); and `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`, `.ss/tests/` (now bundled in the wheel — installer scrubs unmodified byte-equal copies on re-run, but leaves customized files alone since they'll override via the CLI's templates resolver).

### Want to customize a Playwright spec or lighthouserc?

The CLI looks for `.ss/<filename>` first and falls back to the wheel's bundled copy. Use `slopstopper templates` to list, locate, and eject:

```bash
slopstopper templates list                       # see what's bundled + what's already ejected
slopstopper templates path lighthouserc.json     # print the resolved path (override-or-bundled)
slopstopper templates eject lighthouserc.json    # copy bundled → .ss/lighthouserc.json
$EDITOR .ss/lighthouserc.json
```

The CLI picks up the override on the next run. Caveat: customizations don't auto-merge with upstream changes — you own the file once you eject. `slopstopper templates eject` won't overwrite an existing `.ss/<filename>`, and the installer's byte-equality scrub leaves customized files alone.

**Confirm the installed set matches upstream.** `install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. To catch this:

```bash
# inside the target repo, after install
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | grep -vE '^ss-release\.yml$' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is a workflow that exists upstream but didn't land. If any look relevant, copy them from slopstopper's repo into `.github/workflows/` directly (and customize like the rest — Node version, URLs, page paths). Also worth flagging the gap upstream as an `install.sh` fix.

> **Infra workflows are expected misses, not gaps.** The `grep -vE '^ss-release\.yml$'` above filters out `ss-release.yml` — slopstopper's own PyPI release pipeline. It is `ss-`-prefixed but is *not* an adopter workflow (it isn't in `install.sh`'s `GENERIC_WORKFLOWS`), so without the filter it shows up here as a phantom "missing" workflow. If slopstopper adds more internal-only `ss-*` workflows, extend the exclusion rather than chasing them.

The installer's stdout summarises what's active vs what needs config — read it and relay to the user.

## Step 4 — Post-install configuration

The installer seeds a `.slopstopper.yml` config file at the repo root (if one doesn't exist yet) plus sensible defaults for `.github/labeler.yml`, `public/_headers` (commented baseline), `.zap/rules.tsv` (common false positives commented), and appends a `.gitignore` block for `.ss/reports/` and friends. None of those overwrite existing files. The rest of post-install is editing `.slopstopper.yml` to point the dynamic checks at the right URLs and tuning a few knobs.

### Edit `.slopstopper.yml`

The seeded file is fully commented; the main knobs to fill in:

```yaml
node_version: '22'              # match your package.json engines.node

headers:
  source: public/_headers       # or worker/headers.json, or null to skip the check
  format: cloudflare-text       # or json, or auto

urls:
  production: https://your-site.example.com
  preview:    https://staging.your-site.example.com

pages:
  smoke:         /,/about,/pricing
  accessibility: /,/about
  seo:           /

smoke:
  og_image_path: /og-image.png  # set to '' if you use per-post share images

workflows:
  disabled: []                  # list any ss-*.yml workflows to remove on next install.sh
```

### Optional: tune the hygiene thresholds

Every hygiene check reads its own thresholds from `.slopstopper.yml`, falling back to a sensible default when unset. You don't need to touch these to get started — but if a check fires for a reason that's actually fine (e.g. your repo intentionally has 30 docs pages, or your `CLAUDE.md` is meaningfully longer than 1500 words for project reasons), tune the cap rather than dropping content. Don't tune to silence noise; tune to match a deliberate design decision.

```yaml
hygiene:
  docs_size:
    max_total_size_kb: 150   # default — total .md under docs/ (excl. archive/)
    max_file_size_kb: 20     # default — largest single doc
    max_files: 25            # default — total doc count
  entry_files:
    max_words: 1500          # default — README.md, CLAUDE.md, AGENTS.md, etc.
```

Larger sites should also opt into `reliability.coverage.*` modes so accessibility/SEO/broken-links audit the whole sitemap on main and only changed pages on PRs — see [`.slopstopper.yml.example`](https://github.com/hungovercoders/slopstopper/blob/main/.slopstopper.yml.example) for the schema reference and resolution order.

### Push the Node version to a GitHub repo variable

Workflows read `${{ vars.SLOPSTOPPER_NODE_VERSION || '20' }}` — set the variable from `.slopstopper.yml`:

```bash
gh variable set SLOPSTOPPER_NODE_VERSION --body "$(grep '^node_version:' .slopstopper.yml | cut -d\' -f2)"
```

### URLs: GitHub repo variables vs. hardcoded vs. inert

`.slopstopper.yml` `urls.*` is the recommended path — survives `install.sh` re-runs. For per-environment overrides without editing the file, GitHub repo variables (`SMOKE_TEST_URL`, `ACCESSIBILITY_TEST_URL`, `LIGHTHOUSE_URL`, `SEO_TEST_URL`, `BROKEN_LINKS_TEST_URL`, `DAST_TEST_URL`) take precedence and live in repo settings.

Hardcoding inside `ss-reliability-*.yml` workflow files still works but gets wiped on `install.sh` re-run — avoid unless you have a reason.

## Step 5 — Set up the Map Pattern (if keeping the docs-* checks)

**Why the Map Pattern is worth it beyond passing the check:** the map is a token-efficiency play, not just a docs-structure rule. When `README.md`, `AGENTS.md` and `CLAUDE.md` are thin pointers into a `docs/index.md` index — rather than three fat files each restating the project — an agent (or a human) reads the index and opens only the category files relevant to the task. That cuts the tokens pulled into context on every agent invocation, which is real money at scale. Frame it to the user as a cost/latency win for AI-assisted work, not paperwork the check demands.

The three docs-* workflows (`docs-accuracy`, `docs-structure`, `docs-size`) validate a `docs/` directory laid out per slopstopper's governance pattern. If you're keeping them, the target needs a `docs/` directory shaped like this:

```
docs/
  index.md                    The map — table of categories, each linked
  <category-a>/README.md      One README per category named in the index
  <category-b>/README.md
  …
```

The structure check parses the table in `docs/index.md` (pattern: `| [category/](category/) | … |`) and fails the build if any listed category lacks a directory or `README.md`, or if there's an undocumented directory inside `docs/`. The directory tree must conform to the index — not the reverse. The entry-files check enforces the reverse half: README.md and AGENTS.md must link to `docs/index.md`, and CLAUDE.md must be a thin pointer to AGENTS.md (`@AGENTS.md` directive or a link). A budget without the pointer is pointless; the map only works if the entry files defer to it.

**Auto-seeded scaffolds.** On a fresh install, `install.sh` writes minimal pointer-shaped versions of all four files (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/index.md`) from `cli/slopstopper/data/templates/entry-files/` when they don't already exist — so a greenfield clone is green on Step 7's local loop without manual work. If a file already exists, the installer leaves it alone; remediation runs through the check's report-driven path (next paragraph).

**Remediating existing files.** When the target already has entry files but they don't link the map, `task ss:hygiene:entry-files` fails and writes `.ss/reports/entry-files/entry-file-size-report.md` with a paste-ready snippet for each violation:

- For a missing map pointer on `README.md` / `AGENTS.md` — a `> 🗺️ **Documentation map.** ...` callout to paste near the top of the file.
- For a CLAUDE.md that isn't a thin pointer — the full canonical CLAUDE.md body to replace the file contents with.
- For a missing `docs/index.md` — a minimal map template with an empty categories table.

Read the report, confirm the placement with the user if the file is non-trivial, then paste the snippet at the top of the offending file. Re-run `task ss:hygiene:entry-files` to confirm green.

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

The `ss:hygiene:entry-files` check enforces both the 1500-word budget on each of the three entry files AND the pointer rule above. Aim well under the budget — it's the ceiling, not the target. Knobs in `.slopstopper.yml` if you need to override:

```yaml
hygiene:
  entry_files:
    max_words: 1500
    require_map_pointer: true        # set to false to disable the pointer rule only
    map_path: docs/index.md          # override if your map lives elsewhere
```

**Cross-references in docs:** the `docs-accuracy` check scans for `` `backtick-quoted` `` filenames and broken markdown links. Use full repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) so the checker can resolve them.

If none of this fits the target — short-lived prototype, single-file tool, generated docs only — delete the three workflows instead. `.ss/.workflows-installed` will remember the deletion so re-installs don't bring them back.

## Step 6 — Surface what's installed via README badges

After the workflows are live, surface them in the target's README. One GitHub Actions badge per `ss-*.yml` workflow plus a "powered by slopstopper" advert badge — gives anyone landing on the repo an instant sense of what's being checked and that the gates are real.

Generate the block via the CLI:

```bash
slopstopper badges                     # preview to stdout
slopstopper badges > badges.md         # write to a file for review
slopstopper badges --no-advert         # skip the powered-by badge
```

The command:

- Scans `.github/workflows/ss-*.yml` so it only badges workflows actually installed (deletions tracked via `.ss/.workflows-installed` are respected).
- Detects `OWNER/REPO` from `$GITHUB_REPOSITORY` (in CI) or `git remote get-url origin` (locally). Pass `--owner X --repo Y` to override (useful for a freshly-init'd repo with no remote yet).
- Groups badges by loop (Security / Hygiene / Reliability / Operational) with curated short labels (`SAST`, `Dependency CVEs`, `Core Web Vitals`, etc.) and always adds `?branch=main` so PR-run failures don't make the badge flicker red on `main`.
- Includes the static shields.io "powered by slopstopper" advert at the top unless `--no-advert` is passed (no live status, just an advert — keeps it portable).

**Then paste the block into the README**, at the right insertion point. Most READMEs have a "what this is" intro at the top; the Pipeline status block reads best immediately after that, before the install/usage section — so visitors see what's guarded before they read what it is.

## Refresh-only — diff upstream, re-apply customizations, spot new knobs

**Skip this section on a first install.** It's relevant only when `.slopstopper.yml` and `.ss/.workflows-installed` both existed in Step 1 (mode-detection) — i.e. the installer just ran in-place over an existing slopstopper install.

`install.sh` is idempotent but **not transactional** — every workflow YAML in `GENERIC_WORKFLOWS`, `Taskfile.ss.yml`, and `.ss/server.js` is rewritten wholesale on every run, and the CLI is reinstalled at the **pinned** version in `mise.toml` (a refresh never bumps it — see "Move the CLI pin" below). A refresh of an older install also migrates a legacy `cli_version` from `.slopstopper.yml` into `mise.toml` and strips the dead key. A few classes of customization get wiped and need re-applying; a few classes of upstream change need manual catch-up because the installer doesn't drag everything across. Walk this section before the local-verify loop in Step 7.

### Diff installed workflows against upstream

`install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. Catch the gap:

```bash
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | grep -vE '^ss-release\.yml$' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is an `ss-*.yml` workflow that exists upstream but isn't in your target. If any look relevant, copy them across directly (and customize like the rest — Node version pin, URLs, page paths). Flag the gap upstream as an `install.sh` fix. The `grep -vE '^ss-release\.yml$'` filters out slopstopper's own PyPI release pipeline — an infra workflow that isn't part of the adopter set, so it's an expected miss, not a gap.

### Re-apply customizations the installer wiped

The installer refreshes `Taskfile.ss.yml`, the `.ss/` overlay, and the `ss-*.yml` workflows wholesale. Anything hand-edited in those files is gone — but `.slopstopper.yml` is **never** overwritten by the installer, so the bulk of customization (node version, headers source/format, URLs, pages, og-image path, disabled workflows, hygiene thresholds) survives every re-run.

What still needs re-checking after a refresh:

- **Anything hand-edited inside `ss-*.yml` workflow files** beyond what `.slopstopper.yml` covers. Common case: extra workflow-level `permissions:` for a custom integration, a non-standard schedule, or workflow-level env vars beyond the documented URL/PAGES set. Diff against upstream to find them. Push bespoke wording into the check's META in `slopstopper-cli` upstream rather than hand-editing the YAML locally — workflow edits don't survive `install.sh` re-runs.
- **Anything hand-edited inside `.ss/tests/*.spec.ts`, `.ss/playwright.config.js`, or `.ss/lighthouserc.json`.** These used to be seeded by `install.sh` but now live inside the `slopstopper-cli` wheel. The installer's byte-equality scrub removes unmodified copies (so the wheel's version wins via the templates resolver); customized copies survive in `.ss/` and continue to override.
- **GitHub repo variables.** If `.slopstopper.yml` `node_version` changed, re-sync the `SLOPSTOPPER_NODE_VERSION` repo variable. If URLs are mirrored as repo variables, push those too:

  ```bash
  NODE_VER=$(slopstopper config get node_version 20)
  gh variable set SLOPSTOPPER_NODE_VERSION --body "$NODE_VER"
  ```

- **`.github/labeler.yml`** if upstream's labeler template added categories you want (the installer never overwrites your existing file, so new categories don't land automatically).

### Move the CLI pin (intentional upgrades)

`slopstopper-cli` is pinned per-repo in `mise.toml` (`[tools]` "pipx:slopstopper-cli"), and a plain refresh installs exactly that version — it never bumps the CLI. This is deliberate: a breaking upstream release can't surprise the repo. To move the pin:

```bash
bash install.sh --upgrade-cli        # bump to the latest published version
bash install.sh --cli-version X.Y.Z  # pin to an exact version
```

Either flag wraps `mise use` to rewrite the `"pipx:slopstopper-cli"` entry in `mise.toml`, install that version locally, and the change ships to CI (`jdx/mise-action`) once you commit. The post-install banner surfaces "PyPI latest is X — run `install.sh --upgrade-cli`" when the pin is behind, so you always know an upgrade is available without it being forced. Before bumping, skim the slopstopper changelog for breaking changes, then run the Step 7 local-verify loop so the new version is green before you push the pin bump.

### Spot newly-shipped knobs in `.slopstopper.yml.example`

The `.slopstopper.yml.example` file in the slopstopper repo is the schema reference. Diff it against your repo's `.slopstopper.yml`:

```bash
diff <(curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/.slopstopper.yml.example) .slopstopper.yml
```

Any keys present upstream but missing locally are new knobs you can opt into. Most ship with sensible defaults so no action is required — but the diff is the easiest way to know what changed.

Surfaces worth checking explicitly:

- **`hygiene.docs_size.*` / `hygiene.entry_files.*`** — per-check thresholds and rule toggles. Defaults are intentionally tight (150 KB / 25 files / 1500 words / map-pointer required). If a `docs-size`, `entry-files` budget, or `entry-files` pointer alert started firing post-refresh, the threshold knob (or `require_map_pointer: false` if the rule is wrong for this repo) is usually what's wanted — not deleting docs.
- **`reliability.coverage.{pr,main,cron}`** — page-discovery modes. Adopters with a sitemap should opt in to `sitemap` on main and `changed` on PRs; otherwise reliability checks only audit `/` by default.
- **`reliability.coverage.cross_cutting_paths`** — escalation triggers for `changed` mode. If a PR-only audit skipped pages that should have been included, this is the lever.

If a previously-failing check started passing after a refresh without any code change, eyeball whether a default got loosened upstream — those are flagged in the slopstopper changelog.

### Spot new checks and task targets

Two surfaces to scan after a refresh:

1. **The CLI's check registry.** `slopstopper --help` lists subcommands; the canonical list of check names is in `cli/slopstopper/checks/__init__.py`'s `REGISTRY` dict upstream. If a new check landed (e.g. `reliability:<new-check>`), it's runnable as `slopstopper run reliability:<new-check>` even before any workflow ships it.
2. **The Taskfile shims.** Re-running the installer refreshes `Taskfile.ss.yml`, which mirrors every CLI check as a `task ss:*` shim. Eyeball:

   ```bash
   task --list | grep '^\* ss:'
   ```

If anything looks unfamiliar, check `Taskfile.ss.yml` for the `desc:` and `summary:` (each shim documents the env vars it forwards). New checks are usually surfaced as part of a new workflow — if a new workflow landed in the diff above, you'll see the matching task here regardless, since `Taskfile.ss.yml` is refreshed wholesale.

If new workflows did land and you want the README badges refreshed to match, re-run `slopstopper badges` and replace the existing Pipeline status block in `README.md`.

### Clean up redundant artefacts

Adopter repos should hold exactly the **expected set** of slopstopper artefacts plus their own customisations — nothing more. Anything outside that set is noise: a former skill that's been folded into another, an old `ss-*-check.yml` that's been renamed upstream, a `.ss/` file that moved into the CLI wheel. Keep the working tree tidy on every refresh.

**What `install.sh` and `install-skill.sh` already clean up automatically:**

- `<repo>/.claude/skills/<name>/` directories listed in `OBSOLETE_SKILLS` — currently `install-slopstopper` (single-skill legacy) and `slopstopper-update` (folded into `slopstopper-install`). Both installer scripts hold the same list.
- `.ss/scripts/` — pre-CLI artefact, scrubbed wholesale on every install.
- Byte-equal copies of `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`, `.ss/tests/` — these moved into the slopstopper-cli wheel; byte-identical adopter copies are removed (the wheel's version wins via the templates resolver). Customised copies survive.
- Workflows the adopter explicitly disabled via `.slopstopper.yml` `workflows.disabled` — removed on every install.

**What you should sanity-check manually on refresh** (the installer can't auto-detect these without an explicit removal list):

```bash
# 1. Skills: anything in .claude/skills/slopstopper-* that isn't in the current expected set is stale
ls -d .claude/skills/slopstopper-*/ 2>/dev/null
# Expected currently: slopstopper-install, slopstopper-triage. Anything else → flag for the user.

# 2. Workflows: anything matching ss-*-check.yml that doesn't exist upstream is stale
diff \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | grep -vE '^ss-release\.yml$' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
# Lines prefixed with `>` are local-only ss-* files — could be stale or a workflow the adopter
# deliberately customised away from upstream. Ask the user before deleting.
```

The line to draw before deleting:

- **Slopstopper-shipped, no longer in the expected set** → delete. Examples: `slopstopper-update/SKILL.md`, an `ss-old-check.yml` that was renamed in a recent slopstopper release.
- **Adopter-customised, intentionally divergent** → keep. Examples: an `ss-*.yml` the adopter forked under the same name with bespoke logic, a hand-edited `Taskfile.ss.yml` shim. `.ss/.workflows-installed` tracks adopter deletions but not adopter modifications — when in doubt, ask the user.
- **Adopter-added content under `.claude/skills/` with a non-`slopstopper-` prefix** → not slopstopper's, never touch.

When a clean-up surfaces something the installer should've handled automatically, the fix is to add it to `OBSOLETE_SKILLS` (or the equivalent list for the artefact type) in both `install.sh` and `install-skill.sh` upstream — see the AGENTS.md change-impact table's "Removing a slopstopper-shipped artefact" row. The next adopter then gets the cleanup for free.

## Step 7 — Drive every check to green locally, **before** pushing

This is the spine of a good install. `task ss:<category>:<action>` is the canonical interface — humans, agents and CI all go through it. The shipped workflows install Task themselves and invoke checks the same way. Running locally in a tight loop — fix, re-run, fix, re-run — is an order of magnitude faster than pushing and waiting on CI for each iteration. The goal of this step is that the first CI run on the target's PR is a **confirmation pass**, not a discovery pass.

If the target was installed with `--no-task` (rare; opt-out for adopters who don't want Task in their CI), replace every `task ss:<X>` below with `slopstopper run <X>` — same code, same exit codes, same reports.

**Two passes, in order:**

### Pass A — Static checks (no URL, no build needed, runs in seconds)

Run the two static aggregates first. They cover every static workflow that ships with the install:

```bash
npm install                  # pulls merged devDeps once
task ss:hygiene:test         # docs-size + docs-structure + docs-accuracy + entry-files + csp-exceptions + complexity
task ss:security:scan        # SAST + secrets + dependency CVEs + DAST (DAST needs URL — skip or run after Pass B)
```

Or invoke each shim individually:

```bash
task ss:security:secrets           # Gitleaks — fast, usually surfaces something
task ss:security:sast              # Semgrep
task ss:security:vulnerability:all # Trivy (CVE scan of dependencies)
task ss:hygiene:complexity         # lizard
task ss:hygiene:docs-accuracy      # repo-relative link resolver
task ss:hygiene:docs-structure     # Map Pattern validator
task ss:hygiene:docs-size          # docs/ size budget
task ss:hygiene:entry-files        # README/AGENTS/CLAUDE word budget
task ss:hygiene:csp-exceptions     # if headers.source is configured
```

For each failure: fix the root cause locally, re-run **just that one check** to confirm, and only move on once green. Anticipated issues during Pass A are covered in `slopstopper-triage`.

### Pass B — Dynamic checks (need a URL + a built site)

The reliability and DAST shims assert behaviour on a running site. The fastest local loop is to build once, serve via the installed `.ss/server.js` shim on `localhost:8080`, then run each dynamic shim against `http://localhost:8080` as a bare-positional URL arg.

```bash
npm run build                                            # target's own build
node .ss/server.js &                                     # static server on :8080
task ss:reliability:smoke         -- http://localhost:8080
task ss:reliability:accessibility -- http://localhost:8080
task ss:reliability:cwv           -- http://localhost:8080
task ss:reliability:seo           -- http://localhost:8080
task ss:reliability:broken-links         -- http://localhost:8080
task ss:security:dast             -- http://localhost:8080    # needs Docker for OWASP ZAP
```

`task ss:security:dast` is the heaviest local check (pulls and runs the OWASP ZAP container) — leave it for last in the loop. Skip it locally if Docker isn't installed and run it on CI only.

Iterate the same way as Pass A: fix root cause locally, re-run the single task, move on once green.

**Only when both passes are clean do you push.** At that point CI is confirming what you already know.

### When a check fails during the local loop

A few classes of failure come up reliably on first installs (Node version pin, missing security headers, missing `.github/labeler.yml`, third-party-widget a11y violations, ZAP false positives, etc.). The **`slopstopper-triage`** skill has the per-check playbook — symptom → diagnostic step → fix location → cross-link to the relevant category README. Let it handle each failure as you iterate.

Don't try to fix everything yourself inside this skill. Hand off, fix the one check, come back to Pass A / Pass B and re-run.

## Step 8 — Push and watch the confirmation pass

After Step 7's local loop is fully green, push to a PR branch. CI should mirror what you saw locally.

A few checks are CI-only by design (Dependency Review needs GHAS or Dependency Graph; auto-label-pr needs `.github/labeler.yml`). If they fail on the first CI run, hand them to the **`slopstopper-triage`** skill — its check-by-check table covers them alongside the local checks.

If anything was green locally but red on CI: that's signal there's an environmental delta (Node version pin, missing env var, file-permissions, OS-specific tool). Diagnose, fix, and add the difference to the local pre-flight for next time.

## Step 9 — When NOT to install slopstopper

Don't push the user to install if:
- The target already has a competing quality suite they're happy with (don't double up).
- It's a one-file script or library where 21 workflows is overkill.
- The target is a **private repo with a tight CI minutes budget**. Actions minutes are free on public repos but billed on private ones, and slopstopper is minutes-hungry: ~18 checks per PR plus scheduled reliability/smoke runs, with the dynamic checks (Playwright, Lighthouse CI, ZAP-in-Docker) the heaviest. Public repos run the whole suite free; private repos should weigh the recurring cost (see the Step 1.12 pre-flight callout).
- The target's deploy isn't Cloudflare Workers Builds. Slopstopper's deploy story assumes that — the install still works, but the user loses one of its selling points.

In any of those cases: recommend a partial adoption (cherry-pick specific workflows) rather than the full install.

## Step 10 — When to hand off + maintaining this skill

This skill is one of two in the slopstopper skill set:

- **`slopstopper-install`** (this one) — first-time install OR refresh of an existing install. The mode-detection branch at the top of the skill routes you to the right subset of steps.
- **`slopstopper-triage`** — diagnose a failing slopstopper check, end-to-end: workflow → local task → report → finding category → fix location.

Hand off to `slopstopper-triage` mid-install whenever a check fails during Step 7's local loop, or during a refresh when a previously-green check goes red.

### Maintaining this skill when slopstopper changes

This skill names specific files, env vars, workflow IDs, the `GENERIC_WORKFLOWS` list in `install.sh`, and the local `task ss:*` commands that mirror each workflow. **Any change to slopstopper that touches one of those needs a corresponding update here**, or the skill silently drifts away from reality.

Triggers that require revisiting this skill:

- A workflow is added, removed, or renamed under `slopstopper/.github/workflows/ss-*.yml` → update the workflow count in the intro, Step 1.2, and Step 3; add/remove the matching local-CLI row in Step 7's Pass A or Pass B; add/remove the badge example in Step 6. (The per-check failure entry lives in `slopstopper-triage` — update there too.)
- The `GENERIC_WORKFLOWS` array in `slopstopper/install.sh` changes → confirm the "What just landed" inventory in Step 3 still matches.
- A check is added or renamed in `cli/slopstopper/checks/__init__.py`'s `REGISTRY` → update Step 7's `slopstopper run` list (and `slopstopper-triage`'s reproduce table).
- A `task ss:*` shim is renamed in `slopstopper/Taskfile.ss.yml` → update the matching command in Step 7's Pass A or Pass B (and `slopstopper-triage`).
- A new env var is introduced for a dynamic check → add to the URL-defaults list in Step 4 and to the Pass B example in Step 7.
- A new `slopstopper` subcommand is added (e.g. `init`, `inspect`) → mention in the intro and surface in the relevant Step.
- The installer's behaviour changes (new tracked-files mechanism, different deletion semantics, additional refresh targets, CLI install path change) → update the "Refresh-only" section's "what the installer wipes / leaves alone" lists.
- A new hardcoded-on-reinstall surface emerges (another file the installer overwrites that users commonly hand-edit) → add to the "Re-apply customizations" subsection of the "Refresh-only" section.

The companion to this is `AGENTS.md` in the slopstopper repo: its "When making changes" table flags the skill as a follow-on target whenever a change of the above kind ships. If you're updating slopstopper itself and that table isn't pointing readers back here, fix that first.

The skills are installed at project level by `install.sh` (and by `install-skill.sh` when run standalone — refresh mode). Both scripts iterate a `SKILLS` array (`slopstopper-install`, `slopstopper-triage`), atomically write each `<repo>/.claude/skills/<skill>/SKILL.md`, and validate each download starts with frontmatter. If you rename a skill, add a third, change the frontmatter contract, or otherwise change the shape of what gets fetched, update both scripts' arrays AND `docs/runbooks/INSTALL_SKILLS.md` in the same change — otherwise the installers silently drift away from what the skill set expects to land at.

## Notes for the agent

- The install is reversible by deleting the slopstopper-added files. Commit the install as its own commit so it's easy to revert.
- Re-running `install.sh` is safe — it tracks deletions in `.ss/.workflows-installed` so workflows the user has deliberately removed don't come back.
- Hardcoded URL edits to `ss-*.yml` workflows are wiped on reinstall. Tell the user this so they're not surprised later.
- Step 7 is the most important part of the install. Don't push until it's green locally — the local loop is faster than CI by an order of magnitude.
- Surface findings, don't auto-fix everything. The user decides what's a real issue vs. a tuning task vs. a deletion candidate.
