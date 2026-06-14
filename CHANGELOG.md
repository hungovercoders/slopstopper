# Changelog

All notable changes to **slopstopper-cli** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The release workflow (`.github/workflows/ss-release.yml`) reads the section matching the pushed tag and posts it as the GitHub Release notes. To cut a release: bump `version` in `cli/pyproject.toml` and `__version__` in `cli/slopstopper/__init__.py`, move the `## [Unreleased]` block down to a new `## [X.Y.Z] - YYYY-MM-DD`, push a `vX.Y.Z` tag.

## [0.5.0](https://github.com/hungovercoders/slopstopper/compare/v0.4.1...v0.5.0) (2026-06-14)


### Features

* **release-please:** mint App token to eliminate manual touch points ([#251](https://github.com/hungovercoders/slopstopper/issues/251)) ([20365a3](https://github.com/hungovercoders/slopstopper/commit/20365a3f5f20d12564692655ef57c28d30fabfcb))

## [0.4.1](https://github.com/hungovercoders/slopstopper/compare/v0.4.0...v0.4.1) (2026-06-14)


### Bug Fixes

* **release:** tighten sanity-check sed to handle trailing marker comment ([#248](https://github.com/hungovercoders/slopstopper/issues/248)) ([29cdd07](https://github.com/hungovercoders/slopstopper/commit/29cdd0705f24c3fe400bb7fff07d8463072f18d0))

## [0.4.0](https://github.com/hungovercoders/slopstopper/compare/v0.3.0...v0.4.0) (2026-06-14)


### Features

* **release:** automate version bumps + tagging via release-please ([#245](https://github.com/hungovercoders/slopstopper/issues/245)) ([b7c1944](https://github.com/hungovercoders/slopstopper/commit/b7c1944a04a6667228236f6f121bae7ad25c0814))


### Bug Fixes

* **release-please:** switch to release-type simple with extra-files ([#246](https://github.com/hungovercoders/slopstopper/issues/246)) ([6ffd25e](https://github.com/hungovercoders/slopstopper/commit/6ffd25ec4468860d04ab802e2fdad98b65c328e7))

## [Unreleased]

Nothing yet.

## [0.3.0] - 2026-06-14

First release published to PyPI. Adopter docs, the website, `install.sh` and every `ss-*-check.yml` workflow stop pinning a wheel URL — they all install `slopstopper-cli` by name, so future releases land everywhere automatically with no doc churn.

### Added

- **PyPI distribution.** `pipx install slopstopper-cli` (and `pipx upgrade slopstopper-cli`) is now the canonical install. Released to PyPI on every `v*.*.*` tag via the OIDC Trusted Publisher flow — no API tokens, no manual `twine upload`. The release workflow's new `Publish to PyPI` step uses `pypa/gh-action-pypi-publish@release/v1` with `skip-existing: true` for idempotent re-runs.
- **LICENSE bundled in the wheel.** Added `cli/LICENSE` (verbatim copy of the root MIT licence) and `license-files = ["LICENSE"]` to `cli/pyproject.toml`. PyPI displays the licence correctly and `python -m zipfile -l` confirms it ships at the wheel root.
- **`ATTRIBUTIONS.md` at repo root.** Canonical third-party crediting for every tool slopstopper-cli subprocess-invokes (Semgrep, Gitleaks, Trivy, OWASP ZAP, Playwright, axe-core, Lighthouse CI, Lizard, markdownlint-cli, Docker, GitHub CLI, Node.js) plus build-time GitHub Actions. Linked from `README.md`, `cli/README.md`, `app/tools.html`, and `cli/pyproject.toml`'s `Acknowledgements` URL.
- **`maintainers` field** on `cli/pyproject.toml` so PyPI has a contact for the project.
- **`Changelog` + `Acknowledgements` URLs** on the PyPI project page (`[project.urls]`).
- **Per-tool licence badges** on every card in `app/tools.html` plus a footer linking to `ATTRIBUTIONS.md`.

### Changed

- **`install.sh`** no longer carries a pinned wheel URL constant. Installs/refreshes from PyPI directly via `pipx install slopstopper-cli` (or `python3 -m pip install --user --upgrade slopstopper-cli` fallback).
- **All 15 `ss-*-check.yml` workflows** install with `pip install slopstopper-cli` instead of the pinned `releases/download/v0.2.1/slopstopper_cli-0.2.1-py3-none-any.whl` URL. Adopter CI tracks the latest release automatically.
- **`docs/runbooks/RELEASE.md`** rewritten around the new flow. The "Bump the pinned wheel URL" step and its `sed` one-liner are gone. The "Manual PyPI publish" section is gone (automated). New section: "One-time PyPI Trusted Publisher setup".
- **READMEs + website install commands** all show `pipx install slopstopper-cli`; release-tag links go to `releases/latest` rather than a pinned version.

### Notes for adopters

Existing adopter repos keep working — their installed workflows still install slopstopper-cli 0.2.1 from the GitHub Release URL until they next run `install.sh`, which rewrites their workflows to the new `pip install slopstopper-cli` shape. No forced migration.

## [0.2.1] - 2026-06-14

### Added

- **Build provenance attestations** on release artifacts. The release workflow now signs every wheel and sdist with `actions/attest-build-provenance@v2` (Sigstore keyless OIDC). Adopters verify with `gh attestation verify <wheel> --owner hungovercoders` — proves the artifact came from this repo's release pipeline, not a tampered upload. See [`docs/runbooks/RELEASE.md`](docs/runbooks/RELEASE.md#verifying-build-provenance).

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
