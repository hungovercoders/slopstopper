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
| `task contributing:setup` | `npm install` + editable `pip install -e ./cli` + wire the pre-push hook |
| `task contributing:test` | The CLI's pytest suite under `cli/tests/` (what `ci-cli.yml` runs) |
| `task contributing:run` | Serve `app/` on port 8080 via `slopstopper serve` |
| `task contributing:test:site` | Playwright smoke + a11y against `SITE_URL` (default the server above) |
| `task contributing:lint` | markdownlint over `docs/` — advisory, not a CI gate |
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

For CI-style output (retries, HTML reports, fail-on-flake), pass
`--ci` through the Task `--` separator the same way the workflows do —
e.g. `task ss:reliability:accessibility -- --ci`. Same Task command runs
in both loops; the flag toggles the run shape.

## Exit codes

Every check returns the same three codes, and CI gates on them directly —
there is no per-check post-processing step deciding the verdict:

| Code | Meaning |
|---|---|
| `0` | Ran; nothing to fail on. Includes a graceful skip — an unconfigured check is not a failing check |
| `1` | Ran; the repo failed it. Findings over a threshold, drift, a budget exceeded |
| `2` | Could not run. Missing tool, missing input, unreadable report, an argument the check has no parser for |

The full contract, and why it matters, is in the `slopstopper.checks`
package docstring; `cli/tests/test_exit_code_contract.py` checks every
check's docstring against what its code can actually return.

## Quick verification checklist

Run these before opening a PR. Each one mirrors the equivalent CI check
exactly:

```bash
task contributing:test                # CLI pytest suite (ci-cli.yml)
task ss:hygiene:test                  # Full hygiene suite (also the pre-push hook)
task contributing:run                 # Serve app/ on :8080 — separate terminal
task contributing:test:site           # Playwright smoke + a11y against it
task ss:reliability:cwv -- --url http://localhost:8080   # Lighthouse CI
task ss:security:sast                 # Semgrep
```

Or call the CLI directly if you'd rather skip the `task` shim layer
(`slopstopper serve &`, `slopstopper run reliability:smoke`, etc.) —
the shims are thin and call the same code path either way.

## The CLI test suite (pytest)

The product is the Python package under [`cli/`](../../cli/); its tests
live in `cli/tests/` and are the first thing to run after any change to a
check, the installer, or a workflow (several tests read the workflow files
and the skills as fixtures — `cli/tests/test_workflow_triggers.py`, for one, so a
YAML edit can fail a Python test).

```bash
task contributing:test                       # whole suite
task contributing:test -- -k docs_size       # filter (any pytest args after --)
task -t cli/Taskfile.yml test                # same thing, without the alias
```

The target creates and reuses a project-local venv at `cli/.venv/`
(gitignored) with the `test` extra installed, so it doesn't fight system
Python under PEP 668. CI runs the identical target from
[`ci-cli.yml`](../../.github/workflows/ci-cli.yml).

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
