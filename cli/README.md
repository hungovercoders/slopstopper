# slopstopper-cli

The slopstopper quality suite, packaged as a `pipx`-installable CLI.

> **Status: alpha.** This package is the in-progress CLI pivot — see
> [the plan](../docs/runbooks/CLI_PIVOT.md) for context. During the pivot the
> bash/python scripts under `../.ss/scripts/` remain authoritative; the CLI
> reproduces them check-by-check with the goal of producing byte-equivalent
> reports.

## Install (development)

```bash
pip install -e ./cli
slopstopper --version
slopstopper run hygiene:docs-size
```

## Run the tests

```bash
# From the repo root:
task -t cli/Taskfile.yml test

# Or from cli/:
task test

# Filter to a single test:
task -t cli/Taskfile.yml test -- -k docs_size
```

The same `task test` target is what CI runs (see
[`.github/workflows/ci-cli.yml`](../.github/workflows/ci-cli.yml)), so
local and CI invocations stay in sync. The Taskfile creates and reuses
a project-local venv at `cli/.venv/` (gitignored) so it doesn't conflict
with system Python under PEP 668.

This workflow is slopstopper-internal — it is **not** part of the
distributed `ss-*-check.yml` suite and is never seeded into adopter repos.

## Install (eventual, post-publish)

```bash
pipx install slopstopper-cli
slopstopper init
```

## Layout

- `slopstopper/cli.py` — argparse dispatcher
- `slopstopper/config.py` — `.slopstopper.yml` reader (stdlib-only YAML subset)
- `slopstopper/checks/` — one module per check; registry in `__init__.py`

## Adding a check

1. Add `slopstopper/checks/<name>.py` exposing `run(args) -> int`.
2. Register it in `slopstopper/checks/__init__.py`'s `REGISTRY` dict.
3. Write its report to `.ss/reports/<category>/<name>-report.md` in the CWD.
4. Keep behaviour byte-identical to the bash/python script it replaces until parity is proven.
