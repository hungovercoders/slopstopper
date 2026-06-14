# Third-party attributions

`slopstopper-cli` is MIT-licensed (see [`LICENSE`](./LICENSE)). It does not
bundle or statically link any third-party code — `cli/pyproject.toml`
declares `dependencies = []`. The checks below invoke the following external
tools via `subprocess` only; each remains under its own licence, owned and
maintained by its upstream project. Adopters install them separately.

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

| Action | Licence | Purpose |
|--------|---------|---------|
| `actions/checkout@v4` | MIT | check out the repo in workflows |
| `actions/setup-python@v5` | MIT | install Python in workflows |
| `actions/setup-node@v4` | MIT | install Node in workflows |
| `actions/attest-build-provenance@v2` | MIT | Sigstore build-provenance attestation on releases |
| `pypa/gh-action-pypi-publish@release/v1` | BSD-3-Clause | publish wheels to PyPI via OIDC Trusted Publisher |

## Verification

The authoritative current state lives in:

- subprocess call sites under [`cli/slopstopper/checks/`](./cli/slopstopper/checks/),
- workflow definitions under [`.github/workflows/ss-*.yml`](./.github/workflows/), and
- the per-tool cards on [`app/tools.html`](./app/tools.html) (which renders the
  user-facing view at <https://slopstopper.dev/tools.html>).

The CI check `slopstopper run hygiene:docs-accuracy` catches drift between
this document and the workflow set.
