# Third-party attributions

`slopstopper-cli` is MIT-licensed (see [`LICENSE`](./LICENSE)). Its only
bundled runtime dependency is **Lizard** (MIT) — declared in
`cli/pyproject.toml` so pip/pipx installs it into the same environment, where
its own package metadata carries its licence notice. slopstopper-cli does not
bundle or statically link any other third-party code: every remaining tool
below is invoked via `subprocess` only; each stays under its own licence,
owned and maintained by its upstream project, and adopters install them
separately.

The same boundary applies at runtime: `slopstopper run <check>` shells out
to these tools and does not import them. Updating this file is part of the
checklist whenever a new check or external tool is added (see
[`AGENTS.md`](./AGENTS.md)).

## Tools invoked by slopstopper-cli

| Tool | Licence | Used by | Upstream |
|------|---------|---------|----------|
| Semgrep | LGPL-2.1 | `ss-security-sast` | <https://github.com/semgrep/semgrep> |
| Gitleaks | MIT | `ss-security-secrets` | <https://github.com/gitleaks/gitleaks> |
| Trivy | Apache-2.0 | `ss-security-vulnerability-all` | <https://github.com/aquasecurity/trivy> |
| OWASP ZAP | Apache-2.0 | `ss-security-dast` | <https://github.com/zaproxy/zaproxy> |
| Lizard | MIT | `ss-hygiene-complexity` | <https://github.com/terryyin/lizard> |
| markdownlint-cli | MIT | hygiene doc lint (slopstopper.dev-internal) | <https://github.com/igorshubovych/markdownlint-cli> |
| Playwright | Apache-2.0 | smoke, accessibility, broken-links | <https://github.com/microsoft/playwright> |
| axe-core | MPL-2.0 | accessibility audit (loaded into Playwright) | <https://github.com/dequelabs/axe-core> |
| Lighthouse CI | Apache-2.0 | Core Web Vitals | <https://github.com/GoogleChrome/lighthouse-ci> |
| Docker | Apache-2.0 | runs the ZAP container for DAST | <https://github.com/moby/moby> |
| GitHub CLI (`gh`) | MIT | `slopstopper emit` (PR comments, issues, attestation verify) | <https://github.com/cli/cli> |
| Node.js | MIT | runs Playwright, Lighthouse, `slopstopper serve` | <https://github.com/nodejs/node> |

## GitHub Actions / build-time dependencies

Used across `.github/workflows/*.yml`. Versions track the pins in those files
(some pinned to a commit SHA at the same release); licences are what matter
here and are stable across patch bumps.

GitHub-maintained actions (all MIT):

| Action | Licence | Purpose |
|--------|---------|---------|
| `actions/checkout@v6` | MIT | check out the repo in workflows |
| `actions/setup-python@v6` | MIT | install Python in workflows |
| `actions/setup-node@v6` | MIT | install Node in workflows |
| `actions/cache@v5` | MIT | restore/save tool + dependency caches |
| `actions/upload-artifact@v4` | MIT | upload reports/test artifacts |
| `actions/download-artifact@v8` | MIT | download artifacts between jobs |
| `actions/github-script@v9` | MIT | inline JS for PR comments / labels |
| `actions/labeler@v5` | MIT | auto-label PRs (`ss-hygiene-auto-label-pr`) |
| `actions/dependency-review-action@v4` | MIT | dependency vuln + licence gate |
| `actions/attest-build-provenance@v4` | MIT | Sigstore build-provenance attestation on releases |
| `actions/create-github-app-token@v2` | MIT | mint a GitHub App token for release automation |

Third-party actions:

| Action | Licence | Purpose |
|--------|---------|---------|
| `jdx/mise-action@v2` | MIT | install the pinned toolchain from `mise.toml` |
| `googleapis/release-please-action@v4` | Apache-2.0 | automated release PRs + changelog |
| `pypa/gh-action-pypi-publish@release/v1` | BSD-3-Clause | publish wheels to PyPI via OIDC Trusted Publisher |
| `github/gh-aw`, `github/gh-aw-actions` | GitHub-proprietary | GitHub Agentic Workflows runtime (GitHub-owned, used within GitHub Actions) for the agentic doc-updater |

## Verification

The authoritative current state lives in:

- subprocess call sites under [`cli/slopstopper/checks/`](./cli/slopstopper/checks/),
- workflow definitions under [`.github/workflows/ss-*.yml`](./.github/workflows/), and
- the per-tool cards on [`app/tools.html`](./app/tools.html) (which renders the
  user-facing view at <https://slopstopper.dev/tools.html>).

The CI check `slopstopper run hygiene:docs-accuracy` catches drift between
this document and the workflow set.
