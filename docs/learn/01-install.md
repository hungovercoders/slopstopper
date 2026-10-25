# Lesson 1: Install slopstopper into a repo

**Goal.** Install the suite into an empty repo, pick a profile, know
what every file it wrote is for, and see the pre-push gate pass on the
fresh repo.

## Why this lesson

Adopters meet `install.sh` first, and an installer that drops thirty
files into a repo is itself a kind of slop unless every one of them can
be explained. The suite earns the files by making each one answer a
question you will ask later: where does a check run (the workflow), how
do I run it here (the shim), which version runs (the pin), what does
this repo configure (one YAML file), and where did the output go (one
report directory). This lesson is the tour, so nothing in the repo is a
mystery afterwards.

Three prerequisites, each for a reason. [mise](https://mise.jdx.dev)
pins the CLI per repo in `mise.toml`, so two repos can run two versions
and CI runs the same one you do. Python 3.11 or newer, because mise
installs the CLI through its pipx backend and `slopstopper-cli` needs
3.11. And `task`, because `task ss:<category>:<check>` is the one
surface humans, agents and CI all call; mise installs it from the same
pin file.

A **profile** names the repo's shape and switches off the checks that
shape has no use for: `ui` (a site, every check), `api` (no browser
surface, so the nine browser checks are dropped), `library` (nothing
deployed, so everything that needs a URL goes). The installer only ever
subtracts, and `workflows.enabled` takes one check back. Lesson 19 goes
deeper; here you pick `ui` and look at what it means.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- mise activated in your shell (`mise --version` prints a version), and
  the network: the installer pins and installs the published CLI from
  PyPI. For that reason the blocks in this lesson are not run by the
  course harness; `demos/install.tape` records the same flow.

## Steps

### 1. Make an empty repo beside the checkout

The installer runs from a checkout (the README's `curl | bash` one-liner
fetches the same script from GitHub). A sibling directory keeps the
checkout clean and the lesson disposable.

```sh
cd ..
git init -q demo-site && cd demo-site
```

### 2. Run the installer with a profile

```sh
bash ../slopstopper/install.sh --profile ui
```

```
  🛠  SlopStopper: installing tooling
  ✅ Taskfile.ss.yml installed
  ✅ Taskfile.yml installed
  ✅ .slopstopper.yml: seeded demo-site/.slopstopper.yml as a starter. Every other key is in …/.slopstopper.yml.example
  ✅ .slopstopper.yml: profile set to 'ui'
  ℹ  Pinning slopstopper-cli@0.25.0 (+ task) in mise.toml via mise…
  ✅ slopstopper-cli installed (0.25.0, pinned in mise.toml)
  ✅ 27 workflow(s) installed, 0 refreshed, 0 previously-deleted skipped
  ✅ composite actions refreshed under .github/actions/ (ss-resolve-url, ss-setup)
  ℹ  profile 'ui': 4 workflow(s) not installed for this repo shape (0 removed from a previous install)
  ✅ package.json created (devDependencies only; add scripts.build if your site needs building)
  ✅ .github/labeler.yml: seeded
  ✅ .github/dependency-review-config.yml: seeded
  ✅ .zap/rules.tsv: seeded
  ✅ README.md: seeded
  ✅ AGENTS.md: seeded
  ✅ CLAUDE.md: seeded
  ✅ docs/README.md: seeded
  ✅ .gitignore: appended slopstopper block
  ✅ slopstopper-install: installed
  ✅ slopstopper-triage: installed
  ✅ pre-push hook installed (core.hooksPath → .githooks)

  🎉 Installation complete!
```

Trimmed to the lines that name a file. Two things to notice before the
tour. The CLI version is **pinned**: a later run installs that same
version and never moves it, so a release upstream cannot reach this
repo unannounced (`--upgrade-cli` moves the pin, on purpose, in a
commit). And four workflows were **not installed**: the `ui` profile
holds back the API checks until the repo shows an API, so a static site
does not run four jobs that check nothing.

### 3. Tour what landed

```sh
git status --short
```

```
?? .claude/
?? .githooks/
?? .github/
?? .gitignore
?? .markdownlint.json
?? .slopstopper.yml
?? .ss/
?? .zap/
?? AGENTS.md
?? CLAUDE.md
?? README.md
?? Taskfile.ss.yml
?? Taskfile.yml
?? docs/
?? mise.toml
?? package.json
```

Sixteen entries, in five groups:

| Files | What they are for |
|---|---|
| `.github/workflows/ss-*.yml`, `.github/actions/ss-*/` | One workflow per check (lesson 17), each a handful of steps built on the two composite actions. The installer owns these; a refresh rewrites them. |
| `Taskfile.ss.yml`, `Taskfile.yml`, `mise.toml`, `package.json` | The shims (`task ss:*`), a root Taskfile that includes them under `ss`, the version pins, and the browser checks' npm dependencies. |
| `.slopstopper.yml`, `.zap/rules.tsv`, `.github/labeler.yml`, `.github/dependency-review-config.yml`, `.markdownlint.json` | Config that is **yours**: seeded once, never overwritten. Every key the checks read is in `.slopstopper.yml.example` upstream. |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/README.md` | The entry-file scaffolds for the AGENTS.md-first model (lessons 3 and 4). Seeded only when absent. |
| `.claude/skills/slopstopper-*/`, `.githooks/pre-push`, `.ss/` | The two Claude Code skills (lesson 18), the pre-push gate, and the directory every check writes its reports under. |

The pin is the whole of `mise.toml`:

```sh
cat mise.toml
```

```
[tools]
node = "20"
"pipx:slopstopper-cli" = "0.25.0"
task = "3"
```

And `.ss/.workflows-installed` is the installer's memory: it lists the
workflows it wrote, so a workflow you delete on purpose stays deleted
on the next refresh.

### 4. See what the profile decided

mise activates the pinned tools per directory. The first time you enter
a directory with a new `mise.toml` it asks you to trust the file; after
that `slopstopper` and `task` resolve to this repo's pins.

```sh
mise trust
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

### 5. Ask which tools are missing

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

### 6. See everything runnable

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

One line per check, the same names the workflows call. This list is the
map of the suite in any repo that has it; every later lesson starts from
a line on it.

## Checkpoint

The pre-push hook runs the static hygiene suite before every push. Run
it by hand on the fresh repo:

```sh
task ss:hygiene:test; echo "exit $?"
```

```
task: [ss:hygiene:docs-size] slopstopper run hygiene:docs-size
✅ Status: Within acceptable limits
task: [ss:hygiene:docs-structure] slopstopper run hygiene:docs-structure
✅ Documentation structure is valid: all 0 docs are routed
task: [ss:hygiene:docs-accuracy] slopstopper run hygiene:docs-accuracy
✅ Documentation accuracy checks passed
task: [ss:hygiene:entry-files] slopstopper run hygiene:entry-files
✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
task: [ss:hygiene:csp-exceptions] slopstopper run hygiene:csp-exceptions
ℹ️  CSP exceptions check: no headers.source configured in .slopstopper.yml, so skipping.
task: [ss:hygiene:complexity] slopstopper run hygiene:complexity
✅ No high-complexity functions found (all CCN ≤ 15).
exit 0
```

Green on an empty repo, with one check saying it has nothing configured
and skipping: an unconfigured check is not a failing check. Clean up
when you are done:

```sh
cd .. && rm -rf demo-site
```

## Exercise

Install again with `--profile library` into a second empty repo and find
out, without reading the docs, which checks a library does not get.

<details>
<summary>Solution</summary>

```sh
git init -q demo-lib && cd demo-lib
bash ../slopstopper/install.sh --profile library
mise trust && slopstopper profile show
```

The installer line reads `15 workflow(s) installed`, and `profile show`
lists sixteen disabled workflows with the reason `(profile)`: the nine
browser checks, DAST, CSP exceptions, the privacy statement and the four
API checks, which is everything that needs a URL or a served page. What
remains is the static layer: SAST, secrets, dependency CVEs, review and
licences, complexity, the four docs checks.
`cd .. && rm -rf demo-lib` afterwards.

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
   mise, Python, task, and what each one is for.
2. The empty repo; the install line; the pin and the four workflows
   held back.
3. The tour: five groups, which are the installer's and which are
   yours.
4. `profile show`: nothing quietly off. `doctor`: a missing tool is a
   2, not a failure.
5. `task --list` as the map; the checkpoint on an empty repo.
6. Exercise: the library profile and what "needs a URL" removes.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`demos/install.tape` drives the install itself. Zoom on the pin line,
on "4 workflow(s) not installed", and on `exit 0`.

**Chapters.** `0:00 Why` · `1:00 Install` · `2:30 What landed` ·
`4:30 Profile and doctor` · `6:30 The map` · `7:30 Checkpoint` ·
`8:30 Next lesson`.

</details>
