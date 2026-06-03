# Contributing to SlopStopper

Thanks for considering a contribution. The full contributor guide lives at:

→ [`docs/contributing/README.md`](./docs/contributing/README.md)

## Short version

- Branch from `main` and keep changes focused
- Use [Conventional Commits](https://www.conventionalcommits.org/):
  `<type>(<scope>): <description>` (types: `feat`, `fix`, `docs`, `style`,
  `test`, `chore`, `refactor`)
- Run `task --list` to see check tasks before pushing
- The Taskfile is the single source of truth — `task <name>` runs the same
  thing locally that CI runs
- Open a pull request; the SlopStopper checks will report back

## Quick checks before pushing

```bash
task contributing:build               # TypeScript build
task contributing:test                # Playwright smoke + a11y
task reliability:accessibility        # axe-core WCAG 2.1 AA
task hygiene:complexity               # Lizard cap
task security:sast                    # Semgrep
```

## Agents

If you're an AI agent working on this repo, read
[`AGENTS.md`](./AGENTS.md) for the canonical conventions and constraints.

## Code of conduct, support, escalation

See [`docs/support/`](./docs/support/).
