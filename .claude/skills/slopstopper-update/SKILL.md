---
name: slopstopper-update
description: Update an existing slopstopper installation in place. Use when a user asks to refresh slopstopper, pull in new slopstopper checks, upgrade slopstopper, re-sync slopstopper after a long gap, or "see what's new in slopstopper". Covers re-running install.sh idempotently, refreshing the trio of skills via install-skill.sh, diffing the installed workflow set against upstream for additions, re-applying customizations that get wiped on reinstall, surfacing new task targets, and running the local static aggregates before pushing. For a first-time install use slopstopper-install; for diagnosing a failing check after the update use slopstopper-triage.
---

# Update slopstopper

You're being asked to refresh an existing slopstopper installation in a repo that already has it. The install is idempotent, so the mechanical part is "re-run the installer" — but a few classes of customization get wiped on every re-run, and a few classes of upstream change need manual catch-up because the installer doesn't drag everything across. This skill walks the steady-state upgrade flow so nothing important gets missed.

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
- `Taskfile.ss.yml`
- `.ss/scripts/`
- `.ss/tests/`
- `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`
- Each workflow in `install.sh`'s `GENERIC_WORKFLOWS` array — provided it's still present in the target's `.github/workflows/`

What it leaves alone:
- Any workflow you've deleted (tracked via `.ss/.workflows-installed` — the marker file is the source of truth, commit it)
- Your existing `Taskfile.yml` if you have one (just verifies the include is present, otherwise prints the block to paste)
- Anything in `package.json` apart from devDependencies merges
- Your own files outside the `ss` namespace

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

The installer refreshes `Taskfile.ss.yml`, `.ss/scripts/`, and the `ss-*.yml` workflows wholesale. Anything hand-edited in those files is gone — but `.slopstopper.yml` is **never** overwritten by the installer, so the bulk of customization (node version, headers source/format, URLs, pages, og-image path, disabled workflows) survives every re-run.

What still needs re-checking after an update:

- **Anything you hand-edited inside `ss-*.yml` workflow files** beyond what `.slopstopper.yml` covers. Common case: extra workflow-level `permissions:` for a custom integration, or a non-standard schedule. Diff against upstream to find them.
- **GitHub repo variables.** If `.slopstopper.yml` `node_version` changed, re-sync the `SLOPSTOPPER_NODE_VERSION` repo variable. If `urls.production` / `urls.preview` changed and you mirror them as repo variables, push those too:

  ```bash
  gh variable set SLOPSTOPPER_NODE_VERSION --body "$(grep '^node_version:' .slopstopper.yml | cut -d\' -f2)"
  # plus any URL variables you mirror
  ```

- **`.github/labeler.yml`** if upstream's labeler template added categories you want (the installer never overwrites your existing file, so new categories don't land automatically).

## Step 5 — Spot newly-shipped knobs

The `.slopstopper.yml.example` in the slopstopper repo is the schema reference. Diff it against your repo's `.slopstopper.yml`:

```bash
diff <(curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/.slopstopper.yml.example) .slopstopper.yml
```

Any keys present upstream but missing locally are new knobs you can opt into. Most ship with sensible defaults so no action is required — but the diff is the easiest way to know what changed.

## Step 6 — Check for new task targets

Re-running the installer refreshes `Taskfile.ss.yml`, which may now expose new `task ss:*` targets that weren't there last time. Eyeball the list:

```bash
task --list | grep '^\* ss:'
```

If anything looks unfamiliar, check `Taskfile.ss.yml` for the `desc:` and `summary:` to understand what it does. New tasks are usually surfaced as part of a new workflow — if you skipped the workflow in Step 3 you'll see the task in here regardless, since `Taskfile.ss.yml` is refreshed wholesale.

Flag any new tasks the user might want to wire into local pre-commit hooks or the standard dev loop.

## Step 7 — Re-run the static aggregates locally before pushing

Same loop as `slopstopper-install` Step 7, condensed because the build / Playwright deps are already in place:

```bash
task ss:hygiene:test    # complexity + docs-* + entry-files + lint + structure + size
task ss:security:scan   # SAST + secrets + dependency CVEs (+ DAST if a URL is wired)
```

Anything that comes back red is one of two things:

1. **A new check** that just landed and is hitting your repo for the first time → hand off to `slopstopper-triage` for the per-check playbook.
2. **An existing check** with a stricter tuning than before (e.g. complexity threshold tightened in the new `Taskfile.ss.yml`) → check the config under `docs/<loop>/` for tunable values; `slopstopper-triage` also covers this.

Don't push until the local loop is green. The point of running the aggregates first is to keep the upgrade-PR's CI run as a confirmation pass, not a discovery pass — same principle as a fresh install.

## Step 8 — Push and watch the confirmation pass

Push to a PR branch. CI should mirror local. If a CI-only check goes red (Dependency Review, auto-label) or a previously-green check fails on CI but was green locally (Node version pin in the runner, missing repo variable, etc.), hand off to `slopstopper-triage`.

## When to hand off

- **First-time install on a different repo** → `slopstopper-install`.
- **A specific check is failing right now** (during or after the update) → `slopstopper-triage`.

## Maintaining this skill when slopstopper changes

Update this skill when:

- The installer's behaviour changes (new tracked-files mechanism, different deletion semantics, additional refresh targets) → update Step 2's "what this refreshes / leaves alone" lists.
- A new env var is introduced for a dynamic check → add to Step 4's list and Step 5's `gh variable set` example.
- A new hardcoded-on-reinstall surface emerges (e.g. another file the installer overwrites that users commonly hand-edit) → add to Step 4.
- The trio gains a fourth skill → update the Step 1 description of what `install-skill.sh` refreshes and the "When to hand off" pointers.

The AGENTS.md "When making changes" table in the slopstopper repo flags this skill alongside `slopstopper-install` and `slopstopper-triage` whenever a change of the above kind ships.
