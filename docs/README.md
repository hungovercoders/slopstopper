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

See [`index.md`](index.md) for the canonical list, but at a glance:

| Category | Purpose |
| -------- | ------- |
| [`app/`](app/) | What the site does and how pages are organised |
| [`architecture/`](architecture/) | System structure and boundaries |
| [`contributing/`](contributing/) | Contributor workflow and expectations |
| [`decisions/`](decisions/) | Significant decisions and rationale |
| [`deployment/`](deployment/) | Release and environment workflows |
| [`hygiene/`](hygiene/) | Quality gates and maintenance |
| [`reliability/`](reliability/) | Service level, accessibility, incident response |
| [`runbooks/`](runbooks/) | Operational procedures |
| [`security/`](security/) | Security scanning and controls |
| [`support/`](support/) | How to get help and escalation flow |

## Tasks

Documentation has its own Task targets — see
[`Taskfile.yml`](../Taskfile.yml) and run `task --list` for the full set.
Examples:

- `task ss:decisions:validate`
- `task ss:decisions:new SLUG=<name>`
