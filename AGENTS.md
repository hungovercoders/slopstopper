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
>
> **`task ss:<check>` is the canonical interface** — humans, agents AND CI all
> go through it, so the suite shares one invocation surface with everything
> else in the codebase. The underlying `slopstopper-cli` is the implementation
> the shims call; it's not a parallel surface to promote. Adopters who'd
> rather skip Task in their CI can install with `--no-task` and get workflows
> that call the CLI directly — but the canonical contract is Task.

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
| New quality check | Add workflow under `.github/workflows/ss-*.yml`, add `task ss:<category>:<action>` target, add to `install.sh`'s `GENERIC_WORKFLOWS`, surface on `app/features.html` and `app/tools.html`, mention in `README.md`, **add to the skill trio**: workflow inventory + Pass A/B example in [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md), reproduce row in [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) Step 2 table + gotcha row in Step 5 |
| Renaming a `task ss:*` target or env var | `Taskfile.ss.yml`, `docs/<category>/README.md`, **all three skills**: [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) (local-task commands + env-var list), [`slopstopper-update`](./.claude/skills/slopstopper-update/SKILL.md) (Step 4 customization list + Step 7 aggregates), [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) (Step 2 reproduce table) |
| Editing `install.sh` (esp. `GENERIC_WORKFLOWS` or post-install stdout) | `install.sh` (the `REPO_URL` must always match this repo's actual location), [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) Step 3 "what just landed" inventory, [`slopstopper-update`](./.claude/skills/slopstopper-update/SKILL.md) Step 2 "what this refreshes / leaves alone" lists |
| Editing any skill in `.claude/skills/slopstopper-*/SKILL.md` | [`install-skill.sh`](./install-skill.sh) (validates fetched file has frontmatter; if you add or rename a skill, also update its `SKILLS` array), [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md), `README.md` "Using Claude Code?" section, `app/index.html` "Claude Code users" section, and the other two trio skills' "When to hand off" pointers |
| Adding a new `slopstopper-*` skill | New `.claude/skills/<name>/SKILL.md`, [`install-skill.sh`](./install-skill.sh) `SKILLS` array, [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md) (trigger-table + What-lands + Uninstall), `README.md` link, `app/index.html` link, "When to hand off" pointers in each existing skill's closing section |
| Editing `install-skill.sh` | [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md) (keep description aligned), `README.md` + `app/index.html` if the install command line changes |
| Editing `.slopstopper.yml` schema (adding/renaming a key, changing a default) | [`.slopstopper.yml.example`](./.slopstopper.yml.example) (single source of truth — schema reference AND adopter seed that `install.sh` copies into adopter repos), [`.slopstopper.yml`](./.slopstopper.yml) (slopstopper.dev's own config), the trio skills (all three reference the schema), the script that consumes the new key, [`install.sh`](./install.sh) if the new key drives installer behaviour |
| Adding a config-driven knob to a check (new `config.get("<x>")` call) | The check's module docstring (a Configuration block listing the keys it reads + defaults), [`.slopstopper.yml.example`](./.slopstopper.yml.example) (schema + seed), [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) (post-install "tunable knobs" pointer), [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) (the "real / false-positive / threshold" branch should call out the config override) |
| Adding a new headers-source adapter | New module under [`cli/slopstopper/headers_adapters/`](./cli/slopstopper/headers_adapters/), register in `__init__.py`'s `ADAPTERS` dict, add to the `format:` documentation in [`.slopstopper.yml.example`](./.slopstopper.yml.example), mention in `slopstopper-install` Step 1.5 and `slopstopper-triage`'s gotcha table |
| Editing a Playwright spec, `playwright.config.js`, or `lighthouserc{,.prod}.json` | **`cli/slopstopper/data/` is the only home** — adopter repos no longer carry these files by default; the CLI ships them inside the wheel and resolves `.ss/<filename>` first only if an adopter has explicitly overridden it. Edit under `cli/slopstopper/data/` and the change ships on the next `slopstopper-cli` release. |
| New page | Add HTML + page-specific CSS in `app/`; link `app/shared.css` first; copy header/nav/footer; add to nav on the other pages; add to `tests/smoke.spec.ts` and `tests/accessibility.spec.ts` (under `cli/slopstopper/data/tests/`, per the row above) |
| Headers / CSP | `worker/headers.json` (single source of truth — CSP changes are blast-radius, touch DAST tests too) |
| Worker behaviour | `worker/index.ts` (path matching, redirects); `wrangler.jsonc` (assets binding, compatibility date) |

The right-hand column flags the [skill trio](./.claude/skills/) wherever a change would drift any of the three from reality — they name specific workflows, tasks and env vars, and silently rot if those change without them. Each skill's Step 10 (or equivalent closing section) carries the same instruction in the other direction.

## Skills for agents

Skills under [`.claude/skills/`](./.claude/skills/) are committed and shipped with the repo (the `.gitignore` carves them out from local Claude Code state). They're the long-form playbooks an agent should follow when doing one of these jobs:

- [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) — first-time install into a repo. Pre-flight, install command, post-install URL config, Map Pattern setup, badges, local-first verification loop.
- [`slopstopper-update`](./.claude/skills/slopstopper-update/SKILL.md) — refresh an existing install: re-run installer, diff upstream for new workflows, re-apply customizations that get wiped on reinstall, bump Node version pins.
- [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) — diagnose a failing slopstopper check: workflow → local task → report → finding category (real / false-positive / threshold) → fix location.

Distributed to adopter machines as a trio via [`install-skill.sh`](./install-skill.sh) — see [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md).
