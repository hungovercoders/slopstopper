# Steps 2–3 — Run the installer, then read what landed

> Part of the `slopstopper-install` skill. `SKILL.md` says when to read this; it is not loaded until then.

## Step 2 — Run the installer

Before running anything, ensure you're on a clean branch:

```bash
git status                              # must show clean
git checkout -b chore/slopstopper-install   # or chore/slopstopper-refresh for a refresh
```

`install.sh` adds up to 27 workflow files, the two composite actions, a `Taskfile.ss.yml` and a `.slopstopper.yml` to the repo in one shot. On `main` that's an awkward 27+-file commit; on a dedicated branch the diff is reviewable and the rollback is `git checkout main && git branch -D <branch>`. If `git status` is dirty, stop and reconcile first — the installer doesn't ask before writing into `ss-*.yml` or `Taskfile.ss.yml`. On a refresh, the wipe-and-replace behaviour will clobber anything sitting in the tracked files it rewrites — commit or stash first.

From the target repo root, download-review-run in two steps:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh -o install.sh
bash install.sh                                # default Task mode, `ui` profile
bash install.sh --profile api                  # or the profile you agreed above
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

The installer is idempotent. Re-running it pulls newer checks but respects deletions (tracked via `.ss/.workflows-installed`). It does **not** bump `slopstopper-cli`: the CLI is pinned per-repo in `mise.toml` (`[tools]` "pipx:slopstopper-cli"), and a plain re-run honours that pin via `mise use` (which installs exactly that version). A breaking upstream release therefore can't reach the repo until someone moves the pin with `install.sh --upgrade-cli` (latest) or `install.sh --cli-version X.Y.Z` (exact). An older install that pinned `cli_version` in `.slopstopper.yml` has the value migrated into `mise.toml` and the dead key stripped on the next run; a dead `node_version` key (never read — node lives in `mise.toml`) is likewise stripped. All slopstopper files live under the `ss` namespace — your repo's existing files are not touched. If a pre-CLI install left a `.ss/scripts/` directory behind, the installer scrubs it on first run.

**`install.sh` also installs the SlopStopper Claude Code skills at project level** — `<target>/.claude/skills/slopstopper-{install,triage}/SKILL.md` — so every contributor that clones the repo picks them up automatically (Claude Code auto-discovers project-level skills). Commit the resulting files alongside the workflows. Pass `--no-skills` or set `SLOPSTOPPER_NO_SKILLS=1` to disable. To refresh just the skills later without re-running the whole installer, use `install-skill.sh` from inside the repo. If you've previously run an older version of `install-skill.sh` that wrote to `~/.claude/skills/slopstopper-*`, the installer warns you so you can clean up the user-level copies before they shadow the project-level ones.

### What `install.sh` writes (and leaves alone)

Three categories of write, in order of "how much trust to extend on re-run":

**Always overwritten — slopstopper-owned, safe to clobber:**

- `Taskfile.ss.yml`, `.ss/.workflows-installed`, `.github/actions/ss-*/`
- Workflows under `.github/workflows/ss-*.yml` that are in `GENERIC_WORKFLOWS` and not listed in `.slopstopper.yml` `workflows.disabled`
- `mise.toml` — the `"pipx:slopstopper-cli"` + `task` + `node` pins (written via `mise use`); `slopstopper-cli` itself is installed/activated by mise at the **pinned** version. A plain re-run never bumps the CLI; `node` is seeded (`= "20"`) only when the repo doesn't already declare one; `--upgrade-cli` / `--cli-version` move the CLI pin
- `<repo>/.claude/skills/slopstopper-install/SKILL.md` and `<repo>/.claude/skills/slopstopper-triage/SKILL.md` (project level — opt out with `--no-skills`)
- `.githooks/pre-push` — the pre-push hygiene gate (opt out with `--no-hooks`). The *file* is always refreshed; the `core.hooksPath` **wiring** is only set when safe (see next list — it's left alone if the adopter runs their own hook manager)

**Seeded only if missing — adopter-owned, NEVER overwritten on re-run:**

- `.slopstopper.yml` (config; once it exists `install.sh` never touches it — **except** stripping a legacy `cli_version` pin line (value migrated into `mise.toml` once) and a dead `node_version` key (just removed — node lives in `mise.toml`)). The CLI + node pins now live in `mise.toml`, which the installer writes on first install and rewrites only when you pass `--upgrade-cli` / `--cli-version`
- `.github/labeler.yml`, `.zap/rules.tsv`, `.markdownlint.json`
- Root `Taskfile.yml` — only if absent; otherwise install.sh prints the `includes:` block to paste in
- `package.json` — only if absent (otherwise see below)
- Map Pattern entry files (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/index.md`) — seeded from `cli/slopstopper/data/templates/entry-files/` when absent; never overwritten. If they exist but don't link the map, the `ss:hygiene:entry-files` check fails with a paste-ready snippet in its report — apply it manually rather than re-seeding

**Conservatively additive on shared files — adopter content preserved:**

- `package.json` devDeps merge: adds missing keys; existing keys are kept on version conflict (warning printed, not error).
- `.gitignore`: appends a `# slopstopper begin` / `# slopstopper end` marker-bracketed block exactly once. Re-runs detect the marker and skip; adopter's existing lines are never edited.
- `public/_headers` (only if `public/` exists): appends a commented-out security-headers baseline inside `# slopstopper security headers begin/end` markers. Same idempotent skip on re-run.
- `core.hooksPath` (git config, not a file): set to `.githooks` **only** when the adopter has no custom `core.hooksPath` and no other hook manager (`.husky/`, `lefthook.yml`/`.yaml`, `.pre-commit-config.yaml`). If they already manage hooks, the installer drops `.githooks/pre-push` in but leaves their config alone and prints a one-line opt-in. `--no-hooks` / `SLOPSTOPPER_NO_HOOKS=1` skips the whole step.

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
bash install.sh --no-hooks [TARGET_DIR]        # skip the pre-push hygiene hook
```

## Step 3 — What just landed

Sanity-check the install dropped what you expect:

- `slopstopper-cli` — installed and activated by **mise**, **pinned in `mise.toml`** (`[tools]` "pipx:slopstopper-cli"). Confirm with `slopstopper --version` (must equal the pin; ensure mise is activated in your shell). Every check runs through this. First install records the latest published version as the pin; it never moves on a plain re-run.
- `mise.toml` — the per-repo toolchain pins (`"pipx:slopstopper-cli"` + `task` + `node`). Both `install.sh` (local) and the `ss-*.yml` workflows (`jdx/mise-action`) read it, so local and CI run the same versions — node included, with no separate `setup-node` step. Commit it. Move the CLI pin deliberately with `install.sh --upgrade-cli` or `install.sh --cli-version X.Y.Z` (both wrap `mise use`). A legacy `cli_version` in `.slopstopper.yml` is migrated here and removed on the next run; a dead `node_version` key is removed too.
- `Taskfile.ss.yml` — thin `task ss:*` shims that each call `slopstopper run <category>:<check>` under the covers. Useful for adopters who already drive their dev loop with `task`.
- `Taskfile.yml` — created if missing (otherwise: needs manual `includes:` block per Step 1.1).
- `.ss/.workflows-installed` — the **only** file the installer seeds into `.ss/`: the manifest of what it installed, which is how re-runs respect a deliberate deletion. The static server for the local loop is not a file in the repo any more — it ships inside the wheel as `slopstopper serve` (eject with `slopstopper templates eject server.js` only if you need to customise it).
- `.ss/.workflows-installed` — manifest of installed workflows (tracks deletions on reinstall; commit this).
- `.github/workflows/ss-*.yml` — the curated installer set, minus whatever the profile drops (24 checks on `ui`, 16 on `api`, 10 on `library`), plus `ss-pr-summary.yml`, `ss-workflow-failure-issue.yml` and the doc-updater under all three. Each workflow body is now ~8 lines: install CLI, `slopstopper run …`, `slopstopper emit … --target pr-comment|issue`.
- `ss-pr-summary.yml` — posts **one** rolling comment per PR summarising every check (`❌ SlopStopper — 2 of 24 checks failed`, failures in a table, the rest folded). The per-check workflows post compact comments — a verdict line, the failing items, the report folded away — and **delete their comment when they pass**, so a green PR carries only the summary. Tell the user this up front: the first green PR looking "empty" of bot comments is the intended behaviour, not a broken install.
- `.slopstopper.yml` `profile:` — the key the installer wrote (or left alone). Confirm the installed set matches it with `slopstopper profile show`: it prints the active profile, where it came from, and every workflow this repo is deliberately not carrying. Worth running before the missing-workflow comparison below — a workflow the profile dropped is *supposed* to be absent, and will otherwise read as a gap.
- `package.json` — devDeps merged.
- `.claude/skills/slopstopper-install/SKILL.md` + `.claude/skills/slopstopper-triage/SKILL.md` — the project-level Claude Code playbooks. Auto-discovered by Claude Code for any contributor working in this repo. Commit them.
- `.githooks/pre-push` — the pre-push hygiene gate (runs `task ss:hygiene:test` before every push). Commit it. On a normal install the installer also sets `git config core.hooksPath .githooks`; confirm with `git config --get core.hooksPath`. If the adopter already runs husky/lefthook/pre-commit (or a custom hooksPath), the file lands but the wiring is skipped with an opt-in note (run `git config core.hooksPath .githooks`, or add `task ss:hygiene:test` to their own manager). Skipped entirely under `--no-hooks`.

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

Any line in the output is a workflow that exists upstream but didn't land. **Subtract the profile's set first** — `slopstopper profile expand <name>` lists the workflows this repo drops on purpose, and they'll all show up here otherwise. Of what remains, if any look relevant, copy them from slopstopper's repo into `.github/workflows/` directly (and customize like the rest — Node version, URLs, page paths). Also worth flagging the gap upstream as an `install.sh` fix.

> **Infra workflows are expected misses, not gaps.** The `grep -vE '^ss-release\.yml$'` above filters out `ss-release.yml` — slopstopper's own PyPI release pipeline. It is `ss-`-prefixed but is *not* an adopter workflow (it isn't in `install.sh`'s `GENERIC_WORKFLOWS`), so without the filter it shows up here as a phantom "missing" workflow. If slopstopper adds more internal-only `ss-*` workflows, extend the exclusion rather than chasing them.

The installer's stdout summarises what's active vs what needs config — read it and relay to the user.
