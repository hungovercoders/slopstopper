---
name: slopstopper-update
description: Update an existing slopstopper installation in place. Use when a user asks to refresh slopstopper, pull in new slopstopper checks, upgrade slopstopper, re-sync slopstopper after a long gap, or "see what's new in slopstopper". Covers re-running install.sh idempotently, refreshing the trio of skills via install-skill.sh, diffing the installed workflow set against upstream for additions, re-applying customizations that get wiped on reinstall, surfacing new task targets, and running the local static aggregates before pushing. For a first-time install use slopstopper-install; for diagnosing a failing check after the update use slopstopper-triage.
---

# Update slopstopper

You're being asked to refresh an existing slopstopper installation in a repo that already has it. The install is idempotent, so the mechanical part is "re-run the installer" — which also re-pulls `slopstopper-cli` from upstream (via `pipx upgrade` or `pip install --user --upgrade`). A few classes of customization get wiped on every re-run, and a few classes of upstream change need manual catch-up because the installer doesn't drag everything across. This skill walks the steady-state upgrade flow so nothing important gets missed.

**The CLI is the upgrade path for every check's logic.** Each check used to be a Python/bash script under `.ss/scripts/`; now it's a module inside `slopstopper-cli`, and `install.sh` ships the CLI itself. That means a re-run picks up new behaviour in checks without touching adopter files — and a pre-CLI install gets its old `.ss/scripts/` scrubbed clean automatically.

If the target doesn't have slopstopper installed yet, this is the wrong skill — use `slopstopper-install` instead. If you're triaging a check that's failing right now, use `slopstopper-triage`.

## Step 1 — Refresh this skill first

The update playbook itself evolves. Before doing anything else, re-run the skill installer so you're working from the latest version:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
```

The script is idempotent: it compares each fetched `SKILL.md` against what's on disk and only overwrites if the content differs. Safe to run any time. It refreshes the whole trio (`slopstopper-install`, `slopstopper-update`, `slopstopper-triage`), not just this one.

## Step 2 — Re-run the installer in-place

From the target repo root:

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

What this refreshes (always, on every run):
- `slopstopper-cli` — `pipx upgrade slopstopper-cli` (preferred) or `pip install --user --upgrade slopstopper-cli` fallback. Pulled from PyPI, so always lands the latest release. Confirm with `slopstopper --version`.
- `Taskfile.ss.yml` — thin `task ss:*` shims that all call `slopstopper run …` under the hood.
- `.ss/server.js` — the only file the installer seeds into `.ss/`. Wholesale replacement.
- Each workflow in `install.sh`'s `GENERIC_WORKFLOWS` array — provided it's still present in the target's `.github/workflows/`. The workflow body itself is short now (~8 lines: install CLI, `slopstopper run …`, `slopstopper emit …`, optionally `slopstopper emit … --on-pass=close`), so most updates are CLI-version bumps invisible to the workflow YAML. Issue lifecycle (open + close + body marker + `slopstopper` label) is fully owned by `slopstopper emit` as of the issue-emission unification — adopters who customised the legacy inline `gh issue create` blocks will see them replaced on update; re-apply any bespoke wording via the check's META (`issue_title` / `issue_close_comment` / etc.) rather than back in the workflow YAML. `ss-workflow-failure-issue.yml` now dedupes against per-check issues by looking for the `<!-- slopstopper:check=… -->` body marker (run-URL fallback retained for 30 days for pre-marker issues).

What it scrubs:
- `.ss/scripts/` — pre-CLI installs leave this directory behind. Every Python/bash script that used to live there is now bundled in `slopstopper-cli`. The installer detects the directory and removes it; commit the deletion as part of the upgrade PR.
- Byte-equal copies of `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`, `.ss/tests/` — these used to be seeded by `install.sh` but now live in the wheel. The installer checks each against the package-data copy and only removes the file if it's identical. Customized files survive and continue to override via the CLI's templates resolver.

What it leaves alone:
- Any workflow you've deleted (tracked via `.ss/.workflows-installed` — the marker file is the source of truth, commit it).
- `.slopstopper.yml` — never overwritten. All config (URLs, headers source, thresholds, disabled workflows) survives every re-run.
- Your existing `Taskfile.yml` if you have one (just verifies the include is present, otherwise prints the block to paste).
- Anything in `package.json` apart from devDependencies merges.
- Your own files outside the `ss` namespace.

The installer's stdout summarises what was installed, refreshed, or skipped as a previously-deleted item. Read it and relay to the user — especially if anything was added (a newly-shipped upstream workflow showing up for the first time) or skipped (a workflow you deleted that the installer is honouring).

## Step 3 — Diff installed workflows against upstream

`install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. Catch the gap:

```bash
# inside the target repo, after re-running install.sh
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is an `ss-*.yml` workflow that exists upstream but isn't in your target. If any look relevant, copy them across directly from `https://github.com/hungovercoders/slopstopper/blob/main/.github/workflows/<name>` (and customize like the rest — Node version pin, URLs, page paths). Also worth flagging the gap upstream as an `install.sh` fix so the next adopter gets it for free.

## Step 4 — Re-apply customizations that got wiped (much smaller than it used to be)

The installer refreshes `Taskfile.ss.yml`, the `.ss/` overlay, and the `ss-*.yml` workflows wholesale. Anything hand-edited in those files is gone — but `.slopstopper.yml` is **never** overwritten by the installer, so the bulk of customization (node version, headers source/format, URLs, pages, og-image path, disabled workflows, hygiene thresholds) survives every re-run.

What still needs re-checking after an update:

- **Anything you hand-edited inside `ss-*.yml` workflow files** beyond what `.slopstopper.yml` covers. Common case: extra workflow-level `permissions:` for a custom integration, a non-standard schedule, or workflow-level env vars beyond the documented URL/PAGES set. Diff against upstream to find them.
- **Anything you hand-edited inside `.ss/tests/*.spec.ts`, `.ss/playwright.config.js`, or `.ss/lighthouserc.json`.** These are refreshed wholesale on every install. If you need persistent customization, fork the spec under a different name and update `pages.smoke|accessibility|broken_links` in `.slopstopper.yml` to skip the bundled one, OR upstream the change.
- **GitHub repo variables.** If `.slopstopper.yml` `node_version` changed, re-sync the `SLOPSTOPPER_NODE_VERSION` repo variable. If `urls.production` / `urls.preview` changed and you mirror them as repo variables, push those too:

  ```bash
  NODE_VER=$(slopstopper config get node_version 20)
  gh variable set SLOPSTOPPER_NODE_VERSION --body "$NODE_VER"
  # plus any URL variables you mirror
  ```

- **`.github/labeler.yml`** if upstream's labeler template added categories you want (the installer never overwrites your existing file, so new categories don't land automatically).

## Step 5 — Spot newly-shipped knobs

The `.slopstopper.yml.example` in the slopstopper repo is the schema reference. Diff it against your repo's `.slopstopper.yml`:

```bash
diff <(curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/.slopstopper.yml.example) .slopstopper.yml
```

Any keys present upstream but missing locally are new knobs you can opt into. Most ship with sensible defaults so no action is required — but the diff is the easiest way to know what changed.

Surfaces worth checking explicitly:

- **`hygiene.docs_size.*` / `hygiene.entry_files.max_words`** — per-check thresholds. Defaults are intentionally tight (150 KB / 25 files / 1500 words). If a `docs-size` or `entry-files` alert started firing post-upgrade, the threshold knob is usually what's wanted — not deleting docs.
- **`reliability.coverage.{pr,main,cron}`** — page-discovery modes. Adopters with a sitemap should opt in to `sitemap` on main and `changed` on PRs; otherwise reliability checks only audit `/` by default.
- **`reliability.coverage.cross_cutting_paths`** — escalation triggers for `changed` mode. If a PR-only audit skipped pages that should have been included, this is the lever.

If a previously-failing check started passing after an update without any code change, eyeball whether a default got loosened upstream — those are flagged in the slopstopper changelog.

## Step 6 — Check for new checks and task targets

Two surfaces to scan after an upgrade:

1. **The CLI's check registry.** `slopstopper --help` lists subcommands; the canonical list of check names is in `cli/slopstopper/checks/__init__.py`'s `REGISTRY` dict upstream. If a new check landed (e.g. `reliability:<new-check>`), it's runnable as `slopstopper run reliability:<new-check>` even before any workflow ships it.
2. **The Taskfile shims.** Re-running the installer refreshes `Taskfile.ss.yml`, which mirrors every CLI check as a `task ss:*` shim. Eyeball:

   ```bash
   task --list | grep '^\* ss:'
   ```

If anything looks unfamiliar, check `Taskfile.ss.yml` for the `desc:` and `summary:` (each shim documents the env vars it forwards). New checks are usually surfaced as part of a new workflow — if you skipped the workflow in Step 3 you'll see the task here regardless, since `Taskfile.ss.yml` is refreshed wholesale.

Flag any new checks the user might want to wire into local pre-commit hooks or the standard dev loop.

## Step 7 — Re-run the static aggregates locally before pushing

Same loop as `slopstopper-install` Step 7, condensed because the build / Playwright deps are already in place:

```bash
task ss:hygiene:test    # docs-size + docs-structure + docs-accuracy + entry-files + csp-exceptions + complexity
task ss:security:scan   # SAST + secrets + dependency CVEs (+ DAST if a URL is wired)
```

Or invoke each shim individually:

```bash
task ss:hygiene:docs-size
task ss:hygiene:docs-structure
task ss:hygiene:docs-accuracy
task ss:hygiene:entry-files
task ss:hygiene:complexity
task ss:hygiene:csp-exceptions
task ss:security:secrets
task ss:security:sast
task ss:security:vulnerability:all
```

(If the target was installed with `--no-task`, replace `task ss:<X>` with `slopstopper run <X>` throughout — same code path, same exit codes.)

Anything that comes back red is one of two things:

1. **A new check** that just landed and is hitting your repo for the first time → hand off to `slopstopper-triage` for the per-check playbook.
2. **An existing check** with a stricter default tuning than before (e.g. complexity threshold tightened in the new CLI release) → check `.slopstopper.yml.example` for the canonical schema and the per-check defaults; `slopstopper-triage` covers when to tune vs. fix.

Don't push until the local loop is green. The point of running the aggregates first is to keep the upgrade-PR's CI run as a confirmation pass, not a discovery pass — same principle as a fresh install.

## Step 8 — Push and watch the confirmation pass

Push to a PR branch. CI should mirror local. If a CI-only check goes red (Dependency Review, auto-label) or a previously-green check fails on CI but was green locally (Node version pin in the runner, missing repo variable, etc.), hand off to `slopstopper-triage`.

## When to hand off

- **First-time install on a different repo** → `slopstopper-install`.
- **A specific check is failing right now** (during or after the update) → `slopstopper-triage`.

## Maintaining this skill when slopstopper changes

Update this skill when:

- The installer's behaviour changes (new tracked-files mechanism, different deletion semantics, additional refresh targets, CLI install path change) → update Step 2's "what this refreshes / scrubs / leaves alone" lists.
- A new check is added to `cli/slopstopper/checks/__init__.py`'s `REGISTRY` → mention it in Step 6 and add to Step 7's `slopstopper run` list (and the equivalents in `slopstopper-install` Step 7 + `slopstopper-triage`'s reproduce table).
- A new env var is introduced for a dynamic check → add to Step 4's list and Step 4's `gh variable set` example.
- A new `slopstopper` subcommand ships (e.g. `init`, `inspect`) → mention in the intro and the relevant Step.
- A new hardcoded-on-reinstall surface emerges (e.g. another file the installer overwrites that users commonly hand-edit) → add to Step 4.
- The trio gains a fourth skill → update the Step 1 description of what `install-skill.sh` refreshes and the "When to hand off" pointers.

The AGENTS.md "When making changes" table in the slopstopper repo flags this skill alongside `slopstopper-install` and `slopstopper-triage` whenever a change of the above kind ships.
