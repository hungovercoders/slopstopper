# Agentic Documentation Updater

The repo ships a weekly agentic workflow that scans recently-merged PRs,
identifies documentation drift, and opens a sync PR with the proposed
fixes. It runs on [GitHub Agentic Workflows (`gh-aw`)](https://github.github.com/gh-aw/)
with the GitHub Copilot CLI engine.

## Quick reference

| File | Purpose |
| ---- | ------- |
| [`.github/workflows/ss-hygiene-doc-updater.md`](../../.github/workflows/ss-hygiene-doc-updater.md) | Human-authored source. Frontmatter + prompt body. **This is what you edit.** |
| [`.github/workflows/ss-hygiene-doc-updater.lock.yml`](../../.github/workflows/ss-hygiene-doc-updater.lock.yml) | Compiled artifact gh-aw runtime executes. Generated — do not hand-edit. |
| [`.github/aw/actions-lock.json`](../../.github/aw/actions-lock.json) | gh-aw companion lockfile that pins SHAs for the GitHub Actions referenced in compiled workflows. |

## What it does

1. Triggers weekly (Friday, around 22:36 UTC) and on `workflow_dispatch`.
2. Searches for PRs merged in the last 7 days and open issues labelled
   `documentation`.
3. Reviews changed files in each PR against the corresponding sections
   of `docs/`.
4. Identifies real drift (added/removed/renamed features, new workflows,
   broken references) and writes a patch.
5. Opens a pull request labelled `documentation, automation` for human
   review.

If no drift is found, it exits via the `noop` safe-output and creates
nothing.

## Required configuration (adopters: read this)

The workflow won't fully function without two pieces of repo configuration:

### 1. Repo secret: `COPILOT_GITHUB_TOKEN`

The gh-aw runtime drives the Copilot CLI engine; the token authorises it.
Generate per the [gh-aw Copilot setup guide](https://github.github.com/gh-aw/reference/engines/#github-copilot-default)
and add under **Settings → Secrets and variables → Actions**. Without it,
the workflow runs to the engine-invocation step and fails authentication.

### 2. Repo setting: "Allow GitHub Actions to create and approve pull requests"

**Settings → Actions → General → Workflow permissions → tick "Allow GitHub
Actions to create and approve pull requests" → Save.**

Without this, the workflow's `safe-outputs.create-pull-request` step is
denied. The agent still does the work and pushes its branch
(`docs/weekly-update-<date>-<hash>`), but instead of opening a PR it
opens an *issue* labelled `documentation, automation, agentic-workflows`
with a `Click here to create the pull request` link. You then have to
manually open the PR from the link.

Enabling the setting is preferable — the agent's intended output is a
PR, and the issue-fallback workflow adds manual steps every week.

## What it produces

| Scenario | Output |
| -------- | ------ |
| Drift found, PR-creation allowed | A PR labelled `documentation, automation`, auto-marked for `copilot` review, auto-merge enabled (you still review before it merges). |
| Drift found, PR-creation blocked | A tracking issue with the patch preview and a manual-open link to the pushed branch. |
| No drift | A `noop` safe-output message; no PR or issue. |
| Tool/env failure | A workflow-run failure; the [workflow-failure-issue tracker](../../.github/workflows/ss-workflow-failure-issue.yml) raises a tracking issue automatically. |

## Editing the prompt or frontmatter

The `.md` source is authoritative. After editing it you **must** recompile
the `.lock.yml`, otherwise the scheduled run will execute the old
behaviour (or fail outright — see the next section).

```bash
# One-time: install the gh-aw extension
gh extension install githubnext/gh-aw

# Recompile after editing the .md
gh aw compile ss-hygiene-doc-updater

# Commit both files
git add .github/workflows/ss-hygiene-doc-updater.lock.yml \
        .github/aw/actions-lock.json
git commit -m "chore(workflows): recompile doc-updater after prompt edit"
```

The compiler also updates `.github/aw/actions-lock.json` if it picks up
newer action versions — commit both files together.

## Troubleshooting

### Scheduled run fails immediately with `ERR_SYSTEM: Runtime import file not found`

Cause: the `.md` source filename changed (or was renamed to follow the
`ss-` prefix convention) but the `.lock.yml` was never recompiled, so
its embedded `runtime-import` directive still references the old path.

Fix: recompile per the section above. This is exactly what
[PR #164](https://github.com/hungovercoders/slopstopper/pull/164) did.

### Workflow runs successfully but no PR appears

You're missing the workflow-permissions setting above. Look in the issue
list for one labelled `documentation, automation` — the agent put the
patch and a manual-open link there.

### `COPILOT_GITHUB_TOKEN` rotated, runs failing auth

Refresh the secret per the [gh-aw Copilot setup guide](https://github.github.com/gh-aw/reference/engines/#github-copilot-default).
The next scheduled run picks up the new value; no recompile needed.

### "Don't want this workflow at all"

Delete `.github/workflows/ss-hygiene-doc-updater.md` and
`.github/workflows/ss-hygiene-doc-updater.lock.yml`. Re-running the
installer respects the deletion (tracked via
`.ss/.workflows-installed`).
