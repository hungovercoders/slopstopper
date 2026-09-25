# SlopStopper documentation

This directory holds the structured project documentation.

- **Documentation hub:** [`index.md`](index.md) is the naming-governance
  spec and category map for everything under `docs/`.
- **Project overview, install instructions, contributor pointers:** see the
  repo root [`README.md`](../README.md).
- **Canonical agent instructions:** see the repo root
  [`AGENTS.md`](../AGENTS.md) (this directory keeps a thin
  [`AGENTS.md`](AGENTS.md) pointer for backwards compatibility).

## Categories

The category map — every directory under `docs/`, its purpose, README and
Task namespace — lives in [`index.md`](index.md) and nowhere else. The
[`ss:hygiene:docs-structure`](hygiene/README.md) check keeps the directory
tree honest against it, and `cli/tests/test_docs_layout.py` keeps this file
from growing a second copy.

## Tasks

Documentation has its own Task targets — see
[`Taskfile.yml`](../Taskfile.yml) and run `task --list` for the full set.
Examples:

- `task decisions:validate`
- `task decisions:new SLUG=<name>`
