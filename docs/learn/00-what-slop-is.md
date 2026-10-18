# Lesson 0: What slop is, and the five loops

**Goal.** Say what slopstopper stops and how, so every later lesson has
a frame to sit in.

## Why this lesson

Every other lesson explains one check. This one explains why there are
checks at all. Without it the suite reads as twenty-odd unrelated
linters; with it, each check is one answer to the same question.

## What slop is

Slop is code and documentation produced faster than anyone reads it.
People write it under deadline; agents write it by the page. It is
plausible, it passes a glance, and it carries the same defects every
time:

- a key pasted into a config file as an "example"
- a function with sixteen branches that passes every test and that
  nobody can follow
- a doc that describes the repo as it was a month ago, with a `task`
  name that no longer exists
- a page whose heading uses the brand colour and fails contrast
- a dependency pinned to a version with a known CVE, or a package name
  that does not exist
- a CSP relaxed with `'unsafe-inline'` to make one widget work

None of these is hard to spot. All of them get merged, because review
does not scale with the volume of plausible-looking change. Slop is not
a quality of the author. It is what any process produces once output
outruns attention.

## The thesis: gates, not reviews

slopstopper's answer is a gate for each of those defects, run the same
way by a human at a terminal, an agent in a conversation and CI on a
pull request. Three rules make that work:

1. **One surface.** Every check is `task ss:<category>:<action>`. The
   shim calls `slopstopper run <category>:<action>`, and the workflow
   under `.github/workflows/ss-*.yml` runs the same `task` line. There
   is no CI-only threshold and no local-only shortcut, so "it passed on
   my machine" and "it passed in CI" mean the same thing.
2. **One definition of green.** `task ss:hygiene:test` is what the
   pre-push hook runs and what CI runs. A check reports its verdict in
   a red line on the terminal and in a report under `.ss/reports/`, so
   the fix is never a guess.
3. **An exit-code contract.** Every check exits 0 when it ran and found
   nothing to fail on, 1 when it ran and the repo failed it, and 2 when
   it could not run: a tool is missing, an input is absent, the check
   crashed. Both 1 and 2 fail the CI job, because a gate that quietly
   passed when its tool was missing would be worse than no gate. The
   difference is what the suite does with the result. A 1 is a finding:
   on `main`, the check's own issue emitter opens or updates a tracking
   issue and closes it when the check goes green. A 2 is not a finding,
   so that emitter stays silent, and the red run is something for the
   person running it to fix first. The separate workflow-failure
   tracker still files any failed run on `main`, so a 2 is never
   invisible either; it is filed as a broken run, not as a verdict on
   the repo.

## The five loops

The checks group into five loops. Four are installed into any repo; the
fifth is how slopstopper's own site ships, there to copy.

| Loop | The slop it catches | Tools |
|---|---|---|
| 🔒 **Security** | leaked secrets, unsafe code patterns, vulnerable or badly licensed dependencies, a running app that misbehaves, wrong response headers | Gitleaks, Semgrep, Trivy, OWASP ZAP |
| 🧹 **Hygiene** | unreadable functions, docs that drift from code, docs nobody can find, entry files too big for an agent to follow, undocumented CSP exceptions, an API that drifts from its spec | Lizard, stdlib Python |
| ✅ **Reliability** | a deploy that does not serve, broken links, pages that fail accessibility, slow pages, missing metadata, pages crawlers and agents cannot find, an API that is slow or down | Playwright, axe-core, Lighthouse CI |
| 🤖 **Operational** | a red check nobody sees: one rolling PR comment, auto-labelled PRs, failed workflows that raise and close their own issues, a weekly doc sync | GitHub Actions, gh-aw |
| 🚀 **Deployment** | a preview per PR and the URL checks run against it after every deploy | Cloudflare Workers Builds |

Lessons 2 to 5 take the hygiene loop, because it needs no external
tools. Lessons 6 to 10 take security, 11 to 16 reliability, and 17 the
operational loop. The last three are about shaping the suite to a repo
and to yourself.

## You will need

The checkout from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See the whole suite once

Before meeting each check on its own, list them. The left column is the
name you give `slopstopper run`; the `task ss:` shim has the same name.

<!-- learn -->
```sh
slopstopper checks list
```

```
     hygiene:complexity          Code complexity analyzer (Lizard wrapper).
     hygiene:csp-exceptions      CSP-Exceptions Drift Detector.
     hygiene:docs-accuracy       Documentation accuracy validator.
     hygiene:docs-size           Documentation size monitor.
     hygiene:docs-structure      Documentation structure validator. Every doc must have an explicit route.
     hygiene:entry-files         Entry-file budget + AGENTS.md-first routing check.
  💤 hygiene:openapi             OpenAPI spec drift audit (in-CLI implementation).
     reliability:accessibility   Accessibility audit (Playwright + axe-core wrapper).
  💤 reliability:api-health      API health/readiness endpoint audit (in-CLI implementation).
  💤 reliability:api-latency     API latency + payload budget audit (in-CLI implementation).
     reliability:broken-links    Broken-link checks (Playwright wrapper).
     reliability:cwv             Core Web Vitals audit (Lighthouse CI wrapper).
     reliability:e2e             End-to-end user journeys against a live URL (Playwright wrapper).
     reliability:llms-txt        llms.txt AI-discoverability audit (in-CLI implementation).
     reliability:robots-txt      robots.txt discoverability + de-index guard audit (in-CLI implementation).
     reliability:seo             SEO + social-share metatag audit (in-CLI implementation).
     reliability:sitemap         sitemap.xml completeness + drift audit (in-CLI implementation).
     reliability:smoke           Smoke tests against a live URL (Playwright wrapper).
  💤 security:api-headers        API response-header + CORS policy audit (in-CLI implementation).
     security:dast               Dynamic Application Security Testing (OWASP ZAP).
     security:sast               Static Application Security Testing (Semgrep wrapper).
     security:secrets            Secrets detection (Gitleaks wrapper).
     security:vulnerability:all  Dependency vulnerability scanning (Trivy wrapper).

  💤 = no workflow in this repo (profile: ui / workflows.disabled). It still runs locally via `slopstopper run`.
```

The four marked 💤 are the API checks. This repo is a site with no API,
so its profile leaves them without a workflow; lesson 19 is about that.

### 2. See the exit-code contract

Ask for a check that does not exist. The CLI cannot run it, so this is
a 2, not a 1: nothing about the repo failed, and the check's issue
emitter would not treat it as a finding.

<!-- learn: fails -->
```sh
slopstopper run hygiene:nope; echo "exit $?"
```

```
❌ unknown check: hygiene:nope
   known checks: hygiene:complexity, hygiene:csp-exceptions, …
exit 2
```

Now run one that exists. The repo passes it, so the exit is 0. Lesson 2
shows a 1.

<!-- learn -->
```sh
slopstopper run hygiene:docs-structure; echo "exit $?"
```

```
🔍 Validating documentation structure…
✅ Documentation structure is valid: all 33 docs are routed (6 excluded by hygiene.docs.exclude)

📁 Reports saved to: .ss/reports/docs/
   • docs-structure-report.md
exit 0
```

### 3. See the one surface

The same check through the shim everyone uses. `task --list` shows every
shim; the `ss:` prefix is the namespace the suite installs under, so it
never clashes with a repo's own tasks.

<!-- learn -->
```sh
task --list | grep 'ss:hygiene'
```

```
* ss:hygiene:complexity:          Analyze code complexity using Lizard
* ss:hygiene:csp-exceptions:      Detect undocumented CSP exceptions (drift check)
* ss:hygiene:docs-accuracy:       Validate documentation accuracy against the codebase
* ss:hygiene:docs-size:           Monitor documentation size and structure
* ss:hygiene:docs-structure:      Validate documentation structure (AGENTS.md-first routing)
* ss:hygiene:entry-files:         Check entry-file budgets and AGENTS.md-first routing
* ss:hygiene:openapi:             Audit OpenAPI spec drift against a live API
* ss:hygiene:test:                Run all hygiene checks (docs-size, docs-structure, docs-accuracy, entry-files, csp-exceptions, complexity)
```

## Checkpoint

<!-- learn -->
```sh
slopstopper checks list | grep -c 'hygiene:'
```

```
7
```

## Exercise

Without running anything, say which loop would catch each of the six
examples at the top of this page, and which check. Then check your
answers against the table in step 1.

<details>
<summary>Solution</summary>

The key: security:secrets; hygiene:complexity; hygiene:docs-accuracy;
reliability:accessibility; security:vulnerability:all (with dependency
review on the PR); hygiene:csp-exceptions. The lessons on each are 6, 2,
5, 12, 8 and 9.

</details>

## Going further

- [The architecture README](../architecture/README.md) for the single-route
  invocation and the C4 diagrams
- [The exit-code contract](../contributing/README.md) as contributors
  see it, and the registry docstring in `cli/slopstopper/checks/__init__.py`
- [What gets installed](../runbooks/INSTALL.md), the adopter's view of
  the five loops

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A PR diff scrolling past: a config file with an
`AKIA…` string, a function that fills the screen, a doc naming a task
that does not exist. A reviewer's "LGTM". Cut to the red line.

**Talking points.**

1. Slop is what any process produces once output outruns attention.
   Six examples, one sentence each.
2. Gates, not reviews: one surface, one definition of green, the
   exit-code contract. Why 2 exists.
3. The five loops and the tools behind them.
4. `slopstopper checks list`, the unknown-check 2, the docs-structure 0.
5. What the course builds, lesson by lesson.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/00.tape`. The loops table as a card, not a terminal.

**Chapters.** `0:00 Why` · `1:30 Gates, not reviews` ·
`3:30 The five loops` · `5:30 The suite in one screen` ·
`7:00 The exit codes` · `8:30 Next lesson`.

</details>
