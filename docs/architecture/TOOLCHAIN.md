# Toolchain — what runs, where it comes from, what it sends

Every tool slopstopper runs, the licence it ships under, where it is
installed from, and what — if anything — it sends off the machine. Written
for whoever has to approve slopstopper: a security review, an
open-source-licence check, an air-gapped CI.

## The rule: nothing leaves without opting in

Out of the box, the only things that leave the runner are:

- **Downloads** — the tools themselves, Semgrep's `p/default` ruleset,
  Trivy's vulnerability database, ZAP's image and add-on updates,
  Playwright's browser. Requests go out; nothing about the repo goes with
  them.
- **Requests to the URLs you configure** — the browser, API and DAST
  checks test the site you point them at. Broken-links follows
  same-origin links only.
- **GitHub, for GitHub's own features** — PR comments, issues, labels and
  dependency review go through the GitHub API with the workflow's
  `GITHUB_TOKEN`, into the same repository.

Anything that would send information about the repo to another party is
**off until a setting turns it on**:

| Setting | Off (default) | On |
| ------- | ------------- | -- |
| `security.sast.send_metrics` | Semgrep runs with `--metrics=off` | Semgrep sends its usage metrics. Required for `security.sast.rules: auto`, where Semgrep picks rules by logging in to its Registry with the repo URL |
| `reliability.cwv.public_report` | Lighthouse reports stay on the runner (`.lighthouseci/`, the CI artifact) | Each report is uploaded to Lighthouse CI's temporary public storage and linked from the PR comment |
| `COPILOT_GITHUB_TOKEN` secret | The documentation-updater workflow stops at its secret check | The weekly doc updater runs: GitHub Copilot reads the repo's docs and recent changes and opens a PR |

Where a tool phones home on its own (usage telemetry, update checks),
slopstopper switches that off: Semgrep via `--metrics=off`, Trivy via `TRIVY_DISABLE_TELEMETRY` and `TRIVY_SKIP_VERSION_CHECK`, ZAP
via `-notel`.

## Every tool

| Tool | Used by | Licence | Installed from | Sends, by default |
| ---- | ------- | ------- | -------------- | ----------------- |
| slopstopper-cli | every check | MIT | PyPI (`pipx:slopstopper-cli` via mise) | Nothing. `install.sh` asks pypi.org for the latest version on first install |
| mise | toolchain pins | MIT | mise.run / `jdx/mise-action` | Nothing from slopstopper's use |
| Task | `task ss:*` shims | MIT | mise | Nothing |
| Semgrep CE | `security:sast` | LGPL-2.1 | `pip install semgrep` | Nothing — downloads its ruleset; usage metrics **off** (see above). Local rule files make it fully offline |
| Gitleaks | `security:secrets` | MIT | GitHub release binary | Nothing — scans git history locally |
| Trivy | `security:vulnerability:all` | Apache-2.0 | Aqua's apt repository | Nothing — downloads its vulnerability DB; telemetry and update check switched off |
| GitHub dependency review | `ss-security-vulnerability-new-check.yml` | MIT (`actions/dependency-review-action`) | GitHub Action | GitHub's own dependency graph, via the GitHub API |
| OWASP ZAP | `security:dast` | Apache-2.0 | `ghcr.io/zaproxy/zaproxy:stable` (Docker) | Requests to the target; add-on update download; telemetry off (`-notel`) |
| lizard | `hygiene:complexity` | MIT | PyPI (a slopstopper-cli dependency) | Nothing |
| Playwright + Chromium | smoke, accessibility, SEO, broken links | Apache-2.0 | npm; browser from Playwright's CDN | Requests to the target only |
| axe-core | `reliability:accessibility` | MPL-2.0 | npm | Nothing — runs in the page |
| Lighthouse CI | `reliability:cwv` | Apache-2.0 | npm (`npx lhci`) | Requests to the target; report upload **off** (see above) |
| markdownlint-cli | `contributing:lint` (this repo) | MIT | npm | Nothing |
| actions/labeler | auto-label PRs | MIT | GitHub Action | Labels via the GitHub API |
| GitHub Agentic Workflows + Copilot | weekly doc updater | — | `github/gh-aw` setup action | **Off** until `COPILOT_GITHUB_TOKEN` is set (see above) |

Licences are as each project publishes them; check the current terms
before relying on this table for a licence review.

## Semgrep, in detail

By default the check runs Semgrep's `p/default` ruleset with
`--metrics=off`. Semgrep downloads the ruleset from its Registry; with
metrics off, nothing about the repo or the scan goes back. Local rule
files (`security.sast.rules: [.semgrep/]`) need no network at all.

With `security.sast.send_metrics: true`, Semgrep sends its
[usage metrics](https://semgrep.dev/docs/metrics):

- a random machine ID, the IP address and the CI provider;
- scan sizes, timings and per-language parse rates;
- one-way hashes of the project URL, the rules and the config;
- finding counts.

Source code, file names, commit data and the findings themselves are never
sent. `rules: auto` — Semgrep picking rules per language — logs in to the
Registry with the repository's URL and only works with metrics on
(Semgrep refuses `--config=auto` with `--metrics=off`), so the check
accepts it only alongside the opt-in. See [SAST.md](../security/SAST.md).

## Lighthouse CI, in detail

Lighthouse CI's `temporary-public-storage` target uploads each report to
Google Cloud Storage. Anyone with the link can read it for a few days:
page content, screenshots and URLs, including a build served only on the
runner. With `public_report` off, `lhci autorun` uploads nothing — the
bundled configs carry no `upload` block — and the PR comment shows the
results table without a "Full Lighthouse Report" link. A Lighthouse config you have ejected
(`slopstopper templates eject lighthouserc.json`) that carries its own
`upload` block uploads regardless of this setting.

## The documentation updater, in detail

`ss-hygiene-doc-updater` is a GitHub Agentic Workflow. It runs GitHub
Copilot against this repo's `docs/` and recently merged changes, then
opens a PR. It runs only when the repo has a `COPILOT_GITHUB_TOKEN`
secret; without one it stops at the secret check and nothing is sent.
Delete the workflow, or list it under `workflows.disabled`, to drop it
entirely.

## Checking this yourself

Every check reports what it did. `security:sast` names its rule source
on the console and in its report. To prove a check sends nothing, run it
with outbound network blocked except to the target: the defaults pass,
apart from the downloads listed above.
