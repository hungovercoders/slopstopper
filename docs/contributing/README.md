# Contributing

This document defines the default way to contribute to this project.

## Prerequisites

- Install Task (Taskfile runner): [taskfile.dev/installation](https://taskfile.dev/installation/)
- Verify installation: `task --version`

## Canonical interface: Taskfile (the `ss` namespace)

**Agents and contributors must use `task ss:<name>` instead of raw commands**
wherever possible. SlopStopper's task definitions live in
[`Taskfile.ss.yml`](../../Taskfile.ss.yml); the root
[`Taskfile.yml`](../../Taskfile.yml) is a thin integration layer that imports
them under the `ss` namespace via `includes:`. This keeps SlopStopper's
tasks isolated from anything a consumer has in their own root Taskfile.

The Taskfile is the single source of truth for build, test, lint and scan
operations so developers, AI agents and CI all run the same thing — no
drift, no version skew.

Run `task --list` for the full set. The most-used ones:

| Task | What it does |
| ---- | ------------ |
| `task ss:contributing:setup` | Install dependencies |
| `task ss:contributing:build` | TypeScript build (`tsc`) |
| `task ss:contributing:run` | Local dev server on port 8080 |
| `task ss:contributing:test` | Playwright smoke + a11y suite |
| `task ss:contributing:lint` | Lint checks |
| `task ss:hygiene:complexity` | Cyclomatic complexity check (Lizard) |
| `task ss:hygiene:entry-files` | Enforce <2k token budget on entry files |
| `task ss:hygiene:docs-accuracy` | Catch broken links + stale task/workflow refs |
| `task ss:security:sast` | Static security scan (Semgrep) |
| `task ss:security:dast` | Dynamic security scan (OWASP ZAP) |
| `task ss:security:secrets` | Secrets detection (Gitleaks) |
| `task ss:security:vulnerability:all` | Dependency CVE scan (Trivy) |
| `task ss:reliability:smoke` | Smoke tests against a URL |
| `task ss:reliability:accessibility` | axe-core WCAG 2.1 AA audit |
| `task ss:reliability:cwv` | Lighthouse CI / Core Web Vitals |

The `:ci` variants (e.g. `reliability:accessibility:ci`) just delegate to
the base task with CI-friendly output paths — same logic.

## Quick verification checklist

Run these before opening a PR. Each one mirrors the equivalent CI check
exactly:

```bash
task ss:contributing:build           # TypeScript build
task ss:contributing:run              # Local server on :8080
task ss:contributing:test             # Playwright smoke + a11y
task ss:reliability:accessibility     # axe-core audit
task ss:reliability:cwv               # Lighthouse CI
task ss:hygiene:test                  # Full hygiene suite
task ss:security:sast                 # Semgrep
```

Or run the underlying npm scripts if you don't have Task installed
(`npm start`, `npm run build`, `npm test`) — but **prefer `task`** so your
behaviour matches CI exactly.

## Workflow

- Create a focused branch for each change.
- Keep pull requests small and reviewable.
- Link changes to relevant decisions or issues when applicable.

## Pre-Merge Checks

- Verify tests and checks pass.
- Confirm documentation is updated when behavior or structure changes.
- Ensure no accidental scope creep is included.

## Commit conventions

[Conventional Commits](https://www.conventionalcommits.org/):
`<type>(<scope>): <description>` where type is one of `feat`, `fix`,
`docs`, `style`, `test`, `chore`, `refactor`. Examples:

- `feat(site): add Taskfile bridge + live issue/PR links`
- `fix(install): correct REPO_URL after rename`
- `docs(agents): refresh visual conventions`

## Coding Conventions

- Prefer clarity over cleverness.
- Keep changes minimal and localized.
- Follow existing project style and naming patterns.

## Contents

- [PITFALLS.md](PITFALLS.md) — Common gotchas when extending SlopStopper
  (workflow naming, CSP, brand contrast, task namespace)
