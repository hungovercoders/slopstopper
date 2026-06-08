# Agent instructions — SlopStopper

Open standard for agents, AI assistants and automation tools working in this
repo. Conformant with [agents.md](https://agents.md).

> 🗺️ **Documentation map.** [`docs/index.md`](./docs/index.md) is the
> single index of all project documentation. This file, [`CLAUDE.md`](./CLAUDE.md)
> and [`README.md`](./README.md) are intentionally thin — they point at
> the map rather than duplicating its content. When you need detail on
> any topic — a check, a runbook, a workflow, a CSP exception — start
> at [`docs/index.md`](./docs/index.md) and follow its links to the
> category README that owns it. The
> [`ss:hygiene:entry-files`](./docs/hygiene/README.md) check enforces a
> <2k token cap on each entry file; the
> [`ss:hygiene:docs-structure`](./docs/hygiene/README.md) check keeps
> the map honest against the directory tree.

> 🏗️ **Naming convention.** The categories in
> [`docs/index.md`](./docs/index.md) drive naming across the project. Task
> targets are defined as `category:action` (e.g. `hygiene:complexity`) and
> invoked under the `ss` namespace (`task ss:hygiene:complexity`). GitHub
> Actions use `ss-category-action-check.yml` (e.g.
> `ss-hygiene-complexity-check.yml`).

## What SlopStopper is

Two things at once:

1. **A portable suite** of GitHub Actions workflows, Task targets and
   analysis scripts that consumers install into their own repos via
   [`install.sh`](./install.sh).
2. **A live reference site** under [`app/`](./app/) that markets the suite
   and proves it works — built and deployed with the same suite it
   advertises.

Changes that affect both layers (e.g. adding a new quality check) must be
reflected in the workflows AND the site copy (`app/features.html`,
`app/tools.html`) AND `README.md`. The
[`ss:hygiene:docs-accuracy`](./docs/hygiene/README.md) check catches drift
between these.

## When making changes

| Change | Affects |
| ------ | ------- |
| Visual / brand | `app/shared.css` (tokens), then individual pages if they use new components |
| New quality check | Add workflow under `.github/workflows/ss-*.yml`, add `task ss:<category>:<action>` target, add to `install.sh`'s `GENERIC_WORKFLOWS`, surface on `app/features.html` and `app/tools.html`, mention in `README.md`, **add to the install-slopstopper skill** (workflow inventory + Pass A/B example in [`.claude/skills/install-slopstopper/SKILL.md`](./.claude/skills/install-slopstopper/SKILL.md)) |
| Renaming a `task ss:*` target or env var | `Taskfile.ss.yml`, `docs/<category>/README.md`, **the install-slopstopper skill** (local-task commands + env-var list) |
| Editing `install.sh` (esp. `GENERIC_WORKFLOWS` or post-install stdout) | `install.sh` (the `REPO_URL` must always match this repo's actual location), **the install-slopstopper skill** (Step 3 "what just landed" inventory) |
| New page | Add HTML + page-specific CSS in `app/`; link `app/shared.css` first; copy header/nav/footer; add to nav on the other pages; add to `tests/smoke.spec.ts` and `tests/accessibility.spec.ts` |
| Headers / CSP | `worker/headers.json` (single source of truth — CSP changes are blast-radius, touch DAST tests too) |
| Worker behaviour | `worker/index.ts` (path matching, redirects); `wrangler.jsonc` (assets binding, compatibility date) |

The right-hand column flags the [install-slopstopper skill](./.claude/skills/install-slopstopper/SKILL.md) wherever a change would drift the skill from reality — the skill names specific workflows, tasks and env vars, and silently rots if those change without it. Its Step 10 carries the same instruction in the other direction.

## Skills for agents

Skills under [`.claude/skills/`](./.claude/skills/) are committed and shipped with the repo (the `.gitignore` carves them out from local Claude Code state). They're the long-form playbooks an agent should follow when doing one of these jobs:

- [`install-slopstopper`](./.claude/skills/install-slopstopper/SKILL.md) — installing SlopStopper into an existing repo. Covers pre-flight, the install command, post-install URL config, verification, and first-PR triage grounded in real installs into non-trivial repos.
