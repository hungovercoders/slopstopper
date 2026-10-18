# From zero to slopstopper

A course in twenty-one short lessons, each with a YouTube episode to
follow. You start with nothing installed and finish able to install the
suite into a repo, read any check's red line and the report it points at,
fix what it found, tailor the suite to a repo's shape, and add a check of
your own. Every lesson explains one check or one idea on its own terms:
the slop it stops, the tool behind it, what it looks like when it fires,
and the fix.

## You will need

Until `slopstopper demo` ships (issue #471), the lessons run in a checkout
of this repo, which is the reference install and has every check
configured. Two things must be on your machine first: [mise](https://mise.jdx.dev),
installed and activated in your shell, which reads `mise.toml` and
installs the pinned `task` and `node`; and Python 3.11 or newer as
`python3` on PATH, because the CLI's virtual environment is created with
the system interpreter and `slopstopper-cli` requires 3.11+. Then clone,
install the toolchain, and put the CLI on your PATH:

```sh
git clone https://github.com/hungovercoders/slopstopper.git
cd slopstopper
mise install                       # task and node, pinned in mise.toml
task contributing:setup            # the CLI (editable, in cli/.venv), npm deps, Chromium, the hook
export PATH="$PWD/cli/.venv/bin:$PATH"
slopstopper --version
```

The `task ss:*` shims call whichever `slopstopper` is on PATH; that last
`export` points them at the editable install so a lesson runs HEAD. Each
lesson says which external tools it needs beyond that (lesson 6 needs
`gitleaks`, lesson 10 needs Docker); `slopstopper doctor` lists what is
missing.

## How the lessons work

Each lesson is one page with the same shape, so you always know where
you are:

| Section | What it is for |
|---|---|
| **Goal** | One sentence: what you can do when you finish. |
| **Why this check** | The slop it stops and the tool behind it. |
| **You will need** | Anything beyond the checkout above. |
| **Steps** | Numbered, each with the command to type and the output to expect. Copy, paste, compare. Most lessons run the same loop: green, break it, red, read the report, fix, green. |
| **Checkpoint** | One command whose output proves the lesson took. |
| **Exercise** | One task to do on your own, with a collapsed solution. |
| **Going further** | Links into the docs for the depth the lesson skipped. |
| **Episode script** | Collapsed at the end: what the video says and shows, with chapter timestamps. |

Runnable blocks are marked for a harness that will run them in CI
(issue #485), so a lesson cannot quietly stop working when the CLI
changes. The sample output comes from the build the lesson was written
against; a later release can word a hint differently, but the commands
and the verdicts are the same.

## Syllabus

| # | Lesson | You will learn | Episode |
|---|---|---|---|
| 0 | [What slop is, and the five loops](00-what-slop-is.md) | The problem, the thesis, the exit-code contract, the five loops | coming soon |
| 1 | Install slopstopper into a repo | `install.sh`, profiles, what landed, `doctor` | coming soon |
| 2 | [Run your first check and read its report](02-first-check-complexity.md) | `hygiene:complexity`, the task → CLI → workflow chain, `.ss/reports/` | coming soon |
| 3 | [Entry files: the AGENTS.md-first model](03-entry-files.md) | `hygiene:entry-files`, token budgets, explicit routes | coming soon |
| 4 | [Docs structure: every doc has a route](04-docs-structure.md) | `hygiene:docs-structure`, hops, line caps | coming soon |
| 5 | Docs accuracy and docs size | `hygiene:docs-accuracy`, `hygiene:docs-size` | coming soon |
| 6 | Secrets | `security:secrets` | coming soon |
| 7 | Static analysis | `security:sast` | coming soon |
| 8 | Dependencies and licences | `security:vulnerability:all`, dependency review | coming soon |
| 9 | Headers and CSP | `hygiene:csp-exceptions`, `security:api-headers` | coming soon |
| 10 | Dynamic scanning | `security:dast` | coming soon |
| 11 | Smoke and end-to-end | `reliability:smoke`, `reliability:e2e` | coming soon |
| 12 | Accessibility | `reliability:accessibility` | coming soon |
| 13 | Core Web Vitals | `reliability:cwv` | coming soon |
| 14 | SEO and social share | `reliability:seo` | coming soon |
| 15 | Discoverability: robots, sitemap, llms.txt and links | `reliability:robots-txt`, `reliability:sitemap`, `reliability:llms-txt`, `reliability:broken-links` | coming soon |
| 16 | API checks | `reliability:api-health`, `reliability:api-latency`, `hygiene:openapi` | coming soon |
| 17 | CI: the workflows and the PR feedback loop | `ss-*.yml`, the PR summary, auto-label, failure issues | coming soon |
| 18 | Agents: the install and triage skills | The two Claude Code skills | coming soon |
| 19 | Profiles and tailoring | `profile`, `workflows.disabled` and `enabled`, upgrading the pin | coming soon |
| 20 | Inside slopstopper: add a check | The registry and the registration test | coming soon |

A lesson without a link is not written yet; issue #483 tracks each one.
The episode column links the video once it is recorded.

Start with [lesson 0](00-what-slop-is.md), or jump to
[lesson 2](02-first-check-complexity.md) if you already know why you are
here and have the checkout above.

## Writing a lesson

Copy [TEMPLATE.md](TEMPLATE.md), which is the lesson shape and the rules
a lesson follows. The course lives under `docs/learn/` but is listed in
`hygiene.docs.exclude` in `.slopstopper.yml`, so the docs checks that
keep the reference docs routed and sized leave it alone: it is read in
order by people, not routed to by agents.
