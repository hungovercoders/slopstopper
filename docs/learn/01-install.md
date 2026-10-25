# Lesson 1: Install slopstopper into a repo

<!-- learn-sandbox: demo -->

**Goal.** Install the suite into a repo, pick a profile, know what
every file it wrote is for, and see which checks the repo is now
carrying.

## Why this lesson

Adopters meet the installer first, and an installer that drops thirty
files into a repo is itself a kind of slop unless every one of them can
be explained. The suite earns the files by making each one answer a
question you will ask later: where does a check run (the workflow), how
do I run it here (the shim), which version runs (the pin), what does
this repo configure (one YAML file), and where did the output go (one
report directory). This lesson is the tour, so nothing in the repo is a
mystery afterwards.

The installer is the CLI: `slopstopper install` writes the suite from
the files its own wheel carries, so the shims and workflows a repo gets
are the ones the CLI that wrote them knows. The `install.sh` one-liner
on the README does one thing on top: it pins `slopstopper-cli` in
`mise.toml` and installs that version through [mise](https://mise.jdx.dev),
then hands over to the same command. mise pins the CLI per repo, so two
repos can run two versions and CI runs the same one you do; `task` comes
from the same pin file, because `task ss:<category>:<check>` is the one
surface humans, agents and CI all call.

A **profile** names the repo's shape and switches off the checks that
shape has no use for: `ui` (a site, every check), `api` (no browser
surface, so the nine browser checks are dropped), `library` (nothing
deployed, so everything that needs a URL goes). The installer only ever
subtracts, and `workflows.enabled` takes one check back. Lesson 19 goes
deeper; here you pick `ui` and look at what it means.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
  Lantern is a repo that already has content, which is the common
  case: the suite is added to something, not the other way round.
- mise, if you want the pin to install anything. Without it the
  installer still writes `mise.toml` and says so.

## Steps

### 1. Run the installer with a profile

`--no-topic` skips the one step that talks to GitHub (adding the
`slopstopper` repo topic through `gh`), which a demo has no remote for.

<!-- learn -->
```sh
slopstopper install --profile ui --no-topic | grep -v '^ ' | grep -E 'installed|pinned|refreshed|seeded|skipping|already|Added|appended'
```

```
✅ Taskfile.ss.yml installed (refreshed)
✅ Taskfile.yml installed
ℹ️  .slopstopper.yml: profile already 'ui'
✅ slopstopper-cli <this CLI's version> pinned in mise.toml
✅ 27 workflow(s) installed, 0 refreshed, 0 previously-deleted skipped
✅ composite actions refreshed under .github/actions/ (ss-playwright, ss-resolve-url, ss-setup)
ℹ️  profile 'ui': 4 workflow(s) not installed for this repo shape (0 removed from a previous install)
✅ Added devDependencies: markdownlint-cli
✅ .github/labeler.yml: seeded
✅ .github/dependency-review-config.yml: seeded
ℹ️  public/_headers: no public/ directory in target, so skipping. Add one and re-run if you want the baseline.
✅ .zap/rules.tsv: seeded
✅ .markdownlint.json: seeded
ℹ️  README.md: already exists, so leaving it alone
ℹ️  AGENTS.md: already exists, so leaving it alone
ℹ️  CLAUDE.md: already exists, so leaving it alone
ℹ️  docs/README.md: already exists, so leaving it alone
✅ .gitignore: appended slopstopper block
✅ slopstopper-install: installed
✅ slopstopper-triage: installed
✅ pre-push hook installed (core.hooksPath → .githooks)
```

Trimmed to the lines that name a file. Three things to notice before
the tour. The CLI version is **pinned**: the installer wrote its own
version into `mise.toml`, a later run installs that same version and
never moves it, so a release upstream cannot reach this repo
unannounced (`install.sh --upgrade-cli` moves the pin, on purpose, in a
commit). Four workflows were **not installed**: the `ui` profile holds
back the API checks until the repo shows an API, so a static site does
not run four jobs that check nothing. And every file Lantern already
had (its config, its README, its `AGENTS.md`) was **left alone**: the
installer seeds what is missing and never overwrites what is yours.

### 2. Tour what landed

<!-- learn -->
```sh
git status --short
```

```
 M .gitignore
 M package.json
?? .claude/
?? .githooks/
?? .github/
?? .markdownlint.json
?? .ss/
?? .zap/
?? Taskfile.ss.yml
?? Taskfile.yml
?? mise.toml
```

Two files changed and nine added, in four groups:

| Files | What they are for |
|---|---|
| `.github/workflows/ss-*.yml`, `.github/actions/ss-*/` | One workflow per check (lesson 17), each a handful of steps built on the three composite actions. The installer owns these; a refresh rewrites them. |
| `Taskfile.ss.yml`, `Taskfile.yml`, `mise.toml`, `package.json` | The shims (`task ss:*`), a root Taskfile that includes them under `ss`, the version pins, and the browser checks' npm dependencies merged into the manifest Lantern already had. |
| `.zap/rules.tsv`, `.github/labeler.yml`, `.github/dependency-review-config.yml`, `.markdownlint.json` | Config that is **yours**: seeded once, never overwritten. `.slopstopper.yml` is the same kind of file, and Lantern already had one, so nothing was seeded there. Every key the checks read is in `.slopstopper.yml.example` upstream. |
| `.claude/skills/slopstopper-*/`, `.githooks/pre-push`, `.ss/`, the block in `.gitignore` | The two Claude Code skills (lesson 18), the pre-push gate, the directory every check writes its reports under, and the ignore rules for what the checks leave behind. |

The pin is the whole of `mise.toml`:

<!-- learn -->
```sh
cat mise.toml
```

```
[tools]
"node" = "20"
"task" = "3"
"pipx:slopstopper-cli" = "<this CLI's version>"
```

And `.ss/.workflows-installed` is the installer's memory: it lists the
workflows it wrote, so a workflow you delete on purpose stays deleted
on the next refresh (remove its line there to have it back).
`.ss/.installed-from` names the version that wrote everything.

<!-- learn -->
```sh
wc -l < .ss/.workflows-installed
cat .ss/.installed-from
```

```
27
<this CLI's version>
```

### 3. See what the profile decided

<!-- learn -->
```sh
slopstopper profile show
```

```
  Profile: ui  (from .slopstopper.yml)
      A web UI: a site or app that serves HTML to a browser.

  Disabled workflows (4):
    · ss-hygiene-openapi-check.yml               (profile, no API detected)
    · ss-reliability-api-health-check.yml        (profile, no API detected)
    · ss-reliability-api-latency-check.yml       (profile, no API detected)
    · ss-security-api-headers-check.yml          (profile, no API detected)
```

Every workflow that is missing is named, with the reason. Nothing is
quietly off.

### 4. Ask which tools are missing

Most checks subprocess-invoke a tool the CLI does not ship: Semgrep,
Gitleaks, Trivy, Docker for ZAP. `doctor` says which are on PATH, and
for each missing one, which check that affects and how to install it.

```sh
slopstopper doctor
```

```
🩺 slopstopper doctor: checking external tools and workflows
✅ node       found at …/node (v20.20.2)
✅ gh         found at /opt/homebrew/bin/gh (gh version 2.101.0)
✅ semgrep    found at /opt/homebrew/bin/semgrep (1.176.0)
✅ gitleaks   found at …/gitleaks (gitleaks version 8.30.1)
✅ trivy      found at …/trivy (Version: 0.74.0)
✅ docker     found at /usr/local/bin/docker (Docker version 29.5.3)
ℹ️  workflows  skipped: gh is missing, unauthenticated, or this isn't a GitHub repo
✅ All required tools available.
```

A missing tool is not a failing check. Every check exits **2** when it
cannot run (tool absent, input missing), which CI reports as "could not
run" and never as a verdict about your code; exit 1 is reserved for "the
repo failed it". Lesson 0 covered the contract; `doctor` is how you clear
the 2s before the first PR.

### 5. See everything runnable

Once mise has installed the pin (`mise install`, or just entering the
directory with mise activated), `task` resolves to this repo's and the
shims are the map of the suite:

```sh
task --list
```

```
task: Available tasks for this project:
* ss:hygiene:complexity:               Analyze code complexity using Lizard
* ss:hygiene:csp-exceptions:           Validate per-page CSP relaxations match docs/security/CSP_EXCEPTIONS.md
* ss:hygiene:docs-accuracy:            Check documentation for broken links + stale refs
* ss:hygiene:docs-size:                Monitor documentation size against configured thresholds
* ss:hygiene:docs-structure:           Validate every doc under docs/ has an explicit route from AGENTS.md or the map
* ss:hygiene:entry-files:              Enforce token budgets + explicit routes on AGENTS.md, README.md, CLAUDE.md and the docs map
* ss:hygiene:test:                     Run all hygiene checks (docs-size, docs-structure, docs-accuracy, entry-files, csp-exceptions, complexity)
* ss:reliability:smoke:                Run smoke tests against a live URL
* ss:security:sast:                    Run static application security testing using Semgrep
* ss:security:secrets:                 Run secrets detection using Gitleaks
…
```

One line per check, the same names the workflows call. The CLI lists
the checks it knows without `task`, and marks the ones this repo
carries no workflow for, which here are the four the profile held back;
they still run locally through `slopstopper run`:

<!-- learn -->
```sh
slopstopper checks list --json | grep -c '"disabled": true'
```

```
4
```

## Checkpoint

The pre-push hook runs the static hygiene suite before every push,
through `task ss:hygiene:test`. On Lantern that gate is red on purpose:
the demo carries one finding per check, and lessons 2 to 5 fix the
hygiene ones. One of them is green already, and it proves the install
took: the entry-file check reads the `AGENTS.md`, `README.md` and
`CLAUDE.md` the demo shipped, under the budgets the suite enforces.

<!-- learn -->
```sh
slopstopper run hygiene:entry-files | tail -1
```

```
✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
```

Put the demo back, so the next lesson starts from the repo as shipped:

<!-- learn -->
```sh
git checkout .gitignore package.json
git clean -fdq
```

## Exercise

Install again with `--profile library` and find out, without reading
the docs, which checks a library does not get.

<details>
<summary>Solution</summary>

```sh
slopstopper install --profile library --no-topic | grep 'workflow(s)'
slopstopper profile show
git checkout .gitignore .slopstopper.yml package.json && git clean -fdq
```

The installer line reads `11 workflow(s) installed`, and `profile show`
lists sixteen disabled workflows with the reason `(profile)`: the nine
browser checks, DAST, CSP exceptions, the privacy statement and the four
API checks, which is everything that needs a URL or a served page. What
remains is the static layer: SAST, secrets, dependency CVEs, review and
licences, complexity, the four docs checks. The last line puts the demo
back, including the `profile: library` the flag wrote into its config.

</details>

## Going further

- [The install runbook](../runbooks/INSTALL.md): every flag, the
  `--no-task` mode, and what a refresh keeps and rewrites
- [The install skill](../../.claude/skills/slopstopper-install/SKILL.md),
  which walks an agent through the same install, the profile choice and
  the post-install verification loop
- Lesson 19 for profiles in depth: `detect`, `list`, keeping one check
  the profile drops, and moving the pin
- `.slopstopper.yml.example` upstream, the schema for the one config
  file you own

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `git status --short` after a tool "set itself up":
thirty unexplained files. "Which of these can I delete?" Cut to the
same list with a reason beside every line.

**Talking points.**

1. Why: an installer earns its files by making each answer a question;
   the CLI writes its own suite; mise, Python, task, and what each one
   is for.
2. The demo repo; the install line; the pin, the four workflows held
   back, the files left alone.
3. The tour: four groups, which are the installer's and which are
   yours.
4. `profile show`: nothing quietly off. `doctor`: a missing tool is a
   2, not a failure.
5. `task --list` and `checks list` as the map; the checkpoint: one
   green check on a demo that is red on purpose.
6. Exercise: the library profile and what "needs a URL" removes.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/01.tape`; `demos/install.tape` drives the `install.sh`
one-liner. Zoom on the pin line, on "4 workflow(s) not installed", and
on "already exists, so leaving it alone".

**Chapters.** `0:00 Why` · `1:00 Install` · `2:30 What landed` ·
`4:30 Profile and doctor` · `6:30 The map` · `7:30 Checkpoint` ·
`8:30 Next lesson`.

</details>
