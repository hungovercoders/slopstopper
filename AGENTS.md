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
| New quality check | Add workflow under `.github/workflows/ss-*.yml`, add `task ss:<category>:<action>` target, add to `install.sh`'s `GENERIC_WORKFLOWS`, surface on `app/features.html` and `app/tools.html`, mention in `README.md`, **add to the skill duo**: workflow inventory + Pass A/B example in [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) (covers first install AND refresh), reproduce row in [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) Step 2 table + gotcha row in Step 5 |
| Renaming a `task ss:*` target or env var | `Taskfile.ss.yml`, `docs/<category>/README.md`, **both skills**: [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) (local-task commands + env-var list + Refresh-only section's "Re-apply customizations" + aggregates), [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) (Step 2 reproduce table) |
| Editing `install.sh` (esp. `GENERIC_WORKFLOWS`, `SKILL_NAMES`, or post-install stdout) | `install.sh` (the `REPO_URL` must always match this repo's actual location; `SKILL_NAMES` must match `install-skill.sh`'s `SKILLS` array), [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) Step 3 "what just landed" inventory + Refresh-only "what the installer wipes / leaves alone" lists |
| Editing any skill in `.claude/skills/slopstopper-*/SKILL.md` | [`install-skill.sh`](./install-skill.sh) (validates fetched file has frontmatter; if you add or rename a skill, also update its `SKILLS` array AND `install.sh`'s `SKILL_NAMES` array), [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md), `README.md` "Using Claude Code?" section, `app/index.html` "Claude Code users" section, and the other skill's "When to hand off" pointer |
| Adding a new `slopstopper-*` skill | New `.claude/skills/<name>/SKILL.md`, [`install-skill.sh`](./install-skill.sh) `SKILLS` array, [`install.sh`](./install.sh) `SKILL_NAMES` array (must match), [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md) (trigger-table + What-lands + Uninstall), `README.md` link, `app/index.html` link, "When to hand off" pointers in each existing skill's closing section |
| Removing or renaming a slopstopper-shipped artefact (skill, workflow, template) so adopter repos shouldn't carry it any more | Add to the relevant obsolete-list so re-runs auto-clean it: skills → `OBSOLETE_SKILLS` in BOTH [`install.sh`](./install.sh) and [`install-skill.sh`](./install-skill.sh); workflows or `.ss/` files → similar list in [`install.sh`](./install.sh) plus the existing byte-equality scrub if it moved into the CLI wheel. Then add a row to [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md)'s "Clean up redundant artefacts" subsection so the agent sanity-check covers it. The principle: adopter repos should hold only the expected set + their own customisations — anything else is noise to be flagged or auto-removed |
| Editing `install-skill.sh` or `install.sh`'s `install_claude_skills()` | Keep both in sync (same `SKILLS`/`SKILL_NAMES` array, same destination path under `<target>/.claude/skills/`), [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md), `README.md` + `app/index.html` if the install command line changes |
| Editing `.slopstopper.yml` schema (adding/renaming a key, changing a default) | [`.slopstopper.yml.example`](./.slopstopper.yml.example) (single source of truth — schema reference AND adopter seed that `install.sh` copies into adopter repos), [`.slopstopper.yml`](./.slopstopper.yml) (slopstopper.dev's own config), both skills reference the schema, the script that consumes the new key, [`install.sh`](./install.sh) if the new key drives installer behaviour |
| Adding a config-driven knob to a check (new `config.get("<x>")` call) | The check's module docstring (a Configuration block listing the keys it reads + defaults), [`.slopstopper.yml.example`](./.slopstopper.yml.example) (schema + seed), [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) (post-install "tunable knobs" pointer + Refresh-only "new knobs" section), [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) (the "real / false-positive / threshold" branch should call out the config override) |
| Changing the Map Pattern pointer rule (what `ss:hygiene:entry-files` enforces, the canonical pointer text, or the entry-file scaffold templates) | [`cli/slopstopper/checks/entry_files.py`](./cli/slopstopper/checks/entry_files.py) (rule + paste-ready snippet generators), [`cli/slopstopper/data/templates/entry-files/`](./cli/slopstopper/data/templates/entry-files/) (the four scaffold files — keep these aligned with this repo's own `README.md` / `AGENTS.md` / `CLAUDE.md` / `docs/index.md`, since they are the canonical examples), [`.slopstopper.yml.example`](./.slopstopper.yml.example) (`require_map_pointer` and `map_path` knobs), [`install.sh`](./install.sh) (`seed_template` calls for the four entry files), [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) Step 1.6 + 1.9 + Step 3 inventory + Step 5 (Map Pattern setup) + Refresh-only knobs list, [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) entry-files reproduce/gotcha rows |
| Adding a new headers-source adapter | New module under [`cli/slopstopper/headers_adapters/`](./cli/slopstopper/headers_adapters/), register in `__init__.py`'s `ADAPTERS` dict, add to the `format:` documentation in [`.slopstopper.yml.example`](./.slopstopper.yml.example), mention in `slopstopper-install` Step 1.5 and `slopstopper-triage`'s gotcha table |
| Editing a Playwright spec, `playwright.config.js`, or `lighthouserc{,.prod}.json` | **`cli/slopstopper/data/` is the only home** — adopter repos no longer carry these files by default; the CLI ships them inside the wheel and resolves `.ss/<filename>` first only if an adopter has explicitly overridden it. Edit under `cli/slopstopper/data/` and the change ships on the next `slopstopper-cli` release. |
| New page | Add HTML + page-specific CSS in `app/`; link `app/shared.css` first; copy header/nav/footer; add to nav on the other pages; add to `tests/smoke.spec.ts` and `tests/accessibility.spec.ts` (under `cli/slopstopper/data/tests/`, per the row above) |
| Headers / CSP | `worker/headers.json` (single source of truth — CSP changes are blast-radius, touch DAST tests too) |
| Worker behaviour | `worker/index.ts` (path matching, redirects); `wrangler.jsonc` (assets binding, compatibility date) |

The right-hand column flags the [skill duo](./.claude/skills/) wherever a change would drift either skill from reality — they name specific workflows, tasks and env vars, and silently rot if those change without them. Each skill's Step 10 (or equivalent closing section) carries the same instruction in the other direction.

## Skills for agents

Skills under [`.claude/skills/`](./.claude/skills/) are committed and shipped with the repo (the `.gitignore` carves them out from local Claude Code state). They're the long-form playbooks an agent should follow when doing one of these jobs:

- [`slopstopper-install`](./.claude/skills/slopstopper-install/SKILL.md) — install into a repo for the first time OR refresh an existing install. Mode-detection branch checks for `.slopstopper.yml` + `.ss/.workflows-installed` and routes to first-install vs refresh sub-flows. Covers pre-flight, install command, post-install URL config, Map Pattern setup, badges, refresh-only customization re-apply and new-knob discovery, and a local-first verification loop.
- [`slopstopper-triage`](./.claude/skills/slopstopper-triage/SKILL.md) — diagnose a failing slopstopper check: workflow → local task → report → finding category (real / false-positive / threshold) → fix location.

Installed at project level into adopter repos by [`install.sh`](./install.sh) (skill subset of the full installer) or refreshed standalone via [`install-skill.sh`](./install-skill.sh) — both write into `<repo>/.claude/skills/slopstopper-*/SKILL.md`. See [`docs/runbooks/INSTALL_SKILLS.md`](./docs/runbooks/INSTALL_SKILLS.md).
