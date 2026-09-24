# Hygiene

Overview of code and documentation hygiene and quality gates.

## Overview

Hygiene checks ensure that the project's code and documentation are well-maintained, appropriately sized, and adhere to quality standards. These checks help maintain code that is efficient and sustainable, and documentation that is easy to navigate, quick to load, and stays within manageable limits for AI context windows.

## Checks

### Code Complexity Analysis
Analyzes code complexity using Lizard to identify overly complex functions and modules. Helps identify refactoring opportunities and maintain code health.

```bash
task ss:hygiene:complexity
```

The check **fails** when any function's cyclomatic complexity (CCN) exceeds `hygiene.complexity.max_ccn` (default `15` — Lizard's own warning line). The gate lives in the CLI, so `task ss:hygiene:complexity` returns the same pass/fail locally, in the pre-push hook, and in CI — there is no separate CI-only threshold. To run stricter, set the knob in `.slopstopper.yml`:

```yaml
hygiene:
  complexity:
    max_ccn: 10   # McCabe's classic "review" bound
```

When a function trips the ceiling and is genuinely well-factored (e.g. a flat dispatch or validation table), prefer raising `max_ccn` with a note over contorting the code — but treat that as a deliberate, documented decision, not a way to silence noise.

### Documentation Size Monitoring
Monitors overall documentation size and checks against configured thresholds:

- **Total documentation size:** max 150 KB
- **Individual file sizes:** max 20 KB
- **Number of documentation files:** max 25

This check is particularly important for AI-assisted development where documentation needs to fit within context windows efficiently. Running this check generates a detailed report in `.ss/reports/docs/docs-size-report.md`.

```bash
task ss:hygiene:docs-size
```

### Documentation Structure Validation
Validates that the documentation directory structure matches the governance model defined in `docs/index.md`. Ensures all expected categories exist with README files and identifies unexpected files for discussion.

The documentation index is the **sole source of truth for documentation structure**—any deviations require discussion and explicit approval before merging.

**Checks:**
- All expected categories from docs/index.md exist
- Each category has a README.md file
- No unexpected files outside the governed structure
- Every doc inside a category, sub-directories included, is linked from its category README or a README.md above it (`unindexed_doc`) — the map is a chain, `docs/index.md` → category README → doc, and a file no README mentions is unreachable from the map. `hygiene.docs_structure.require_indexed_docs: false` turns this rule off
- Violations are raised as blocking issues for discussion

```bash
task ss:hygiene:docs-structure
```

### Documentation Accuracy
Scans markdown for stale or broken references: internal markdown links that don't resolve, `task <name>` references to non-existent Taskfile tasks, workflow filename references that don't match `.github/workflows/`, and stale source-file references. Scans all of `docs/` plus the repo-root entry files (`README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`) so drift in the most-loaded files is caught too.

Runs **weekly on a schedule** (Monday 07:00 UTC), on PRs/pushes that change docs or project structure, and can be triggered manually. When issues are found, a GitHub issue is automatically created or updated.

```bash
task ss:hygiene:docs-accuracy
```

By default it reads `docs/**/*.md` and the four root entry files. `hygiene.docs_accuracy.extra_paths` (repo-relative globs in `.slopstopper.yml`) brings more files into scope, with only the checks that are precise for a file describing an adopter's tree rather than this one: `task ss:…` and workflow references must exist (markdown), and every `github.com/<this repo>/blob|tree/<ref>/<path>` link must point at a path that exists (markdown and HTML). slopstopper.dev scans `app/*.html` and `.claude/skills/**/*.md` this way, because every piece of site and skill drift the repo review found lived in a file the `docs/`-only scan never read.

### Entry-File Budget
Enforces the "thin pointer" principle declared in [`docs/index.md`](../index.md#the-map-pattern):
agent entry files (`README.md`, `AGENTS.md`, `CLAUDE.md`) must stay under
~2k tokens each so they don't crowd the context window of every agent
conversation. Threshold is 1,500 words per file (≈ 2k tokens for English
prose). Fails the build on violation — the fix is to move the over-budget
file's bulk into the category README that owns the topic, leaving a
one-line pointer.

```bash
task ss:hygiene:entry-files
```

Workflow: `ss-hygiene-entry-files-check.yml` — runs on PRs/pushes touching `README.md`, `AGENTS.md`, or `CLAUDE.md`.

### CSP Exceptions Drift Check

Validates that every per-path CSP relaxation in
[`worker/headers.json`](../../worker/headers.json) has a matching documented
entry in [`docs/security/CSP_EXCEPTIONS.md`](../security/CSP_EXCEPTIONS.md),
and vice versa. Fails the build if either side has an entry the other lacks.

The site ships a strict `default-src 'self'` CSP by default. When a page
genuinely needs a vetted third-party widget (e.g. Giscus on
`/feedback.html`), the exception must be declared in both files and
SRI-pinned. This check keeps the two sources of truth in sync so CSP
relaxations are never silent or undocumented.

```bash
task ss:hygiene:csp-exceptions
```

Workflow: `ss-hygiene-csp-exceptions-check.yml` — runs on PRs/pushes touching
`worker/headers.json` or `docs/security/CSP_EXCEPTIONS.md`.

### OpenAPI Drift

The API-shaped analogue of the documentation-accuracy check. That one catches a
doc referencing a file that moved; this one catches a spec that has stopped
describing the API it documents — documentation that quietly became fiction, on
a different surface.

**The only hygiene check that needs a URL**, since drift means the spec measured
against the thing it documents. So it is the one hygiene check `library` drops,
and deliberately **not** part of `task ss:hygiene:test` — that aggregate is what
the pre-push hook runs and is all-static, so adding it would make every `git
push` hit the network.

| Signal | What it means | Needs |
|---|---|---|
| Served but not committed | the committed spec is stale against what is deployed | `served_spec` |
| Committed but not served | a route was removed and the spec wasn't updated, or the deploy is behind | `served_spec` |
| Documented path returns 404 | the spec describes a route that isn't there | a URL |
| Documented path returns 5xx | the route exists but is broken | a URL |

The committed-vs-served comparison is the headline: it compares operation sets
(method + path), not whole documents, so a reordered spec or a different
`servers` block is not drift — no probing, no guessing, no false positives.

Paths taking parameters (`/users/{id}`) are counted but never probed: a 404 from
one could mean "route missing" or merely "no such record", and reporting both as
failures would train people to ignore the check. A 405 proves the route exists
and passes; only `GET` is sent. Detecting *undocumented* routes is out of scope —
it needs framework-specific route introspection.

**JSON specs only.** `slopstopper-cli` ships no third-party dependencies, so it
has no YAML parser. A YAML spec is a graceful skip with that guidance, not a
failure — most frameworks serve the JSON form at `/openapi.json`.

```yaml
# .slopstopper.yml
api:
  openapi:
    spec:                 # URL or repo-relative JSON file; shared with security:dast
    served_spec:          # URL the live API publishes its spec at
    probe_paths: true     # probe parameterless documented paths
    ignore_paths: []      # globs excluded from probing and comparison
```

With `api.openapi.spec` unset the check exits 0 with a note — an unconfigured
check is not a failing check.

```bash
task ss:hygiene:openapi -- https://api.example.com
```

Report: `.ss/reports/openapi/openapi-report.{md,json}`. Workflow:
`ss-hygiene-openapi-check.yml`, resolving `urls.preview` on pull requests and
`urls.production` on main, schedules and deployment events like the API
workflows. With no URL the committed-vs-served comparison still runs (it needs
only `served_spec`); just the probes are skipped.

## Quick Reference

Run all hygiene checks:
```bash
task ss:hygiene:test
```

Run individual checks:
```bash
task ss:hygiene:complexity        # Analyze code complexity
task ss:hygiene:docs-size         # Monitor overall documentation size
task ss:hygiene:entry-files       # Enforce <2k token budget on entry files
task ss:hygiene:docs-structure    # Validate structure matches governance
task ss:hygiene:docs-accuracy     # Check for broken links and stale refs
task ss:hygiene:csp-exceptions    # Validate CSP exceptions are fully documented
```

`task ss:hygiene:test` runs everything above **except** `hygiene:openapi`, which
needs a live API — run that one separately with a URL.

## Contents

- [DOC_UPDATER.md](DOC_UPDATER.md) - Weekly agentic doc-updater (gh-aw): required setup, what it produces, and how to recompile after edits

## When to Run

- **Before commits:** Run `task ss:hygiene:test` to catch code and documentation issues early
- **During code review:** Complexity analysis helps identify refactoring opportunities
- **During PR reviews:** Size monitoring helps track documentation growth
- **In CI/CD:** These checks run automatically in GitHub Actions workflows
- **Local development:** Run manually to validate changes before pushing

## Thresholds & Rationale

The thresholds are designed to:
1. **Keep code maintainable** - Identifies complex functions that may need refactoring
2. **Stay within AI context windows** - Ensures documentation can be referenced in full during AI-assisted development
3. **Maintain document readability** - Prevents any single document from becoming unwieldy
4. **Keep navigation simple** - Limits file count to maintain a reasonable documentation structure
5. **Support rapid iteration** - Smaller documentation and simpler code is easier to update and refactor

## Recommendations

If thresholds are exceeded:
- Consider consolidating related documentation
- Move historical/completed content to an archive folder
- Split large files into focused, topic-specific documents
- Remove redundant or outdated information
- Use the `.ss/reports/docs/docs-size-report.md` report to identify which files need attention
