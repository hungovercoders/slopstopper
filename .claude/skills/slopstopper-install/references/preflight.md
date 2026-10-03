# Step 1 — Pre-flight

> Part of the `slopstopper-install` skill. `SKILL.md` says when to read this; it is not loaded until then.

## Step 1 — Pre-flight: read the target repo before installing

**First: what shape is this repo?** Ask before anything else, because it decides which checks are even relevant. The eight browser-and-SEO reliability checks (smoke, accessibility, Core Web Vitals, SEO, broken links, llms.txt, robots.txt, sitemap) assume HTML, a DOM and a public web surface — on an HTTP API they don't no-op, they build and audit nothing and go **red**. Pick a profile up front:

| Shape | Profile | Install with | Gets |
| ----- | ------- | ------------ | ---- |
| Serves HTML to a browser | `ui` (default) | `bash install.sh` | everything (24 checks) |
| JSON/gRPC API, no browser surface | `api` | `bash install.sh --profile api` | 16 — static layer, the four API checks (`api-health`, `api-latency`, `api-headers`, `openapi`) and DAST via ZAP's OpenAPI mode; no browser checks |
| Library, CLI or package, nothing deployed | `library` | `bash install.sh --profile library` | 10 — the static layer only |

The four API checks (`reliability:api-health`, `reliability:api-latency`, `security:api-headers`, `hygiene:openapi`) ship under `ui` as well as `api`, and stay inert until `api.health.path` / `api.latency.paths` / `api.headers.paths` / `api.openapi.spec` are set — so a UI repo with API routes (Next.js handlers, Astro endpoints) gets them without having to find `workflows.enabled`. Configuring them is Step 4.

Note the odd one out: `hygiene:openapi` is the only **hygiene** check that needs a URL, since drift means the spec measured against the thing it documents. That is why `library` — which drops everything URL-driven — is the one profile without a complete static layer.

`slopstopper profile detect` (or the installer's own suggestion in its post-install output) reads the repo's framework configs, HTML, OpenAPI specs and server-framework deps and proposes one — treat it as a prompt to confirm with the user, not an answer. When in doubt pick the wider profile: a check that runs and goes red is visible; one that's silently off is not. `slopstopper profile list` prints the exact workflow set each one drops, and `workflows.enabled` in `.slopstopper.yml` takes an individual check back (an API that also serves a docs site and wants `broken-links`, say).

A mixed repo — an API *and* its marketing site in one tree — is a `ui` repo: keep the full set and point the dynamic checks at the site.

Then, whatever the shape, learn enough about the target to predict where it'll bite you:

0. **Are `mise` and `python3` available?** Both hard prereqs — `install.sh` errors out without them. mise is the toolchain manager: it pins `slopstopper-cli` (and `task`) in `mise.toml` and installs them, activating the pinned versions per-directory so the active `slopstopper` follows the repo (this is what stops a single global binary from drifting between repos). mise's pipx backend needs `python3` on PATH. The CLI runs every check, so no mise/Python = no slopstopper. Make sure mise is [activated](https://mise.jdx.dev/getting-started.html) in the shell so the pinned binary lands on `$PATH` (CI handles this via `jdx/mise-action`).

1. **Does the target have an existing `Taskfile.yml`?** If yes, the installer prints include instructions instead of overwriting — you (or the user) need to manually add:
   ```yaml
   includes:
     ss:
       taskfile: ./Taskfile.ss.yml
   ```
   to the existing Taskfile.

2. **Does the target already have GitHub Actions workflows?** Slopstopper adds up to 27 new `ss-*.yml` workflows — 24 checks (16 under `--profile api`, 10 under `--profile library`) plus three that ship under every profile: `ss-pr-summary.yml` (the single status comment), `ss-workflow-failure-issue.yml` (raises an issue when a check fails on main) and the doc-updater. They're all `ss-`-prefixed so they group in the Actions UI, but the user should know they're getting that many checks running on every PR.

3. **What `engines.node` does the target need?** Node is pinned in `mise.toml` (`[tools] node`) — mise installs it locally and the workflows get the same version from that pin via `jdx/mise-action` (no `setup-node` step, no repo variable). `install.sh` seeds `node = "20"` on first install and leaves any existing node pin / `.node-version` / `.nvmrc` alone. If the target needs Node 22+ (Astro 6, recent Next, SvelteKit), run `mise use node@22`. One source of truth; survives `install.sh` re-runs.

4. **What's the deploy model and serve story?** Reliability/DAST workflows can target either a deployed URL or a local build served on port 8080 by `slopstopper serve` (a static server bundled in the CLI). If the target is anything other than a static site (Astro, Next, SvelteKit, a backend app) you'll need either to replace the workflow's build-and-serve steps with the app's own start command or to point the workflows at a deployed environment. Pair this with the deploy model — Cloudflare Workers / Vercel / Netlify / GH Pages each call for a different answer.

5. **How does the target manage security headers?** The CSP-exceptions drift check reads from whatever you name in `.slopstopper.yml` `headers.source` (with `headers.format`). Shipped adapters: `json` (for `[{for, values}]` JSON files like slopstopper.dev's `worker/headers.json`), `cloudflare-text` (Cloudflare/Netlify native `_headers` text format), `auto` (infer from extension). Set `source: null` to skip the check entirely — adopters managing headers via framework middleware / `vercel.json` / etc. do this. The installer seeds `.slopstopper.yml` with `source: null` so first-PR is green even before you configure anything; you opt the check in by pointing it at your real headers file.

6. **Does the target follow the Map Pattern for docs?** Three workflows — `ss-hygiene-docs-accuracy-check.yml`, `ss-hygiene-docs-structure-check.yml`, `ss-hygiene-docs-size-check.yml` — require a `docs/` directory with an `index.md` listing categories (each as a subdirectory with its own `README.md`). A fourth — `ss-hygiene-entry-files-check.yml` — also enforces the pointer side of the pattern: README.md and AGENTS.md must link to `docs/index.md`, CLAUDE.md must be a thin pointer to AGENTS.md, and `docs/index.md` itself must exist (unless `hygiene.entry_files.require_map_pointer: false` in `.slopstopper.yml`). Two valid choices: set up the Map Pattern (see Step 5) or disable both halves (`workflows.disabled` the three docs-* workflows AND set `require_map_pointer: false`). A half-built `docs/` directory will fail the structure check until the tree matches the index; a docs/ directory with no pointers from the entry files will fail the entry-files check.

7. **Does the target serve a site-wide `/og-image.png` with `Cross-Origin-Resource-Policy: cross-origin`?** The slopstopper Playwright smoke test — bundled in the CLI, or your `.ss/tests/smoke.spec.ts` if you ejected one with `slopstopper templates eject tests/smoke.spec.ts` — asserts that `/og-image.png` returns 200, has `Content-Type: image/png`, and the CORP header set to `cross-origin` (so social platforms can embed it). Targets that use per-post share images instead won't have it. Either add a 1200×630 `og-image.png` at the site root with CORP configured for that path (Astro/Cloudflare adapter respects `public/_headers`), or set `smoke.og_image_path: ''` in `.slopstopper.yml` to skip the assertion.

8. **Existing `package.json` devDeps that might collide?** Slopstopper merges in `@axe-core/playwright`, `@lhci/cli`, `@playwright/test`, `markdownlint-cli`. Spot collisions ahead of time.

9. **Does the target have its own README/AGENTS/CLAUDE entry files?** The `ss:hygiene:entry-files` check enforces two things: a 1500-word budget on each, AND the Map Pattern pointer rule (README.md + AGENTS.md link to `docs/index.md`; CLAUDE.md is a thin pointer to AGENTS.md). If any of the three are missing, `install.sh` seeds a minimal pointer-shaped scaffold from `cli/slopstopper/data/templates/entry-files/` (never overwrites existing files). If they exist but don't link the map, the check's report at `.ss/reports/entry-files/entry-file-size-report.md` emits a paste-ready snippet for each violation — apply it during the Step 7 local loop. Most repos with existing entry files need 1-3 small additions; flag any that are bloated or that lack the pointer up-front.

10. **Is GitHub Advanced Security (or public-repo Dependency Graph) enabled?** The `ss-security-vulnerability-new-check.yml` workflow uses `actions/dependency-review-action`, which requires either GHAS on a private repo or the Dependency Graph setting enabled on a public repo. Otherwise the check errors with `Dependency review is not supported on this repository`. Repo-admin setting — flag to the user.

11. **Does the target already have a `.github/labeler.yml`?** Slopstopper ships the auto-label workflow (`ss-hygiene-auto-label-pr.yml`) but not the config — labels are repo-specific. Without one, the check errors with `The config file was not found`. Plan to ship a labeler config mapping the target's directory structure to labels.

12. **Is the target a private repo?** Two things to flag, not one. First, some workflows post issues, comments, and PR labels — they need `issues: write`, `pull-requests: write` permissions, usually fine but check if the org restricts this. Second, and more important: **GitHub Actions minutes are free on public repos but billed on private ones.** The full suite runs 24 checks on every PR, and the scheduled reliability/smoke runs add recurring minutes on top of that — the heavier dynamic checks (Playwright, Lighthouse CI, ZAP-in-Docker) are the expensive ones. On a public repo this is a non-issue; on a private repo with a tight minutes budget, slopstopper may not be a good fit as-is. Call the cost out explicitly during pre-flight so the user decides with eyes open — and consider a partial adoption (Step 9) rather than the full suite.

13. **May this repo send data to third parties?** Ask the user directly — don't infer it. Out of the box nothing that identifies the repo leaves the runner; two checks only do so when opted in, and an employer or a private repo often can't (`docs/architecture/TOOLCHAIN.md` lists every tool and what it sends):
    - **SAST (Semgrep)** is off until `security.sast.rules` is set. `auto` uses Semgrep's Registry rules — Semgrep receives the repo URL and usage metrics (no source code or findings). A list of local rule files runs offline and sends nothing, but the user has to supply the rules. Neither → SAST stays off: say so plainly, since the check passes as a skip.
    - **Public Lighthouse reports** (`reliability.cwv.public_report: true`) put each Core Web Vitals report on public temporary storage, readable by anyone with the link, and link it from the PR comment. Off by default.
    Record the answers; Step 4 writes them into `.slopstopper.yml`.

Report what you found to the user before running the installer. The Node-version question and the deploy-model question together drive the largest chunk of first-PR red checks — call them out specifically.
