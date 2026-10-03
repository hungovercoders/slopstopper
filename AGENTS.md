# Agent guide — SlopStopper

Open standard for agents, AI assistants and automation tools working in
this repo (conformant with [agents.md](https://agents.md)). `CLAUDE.md` is
`@AGENTS.md`. This file carries what most tasks need; the routes at the
end say when to open anything else.

## What this repo is

Two things at once: **`slopstopper-cli`** under `cli/` (every check's
logic, published to PyPI) plus the `ss-*.yml` workflows, `task ss:*` shims
and `install.sh` adopters pull in; and **slopstopper.dev** under `app/`,
a reference site built and deployed with the same suite it advertises.
A change that affects adopters usually touches both layers and the docs.

## Ground rules

1. **`task ss:<category>:<action>` is the canonical interface.** Humans,
   agents and CI all go through it; `slopstopper run …` is the
   implementation each shim calls. Run `task --list` before writing a
   one-off command.
2. **One definition of green.** `task ss:hygiene:test` (docs-size,
   docs-structure, docs-accuracy, entry-files, CSP drift, complexity) is
   what the pre-push hook and CI run. Run it before committing; run the
   CLI tests when `cli/` changes.
3. **Every check keeps the exit-code contract:** 0 ran clean, 1 ran and
   failed, 2 could not run. CI gates on it directly.
4. **Budgets are the feature.** When a docs check fails, move content
   deeper into `docs/` and route it; never raise the budget.
5. **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:` …);
   release-please cuts the CLI release from them. Third-party actions are
   pinned to a commit SHA, never a tag.
6. **This repo IS the CLI.** `mise.toml` pins no `slopstopper-cli`;
   workflows install `cli/` editable and run HEAD. Adopters get a pin.

## Commands

| Command                                  | Does                                                       |
| ---------------------------------------- | ---------------------------------------------------------- |
| `task --list`                            | every runnable task                                        |
| `task ss:hygiene:test`                   | the static hygiene suite (what the pre-push hook runs)     |
| `task ss:security:scan`                  | SAST, secrets, dependency scan                             |
| `task ss:reliability:<check> -- <url>`   | a browser check against a running site                     |
| `task -t cli/Taskfile.yml test`          | the pytest suite for `slopstopper-cli`                     |
| `task contributing:run` / `:test`        | local server on :8080 / Playwright smoke + a11y            |
| `slopstopper checks list` / `doctor`     | what exists / which external tools are missing             |

## Layout

```
AGENTS.md            this file (CLAUDE.md is @AGENTS.md)
docs/                topic docs — docs/README.md is the map; one concern per doc
cli/slopstopper/     the CLI: checks/<check>.py, data/ (templates, specs), profiles.json
cli/tests/           pytest; test_check_registration.py enforces every surface a check needs
.github/workflows/   ss-*.yml, each `uses: ./.github/actions/ss-setup` then one task
Taskfile.ss.yml      the `task ss:*` shims  ·  Taskfile.yml includes them under `ss`
install.sh           adopter installer (seeds templates, pins the CLI via mise)
.claude/skills/      slopstopper-install + slopstopper-triage, shipped to adopters
app/  worker/        the site and the Cloudflare Worker that serves it (headers.json = CSP)
.slopstopper.yml     this repo's config; .slopstopper.yml.example is the schema
```

## Conventions most changes touch

- **Naming follows the docs categories:** task `hygiene:complexity`,
  workflow `ss-hygiene-complexity-check.yml`, docs under `docs/hygiene/`.
- **Checks are stdlib-only Python**, subprocess-invoke their tool, write
  `.ss/reports/<check>/`, and carry a `Configuration` block in the module
  docstring for every `config.get("…")` key they read.
- **A new or renamed check is registered in ~12 places** (workflow,
  shim, installer, profiles, badge label, PR summary, docs, tests, both
  skills, site, README). The route below lists them; the registration
  test fails on any you miss.
- **Docs state the present; git holds the past.** No "previously we…"
  sections; the commit message carries the story.
- **Headers/CSP:** `worker/headers.json` is the single source of truth;
  a CSP change is blast-radius (DAST tests, the exceptions doc).

## Routes — read before you act

| When you are…                                                              | Do this                                                                                   |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| changing anything that ships to adopters (a check, workflow, skill, config key, template, page) | Read [docs/contributing/CHANGE_MAP.md](./docs/contributing/CHANGE_MAP.md) before you start — every surface each kind of change must touch |
| about to add a workflow, task, report path or external resource            | Read [docs/contributing/PITFALLS.md](./docs/contributing/PITFALLS.md) first — the gotchas that have bitten before |
| fixing a failing docs or hygiene check                                      | Read [docs/hygiene/README.md](./docs/hygiene/README.md) — what each check enforces, its knobs, its report |
| installing or refreshing slopstopper in another repo                        | Read [.claude/skills/slopstopper-install/SKILL.md](./.claude/skills/slopstopper-install/SKILL.md) — the install/refresh playbook |
| diagnosing a failing slopstopper check in any repo                          | Read [.claude/skills/slopstopper-triage/SKILL.md](./.claude/skills/slopstopper-triage/SKILL.md) — workflow → task → report → fix |
| doing any task not covered above                                            | Read [docs/README.md](./docs/README.md) before you start; do not guess a convention        |

`ss:hygiene:entry-files` keeps this file under ~2k tokens and every route
above explicit; `ss:hygiene:docs-structure` keeps every doc routed.
