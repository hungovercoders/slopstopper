# Documentation Index

This file is **the map** — every other entry point in the repo defers to it.

> 👋 **Saw a SlopStopper check fail in your PR?** Each category README below explains what the check does, how to read its output, and how to tune thresholds. Jump straight in: [Security](security/README.md) · [Hygiene](hygiene/README.md) · [Reliability](reliability/README.md) · [Runbooks](runbooks/README.md) · [Deployment](deployment/README.md). The full env-var contract for dynamic checks lives in [reliability/README.md](reliability/README.md).

## The Map Pattern

The repo has three small entry-point files — [`README.md`](../README.md) (humans), [`AGENTS.md`](../AGENTS.md) (automation tools, conformant with [agents.md](https://agents.md)) and [`CLAUDE.md`](../CLAUDE.md) (Claude Code) — and each one defers to this index instead of duplicating documentation inline.

**Why this matters:**

- **Agents stay focused.** Claude, Copilot or any agent loads only the thin entry file (capped at <2K tokens, enforced by [`task ss:hygiene:entry-files`](hygiene/README.md)) and navigates here when it needs detail. No bloated instruction files competing for context window.
- **One source of truth.** The category READMEs are the canonical answer; entry files just point at them. Changes don't have to ripple through three places.
- **Drift is caught by CI.** The [hygiene docs-structure check](hygiene/README.md) fails the build if the directory tree drifts from the map below, and the [docs-accuracy check](hygiene/README.md) catches broken cross-references in any doc.
- **Reusable convention.** If you install SlopStopper into your own repo, dropping a `docs/index.md` and slimming `README.md` / `AGENTS.md` / `CLAUDE.md` to pointers gives you the same property for free.

## Governance Model

**This index is the sole source of truth for documentation structure.**

The directory structure must conform to this index—not the reverse. This file is the specification that drives organized documentation.

### Key Principles

- **Index-first**: Any new document must have a corresponding entry in this index before being added

## Documentation Categories

Each category has a README that defines its purpose. Content within categories is flexible and evolves with project needs.

| Category | Purpose | README | Tasks |
| -------- | ------- | ------ | ----- |
| [app/](app/) | What the site does and how pages are organised | [README](app/README.md) | — |
| [architecture/](architecture/) | System structure and boundaries | [README](architecture/README.md) | — |
| [decisions/](decisions/) | Significant decisions and rationale | [README](decisions/README.md) | `task decisions:*` |
| [deployment/](deployment/) | Release and environment workflows | [README](deployment/README.md) | — |
| [contributing/](contributing/) | Contributor workflow and expectations | [README](contributing/README.md) | `task contributing:*` |
| [hygiene/](hygiene/) | Quality gates and maintenance | [README](hygiene/README.md) | `task ss:hygiene:*` |
| [reliability/](reliability/) | Service level and incident response | [README](reliability/README.md) | `task ss:reliability:*` |
| [runbooks/](runbooks/) | Operational procedures | [README](runbooks/README.md) | — |
| [security/](security/) | Security scanning and controls | [README](security/README.md) | `task ss:security:*` |
| [support/](support/) | How to get help and escalation flow | [README](support/README.md) | — |
