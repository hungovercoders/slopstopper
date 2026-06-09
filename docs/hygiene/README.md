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

### Documentation Linting
Validates markdown syntax and formatting using markdownlint. Ensures consistent style across all documentation files.

```bash
task ss:hygiene:lint
```

### Documentation Structure
Verifies that the documentation index file exists at `docs/index.md`. This ensures proper documentation organization.

```bash
task ss:hygiene:structure
```

### File Size Checks
Checks individual markdown files to ensure they don't exceed the 2,500 word limit. This keeps documents focused and manageable.

```bash
task ss:hygiene:size
```

### Documentation Size Monitoring
Monitors overall documentation size and checks against configured thresholds:

- **Total documentation size:** max 150 KB
- **Individual file sizes:** max 20 KB
- **Number of documentation files:** max 15

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
[`app/_headers`](../../app/_headers) has a matching documented
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
`app/_headers` or `docs/security/CSP_EXCEPTIONS.md`.

## Quick Reference

Run all hygiene checks:
```bash
task ss:hygiene:test
```

Run individual checks:
```bash
task ss:hygiene:complexity        # Analyze code complexity
task ss:hygiene:lint              # Check markdown formatting
task ss:hygiene:structure         # Verify documentation index exists
task ss:hygiene:size              # Check individual file sizes
task ss:hygiene:docs-size         # Monitor overall documentation size
task ss:hygiene:entry-files       # Enforce <2k token budget on entry files
task ss:hygiene:docs-structure    # Validate structure matches governance
task ss:hygiene:docs-accuracy     # Check for broken links and stale refs
task ss:hygiene:csp-exceptions    # Validate CSP exceptions are fully documented
```

## Contents

- [COMPLEXITY_CONFIG.md](COMPLEXITY_CONFIG.md)
- [DOCS_SIZE_MONITORING.md](DOCS_SIZE_MONITORING.md) - Setup and usage of local documentation size monitoring
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
