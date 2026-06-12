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
python3 -m venv cli/.venv
cli/.venv/bin/pip install -e ./cli[test]
cli/.venv/bin/pytest cli/tests/
```

CI runs the same suite via [`.github/workflows/ci-cli.yml`](../.github/workflows/ci-cli.yml).
That workflow is slopstopper-internal — it is **not** part of the
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
