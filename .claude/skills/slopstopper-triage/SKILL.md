---
name: slopstopper-triage
description: Diagnose and fix a failing slopstopper check, including a check that doesn't apply to the repo's shape (a browser check on an API or library). Use when a user reports a specific slopstopper workflow or task is failing — SAST, secrets, complexity, docs-accuracy, docs-size, docs-structure, entry-files, CSP exceptions, auto-label, smoke, accessibility, Core Web Vitals, SEO, broken links, DAST, dependency review, API health, API latency, OpenAPI drift, API headers/CORS, or the workflow-failure tracker. Maps each check to the local task that reproduces it, the report files it generates, the typical root-cause categories (real finding / false positive / threshold too tight), and a per-symptom gotcha table with diagnostic steps and the file the fix lives in. For first-time install OR refreshing an existing install use slopstopper-install.
---

# Triage a failing slopstopper check

You're being asked to fix a slopstopper check that's failing. This skill is reactive — it assumes the install is in place and at least one check is red. If the user is mid-install or refreshing an existing install, the install playbook (`slopstopper-install` Step 7) already handed off here. Either way, the procedure is the same.

Every check now runs through `slopstopper-cli`. The workflow body for each `ss-*.yml` is ~8 lines: install the CLI, `slopstopper run <category>:<check>`, `slopstopper emit <category>:<check> --target {pr-comment,issue}`. So the local reproducer is always `slopstopper run …` (or its `task ss:*` shim).

The shape of the fix depends on which of three things you're looking at:

1. **A real finding** — the check is right, the code is wrong. Fix the code.
2. **A false positive** — the check's heuristic is misfiring on this codebase. Suppress narrowly via the check's documented mechanism, always with a `# why` comment.
3. **A threshold too tight for this repo** — the check itself is correct, but its config doesn't fit this codebase's reality. Tune in `.slopstopper.yml` (most knobs live there) or the relevant `docs/<loop>/<CONFIG>.md` for the few that aren't config-driven yet.

Don't apply blanket suppressions and don't loosen thresholds without writing down why.

## Step 1 — Identify which check is failing

Slopstopper workflows follow the naming pattern `ss-<loop>-<action>-check.yml`. Decode:

- **`<loop>`** = `security`, `hygiene`, `reliability` → maps to `docs/<loop>/README.md` for the loop-level overview.
- **`<action>`** = `sast`, `secrets`, `complexity`, `docs-accuracy`, etc. → maps to a specific check name `<loop>:<action>` in the CLI's `REGISTRY` (`cli/slopstopper/checks/__init__.py`).

If the user only gave you the workflow URL or a failing CI badge, click through to the workflow file under `.github/workflows/` in the target repo and read the `run:` step — Task-mode workflows call `task ss:<category>:<check>`; `--no-task` mode workflows call `slopstopper run <category>:<check>` directly. Either way the check name is the same one you use locally.

### Fastest route: read the PR summary comment

Every PR carries one rolling comment headed `SlopStopper — N of M checks failed`, with the failures in a table linking straight to their logs, and the passing checks folded below. Start there: it names the failing checks and nothing else, so you don't have to scan the Actions tab or 20 comment cards.

Each failing check also posts its own compact comment — a verdict line, the failing items, and the full report folded into a `<details>`. Open that fold before pulling the artifact: it is the same report, already on the page.

A `⚠️` verdict is neither: the advisory checks (`hygiene:docs-size`) report findings while deliberately exiting 0, so they post `⚠️ … — has alerts` and keep the comment. The job is green and the summary shows ✅ — the alert is a nudge, not a gate.

**A green PR has no per-check comments at all.** Passing checks delete theirs (`emit --on-pass=delete`), so the summary is the only comment. An absent comment means "passed", not "didn't run" — the summary's own table is what distinguishes those.

## Step 2 — Reproduce locally

`task ss:*` is the canonical local interface — same shipped Task in the target's repo as CI uses. Run `task ss:<category>:<check>` and you get the same code path, same exit codes, same reports. The local loop is an order of magnitude faster than pushing to CI per iteration. If the target was installed with `--no-task`, fall back to `slopstopper run <category>:<check>` directly — works identically.

| Workflow | Canonical (Task) | Underlying CLI | Needs URL? | Needs build? | Needs Docker? |
|---|---|---|---|---|---|
| `ss-security-sast-check.yml` | `task ss:security:sast` | `slopstopper run security:sast` | – | – | – |
| `ss-security-secrets-check.yml` | `task ss:security:secrets` | `slopstopper run security:secrets` | – | – | – |
| `ss-security-vulnerability-all-check.yml` | `task ss:security:vulnerability:all` | `slopstopper run security:vulnerability:all` | – | – | – |
| `ss-security-vulnerability-new-check.yml` | (CI-only — Dependency Review action) | – | – | – | – |
| `ss-security-dast-check.yml` | `task ss:security:dast -- <URL>` | `slopstopper run security:dast <URL>` | ✓ | ✓ (site mode only) | ✓ |
| `ss-security-api-headers-check.yml` | `task ss:security:api-headers -- <URL>` | `slopstopper run security:api-headers <URL>` | ✓ | – (probe a deployed origin) | – |
| `ss-hygiene-complexity-check.yml` | `task ss:hygiene:complexity` | `slopstopper run hygiene:complexity` | – | – | – |
| `ss-hygiene-csp-exceptions-check.yml` | `task ss:hygiene:csp-exceptions` | `slopstopper run hygiene:csp-exceptions` | – | – | – |
| `ss-hygiene-docs-accuracy-check.yml` | `task ss:hygiene:docs-accuracy` | `slopstopper run hygiene:docs-accuracy` | – | – | – |
| `ss-hygiene-docs-size-check.yml` | `task ss:hygiene:docs-size` | `slopstopper run hygiene:docs-size` | – | – | – |
| `ss-hygiene-docs-structure-check.yml` | `task ss:hygiene:docs-structure` | `slopstopper run hygiene:docs-structure` | – | – | – |
| `ss-hygiene-entry-files-check.yml` | `task ss:hygiene:entry-files` | `slopstopper run hygiene:entry-files` | – | – | – |
| `ss-hygiene-openapi-check.yml` | `task ss:hygiene:openapi -- <URL>` | `slopstopper run hygiene:openapi <URL>` | ✓ (optional — only the probes need it) | – (never builds locally) | – |
| `ss-hygiene-auto-label-pr.yml` | (CI-only — needs PR context) | – | – | – | – |
| `ss-reliability-smoke-tests.yml` | `task ss:reliability:smoke -- <URL>` | `slopstopper run reliability:smoke <URL>` | ✓ | ✓ (if URL is local) | – |
| `ss-reliability-accessibility-check.yml` | `task ss:reliability:accessibility -- <URL>` | `slopstopper run reliability:accessibility <URL>` | ✓ | ✓ | – |
| `ss-reliability-core-web-vitals.yml` | `task ss:reliability:cwv -- <URL>` | `slopstopper run reliability:cwv <URL>` | ✓ | ✓ | – |
| `ss-reliability-seo-check.yml` | `task ss:reliability:seo -- <URL>` | `slopstopper run reliability:seo <URL>` | ✓ | ✓ | – |
| `ss-reliability-llms-txt-check.yml` | `task ss:reliability:llms-txt -- <URL>` | `slopstopper run reliability:llms-txt <URL>` | ✓ | ✓ | – |
| `ss-reliability-robots-txt-check.yml` | `task ss:reliability:robots-txt -- <URL>` | `slopstopper run reliability:robots-txt <URL>` | ✓ | ✓ | – |
| `ss-reliability-sitemap-check.yml` | `task ss:reliability:sitemap -- <URL>` | `slopstopper run reliability:sitemap <URL>` | ✓ | ✓ | – |
| `ss-reliability-broken-links-check.yml` | `task ss:reliability:broken-links -- <URL>` | `slopstopper run reliability:broken-links <URL>` | ✓ | ✓ | – |
| `ss-reliability-api-health-check.yml` | `task ss:reliability:api-health -- <URL>` | `slopstopper run reliability:api-health <URL>` | ✓ | – (never builds locally) | – |
| `ss-reliability-api-latency-check.yml` | `task ss:reliability:api-latency -- <URL>` | `slopstopper run reliability:api-latency <URL>` | ✓ | – (never builds locally) | – |
| `ss-workflow-failure-issue.yml` | (CI-only — operational, runs on workflow_run) | – | – | – | – |

For dynamic checks (`URL ✓`): pass the URL as a bare-positional arg after `--` (Task) or directly (CLI). Pointing at `http://localhost:8080` with `node .ss/server.js` serving the built site is the fastest local loop.

The four API checks are the exception: they never build and serve the repo (an API isn't a static bundle), so reproduce them against whatever origin actually runs the API — a preview environment, or a locally-running server you started yourself. `security:api-headers` in particular audits headers that usually come from the edge or proxy, so a clean local run is weaker evidence than a clean run against the deployed URL.

Two more reproduce caveats:

- **`reliability:api-latency` does not reproduce reliably anywhere.** Timings depend on the machine, the network and whether the target is cold. A local run that passes proves nothing about the CI failure, and vice versa. Reproduce it against the *same* environment CI audited, and re-run it a few times before believing a single result.
- **`hygiene:openapi` is the one hygiene check that needs a URL** — and only for its reachability probes. The committed-vs-served comparison needs `api.openapi.served_spec`, not a URL, so `slopstopper run hygiene:openapi` with no argument still reproduces that half.

If a reliability workflow's failure is about *which pages it audited* rather than what it found, the page-list comes from `slopstopper discover <check> --event=<event>` — run that directly to see the resolved set before reproducing the check itself.

For `security:vulnerability:all`: if a finding shows up only on CI (or only locally), trivy DB freshness or binary version drift is the usual cause — see `docs/security/README.md` → "Local/CI Parity" before pursuing the finding as real.

## Step 3 — Read the report

Most checks write structured output under `.ss/reports/<check>/`:

- `.ss/reports/<check>/<check>-report.md` — human-readable, this is what you want first.
- `.ss/reports/<check>/<check>-report.json` — machine-readable, useful for grep / jq.

For DAST: `.ss/reports/dast/dast-report.json` + `.ss/reports/dast/dast-report.md` + `.ss/reports/dast/dast-gate.json` (the swallow-vs-block decisions the gate made, with `source` field naming which exception mechanism let each one through).

For Playwright: `playwright-report/` at the target repo root (Playwright's own HTML report).

Read the report before deciding the fix shape — most reports name the file, line, rule, and severity, which collapses Step 4 immediately.

## Step 4 — Categorise the finding

For each failing finding, decide which of the three buckets it falls into:

### Real finding — fix the code

The check is correctly flagging a problem. Examples:
- Secrets check finds an actual leaked API key → revoke immediately, scrub history (`git filter-repo` or BFG), then fix the leak source.
- SAST flags a SQL injection in a query builder → rewrite to use parameterised queries.
- Accessibility flags a missing `alt` on a real image → add the alt text.
- Broken-links check flags an internal link that 404s → fix or remove the link.

There's no escape hatch here. Fix the code.

### False positive — suppress narrowly with `# why`

The check's heuristic is misfiring on this codebase. Use the check's documented suppression mechanism — never disable globally — and always carry a `# why` comment so the next reader knows why the exception is justified.

| Check | Suppression file / mechanism | Granularity |
|---|---|---|
| Secrets (gitleaks) | `.gitleaks.toml` `[allowlist]` block | Path or regex |
| SAST (Semgrep) | `# nosemgrep: <rule-id>` inline, or `.semgrepignore` for path-scoped | Inline or path |
| DAST (OWASP ZAP) — CSP findings | `docs/security/CSP_EXCEPTIONS.md` `## Exceptions` → `### /path` heading (glob patterns supported: `/*`, `/blog/*`) | Per-path |
| DAST — other rule false positives | `.zap/rules.tsv` → `<plugin-id>\tIGNORE\t# why` | Per-rule, site-wide |
| Accessibility (axe-core) | `disabledRules` in the spec, or scope the spec to exclude the offending selector | Per-rule or per-element |
| Vulnerability (Trivy) | `.trivyignore` with the CVE ID + a `# why` line | Per-CVE |
| Complexity (lizard) | Refactor the function, or raise `hygiene.complexity.max_ccn` in `.slopstopper.yml` (default 15) with a `# why` note | Per-repo (the ceiling is global) |

Each suppression is a documented gate exception, not a way to quiet findings that should be fixed. The PR that adds it is the place reviewers catch it.

### Threshold too tight — tune in `.slopstopper.yml`

The check is correct but the default threshold doesn't fit this repo. **First check `.slopstopper.yml`** — many checks read their thresholds from there, falling back to a hardcoded default when unset. The example file ([`.slopstopper.yml.example`](https://github.com/hungovercoders/slopstopper/blob/main/.slopstopper.yml.example)) is the canonical schema reference.

Config-driven knobs (no file edit needed beyond `.slopstopper.yml`):

| Check | Keys | Defaults |
| --- | --- | --- |
| `hygiene:docs-size` | `hygiene.docs_size.max_total_size_kb` / `.max_file_size_kb` / `.max_files` | 150 / 20 / 25 |
| `hygiene:entry-files` | `hygiene.entry_files.max_words` / `.require_map_pointer` / `.map_path` | 1500 / true / `docs/index.md` |
| `reliability:smoke` | `pages.smoke`, `smoke.og_image_path` | `/`, `/og-image.png` |
| `reliability:{accessibility,seo,broken_links}` | `pages.<check>`, `reliability.coverage.<event>` | `/`, hand-list mode |
| `hygiene:csp-exceptions` | `headers.source`, `headers.format` | unset (graceful skip) |
| `hygiene:docs-accuracy` | `hygiene.docs_accuracy.extra_paths` | `[]` — only `docs/` + the root entry files are scanned |
| `hygiene:docs-structure` | `hygiene.docs_structure.require_indexed_docs` | `true` — every doc linked from a README above it |

Tunings that are NOT yet config-driven (require code/file edits):

- `docs/hygiene/README.md` complexity config — lizard cyclomatic complexity caps.
- `.ss/lighthouserc.json` (or the bundled `cli/slopstopper/data/lighthouserc.json`) — Core Web Vitals thresholds. Edit the `.ss/` copy if you want adopter-side persistence; the CLI prefers it over the package-data fallback.

Tuning is a real decision — when you raise a threshold, leave a `# why` comment in `.slopstopper.yml` so the next maintainer doesn't roll it back. Don't tune to silence noise; tune to match a deliberate design decision.

## Step 5 — Per-symptom gotcha table

Common failures, with diagnostic step and the file the fix lives in. Categories use the Step 4 vocabulary: `code` / `suppress` / `tune`.

| Symptom | Diagnostic step | Cause | Fix location | Category |
|---|---|---|---|---|
| `Node.js vXX is not supported by Astro!` on `npm run build` across every reliability/Playwright workflow | Check `package.json` `engines.node` vs the `node` pin in `mise.toml` (`[tools] node`) | Workflows get node from the `mise.toml` pin via `jdx/mise-action`; the pin is older than the build needs | `mise use node@22` (or your version), commit `mise.toml` — mise locally and CI read the same pin | config |
| `task ss:hygiene:complexity` errors with compression-tool usage text instead of cyclomatic output | `which lizard` returns a Homebrew `lz4-lizard` path | PATH collision: `lz4-lizard` compression utility shadows the Python `lizard` | `pip install --upgrade lizard`; reorder PATH so the Python `lizard` wins, or invoke `python3 -m lizard` | code (environment) |
| `task ss:security:secrets` flags an example connection string, sample API key, or emulator config | Open the flagged file: is it real credential or tutorial sample? | gitleaks regex matches sample content as a generic API key | Real → revoke + scrub history (code). Sample → path-scoped allowlist in `.gitleaks.toml` with `# why` | code OR suppress |
| `task ss:hygiene:docs-accuracy` flags backtick-quoted filenames that don't resolve | Grep the docs for the bare filename — does the file exist anywhere under the repo? | Old docs reference renamed/moved files, or use bare filenames the resolver can't find | Fix the link in the doc; use repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) | code (docs) |
| `hygiene:docs-accuracy` reports "Broken Links Into This Repository" for an HTML page or a skill | Open the flagged file at the line; the link's `blob/main/<path>` names a path that isn't on disk | The file was renamed, moved into the CLI wheel, or deleted, and the page kept pointing at it. This is `hygiene.docs_accuracy.extra_paths` doing its job — these files are outside `docs/` and were never scanned before | Fix the link (or the prose around it — often the whole excerpt describes something that no longer exists). Don't remove the path from `extra_paths` to silence it | docs |
| `hygiene:docs-structure` reports "Unindexed doc: docs/<cat>/<file>.md" | `grep -n '<file>.md' docs/<cat>/README.md` | The doc exists but its category README doesn't link it, so nothing on the map reaches it. The map is a chain: `docs/index.md` → category README → doc | Add it to the category README's `## Contents` list (or delete the doc if it's dead) | docs |
| `task ss:hygiene:docs-structure` fails with `❌ docs/ directory not found` or category mismatch | `ls docs/` against the table in `docs/index.md` | Target doesn't follow the Map Pattern, or has an undocumented dir | Set up the Map Pattern (`slopstopper-install` Step 5 has the template) OR delete the three docs-* workflows | code (docs) OR delete check |
| Every reliability check fails at once on a repo with no browser surface — `npm run build` produces nothing to serve, or the audit reports no HTML/`<title>`/sitemap | `slopstopper profile show` — is the profile `ui` on a repo that's actually an API or a library? | Wrong project-shape profile. The eight browser-and-SEO checks (smoke, accessibility, cwv, seo, broken-links, llms-txt, robots-txt, sitemap) assume HTML and a served site; on an API they audit nothing and fail rather than no-op | Set `profile: api` (or `library`) in `.slopstopper.yml` and **re-run `install.sh`** — the key drives the set, the installer moves the files. Confirm with `slopstopper profile detect`. Don't chase these individually: one wrong profile shows up as 8 red checks | config |
| A single reliability check fails on a repo that's otherwise the right shape (an API whose docs site *does* want `broken-links`) | `slopstopper profile show` — is that workflow listed as dropped, or is it genuinely failing? | The profile is right but too coarse for this one check | Add the workflow to `workflows.enabled` in `.slopstopper.yml` and re-run `install.sh` to install it, or triage it normally if it's already installed. A profile only ever subtracts; `enabled` is the per-check escape hatch | config |
| `reliability:api-health` or `security:api-headers` reports "Nothing to audit — skipping" and exits 0 | `slopstopper config get api.health.path` / `api.headers.paths` | Neither key is set — both API checks ship inert, the same contract as `headers.source: null`. This is the unconfigured state, **not** a pass | Set `api.health.path` (e.g. `/health`) and `api.headers.paths` in `.slopstopper.yml`. `slopstopper-install` Step 4 has the full block. If the repo has no API, the skip is the correct end state — or drop to `profile: library` | config |
| `reliability:api-health` fails on `field \`status\` is \`degraded\`, expected \`ok\`` while the endpoint returns HTTP 200 | `curl -s <url>/health` and read the body | Working as designed, and the reason this check isn't just a reachability probe: the service is telling you it's unhealthy. Not a check problem | Fix the dependency the body names (`deps.*` fields usually point at it). Only touch `api.health.expect_fields` if the *contract* changed deliberately — never to make a degraded service look healthy | code |
| `security:api-headers` fails on a wildcard `Access-Control-Allow-Origin` and the API is deliberately public | Read the finding: does it mention `Access-Control-Allow-Credentials`? | Two different findings. A **bare** wildcard on a public read-only API is fine. A wildcard **with credentials** never is — browsers reject the pair, so the policy you intended was never being enforced | Bare wildcard → `api.headers.allow_wildcard_cors: true`. With credentials → fix the server to validate `Origin` against an allowlist and echo the match; the knob deliberately won't silence it | config OR code |
| `security:api-headers` fails on HSTS or `nosniff` but the headers are set at the CDN | Probe the deployed origin, not localhost: `task ss:security:api-headers -- https://api.example.com` | The edge adds them; a local process doesn't. A localhost run is auditing the wrong thing | Run the check against a deployed/preview URL (that's what CI does). If a header is genuinely handled by infrastructure the check can't see, `require_hsts` / `require_nosniff: false` with a `# why` comment | config |
| `security:api-headers` fails on an origin in `allowed_origins` that answers `(none)` | `curl -sI -H 'Origin: <that origin>' <url>` | The allowlist stopped matching — a renamed frontend domain, or a regex that no longer fires. This is the check's main job | Fix the server's allowlist, or remove the origin from `api.headers.allowed_origins` if it's genuinely retired | code |
| `reliability:api-latency` or `hygiene:openapi` reports "Nothing to sample/audit — skipping" and exits 0 | `slopstopper config get api.latency.paths` / `api.openapi.spec` | Neither key is set — both ship inert, the same contract as the other API checks. This is the unconfigured state, **not** a pass | Set `api.latency.paths` (the endpoints whose response time you care about) and `api.openapi.spec`. `slopstopper-install` Step 4 has the full block | config |
| `hygiene:openapi` skips with "this check reads JSON only" | Look at the `api.openapi.spec` value — does it end `.yaml` / `.yml`? | Working as designed. `slopstopper-cli` ships no third-party dependencies, so it has no YAML parser. DAST still uses the YAML spec; only this check skips | Point `api.openapi.spec` at the JSON form — most frameworks serve `/openapi.json`. If the repo only has YAML, this check stays skipped and that is a real coverage gap worth naming, not a config error | config |
| `reliability:api-latency` fails a median budget in CI but passes locally | Compare the report's median against the budget, then re-run in the same environment | Almost always the environment, not the code: a cold-started preview deploy is slower and noisier than a warm local process. Budgets gate on the median precisely so one outlier doesn't do this, so a *median* breach means it was consistently slow | If the budget was guessed rather than observed, it's the budget that's wrong — raise `api.latency.median_ms` to something derived from the reports, or unset it on PRs and rely on the scheduled production run. Only chase the code once the numbers say production regressed | threshold |
| `reliability:api-latency` fails with no budgets configured at all | Read the issue text — it will say "not reachable" or "answered HTTP N" | Not a budget failure. Reachability is the floor and is never opt-in: a timing taken from a connection error or a 500 isn't a measurement | Fix the endpoint or the URL. There is deliberately no knob to make an unreachable endpoint pass | code |
| `hygiene:openapi` reports an operation "served but missing from the committed spec" | `curl -s <served_spec_url>` and diff its `paths` against the committed file | The real thing this check exists for: someone shipped a route and didn't regenerate the spec. Not a false positive | Regenerate the spec from the running app and commit it. If the spec is generated at build time, point `api.openapi.spec` at the served URL instead so it can't drift at all | code |
| `hygiene:openapi` fails on a documented path that 404s, and the route is deliberately undeployed in this environment | `curl -i <url><path>` against the audited environment | Environment-specific routing, not drift — e.g. an admin route only deployed to production being probed on a preview URL | Add the path to `api.openapi.ignore_paths` (globs work) with a `# why` comment. Don't set `probe_paths: false` for one path — that disables the whole reachability half | config |
| A check is red in the Actions tab but its PR comment says `✅ … — passed` (or there's no comment) | Compare the emit line in that workflow: `slopstopper emit <check> --target pr-comment --status ${{ steps.<id>.outcome … }}` — does `<id>` name the step that actually decides the verdict? | The `--status` expression points at the wrong step. Most checks fail their own step, but `security:sast` and `security:secrets` exit 0 and gate on a later step's output, and `hygiene:docs-size` is advisory (always exits 0) | Fix the expression in that workflow to read the deciding step's `outcome` (or the gate's output). The verdict is never inferred from report text, precisely because those three would be read wrong | config (workflow) |
| The PR summary comment is missing, stale, or omits a check | Was `ss-pr-summary.yml` triggered? Check the Actions tab for "SlopStopper · PR Summary" runs on that PR | `workflow_run` can't glob: a check workflow whose `name:` isn't in `ss-pr-summary.yml`'s `workflow_run.workflows` list never re-renders the summary. `workflow_run` also only fires for workflows that exist on the **default branch**, so a brand-new check workflow won't trigger it until merged | Add the workflow's exact `name:` to that list. For a not-yet-merged workflow, expect the summary to lag until the branch lands — that's a GitHub constraint, not a bug | config (workflow) |
| The summary says `⏳ N of M still running` and never settles | Re-read it after the last check finishes; each completion re-renders it | Working as designed — the summary is rendered from run conclusions, so a mid-flight suite honestly reports as unfinished rather than green | Nothing to fix. If it stays stuck with all checks complete, the last summary run failed — check its logs | none |
| `security:dast` runs against an API and reports no alerts at all, or the workflow logs "no URL resolved" and skips | `slopstopper config get api.openapi.spec` | With no spec the check uses ZAP's baseline scan, which spiders a site from a root URL — a JSON API has no links to crawl, so an empty report is the expected (and useless) result, not a clean bill of health | Set `api.openapi.spec` to your OpenAPI URL or file, and `urls.preview` / `urls.production` so the workflow has something to scan. See [docs/security/DAST.md](../../docs/security/DAST.md) | config |
| `security:dast` in API mode reports alerts against the wrong host, or can't reach the operations | Check whether the spec's `servers` block names production while you're scanning a preview URL | The scanned URL is passed as ZAP's `-O` host override precisely for this; `api.openapi.host_override: false` turns it off | Leave `host_override` on unless the spec already names the environment you're scanning | config |
| `security:dast` exits 1 with "OpenAPI spec not found" | `ls <the path in api.openapi.spec>` | The configured spec is a repo-relative path that doesn't exist — a moved or generated-at-build-time file | Fix the path, or point `spec` at the URL the app serves it from so it can't drift from the routes | config |
| `task ss:hygiene:csp-exceptions` reports "no headers.source configured" with exit 0 | `cat .slopstopper.yml \| grep -A2 headers:` | `.slopstopper.yml` `headers.source` is null (the seeded default) | If you want the check active, set `headers.source` to your headers file (e.g. `public/_headers`) and `headers.format` to match (`cloudflare-text` for `_headers` files, `json` for JSON arrays, `auto` to infer). Otherwise this is harmless. | config |
| `slopstopper run hygiene:csp-exceptions` reports "Unknown headers.format" | Run `python3 -c "from slopstopper import headers_adapters; print(list(headers_adapters.ADAPTERS.keys()))"` | `.slopstopper.yml` `headers.format` doesn't match a shipped adapter | Set `headers.format` to one of the listed adapter names or `auto`. If you need a format slopstopper doesn't ship, add a module under `cli/slopstopper/headers_adapters/` and register it in `__init__.py`'s `ADAPTERS`. | config (or new adapter) |
| `task ss:hygiene:entry-files` fails with one of README/AGENTS/CLAUDE over 1500 words | Run the task — the report names the file + word count | Entry file has bloated with content that belongs under `docs/<category>/` | Move the bulk into the appropriate category README; the entry file should be a pointer | code (docs) |
| `task ss:hygiene:entry-files` fails with `missing_map_pointer` on README.md or AGENTS.md | Read `.ss/reports/entry-files/entry-file-size-report.md` — the "How to fix" section emits a paste-ready `> 🗺️ **Documentation map.** …` callout | Entry file exists but doesn't link `docs/index.md`; the Map Pattern is enforced (`hygiene.entry_files.require_map_pointer` default true) | Paste the snippet near the top of the named file (above any other body content). Confirm with `task ss:hygiene:entry-files`. If the rule genuinely doesn't fit this repo, set `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml` with a `# why` comment | code (docs) OR tune |
| `task ss:hygiene:entry-files` fails with `claude_not_thin_pointer` on CLAUDE.md | Read the report's CLAUDE-specific fix section | CLAUDE.md has substantive content instead of being a thin pointer (no `@AGENTS.md` directive, no link to AGENTS.md) | Replace the file contents with the paste-ready canonical body (the report includes it). Claude Code reads `@AGENTS.md` automatically — keep CLAUDE.md short and let AGENTS.md carry the conventions | code (docs) |
| `task ss:hygiene:entry-files` fails with `docs/index.md not found` | `ls docs/index.md` | The Map Pattern is enforced but the map file doesn't exist. Common after migrating an old repo into slopstopper, OR if the install ran on a directory that already had `README.md`/`AGENTS.md` (which suppresses the entry-file scaffold) but no `docs/` | The report ships a minimal `docs/index.md` template — write it to `docs/index.md` and add one `docs/<category>/README.md` per row of the table. Or disable: `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml` AND `workflows.disabled` the three docs-* workflows | code (docs) OR tune |
| `git push` is blocked by a slopstopper pre-push hook (output mentions `ss:hygiene:test`) | Re-run the exact gate: `task ss:hygiene:test` (or `mise exec -- task ss:hygiene:test`) — it's the same command the hook runs | A hygiene check is genuinely red; the pre-push hook (`.githooks/pre-push`, wired via `core.hooksPath`) runs the static hygiene subset before every push | Fix the failing hygiene check via its row above, then push. To bypass a single push, `git push --no-verify`. To remove the gate entirely, unset `git config --unset core.hooksPath` (or reinstall with `--no-hooks`) | code (per failing check) |
| A slopstopper pre-push hook prints `mise/task not found — skipping` (or doesn't run at all) | `command -v mise; git config --get core.hooksPath` | mise isn't activated in the shell git spawned the hook from, or `core.hooksPath` was never wired | Activate mise (https://mise.jdx.dev/getting-started.html); confirm `core.hooksPath` is `.githooks` (`git config core.hooksPath .githooks` if missing). The hook goes through `mise exec` on purpose — git hooks don't source your profile | config (environment) |
| `task ss:reliability:smoke` fails: `expected /og-image.png to return 200` or wrong CORP header | `cat .slopstopper.yml \| grep -A2 smoke:` then `curl -I http://localhost:8080$(yq '.smoke.og_image_path' .slopstopper.yml)` | Site doesn't have a site-wide og-image at the configured path, OR local server isn't applying prod headers | Either (a) add the og-image at the configured path with `Cross-Origin-Resource-Policy: cross-origin`, OR (b) set `smoke.og_image_path: ''` in `.slopstopper.yml` to skip the assertion (use this if you ship per-post share images instead) | config OR code |
| Reliability or DAST tasks fail at "Start local server" / connection refused | `ls .ss/server.js` | No server on `localhost:8080` | (a) start the installed shim: `node .ss/server.js &` (it serves the built output and applies `public/_headers` per request), OR (b) point each workflow at a deployed URL via the `*_TEST_URL` env vars | code |
| `slopstopper run reliability:<check>` audits only `/` when you expected the full sitemap, or audits `/` on a PR you expected to skip | Run `slopstopper discover <check> --event=<event>` (events: `local`, `pr`, `main`, `cron`) to see the resolved page list | `reliability.coverage.<event>` is in hand-list mode (default) instead of `sitemap` / `changed` | Opt into `sitemap` on `main`/`cron` or `changed` on `pr` in `.slopstopper.yml` (see `.slopstopper.yml.example`). The check itself is fine — discovery is the lever. | config |
| `task ss:security:dast` reports `Content Security Policy (CSP) Header Not Set`, `X-Frame-Options Missing`, `Cross-Origin-*-Policy Missing` | Inspect headers: `curl -I http://localhost:8080/` | Site has no security headers configured | Add headers via the platform (Cloudflare: `public/_headers`; Vercel: `vercel.json`; Netlify: `_headers` or `netlify.toml`). Baseline below | code |
| `task ss:security:dast` reports a CSP finding on a page that genuinely needs the relaxation (Giscus, GTM, etc.) | The page legitimately loads a third-party script/iframe that the strict CSP blocks | Per-path CSP relaxation is real and needs documenting | `docs/security/CSP_EXCEPTIONS.md` under `## Exceptions` with a `### /path` heading (glob patterns supported). The DAST gate swallows CSP findings only on documented paths | suppress |
| `task ss:security:dast` reports a ZAP rule that's structurally wrong for this target (SRI on rotating GTM script; SQL Disclosure on blog posts with code blocks) | The flagged finding is genuinely wrong for content-heavy sites | ZAP heuristic doesn't fit | `.zap/rules.tsv` with the plugin ID marked `IGNORE` and a `# why` comment | suppress |
| `task ss:reliability:accessibility` reports `color-contrast`, `link-in-text-block`, or `label-title-only` on DOM that belongs to a third-party widget (cookie banner, chat, search UI, embedded video) | The failing HTML belongs to a runtime-injected widget, not your source | Widget injects its stylesheet at runtime after your CSS — wins on load order. The page owns the violations regardless of authorship | Scope CSS overrides to the widget's root class; use `!important` (runtime-injected styles can't be beaten on specificity alone if loaded last); add `text-decoration: underline` for `link-in-text-block`; add `aria-label` via small post-init script for inputs missing labels | code (CSS / JS) |
| `ss-security-vulnerability-new-check.yml` fails with `Dependency review is not supported on this repository` | Repo Settings → Code security and analysis → Dependency graph status | `actions/dependency-review-action` needs GHAS on a private repo OR Dependency Graph enabled on a public repo | Toggle the setting (admin action), OR delete the workflow | repo-admin OR delete check |
| `ss-security-vulnerability-new-check.yml` fails citing a **denied licence** (e.g. `GPL-3.0` / `LGPL` / `AGPL`) on a new dependency | Read the PR comment — it names the dependency and its SPDX licence | A newly-added dependency carries a copyleft licence the gate denies (real licence-policy hit, not a CVE) | Swap to a permissively-licensed alternative, OR if the licence is acceptable for your project edit the `deny-licenses` (SPDX) list in `ss-security-vulnerability-new-check.yml`. See `docs/security/README.md` → Dependency Vulnerability Scanning | code OR tune |
| `task ss:security:vulnerability:all` reports different findings on CI vs locally (or fails one side but not the other) | `trivy --version` on both sides AND check local DB age: `cat ~/Library/Caches/trivy/db/metadata.json \| jq .UpdatedAt` (macOS) or `~/.cache/trivy/db/metadata.json` (Linux) | Trivy DB freshness drift (~24h cache TTL; CI cold-starts on a fresh DB every run) OR binary version drift (CI uses latest from apt; local install may be older) | `trivy clean --vuln-db && task ss:security:vulnerability:all` to match CI's cold-start; `brew upgrade trivy` (or equivalent) if binary versions differ. See `docs/security/README.md` → Local/CI Parity | environment |
| `ss-hygiene-auto-label-pr.yml` fails with `The config file was not found at .github/labeler.yml` | `ls .github/labeler.yml` | A pre-`install.sh`-seeding install OR you deleted the seeded file | Re-run `install.sh` to re-seed (it won't overwrite an existing file), or tune the seeded labeler.yml's globs to match your repo's directory structure | config |
| `task ss:hygiene:complexity` fails with `function(s) exceed CCN <n>` and the function is genuinely well-factored | Read `.ss/reports/complexity/complexity-report.md` — is it actually complex or just a long flat dispatch/validation table? Note the check now **fails locally and in the pre-push hook exactly as in CI** (one exit code — no CI-only gate) | The `max_ccn` ceiling (default 15) is too tight for this function's shape | Refactor to reduce branching, OR raise `hygiene.complexity.max_ccn` in `.slopstopper.yml` with a `# why` note (10 = McCabe-strict, 15 = default) | code OR tune |
| `task ss:reliability:llms-txt` fails with `not reachable` / `Missing H1 title` / `No markdown links` | Read `.ss/reports/llms-txt/llms-txt-report.md`; `curl -I http://localhost:8080/llms.txt` | No `/llms.txt` published, OR the file exists but isn't a valid llmstxt.org map (missing `# <name>` H1 or any `[label](url)` link) | Add/repair `<app-root>/llms.txt`: start with `# <name>`, a `> summary` line, then `## Section` headings with markdown links. See `docs/reliability/LLMS_TXT.md` and `app/llms.txt` as the canonical example | code (content) |
| `task ss:reliability:llms-txt` fails only with `Link not reachable` under `--check-links` | Read the report's link-check table | A link inside llms.txt 404s, OR `reliability.llms_txt.check_links: true` is auditing links behind auth/rate-limits | Fix the dead link, OR set `reliability.llms_txt.check_links: false` in `.slopstopper.yml` (default) to keep link resolution advisory | code (content) OR tune |
| `task ss:reliability:robots-txt` fails with `de-indexes the entire site` | Read `.ss/reports/robots-txt/robots-txt-report.md`; `curl -s http://localhost:8080/robots.txt` | `User-agent: *` has a blanket `Disallow: /` — usually a staging config leaked into production, which hides the whole site from search | Remove/narrow the `Disallow: /` in `<app-root>/robots.txt`. If blocking everything is genuinely intended (private staging), set `reliability.robots_txt.allow_disallow_all: true` in `.slopstopper.yml` | code (content) OR tune |
| `task ss:reliability:robots-txt` fails with `No Sitemap:` / (under `--require-llms`) `No Llms:` | Read the report; `curl -s http://localhost:8080/robots.txt` | robots.txt lacks a `Sitemap:` pointer (hard-fail), or an `Llms:` pointer with `require_llms: true` set | Add `Sitemap: https://<host>/sitemap.xml` (and `Llms: https://<host>/llms.txt`) to `<app-root>/robots.txt`. See `docs/reliability/ROBOTS_TXT.md` and `app/robots.txt` as the canonical example, OR set `reliability.robots_txt.require_llms: false` (default) | code (content) OR tune |
| `task ss:reliability:sitemap` fails with `missing from sitemap.xml` or `Stale sitemap entry (unreachable …)` | Read `.ss/reports/sitemap/sitemap-report.md`; `curl -s http://localhost:8080/sitemap.xml`; compare the report's crawled-vs-sitemap paths | The sitemap has drifted from the routes: a reachable page isn't listed (incompleteness), or a `<loc>` 404s (a deleted page's stale entry) | **Durable fix — generate, don't hand-patch:** emit `sitemap.xml` from the route inventory at build time (framework sitemap integration, or a build-time endpoint that iterates content) so it can't drift. Stopgap: add the missing page / remove the dead `<loc>` in `<app-root>/sitemap.xml`. See `docs/reliability/SITEMAP.md` and `app/sitemap.xml` as the canonical example | code (content) |
| `task ss:reliability:sitemap` reports an `orphan` note, or `not listed in llms.txt` | Read the report — orphans and llms gaps are advisory (notes) unless escalated | A sitemap entry nothing internally links to (orphan), or a reachable page absent from the curated `llms.txt`. Both are advisory by default — a hard-fail only under `--strict-orphans` / `--require-llms-complete` (or the config equivalents) | Real gap → add an internal link / list the page (ideally by regenerating — see the row above). Intentional → leave advisory, or if you escalated it, set `reliability.sitemap.allow_orphans: true` (default) / `require_llms_complete: false` (default) in `.slopstopper.yml` | code (content) OR tune |
| Lighthouse CWV check fails Performance / LCP / TBT / CLS thresholds | `CWV_URL=<URL> slopstopper run reliability:cwv` and read the report's audit-level breakdown | Site has a genuine perf issue OR the threshold doesn't match the target's nature | Real → optimise (image sizing, render-blocking JS, etc.). Threshold mismatch → tune in `.ss/lighthouserc.json` (adopter override) with the change documented in `docs/reliability/README.md` Core Web Vitals section | code OR tune |
| A check's behaviour disagrees with what slopstopper-cli ships upstream, OR a check behaves differently locally than in CI | `slopstopper --version`; compare against the repo's pin (`"pipx:slopstopper-cli"` in `mise.toml`) — they should match | The CLI is **pinned**; behaviour matching the pin (not latest) is correct. A local ≠ CI mismatch usually means mise isn't activated in your shell (so a stale global `slopstopper` is on PATH) or you haven't run `mise install` | Run `mise install` in the repo and ensure mise is [activated](https://mise.jdx.dev/getting-started.html), or re-run `install.sh` (honours the pin). To intentionally move to newer behaviour: `install.sh --upgrade-cli` (or `--cli-version X.Y.Z`), which rewrites the pin — commit it so CI matches. Confirm with `slopstopper --version`. | environment |
| A slopstopper-emitted issue lacks the `slopstopper` label or `<!-- slopstopper:check=… -->` body marker | `gh issue view <n> --json labels,body \| jq '.labels[].name, .body'` | Pre-PR-261 / pre-marker era — the issue was created before the brand label + body marker landed. Newer dedup paths (e.g. global workflow-failure dedup) won't recognise it | Trigger a re-failure on `main` so `emit_issue` regenerates the body (auto-migrates the marker), OR close manually if the underlying finding is already resolved | environment |

### Baseline security headers (for the missing-headers row above)

For a static site using GTM:

```
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://*.googletagmanager.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://*.google-analytics.com https://*.googletagmanager.com; font-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

Tune `script-src` / `connect-src` to the actual third parties the site loads. `'unsafe-inline'` for `script-src` is the pragmatic call when the build tool injects inline scripts (Astro `define:vars`, GTM bootstrap) and you can't easily add nonces; tighten to nonces or hashes if the framework supports them. Any `'unsafe-inline'` retention should be documented in `docs/security/CSP_EXCEPTIONS.md` under `### /*` so the DAST gate swallows the inevitable site-wide CSP finding.

## Step 6 — When the fix is broader than one check

If multiple checks fail with the same root cause, batch-fix once and re-run all affected checks instead of fixing each in isolation. Common patterns:

- **Node version pin bump** → fixes Core Web Vitals + Accessibility + SEO + Playwright + Smoke + DAST in one edit.
- **Adding `public/_headers` with a security-headers baseline** → fixes DAST's missing-header alerts AND the smoke spec's CORP header check.
- **Setting up the Map Pattern** (`docs/index.md` + per-category READMEs + the `🗺️ Documentation map` callout in README.md / AGENTS.md + a thin CLAUDE.md) → fixes docs-structure + docs-size + docs-accuracy + entry-files (pointer rule) together. The `entry-files` report ships paste-ready snippets for every pointer it expects.
- **Moving the `slopstopper-cli` pin** → if a default tuning was widened upstream, multiple checks go green at once. The CLI is pinned in `mise.toml` (`"pipx:slopstopper-cli"`); bump it with `install.sh --upgrade-cli` (rewrites the pin via `mise use` + installs + commit so CI matches), then re-run the aggregates. Don't install slopstopper-cli globally by hand — that drifts off the committed pin without updating CI.

The aggregates make this fast: `task ss:hygiene:test` re-runs every hygiene check; `task ss:security:scan` re-runs every security check. Both are just sequenced `slopstopper run …` calls under the hood, so adopters who skip the Taskfile can chain the CLI invocations directly.

## Step 7 — When to delete the check instead of fixing it

**First ask whether it's a whole class, not one check.** If a repo is an API or a library, the browser-and-SEO checks don't belong there as a group — that's what `profile:` is for (`slopstopper profile list`), and it's the maintained answer: the profile survives a re-run, is visible in review, and reverses cleanly if the repo grows a web surface later. Reach for deletion only for a check that a profile doesn't cover.

A small number of checks are slopstopper.dev-specific and have no place on a target that doesn't share the pattern they guard. Delete them, or list them under `workflows.disabled` in `.slopstopper.yml` (the config-driven form is easier to audit and survives a clone-and-rebuild). Either way `.ss/.workflows-installed` remembers the deletion, so re-running `install.sh` won't bring them back.

Deletable on legitimate grounds:

- **`ss-hygiene-csp-exceptions-check.yml`** — guards `worker/headers.json`, which only slopstopper.dev uses. (Already dropped by `profile: library`; and harmless under any profile while `headers.source` is null.)
- **`ss-hygiene-docs-accuracy-check.yml` + `docs-size-check.yml` + `docs-structure-check.yml`** — only if the target genuinely won't follow the Map Pattern. If you're keeping docs at all, set up the Map Pattern instead (see `slopstopper-install` Step 5).
- **`ss-security-vulnerability-new-check.yml`** — if Dependency Graph / GHAS can't be enabled.
- **`ss-security-dast-check.yml`** — only if nothing is deployed at all. On an API it works via `api.openapi.spec`; deleting it because "DAST is for websites" removes the repo's only dynamic security scanning.
- **The four API workflows** (`ss-reliability-api-health-check.yml`, `ss-reliability-api-latency-check.yml`, `ss-security-api-headers-check.yml`, `ss-hygiene-openapi-check.yml`) — only if the repo serves no API at all. They're already inert unconfigured, so deleting them is tidiness rather than necessity; `profile: library` drops all four as part of a coherent set, which is the better lever.

Don't delete a check just because it's failing. The bar is *"this check has nothing meaningful to guard on this target"*, not *"this check is inconvenient"*.

## When to hand off

- **First-time install** on a new repo → `slopstopper-install` (you're here because that skill handed off mid-install — go back when this check is green).
- **Refreshing an existing install** → `slopstopper-install` (covers both first install and refresh — its mode-detection branch routes you to the refresh-only section). If the failing check is new since the last refresh, this skill is still the right place; `slopstopper-install`'s refresh section is for the mechanical "re-run installer + re-apply customizations" loop.

## Maintaining this skill when slopstopper changes

Update this skill when:

- A new workflow is added under `slopstopper/.github/workflows/ss-*.yml` → add a row to Step 2's workflow→CLI table and a row to Step 5's gotcha table (with a forward-looking diagnostic step and fix location, not citing the install that surfaced it).
- A workflow is renamed or removed → update both tables.
- A check is added or renamed in `cli/slopstopper/checks/__init__.py`'s `REGISTRY` → update Step 2's table (CLI column AND Taskfile-shim column, since the shim mirrors the CLI name). The new check must also define a `META` dict in its module — the `test_every_check_has_meta` pytest enforces this. PR-comment-only checks need at least `report_path` + `comment_discriminator`; checks that open main-branch issues also need `issue_title` / `issue_labels` / `issue_followup` / `issue_close_comment` (see `cli/slopstopper/emit.py` docstring for the schema).
- A `task ss:*` shim is renamed in `slopstopper/Taskfile.ss.yml` → update Step 2's Taskfile-shim column.
- A new `slopstopper` subcommand ships (e.g. `init`, `inspect`) → mention in the intro and the relevant Step.
- A new suppression mechanism becomes available for an existing check (e.g. a new `.zap/rules.tsv`-shaped file for a different tool) → add a row to Step 4's suppression table.
- A new config-driven knob is added to a check (`config.get("<x>")` in the check module) → add to Step 4's "Config-driven knobs" table, with the default mirroring `.slopstopper.yml.example`.
- A profile is added, or a profile's `disables` list changes in `cli/slopstopper/data/profiles.json` → update the two profile rows in Step 5's gotcha table (they name the checks each profile drops) and the profile note in Step 7.
- A knob is added under `api:` in `.slopstopper.yml.example` → update the API rows in Step 5's gotcha table, which name the specific knob that resolves each symptom.
- The PR comment shape changes (`emit --target pr-comment`, `--status`, `--on-pass=delete`, or `ss-pr-summary.yml`) → update Step 1's "Fastest route" section and the three comment-layer rows in Step 5's gotcha table.

The AGENTS.md "When making changes" table in the slopstopper repo flags this skill alongside `slopstopper-install` whenever a change of the above kind ships.
