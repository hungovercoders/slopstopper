# slopstopper-cli

The SlopStopper quality suite, packaged as a `pipx`-installable CLI.

> **Status: 0.2.0 Beta.** Every check in the [public catalogue](https://slopstopper.dev/features.html) runs through this package. The CI workflows under `.github/workflows/ss-*.yml` install `slopstopper-cli` and call `slopstopper run <category>:<check>` — same code path you use locally.

## Install

End-user (most adopters):

```bash
pipx install https://github.com/hungovercoders/slopstopper/releases/download/v0.2.0/slopstopper_cli-0.2.0-py3-none-any.whl
slopstopper --version
slopstopper checks list
slopstopper doctor
```

> Installing the pre-built wheel from the [v0.2.0 GitHub Release](https://github.com/hungovercoders/slopstopper/releases/tag/v0.2.0). Once `slopstopper-cli` lands on PyPI this collapses to `pipx install slopstopper-cli`. `pipx upgrade slopstopper-cli` works regardless of source.

Development (editable, from a clone of this repo):

```bash
pip install -e ./cli
slopstopper run hygiene:docs-size
```

## CLI surface

```text
slopstopper run <category>:<check>             # run a check, write reports under .ss/reports/
slopstopper emit <c>:<n> --target {pr-comment,issue}
slopstopper discover <check> --event <e>       # resolve pages.<check> from sitemap / changed / list
slopstopper config get <key> [<default>]       # read .slopstopper.yml
slopstopper templates {list, path <n>, eject <n>}   # inspect / customise bundled templates
slopstopper serve                              # bundled static server (auto-detects worker/headers.json)
slopstopper checks list [--category <c>] [--json]
slopstopper doctor                             # verify external tools are installed
slopstopper --quiet …                          # suppress decorative output (CI logs)
```

`slopstopper` with no args prints a banner of the commands above plus a quick-start block.

## Run the tests

```bash
# From the repo root:
task -t cli/Taskfile.yml test

# Or from cli/:
task test

# Filter to a single test:
task -t cli/Taskfile.yml test -- -k docs_size
```

The same `task test` target is what CI runs (see [`.github/workflows/ci-cli.yml`](../.github/workflows/ci-cli.yml)), so local and CI invocations stay in sync. The Taskfile creates and reuses a project-local venv at `cli/.venv/` (gitignored) so it doesn't conflict with system Python under PEP 668.

This workflow is slopstopper-internal — it is **not** part of the distributed `ss-*-check.yml` suite and is never seeded into adopter repos.

## Layout

- `slopstopper/cli.py` — argparse dispatcher + bare-invocation banner
- `slopstopper/output.py` — shared formatters (running / success / warn / error / footer / `--quiet`)
- `slopstopper/config.py` — `.slopstopper.yml` reader (stdlib-only YAML subset)
- `slopstopper/templates.py` — bundled-template resolver + `templates {list, path, eject}` API
- `slopstopper/emit.py` — `gh` CLI wrapper for PR comment + main-branch issue emission
- `slopstopper/discovery.py` — pages-to-audit resolver for reliability checks
- `slopstopper/checks/` — one module per check; registry in `__init__.py`
- `slopstopper/data/` — bundled Playwright specs, lighthouserc dev/prod, server.js

## Adding a check

1. Add `slopstopper/checks/<name>.py` exposing `run(args) -> int`. Start the module docstring with a one-line summary (`slopstopper checks list` reads it).
2. Register it in `slopstopper/checks/__init__.py`'s `REGISTRY` dict.
3. Write the report to `.ss/reports/<category>/<name>-report.md` in the CWD.
4. Use `from slopstopper import output` for any user-facing print calls so `--quiet` and the consistent visual language come for free.
5. If the check should be postable to a PR or issue, declare a `META` dict in the module — `emit.py` reads it.

## Skills for agents

The trio under [`.claude/skills/slopstopper-{install,update,triage}/SKILL.md`](../.claude/skills/) is the long-form playbook for Claude Code agents working with this CLI. Update them when you add or rename a check, env var, or `task ss:*` target.
