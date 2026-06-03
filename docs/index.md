# Documentation Index

This file defines documentation categories and governance.

> 👋 **Saw a SlopStopper check fail in your PR?** Each category README below explains what the check does, how to read its output, and how to tune thresholds. Jump straight in: [Security](security/README.md) · [Hygiene](hygiene/README.md) · [Reliability](reliability/README.md) · [Runbooks](runbooks/README.md) · [Deployment](deployment/README.md). The full env-var contract for dynamic checks lives in [reliability/README.md](reliability/README.md).

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
| [decisions/](decisions/) | Significant decisions and rationale | [README](decisions/README.md) | `task ss:decisions:*` |
| [deployment/](deployment/) | Release and environment workflows | [README](deployment/README.md) | — |
| [contributing/](contributing/) | Contributor workflow and expectations | [README](contributing/README.md) | `task ss:contributing:*` |
| [hygiene/](hygiene/) | Quality gates and maintenance | [README](hygiene/README.md) | `task ss:hygiene:*` |
| [reliability/](reliability/) | Service level and incident response | [README](reliability/README.md) | `task ss:reliability:*` |
| [runbooks/](runbooks/) | Operational procedures | [README](runbooks/README.md) | — |
| [security/](security/) | Security scanning and controls | [README](security/README.md) | `task ss:security:*` |
| [support/](support/) | How to get help and escalation flow | [README](support/README.md) | — |
