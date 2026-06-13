# Changelog

All notable changes to **slopstopper-cli** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The release workflow (`.github/workflows/ss-release.yml`) reads the section matching the pushed tag and posts it as the GitHub Release notes. To cut a release: bump `version` in `cli/pyproject.toml` and `__version__` in `cli/slopstopper/__init__.py`, move the `## [Unreleased]` block down to a new `## [X.Y.Z] - YYYY-MM-DD`, push a `vX.Y.Z` tag.

## [Unreleased]

Nothing yet.

## [0.2.0] - 2026-06-13

First release with a real product surface. Phase 2 of the CLI pivot is complete — every check runs through `slopstopper-cli` and adopter `.ss/` directories shrink to `reports/` + the workflow manifest. The CLI now has a polished UX (bare-invocation banner, `checks list`, `doctor`, consistent output module, `--quiet`).

### Added

- `slopstopper checks list [--category <c>] [--json]` — walk the registry and print every check with its one-line summary.
- `slopstopper doctor` — verify external tools (`node`, `gh`, `lizard`, `semgrep`, `gitleaks`, `trivy`, `docker`) are installed; exit 1 only when a required-and-enabled tool is missing.
- `slopstopper templates {list, path, eject}` — inspect and customise bundled templates (Playwright specs, lighthouserc dev/prod, server.js).
- `slopstopper serve` — runs the bundled static server via `execvp(node)` so backgrounded `slopstopper serve &` gives bash the right PID for kill.
- `slopstopper config get <key> [<default>]` — read `.slopstopper.yml` values for shell scripting.
- `slopstopper discover <check> --event <e>` — resolve `pages.<check>` via sitemap / changed / explicit list.
- Bare `slopstopper` prints a friendly command grid + Quick-start block (no longer errors).
- `--quiet` / `-q` global flag suppresses decorative output while preserving reports.
- Shared output module (`slopstopper.output`) with consistent `running` / `success` / `warn` / `error` / `info` / `status` / `section` / `separator` / `footer` formatters.

### Changed

- `lighthouserc.prod.json` lifted into the wheel; `--prod` flag on `cwv.py` selects it.
- `server.js` lifted into the wheel; CWV/smoke/accessibility/SEO/broken-links/DAST workflows all use `slopstopper serve &` instead of `node server.js &`.
- `.ss/` in a fresh adopter install now contains only `reports/` and `.workflows-installed`.
- `install.sh` pip-installs `slopstopper-cli` (pipx-preferred) and scrubs legacy byte-equal copies of bundled templates from existing adopter `.ss/` directories.
- Workflows now emit PR comments and tracking issues via `slopstopper emit --target {pr-comment, issue}` instead of inline `actions/github-script@v7` JS.

### Removed

- Every Python/bash script previously seeded into adopter repos under `.ss/scripts/` — logic lives in `slopstopper-cli` now.
- `templates-sync-check` CI job — `.ss/` no longer ships byte-equal duplicates of `cli/slopstopper/data/`.

## [0.1.0] - 2026-06-12

Initial CLI pivot. Bash + Python scripts under `.ss/scripts/` remain authoritative; the Python `slopstopper-cli` package reproduces them check-by-check while CI runs both paths in parallel via the `bash↔cli parity` job.

### Added

- `slopstopper run <category>:<check>` dispatcher and the 15 check modules under `cli/slopstopper/checks/`.
- `slopstopper emit <check> --target {pr-comment, issue}` with find-or-update semantics.
- Templates resolver: `.ss/<filename>` override → package-data fallback.
