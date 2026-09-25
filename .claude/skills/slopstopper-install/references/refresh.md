# Refresh-only — diff upstream, re-apply customizations, spot new knobs

> Part of the `slopstopper-install` skill. `SKILL.md` says when to read this; it is not loaded until then.

## Refresh-only — diff upstream, re-apply customizations, spot new knobs

**Skip this section on a first install.** It's relevant only when `.slopstopper.yml` and `.ss/.workflows-installed` both existed in Step 1 (mode-detection) — i.e. the installer just ran in-place over an existing slopstopper install.

`install.sh` is idempotent but **not transactional** — every workflow YAML in `GENERIC_WORKFLOWS`, `Taskfile.ss.yml`, and `.github/actions/ss-*/` is rewritten wholesale on every run, and the CLI is reinstalled at the **pinned** version in `mise.toml` (a refresh never bumps it — see "Move the CLI pin" below). A refresh of an older install also migrates a legacy `cli_version` from `.slopstopper.yml` into `mise.toml` and strips it, and strips a dead `node_version` key. A few classes of customization get wiped and need re-applying; a few classes of upstream change need manual catch-up because the installer doesn't drag everything across. Walk this section before the local-verify loop in Step 7.

### Diff installed workflows against upstream

`install.sh` uses a hardcoded `GENERIC_WORKFLOWS` array, not a wildcard over slopstopper's `.github/workflows/ss-*.yml`. The two can drift — slopstopper may ship a workflow that the installer hasn't been updated to include. Catch the gap:

```bash
comm -23 \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | grep -vE '^ss-release\.yml$' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
```

Any line in the output is an `ss-*.yml` workflow that exists upstream but isn't in your target. If any look relevant, copy them across directly (and customize like the rest — Node version pin, URLs, page paths). Flag the gap upstream as an `install.sh` fix. The `grep -vE '^ss-release\.yml$'` filters out slopstopper's own PyPI release pipeline — an infra workflow that isn't part of the adopter set, so it's an expected miss, not a gap.

### Re-apply customizations the installer wiped

The installer refreshes `Taskfile.ss.yml`, the `.ss/` overlay, `.githooks/pre-push`, and the `ss-*.yml` workflows wholesale. Anything hand-edited in those files is gone — but `.slopstopper.yml` is **never** overwritten by the installer, so the bulk of customization (headers source/format, URLs, pages, og-image path, disabled workflows, hygiene thresholds) survives every re-run. The Node version lives in `mise.toml` and is seeded only when absent, so a bump you made there survives too.

What still needs re-checking after a refresh:

- **Anything hand-edited inside `ss-*.yml` workflow files** beyond what `.slopstopper.yml` covers. Common case: extra workflow-level `permissions:` for a custom integration, a non-standard schedule, or workflow-level env vars beyond the documented URL/PAGES set. Diff against upstream to find them. Push bespoke wording into the check's META in `slopstopper-cli` upstream rather than hand-editing the YAML locally — workflow edits don't survive `install.sh` re-runs.
- **Anything hand-edited inside `.ss/tests/*.spec.ts`, `.ss/playwright.config.js`, or `.ss/lighthouserc.json`.** These used to be seeded by `install.sh` but now live inside the `slopstopper-cli` wheel. The installer's byte-equality scrub removes unmodified copies (so the wheel's version wins via the templates resolver); customized copies survive in `.ss/` and continue to override.
- **The Node version pin.** Lives in `mise.toml` (`[tools] node`), not `.slopstopper.yml`. `install.sh` seeds `node = "20"` only when none is declared, so a bump you made (`mise use node@22`) survives a refresh and there's nothing to re-sync — mise locally and CI via `jdx/mise-action` read the same pin. If you mirror URLs as repo variables, re-push those after editing `.slopstopper.yml`.
- **The pre-push hook file** (`.githooks/pre-push`) is refreshed wholesale, so hand-edits to it are lost — it's slopstopper-owned. The `core.hooksPath` **wiring** is re-applied on every refresh **when safe** — i.e. when hooksPath is unset or already `.githooks` and no other hook manager is present. It won't override a hooksPath the adopter pointed elsewhere, or a husky/lefthook/pre-commit setup. Note the flip side: an adopter who simply *unset* hooksPath will have it re-wired on the next refresh (empty is indistinguishable from never-set) — to opt out durably, pass `--no-hooks` on refreshes or point hooksPath at their own dir.

- **`.github/labeler.yml`** if upstream's labeler template added categories you want (the installer never overwrites your existing file, so new categories don't land automatically).

### Move the CLI pin (intentional upgrades)

`slopstopper-cli` is pinned per-repo in `mise.toml` (`[tools]` "pipx:slopstopper-cli"), and a plain refresh installs exactly that version — it never bumps the CLI. This is deliberate: a breaking upstream release can't surprise the repo. To move the pin:

```bash
bash install.sh --upgrade-cli        # bump to the latest published version
bash install.sh --cli-version X.Y.Z  # pin to an exact version
```

Either flag wraps `mise use` to rewrite the `"pipx:slopstopper-cli"` entry in `mise.toml`, install that version locally, and the change ships to CI (`jdx/mise-action`) once you commit. The post-install banner surfaces "PyPI latest is X — run `install.sh --upgrade-cli`" when the pin is behind, so you always know an upgrade is available without it being forced. Before bumping, skim the slopstopper changelog for breaking changes, then run the Step 7 local-verify loop so the new version is green before you push the pin bump.

### Spot newly-shipped knobs in `.slopstopper.yml.example`

The `.slopstopper.yml.example` file in the slopstopper repo is the schema reference. Diff it against your repo's `.slopstopper.yml`:

```bash
diff <(curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/.slopstopper.yml.example) .slopstopper.yml
```

Any keys present upstream but missing locally are new knobs you can opt into. Most ship with sensible defaults so no action is required — but the diff is the easiest way to know what changed.

Surfaces worth checking explicitly:

- **`profile:`** — project-shape preset (`ui` / `api` / `library`). A config that predates the key has no `profile:` line, which resolves to `ui` — i.e. the full suite, exactly as before, so nothing changed under the repo. If the repo is an API or a library, this is the highest-value knob in the diff: setting it and re-running the installer removes the browser-and-SEO checks that were never going to pass. Run `slopstopper profile detect` and confirm with the user before switching. Check `workflows.disabled` at the same time — entries that a profile now covers can be dropped from it.
- **`hygiene.docs_size.*` / `hygiene.entry_files.*`** — per-check thresholds and rule toggles. Defaults are intentionally tight (150 KB / 25 files / 1500 words / map-pointer required). If a `docs-size`, `entry-files` budget, or `entry-files` pointer alert started firing post-refresh, the threshold knob (or `require_map_pointer: false` if the rule is wrong for this repo) is usually what's wanted — not deleting docs.
- **`hygiene.complexity.max_ccn`** — CCN ceiling (default 15). As of this knob, the complexity gate lives in the CLI, so `task ss:hygiene:complexity` fails locally and in the pre-push hook exactly as it does in CI (previously it warned locally but only failed in CI). If a function newly blocks a push and is genuinely well-factored, raise the ceiling here rather than contorting the code.
- **`hygiene.docs_accuracy.extra_paths`** — globs for files outside `docs/` the accuracy check should scan (task and workflow references in markdown, plus every `github.com/<this repo>/blob|tree/…` link in markdown or HTML, must resolve). Off by default. Worth setting for a repo with a marketing site that links into its own source tree, or that ships skills/instructions naming files — those rot silently otherwise.
- **`hygiene.docs_structure.require_indexed_docs`** — on by default: `hygiene:docs-structure` now fails when a doc under `docs/<category>/` (sub-directories included) isn't linked from a README above it. An existing install upgrading the CLI may see its first `unindexed_doc` findings — link the doc, or set this to `false` while you sort the map out.
- **`security.sast.fail_on`** — lowest Semgrep severity that fails `security:sast` (`error` default; `warning`, `info`, `none`). The check's exit code is now the verdict — the workflow no longer re-counts findings in a separate step, so what you see locally is what CI gates on.
- **`api.latency.*`** — endpoints to sample plus three opt-in budgets (`median_ms`, `slowest_ms`, `max_bytes`). Set `paths` and leave the budgets unset on first adoption: the check reports timings and enforces nothing until a budget exists, and budgets should be derived from observed numbers rather than guessed.
- **`api.openapi.served_spec` / `probe_paths` / `ignore_paths`** — new keys alongside the existing `spec` (which DAST already used). `served_spec` is the one worth setting: it turns `hygiene:openapi` from a reachability prober into a committed-vs-deployed drift comparison, which is the signal with no false positives. Note `hygiene:openapi` reads **JSON specs only** — if `spec` is YAML it skips with guidance, while DAST keeps using it.
- **`reliability.coverage.{pr,main,cron}`** — page-discovery modes. Adopters with a sitemap should opt in to `sitemap` on main and `changed` on PRs; otherwise reliability checks only audit `/` by default.
- **`reliability.coverage.cross_cutting_paths`** — escalation triggers for `changed` mode. If a PR-only audit skipped pages that should have been included, this is the lever.

If a previously-failing check started passing after a refresh without any code change, eyeball whether a default got loosened upstream — those are flagged in the slopstopper changelog.

### Spot new checks and task targets

Two surfaces to scan after a refresh:

1. **The CLI's check registry.** `slopstopper --help` lists subcommands; the canonical list of check names is in `cli/slopstopper/checks/__init__.py`'s `REGISTRY` dict upstream. If a new check landed (e.g. `reliability:<new-check>`), it's runnable as `slopstopper run reliability:<new-check>` even before any workflow ships it.
2. **The Taskfile shims.** Re-running the installer refreshes `Taskfile.ss.yml`, which mirrors every CLI check as a `task ss:*` shim. Eyeball:

   ```bash
   task --list | grep '^\* ss:'
   ```

If anything looks unfamiliar, check `Taskfile.ss.yml` for the `desc:` and `summary:` (each shim documents the env vars it forwards). New checks are usually surfaced as part of a new workflow — if a new workflow landed in the diff above, you'll see the matching task here regardless, since `Taskfile.ss.yml` is refreshed wholesale.

If new workflows did land and you want the README badges refreshed to match, re-run `slopstopper badges` and replace the existing Pipeline status block in `README.md`.

### Clean up redundant artefacts

Adopter repos should hold exactly the **expected set** of slopstopper artefacts plus their own customisations — nothing more. Anything outside that set is noise: a former skill that's been folded into another, an old `ss-*-check.yml` that's been renamed upstream, a `.ss/` file that moved into the CLI wheel. Keep the working tree tidy on every refresh.

**What `install.sh` and `install-skill.sh` already clean up automatically:**

- `<repo>/.claude/skills/<name>/` directories listed in `OBSOLETE_SKILLS` — currently `install-slopstopper` (single-skill legacy) and `slopstopper-update` (folded into `slopstopper-install`). Both installer scripts hold the same list.
- `.ss/scripts/` — pre-CLI artefact, scrubbed wholesale on every install.
- Byte-equal copies of `.ss/playwright.config.js`, `.ss/lighthouserc.json`, `.ss/lighthouserc.prod.json`, `.ss/tests/` — these moved into the slopstopper-cli wheel; byte-identical adopter copies are removed (the wheel's version wins via the templates resolver). Customised copies survive.
- Workflows the adopter explicitly disabled via `.slopstopper.yml` `workflows.disabled` — removed on every install.

**What you should sanity-check manually on refresh** (the installer can't auto-detect these without an explicit removal list):

```bash
# 1. Skills: anything in .claude/skills/slopstopper-* that isn't in the current expected set is stale
ls -d .claude/skills/slopstopper-*/ 2>/dev/null
# Expected currently: slopstopper-install, slopstopper-triage. Anything else → flag for the user.

# 2. Workflows: anything matching ss-*-check.yml that doesn't exist upstream is stale
diff \
  <(curl -s https://api.github.com/repos/hungovercoders/slopstopper/contents/.github/workflows | jq -r '.[].name' | grep '^ss-' | grep -vE '^ss-release\.yml$' | sort) \
  <(ls .github/workflows/ | grep '^ss-' | sort)
# Lines prefixed with `>` are local-only ss-* files — could be stale or a workflow the adopter
# deliberately customised away from upstream. Ask the user before deleting.
```

The line to draw before deleting:

- **Slopstopper-shipped, no longer in the expected set** → delete. Examples: `slopstopper-update/SKILL.md`, an `ss-old-check.yml` that was renamed in a recent slopstopper release.
- **Adopter-customised, intentionally divergent** → keep. Examples: an `ss-*.yml` the adopter forked under the same name with bespoke logic, a hand-edited `Taskfile.ss.yml` shim. `.ss/.workflows-installed` tracks adopter deletions but not adopter modifications — when in doubt, ask the user.
- **Adopter-added content under `.claude/skills/` with a non-`slopstopper-` prefix** → not slopstopper's, never touch.

When a clean-up surfaces something the installer should've handled automatically, the fix is to add it to `OBSOLETE_SKILLS` (or the equivalent list for the artefact type) in both `install.sh` and `install-skill.sh` upstream — see the AGENTS.md change-impact table's "Removing a slopstopper-shipped artefact" row. The next adopter then gets the cleanup for free.
