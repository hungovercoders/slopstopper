# From zero to slopstopper

A course in twenty-one short lessons, each with a YouTube episode to
follow. You start with nothing installed and finish able to install the
suite into a repo, read any check's red line and the report it points at,
fix what it found, tailor the suite to a repo's shape, and add a check of
your own. Every lesson explains one check or one idea on its own terms:
the slop it stops, the tool behind it, what it looks like when it fires,
and the fix.

## You will need

The lessons about the checks (2 to 16) run in a small repo the CLI
writes for you, so they need the CLI and nothing of this repository.
Python 3.11 or newer, then:

```sh
pipx install slopstopper-cli       # or: pip install --user slopstopper-cli
slopstopper demo                   # writes slopstopper-demo/, a status page with one finding per check
cd slopstopper-demo
git init -q -b main && git add -A && git commit -q -m "lantern"
```

The demo is "Lantern", a two-page status page laid out the way the
suite expects, deliberately a little slopped: each check lesson opens
on a red check already in it, reads the report, fixes the finding, and
puts the demo back with `git checkout`. The commit is what lesson 6
scans. Each lesson says which external tool it needs beyond the CLI
(lesson 6 `gitleaks`, lesson 7 `semgrep`, lesson 8 `trivy`, lesson 10
Docker, lessons 11 to 15 `node`); `slopstopper doctor` lists what is
missing.

The lessons about the suite itself (1, 17, 18, 19 and 20: the
installer, the workflows, the skills, profiles and the source) run in a
checkout of this repository, which is the reference install. For those,
[mise](https://mise.jdx.dev) must be installed and activated in your
shell, then:

```sh
git clone https://github.com/hungovercoders/slopstopper.git
cd slopstopper
mise install                       # task and node, pinned in mise.toml
task contributing:setup            # the CLI (editable, in cli/.venv), npm deps, Chromium, the hook
export PATH="$PWD/cli/.venv/bin:$PATH"
slopstopper --version
```

The `task ss:*` shims call whichever `slopstopper` is on PATH; that last
`export` points them at the editable install so a lesson runs HEAD.
Lesson 0 reads from either.

## How the lessons work

Each lesson is one page with the same shape, so you always know where
you are:

| Section | What it is for |
|---|---|
| **Goal** | One sentence: what you can do when you finish. |
| **Why this check** | The slop it stops and the tool behind it. |
| **You will need** | Which of the two sandboxes above, and any tool beyond the CLI. |
| **Steps** | Numbered, each with the command to type and the output to expect. Copy, paste, compare. Most check lessons run the same loop: red on the demo as shipped, read the report, fix, green, put the demo back. |
| **Checkpoint** | One command whose output proves the lesson took. |
| **Exercise** | One task to do on your own, with a collapsed solution. |
| **Going further** | Links into the docs for the depth the lesson skipped. |
| **Episode script** | Collapsed at the end: what the video says and shows, with chapter timestamps. |

Runnable blocks are marked, and `task contributing:learn:check` runs
them in order in a sandbox (the demo repo or a scratch clone, as each
lesson's marker says), locally and in CI (on every push to main,
nightly, and on a pull request that changes the course), so a lesson
cannot quietly stop working when the CLI changes. The sample output comes from the build the lesson was written
against; a later release can word a hint differently, but the commands
and the verdicts are the same.

## Syllabus

| # | Lesson | You will learn | Episode |
|---|---|---|---|
| 0 | [What slop is, and the five loops](00-what-slop-is.md) | The problem, the thesis, the exit-code contract, the five loops | coming soon |
| 1 | [Install slopstopper into a repo](01-install.md) | `install.sh`, profiles, what landed, `doctor` | coming soon |
| 2 | [Run your first check and read its report](02-first-check-complexity.md) | `hygiene:complexity`, the task → CLI → workflow chain, `.ss/reports/` | coming soon |
| 3 | [Entry files: the AGENTS.md-first model](03-entry-files.md) | `hygiene:entry-files`, token budgets, explicit routes | coming soon |
| 4 | [Docs structure: every doc has a route](04-docs-structure.md) | `hygiene:docs-structure`, hops, line caps | coming soon |
| 5 | [Docs accuracy and docs size](05-docs-accuracy-and-size.md) | `hygiene:docs-accuracy`, `hygiene:docs-size`, why one gates and one advises | coming soon |
| 6 | [Secrets](06-secrets.md) | `security:secrets`, why history is what is scanned, revoke then rewrite | coming soon |
| 7 | [Static analysis](07-sast.md) | `security:sast`, shape not text, the finding, fix the code not the rule | coming soon |
| 8 | [Dependencies and licences](08-dependencies.md) | `security:vulnerability:all`, dependency review | coming soon |
| 9 | [Headers and CSP](09-headers-and-csp.md) | `hygiene:csp-exceptions`, `security:api-headers`, the exceptions ledger, wildcard-plus-credentials | coming soon |
| 10 | [Dynamic scanning](10-dast.md) | `security:dast`, the running thing, the gate, the ledger versus `rules.tsv` | coming soon |
| 11 | [Smoke and end-to-end](11-smoke-and-e2e.md) | `reliability:smoke`, `reliability:e2e`, does it serve and can a visitor get around | coming soon |
| 12 | [Accessibility](12-accessibility.md) | `reliability:accessibility`, axe impact levels, the contrast rule | coming soon |
| 13 | [Core Web Vitals](13-core-web-vitals.md) | `reliability:cwv`, LCP, TBT and CLS, budgets you tighten to what you measure | coming soon |
| 14 | [SEO and social share](14-seo.md) | `reliability:seo`, the tags search and previews read | coming soon |
| 15 | [Discoverability: robots, sitemap, llms.txt and links](15-discoverability.md) | `reliability:robots-txt`, `reliability:sitemap`, `reliability:llms-txt`, `reliability:broken-links` | coming soon |
| 16 | [API checks](16-api-checks.md) | `reliability:api-health`, `reliability:api-latency`, `hygiene:openapi`, budgets from what you measured | coming soon |
| 17 | [CI: the workflows and the PR feedback loop](17-ci.md) | `ss-*.yml`, pinned actions, the PR summary, the issue a red main raises, auto-label, the deploy trigger | coming soon |
| 18 | [Agents: the install and triage skills](18-agents.md) | The two Claude Code skills | coming soon |
| 19 | [Profiles and tailoring](19-profiles-and-tailoring.md) | `profile show`, `detect` and `list`, `workflows.enabled`, the pin in `mise.toml` | coming soon |
| 20 | [Inside slopstopper: add a check](20-inside-slopstopper.md) | The registry, the registration test, the shape every check shares | coming soon |

A lesson without a link is not written yet; issue #483 tracks each one.
The episode column links the video once it is recorded. The title,
thumbnail and description every episode follows are in
[EPISODES.md](EPISODES.md), and `docs/learn/tapes/NN.tape` holds each
lesson's terminal parts, generated from its runnable blocks.

Start with [lesson 0](00-what-slop-is.md), or jump to
[lesson 2](02-first-check-complexity.md) if you already know why you are
here and have the demo above.

## Writing a lesson

Copy [TEMPLATE.md](TEMPLATE.md), which is the lesson shape and the rules
a lesson follows. The course lives under `docs/learn/` but is listed in
`hygiene.docs.exclude` in `.slopstopper.yml`, so the docs checks that
keep the reference docs routed and sized leave it alone: it is read in
order by people, not routed to by agents.
