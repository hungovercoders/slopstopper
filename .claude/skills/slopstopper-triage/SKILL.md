---
name: slopstopper-triage
description: Diagnose and fix a failing slopstopper check. Use when a user reports a specific slopstopper workflow or task is failing — SAST, secrets, complexity, docs-accuracy, docs-size, docs-structure, entry-files, CSP exceptions, auto-label, smoke, accessibility, Core Web Vitals, SEO, broken links, DAST, dependency review, or the workflow-failure tracker. Maps each check to the local task that reproduces it, the report files it generates, the typical root-cause categories (real finding / false positive / threshold too tight), and a per-symptom gotcha table with diagnostic steps and the file the fix lives in. For first-time install OR refreshing an existing install use slopstopper-install.
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

## Step 2 — Reproduce locally

`task ss:*` is the canonical local interface — same shipped Task in the target's repo as CI uses. Run `task ss:<category>:<check>` and you get the same code path, same exit codes, same reports. The local loop is an order of magnitude faster than pushing to CI per iteration. If the target was installed with `--no-task`, fall back to `slopstopper run <category>:<check>` directly — works identically.

| Workflow | Canonical (Task) | Underlying CLI | Needs URL? | Needs build? | Needs Docker? |
|---|---|---|---|---|---|
| `ss-security-sast-check.yml` | `task ss:security:sast` | `slopstopper run security:sast` | – | – | – |
| `ss-security-secrets-check.yml` | `task ss:security:secrets` | `slopstopper run security:secrets` | – | – | – |
| `ss-security-vulnerability-all-check.yml` | `task ss:security:vulnerability:all` | `slopstopper run security:vulnerability:all` | – | – | – |
| `ss-security-vulnerability-new-check.yml` | (CI-only — Dependency Review action) | – | – | – | – |
| `ss-security-dast-check.yml` | `task ss:security:dast -- <URL>` | `slopstopper run security:dast <URL>` | ✓ | ✓ (if local) | ✓ |
| `ss-hygiene-complexity-check.yml` | `task ss:hygiene:complexity` | `slopstopper run hygiene:complexity` | – | – | – |
| `ss-hygiene-csp-exceptions-check.yml` | `task ss:hygiene:csp-exceptions` | `slopstopper run hygiene:csp-exceptions` | – | – | – |
| `ss-hygiene-docs-accuracy-check.yml` | `task ss:hygiene:docs-accuracy` | `slopstopper run hygiene:docs-accuracy` | – | – | – |
| `ss-hygiene-docs-size-check.yml` | `task ss:hygiene:docs-size` | `slopstopper run hygiene:docs-size` | – | – | – |
| `ss-hygiene-docs-structure-check.yml` | `task ss:hygiene:docs-structure` | `slopstopper run hygiene:docs-structure` | – | – | – |
| `ss-hygiene-entry-files-check.yml` | `task ss:hygiene:entry-files` | `slopstopper run hygiene:entry-files` | – | – | – |
| `ss-hygiene-auto-label-pr.yml` | (CI-only — needs PR context) | – | – | – | – |
| `ss-reliability-smoke-tests.yml` | `task ss:reliability:smoke -- <URL>` | `slopstopper run reliability:smoke <URL>` | ✓ | ✓ (if URL is local) | – |
| `ss-reliability-accessibility-check.yml` | `task ss:reliability:accessibility -- <URL>` | `slopstopper run reliability:accessibility <URL>` | ✓ | ✓ | – |
| `ss-reliability-core-web-vitals.yml` | `task ss:reliability:cwv -- <URL>` | `slopstopper run reliability:cwv <URL>` | ✓ | ✓ | – |
| `ss-reliability-seo-check.yml` | `task ss:reliability:seo -- <URL>` | `slopstopper run reliability:seo <URL>` | ✓ | ✓ | – |
| `ss-reliability-broken-links-check.yml` | `task ss:reliability:broken-links -- <URL>` | `slopstopper run reliability:broken-links <URL>` | ✓ | ✓ | – |
| `ss-workflow-failure-issue.yml` | (CI-only — operational, runs on workflow_run) | – | – | – | – |

For dynamic checks (`URL ✓`): pass the URL as a bare-positional arg after `--` (Task) or directly (CLI). Pointing at `http://localhost:8080` with `node .ss/server.js` serving the built site is the fastest local loop.

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
| SAST (Bandit, if used) | `# nosec` inline | Inline |
| DAST (OWASP ZAP) — CSP findings | `docs/security/CSP_EXCEPTIONS.md` `## Exceptions` → `### /path` heading (glob patterns supported: `/*`, `/blog/*`) | Per-path |
| DAST — other rule false positives | `.zap/rules.tsv` → `<plugin-id>\tIGNORE\t# why` | Per-rule, site-wide |
| Accessibility (axe-core) | `disabledRules` in the spec, or scope the spec to exclude the offending selector | Per-rule or per-element |
| Vulnerability (Trivy) | `.trivyignore` with the CVE ID + a `# why` line | Per-CVE |
| Complexity (lizard) | `# nolint` on the function, or raise the threshold in `docs/hygiene/README.md` complexity config block | Per-function or repo-wide |

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

Tunings that are NOT yet config-driven (require code/file edits):

- `docs/hygiene/README.md` complexity config — lizard cyclomatic complexity caps.
- `.ss/lighthouserc.json` (or the bundled `cli/slopstopper/data/lighthouserc.json`) — Core Web Vitals thresholds. Edit the `.ss/` copy if you want adopter-side persistence; the CLI prefers it over the package-data fallback.

Tuning is a real decision — when you raise a threshold, leave a `# why` comment in `.slopstopper.yml` so the next maintainer doesn't roll it back. Don't tune to silence noise; tune to match a deliberate design decision.

## Step 5 — Per-symptom gotcha table

Common failures, with diagnostic step and the file the fix lives in. Categories use the Step 4 vocabulary: `code` / `suppress` / `tune`.

| Symptom | Diagnostic step | Cause | Fix location | Category |
|---|---|---|---|---|
| `Node.js vXX is not supported by Astro!` on `npm run build` across every reliability/Playwright workflow | Check `package.json` `engines.node` vs `.slopstopper.yml` `node_version` AND the `SLOPSTOPPER_NODE_VERSION` repo variable | Workflows read `${{ vars.SLOPSTOPPER_NODE_VERSION \|\| '20' }}`; the repo variable isn't set | Set `node_version:` in `.slopstopper.yml` AND `gh variable set SLOPSTOPPER_NODE_VERSION --body 22` (or your version) | config |
| `task ss:hygiene:complexity` errors with compression-tool usage text instead of cyclomatic output | `which lizard` returns a Homebrew `lz4-lizard` path | PATH collision: `lz4-lizard` compression utility shadows the Python `lizard` | `pip install --upgrade lizard`; reorder PATH so the Python `lizard` wins, or invoke `python3 -m lizard` | code (environment) |
| `task ss:security:secrets` flags an example connection string, sample API key, or emulator config | Open the flagged file: is it real credential or tutorial sample? | gitleaks regex matches sample content as a generic API key | Real → revoke + scrub history (code). Sample → path-scoped allowlist in `.gitleaks.toml` with `# why` | code OR suppress |
| `task ss:hygiene:docs-accuracy` flags backtick-quoted filenames that don't resolve | Grep the docs for the bare filename — does the file exist anywhere under the repo? | Old docs reference renamed/moved files, or use bare filenames the resolver can't find | Fix the link in the doc; use repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) | code (docs) |
| `task ss:hygiene:docs-structure` fails with `❌ docs/ directory not found` or category mismatch | `ls docs/` against the table in `docs/index.md` | Target doesn't follow the Map Pattern, or has an undocumented dir | Set up the Map Pattern (`slopstopper-install` Step 5 has the template) OR delete the three docs-* workflows | code (docs) OR delete check |
| `task ss:hygiene:csp-exceptions` reports "no headers.source configured" with exit 0 | `cat .slopstopper.yml \| grep -A2 headers:` | `.slopstopper.yml` `headers.source` is null (the seeded default) | If you want the check active, set `headers.source` to your headers file (e.g. `public/_headers`) and `headers.format` to match (`cloudflare-text` for `_headers` files, `json` for JSON arrays, `auto` to infer). Otherwise this is harmless. | config |
| `slopstopper run hygiene:csp-exceptions` reports "Unknown headers.format" | Run `python3 -c "from slopstopper import headers_adapters; print(list(headers_adapters.ADAPTERS.keys()))"` | `.slopstopper.yml` `headers.format` doesn't match a shipped adapter | Set `headers.format` to one of the listed adapter names or `auto`. If you need a format slopstopper doesn't ship, add a module under `cli/slopstopper/headers_adapters/` and register it in `__init__.py`'s `ADAPTERS`. | config (or new adapter) |
| `task ss:hygiene:entry-files` fails with one of README/AGENTS/CLAUDE over 1500 words | Run the task — the report names the file + word count | Entry file has bloated with content that belongs under `docs/<category>/` | Move the bulk into the appropriate category README; the entry file should be a pointer | code (docs) |
| `task ss:hygiene:entry-files` fails with `missing_map_pointer` on README.md or AGENTS.md | Read `.ss/reports/entry-files/entry-file-size-report.md` — the "How to fix" section emits a paste-ready `> 🗺️ **Documentation map.** …` callout | Entry file exists but doesn't link `docs/index.md`; the Map Pattern is enforced (`hygiene.entry_files.require_map_pointer` default true) | Paste the snippet near the top of the named file (above any other body content). Confirm with `task ss:hygiene:entry-files`. If the rule genuinely doesn't fit this repo, set `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml` with a `# why` comment | code (docs) OR tune |
| `task ss:hygiene:entry-files` fails with `claude_not_thin_pointer` on CLAUDE.md | Read the report's CLAUDE-specific fix section | CLAUDE.md has substantive content instead of being a thin pointer (no `@AGENTS.md` directive, no link to AGENTS.md) | Replace the file contents with the paste-ready canonical body (the report includes it). Claude Code reads `@AGENTS.md` automatically — keep CLAUDE.md short and let AGENTS.md carry the conventions | code (docs) |
| `task ss:hygiene:entry-files` fails with `docs/index.md not found` | `ls docs/index.md` | The Map Pattern is enforced but the map file doesn't exist. Common after migrating an old repo into slopstopper, OR if the install ran on a directory that already had `README.md`/`AGENTS.md` (which suppresses the entry-file scaffold) but no `docs/` | The report ships a minimal `docs/index.md` template — write it to `docs/index.md` and add one `docs/<category>/README.md` per row of the table. Or disable: `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml` AND `workflows.disabled` the three docs-* workflows | code (docs) OR tune |
| `task ss:reliability:smoke` fails: `expected /og-image.png to return 200` or wrong CORP header | `cat .slopstopper.yml \| grep -A2 smoke:` then `curl -I http://localhost:8080$(yq '.smoke.og_image_path' .slopstopper.yml)` | Site doesn't have a site-wide og-image at the configured path, OR local server isn't applying prod headers | Either (a) add the og-image at the configured path with `Cross-Origin-Resource-Policy: cross-origin`, OR (b) set `smoke.og_image_path: ''` in `.slopstopper.yml` to skip the assertion (use this if you ship per-post share images instead) | config OR code |
| Reliability or DAST tasks fail at "Start local server" / connection refused | `ls .ss/server.js` | No server on `localhost:8080` | (a) start the installed shim: `node .ss/server.js &` (it serves the built output and applies `public/_headers` per request), OR (b) point each workflow at a deployed URL via the `*_TEST_URL` env vars | code |
| `slopstopper run reliability:<check>` audits only `/` when you expected the full sitemap, or audits `/` on a PR you expected to skip | Run `slopstopper discover <check> --event=<event>` (events: `local`, `pr`, `main`, `cron`) to see the resolved page list | `reliability.coverage.<event>` is in hand-list mode (default) instead of `sitemap` / `changed` | Opt into `sitemap` on `main`/`cron` or `changed` on `pr` in `.slopstopper.yml` (see `.slopstopper.yml.example`). The check itself is fine — discovery is the lever. | config |
| `task ss:security:dast` reports `Content Security Policy (CSP) Header Not Set`, `X-Frame-Options Missing`, `Cross-Origin-*-Policy Missing` | Inspect headers: `curl -I http://localhost:8080/` | Site has no security headers configured | Add headers via the platform (Cloudflare: `public/_headers`; Vercel: `vercel.json`; Netlify: `_headers` or `netlify.toml`). Baseline below | code |
| `task ss:security:dast` reports a CSP finding on a page that genuinely needs the relaxation (Giscus, GTM, etc.) | The page legitimately loads a third-party script/iframe that the strict CSP blocks | Per-path CSP relaxation is real and needs documenting | `docs/security/CSP_EXCEPTIONS.md` under `## Exceptions` with a `### /path` heading (glob patterns supported). The DAST gate swallows CSP findings only on documented paths | suppress |
| `task ss:security:dast` reports a ZAP rule that's structurally wrong for this target (SRI on rotating GTM script; SQL Disclosure on blog posts with code blocks) | The flagged finding is genuinely wrong for content-heavy sites | ZAP heuristic doesn't fit | `.zap/rules.tsv` with the plugin ID marked `IGNORE` and a `# why` comment | suppress |
| `task ss:reliability:accessibility` reports `color-contrast`, `link-in-text-block`, or `label-title-only` on DOM that belongs to a third-party widget (cookie banner, chat, search UI, embedded video) | The failing HTML belongs to a runtime-injected widget, not your source | Widget injects its stylesheet at runtime after your CSS — wins on load order. The page owns the violations regardless of authorship | Scope CSS overrides to the widget's root class; use `!important` (runtime-injected styles can't be beaten on specificity alone if loaded last); add `text-decoration: underline` for `link-in-text-block`; add `aria-label` via small post-init script for inputs missing labels | code (CSS / JS) |
| `ss-security-vulnerability-new-check.yml` fails with `Dependency review is not supported on this repository` | Repo Settings → Code security and analysis → Dependency graph status | `actions/dependency-review-action` needs GHAS on a private repo OR Dependency Graph enabled on a public repo | Toggle the setting (admin action), OR delete the workflow | repo-admin OR delete check |
| `task ss:security:vulnerability:all` reports different findings on CI vs locally (or fails one side but not the other) | `trivy --version` on both sides AND check local DB age: `cat ~/Library/Caches/trivy/db/metadata.json \| jq .UpdatedAt` (macOS) or `~/.cache/trivy/db/metadata.json` (Linux) | Trivy DB freshness drift (~24h cache TTL; CI cold-starts on a fresh DB every run) OR binary version drift (CI uses latest from apt; local install may be older) | `trivy clean --vuln-db && task ss:security:vulnerability:all` to match CI's cold-start; `brew upgrade trivy` (or equivalent) if binary versions differ. See `docs/security/README.md` → Local/CI Parity | environment |
| `ss-hygiene-auto-label-pr.yml` fails with `The config file was not found at .github/labeler.yml` | `ls .github/labeler.yml` | A pre-`install.sh`-seeding install OR you deleted the seeded file | Re-run `install.sh` to re-seed (it won't overwrite an existing file), or tune the seeded labeler.yml's globs to match your repo's directory structure | config |
| `slopstopper run hygiene:complexity` flags a function with high cyclomatic complexity and the function is genuinely well-factored | Read the function — is it actually complex or just long-tabular? | Default complexity cap is too tight for this codebase's patterns | Raise the threshold in `docs/hygiene/README.md` complexity section with a `## why` note | tune |
| Lighthouse CWV check fails Performance / LCP / TBT / CLS thresholds | `CWV_URL=<URL> slopstopper run reliability:cwv` and read the report's audit-level breakdown | Site has a genuine perf issue OR the threshold doesn't match the target's nature | Real → optimise (image sizing, render-blocking JS, etc.). Threshold mismatch → tune in `.ss/lighthouserc.json` (adopter override) with the change documented in `docs/reliability/README.md` Core Web Vitals section | code OR tune |
| A check's behaviour disagrees with what slopstopper-cli ships upstream | `slopstopper --version`; compare against the repo's pin (`cli_version` in `.slopstopper.yml`) — they should match | The CLI is **pinned**; behaviour matching the pin (not latest) is correct. If `slopstopper --version` ≠ the pin, a manual `pipx upgrade` drifted the local binary off it | To re-pin without changing the pin: re-run `install.sh` (reinstalls `slopstopper-cli==<cli_version>`). To intentionally move to newer behaviour: `install.sh --upgrade-cli` (or `--cli-version X.Y.Z`), which rewrites the pin — commit it so CI matches. Confirm with `slopstopper --version`. | environment |
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
- **Moving the `slopstopper-cli` pin** → if a default tuning was widened upstream, multiple checks go green at once. The CLI is pinned in `.slopstopper.yml`; bump it with `install.sh --upgrade-cli` (rewrites the pin + reinstalls + commit so CI matches), then re-run the aggregates. Don't `pipx upgrade` by hand — that drifts the local binary off the committed pin without updating CI.

The aggregates make this fast: `task ss:hygiene:test` re-runs every hygiene check; `task ss:security:scan` re-runs every security check. Both are just sequenced `slopstopper run …` calls under the hood, so adopters who skip the Taskfile can chain the CLI invocations directly.

## Step 7 — When to delete the check instead of fixing it

A small number of checks are slopstopper.dev-specific and have no place on a target that doesn't share the pattern they guard. Delete them — `.ss/.workflows-installed` remembers the deletion, so re-running `install.sh` won't bring them back.

Deletable on legitimate grounds:

- **`ss-hygiene-csp-exceptions-check.yml`** — guards `worker/headers.json`, which only slopstopper.dev uses.
- **`ss-hygiene-docs-accuracy-check.yml` + `docs-size-check.yml` + `docs-structure-check.yml`** — only if the target genuinely won't follow the Map Pattern. If you're keeping docs at all, set up the Map Pattern instead (see `slopstopper-install` Step 5).
- **`ss-security-vulnerability-new-check.yml`** — if Dependency Graph / GHAS can't be enabled.

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

The AGENTS.md "When making changes" table in the slopstopper repo flags this skill alongside `slopstopper-install` whenever a change of the above kind ships.
