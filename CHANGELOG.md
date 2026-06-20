# Changelog

All notable changes to **slopstopper-cli** are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The release workflow (`.github/workflows/ss-release.yml`) reads the section matching the pushed tag and posts it as the GitHub Release notes. To cut a release: bump `version` in `cli/pyproject.toml` and `__version__` in `cli/slopstopper/__init__.py`, move the `## [Unreleased]` block down to a new `## [X.Y.Z] - YYYY-MM-DD`, push a `vX.Y.Z` tag.

## [0.8.0](https://github.com/hungovercoders/slopstopper/compare/v0.7.1...v0.8.0) (2026-06-20)


### Features

* **hygiene:** enforce and remediate the Map Pattern in entry-files check ([#276](https://github.com/hungovercoders/slopstopper/issues/276)) ([cc6de07](https://github.com/hungovercoders/slopstopper/commit/cc6de07b13a8f89e65fbe03110f8142c10136c23))
* **skills:** install at project level and merge update into install ([3bd27f9](https://github.com/hungovercoders/slopstopper/commit/3bd27f9a40c3b8f7906631fc8b433b5c2187d956))
* **skills:** install at project level and merge update into install ([5c58f81](https://github.com/hungovercoders/slopstopper/commit/5c58f81f1262ead4faf0e95104537a9a2a9ce7a4))

## [0.7.1](https://github.com/hungovercoders/slopstopper/compare/v0.7.0...v0.7.1) (2026-06-19)


### Bug Fixes

* **reliability:** read scheduled-run URL from .slopstopper.yml urls.production ([f4c36b7](https://github.com/hungovercoders/slopstopper/commit/f4c36b77a8aab0272e5cb3905ed126de123659b2))
* **reliability:** read scheduled-run URL from .slopstopper.yml urls.production ([c91136f](https://github.com/hungovercoders/slopstopper/commit/c91136f28aa441c66842dd3e394bd8b007c03e9e))

## [0.7.0](https://github.com/hungovercoders/slopstopper/compare/v0.6.0...v0.7.0) (2026-06-16)


### Features

* **checks:** META + markdown reports for smoke/accessibility/broken-links ([621ff93](https://github.com/hungovercoders/slopstopper/commit/621ff937d801b8040007b69641982b6750af76de))
* **checks:** META + markdown reports for smoke/accessibility/broken-links ([1da48df](https://github.com/hungovercoders/slopstopper/commit/1da48dfbe49d9e378f90ca45bf7dcb86dea40d72))
* **cli:** add `slopstopper badges` to generate README status block ([44f5521](https://github.com/hungovercoders/slopstopper/commit/44f55211feba04723c7baaf1d54203867c03e4ae))
* **cli:** add slopstopper badges to generate README status block ([3085dea](https://github.com/hungovercoders/slopstopper/commit/3085deaabf709a98c35b9116766996d666ba0567))
* **emit:** add --on-pass=close to slopstopper emit ([ada4ce1](https://github.com/hungovercoders/slopstopper/commit/ada4ce19690bbbf094cd27e121121fcdaad7135c))
* **emit:** add --on-pass=close to slopstopper emit ([7b0564d](https://github.com/hungovercoders/slopstopper/commit/7b0564ddc9289474667f856759a688a0f7a53211))
* **emit:** brand emitted issues with slopstopper label + body marker ([787d2ef](https://github.com/hungovercoders/slopstopper/commit/787d2efcb0b20c7fef75bca3665232f1e6492f4b))
* **emit:** brand emitted issues with slopstopper label + body marker ([12272da](https://github.com/hungovercoders/slopstopper/commit/12272dacbab5650090e31e0fc6fda709d39b431c))
* **install:** bundle Claude Code skill trio into install.sh ([bcae4aa](https://github.com/hungovercoders/slopstopper/commit/bcae4aa988f7ed1a2ff0e0ee7c648131183113a5))
* **install:** bundle Claude Code skill trio into install.sh ([9c5e81b](https://github.com/hungovercoders/slopstopper/commit/9c5e81bbf47c489ad943792d6897068a5272f915))
* **workflows:** unify issue lifecycle through `slopstopper emit` ([a95ca38](https://github.com/hungovercoders/slopstopper/commit/a95ca38526885c6a6d74b946647ddccb9070d5aa))
* **workflows:** unify issue lifecycle through slopstopper emit ([1d70ece](https://github.com/hungovercoders/slopstopper/commit/1d70eced847c829bb418109aab45b9ac5075bcdb))


### Bug Fixes

* **workflows:** dedupe failure-issue against slopstopper body marker ([648de14](https://github.com/hungovercoders/slopstopper/commit/648de14b984444ebf7734b24382500ea4175282f))
* **workflows:** dedupe failure-issue against slopstopper body marker ([d5e985e](https://github.com/hungovercoders/slopstopper/commit/d5e985e7f0a71ba7279bbdbb2bd77afff59bf926))

## [0.6.0](https://github.com/hungovercoders/slopstopper/compare/v0.5.1...v0.6.0) (2026-06-15)


### Features

* **canonical:** make task ss:* the single invocation surface — CI included ([821ddd3](https://github.com/hungovercoders/slopstopper/commit/821ddd3de3c04d5dda98f3c6d8126c88e7172ca5))
* **canonical:** make task ss:* the single invocation surface — CI included ([392b729](https://github.com/hungovercoders/slopstopper/commit/392b729faaa790926a7254a1fd685de1dfde1ddd))


### Bug Fixes

* **canonical:** emit + docs-accuracy follow-ups for the alignment refactor ([5fdc656](https://github.com/hungovercoders/slopstopper/commit/5fdc65635be55b57b2bd1ed6f595d272b3a4e8f8))
* **canonical:** handle shim/CLI name aliases in workflow + --no-task transform ([ba92c75](https://github.com/hungovercoders/slopstopper/commit/ba92c75f4cb315df3a938980c0f628222b29bdd8))

## [0.5.1](https://github.com/hungovercoders/slopstopper/compare/v0.5.0...v0.5.1) (2026-06-14)


### Bug Fixes

* **cli:** exit non-zero on HIGH+ vulnerabilities to match CI gate behaviour ([2f5854b](https://github.com/hungovercoders/slopstopper/commit/2f5854bdba7e9013bc7819de51b43b1755a9b62d))
* **cli:** exit non-zero on HIGH+ vulnerabilities to match CI gate behaviour ([80be098](https://github.com/hungovercoders/slopstopper/commit/80be098886f2edd9549b331115b0cce8d56e25a9))
* **cli:** make complexity, playwright, serve work out of the box ([07ee735](https://github.com/hungovercoders/slopstopper/commit/07ee735d19b44443fa396ef01de79020860452ff))
* **cli:** make complexity, playwright, serve work out of the box ([70cf72e](https://github.com/hungovercoders/slopstopper/commit/70cf72e64e7a6473457fb24c7f375e29c1e2ad7f))
* **install:** three install.sh issues found by first real adopter ([29bbff8](https://github.com/hungovercoders/slopstopper/commit/29bbff8eb5381e3092365c491144ab04439fce33))
* **install:** three install.sh issues found by first real adopter ([f3ddb84](https://github.com/hungovercoders/slopstopper/commit/f3ddb8497b6db9d188da882a33eecab99ef0fad2))
* **server.js:** split parseCloudflareHeaders to satisfy CCN &lt; 10 ([f7d059c](https://github.com/hungovercoders/slopstopper/commit/f7d059c4d02b74d1feb68eb60a02b1462148d323))

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
