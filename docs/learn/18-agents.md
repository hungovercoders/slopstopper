# Lesson 18: Agents: the install and triage skills

<!-- learn-sandbox: demo -->

**Goal.** Install the two Claude Code skills into a repo, read how they
are shaped, and see how an agent uses them to install the suite or
fix a red check without being told the steps.

## Why this lesson

slopstopper is built to be run by agents as much as by people. The
AGENTS.md-first model from lesson 3 exists so an agent knows where to
read; the `task ss:*` surface exists so there is one thing to learn;
every check prints a red line that names the file and the report so
the next step is never a guess. The two skills close the loop. A skill
is a markdown playbook that Claude Code loads when a prompt matches
its description, and these two turn "add slopstopper to this repo" and
"this check is red" into things an agent does the same way every time.

- **`slopstopper-install`** covers a first install and a refresh. It
  detects which one it is doing, picks a profile from the repo's
  shape, runs the installer, sets the URLs and page lists, lays out the
  AGENTS.md-first docs, and closes every check locally before anything
  is pushed. It also knows what a refresh overwrites and what it must
  re-apply.
- **`slopstopper-triage`** is reactive. It decodes the failing
  workflow's name into a check, reproduces it with the `task ss:*`
  shim, reads the report, sorts the finding into one of three kinds (a
  real finding, a false positive, a threshold too tight for this repo)
  and fixes the right thing, with a per-symptom table of what has
  bitten before.

Both are shaped the same way: a short `SKILL.md` that is the map, and
a `references/` directory of long sections an agent reads only when a
step needs them, so a skill costs one page of context until it does.
They name specific tasks, reports and env vars, which is why the
change map in lesson 20 lists them as a surface: a skill that does not
know a check exists will never suggest it or fix it.

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH.
Claude Code, from [claude.com/claude-code](https://claude.com/claude-code),
for the agent steps, which are not run by the harness.

## Steps

### 1. Install the skills into a repo

The skills ship inside the CLI's wheel, and `slopstopper install`
writes them with the rest of the suite: the map, plus only the
references the map links, swapped in as a whole directory so a refresh
never leaves a stale file behind.

<!-- learn -->
```sh
slopstopper install --no-topic --no-hooks | grep -A2 'Installing the SlopStopper Claude Code skills' | tail -1
find .claude -type f | LC_ALL=C sort
```

```
✅ slopstopper-install: installed
.claude/skills/slopstopper-install/SKILL.md
.claude/skills/slopstopper-install/references/configure.md
.claude/skills/slopstopper-install/references/install.md
.claude/skills/slopstopper-install/references/maintaining.md
.claude/skills/slopstopper-install/references/map-pattern.md
.claude/skills/slopstopper-install/references/preflight.md
.claude/skills/slopstopper-install/references/refresh.md
.claude/skills/slopstopper-install/references/verify.md
.claude/skills/slopstopper-triage/SKILL.md
.claude/skills/slopstopper-triage/references/broader-fixes.md
.claude/skills/slopstopper-triage/references/categorise.md
.claude/skills/slopstopper-triage/references/gotchas.md
.claude/skills/slopstopper-triage/references/maintaining.md
.claude/skills/slopstopper-triage/references/reproduce.md
.claude/skills/slopstopper-triage/references/upstream.md
```

Project level, under the repo's own `.claude/skills/`, so every
contributor who clones the repo gets them, and they are committed
alongside the workflows. `install-skill.sh` upstream refreshes just the
playbooks without re-running the whole installer.

### 2. Read the map of the triage skill

<!-- learn -->
```sh
grep '^## ' .claude/skills/slopstopper-triage/SKILL.md
```

```
## Step 1: Identify which check is failing
## Step 2: Reproduce locally
## Step 3: Read the report
## Step 4: Categorise the finding
## Step 5: Per-symptom gotcha table
## Steps 6–7: Broader fixes, and deleting the check instead
## When to hand off
```

That is lesson 2's loop, written for an agent: name the check,
reproduce it with the shim, read the report, decide what kind of
finding it is, fix that. Step 1 starts from the pull request's summary
comment, because it names the failing checks and nothing else. The
hand-off section points at the other skill for anything that is
really an install problem, and the install skill points back.

### 3. Trigger it

Break the entry-files check the way lesson 3 did, then ask Claude Code
to fix it. The prompt is the only input; the skill's description is
what makes it load.

```sh
cat docs/README.md >> README.md
claude "the entry-files check is failing on this repo, fix it"
```

What a good run looks like: the agent reads the skill's map, runs
`task ss:hygiene:entry-files`, opens
`.ss/reports/entry-files/entry-file-size-report.md`, sees the README
over budget, and moves the pasted map out rather than raising the
budget, because the skill's Step 4 says a threshold is the fix only
when the check is right and the config is wrong, and the report's own
fix says the same. Then it reruns the check and shows it green. Put
the demo back when you are done:

```sh
git checkout README.md
```

### 4. Why the skills are a surface

Every task, report path and env var a skill names is a promise about
the suite, and lesson 5's docs-accuracy check scans the skills for the
ones it can verify: that each `task ss:*` and workflow they mention
exists. The rest, the steps and the gotcha rows, is kept honest by the
change map: a new check adds a row to the triage skill's reproduce and
gotcha tables and an inventory line to the install skill, and the
registration test from lesson 20 fails while the check's count quoted
in the skills is stale.

<!-- learn -->
```sh
grep -c 'task ss:' .claude/skills/slopstopper-triage/references/reproduce.md
```

```
24
```

## Checkpoint

<!-- learn -->
```sh
grep -c '^name: slopstopper-' .claude/skills/*/SKILL.md | tr '\n' ' '
```

```
.claude/skills/slopstopper-install/SKILL.md:1 .claude/skills/slopstopper-triage/SKILL.md:1 
```

Put the demo back:

<!-- learn -->
```sh
git checkout .gitignore package.json
git clean -fdq
```

## Exercise

Find where the install skill decides whether it is installing or
refreshing, and what it looks for.

<details>
<summary>Solution</summary>

```sh
grep -n -A6 '^## Mode detection' .claude/skills/slopstopper-install/SKILL.md
```

It checks for `.slopstopper.yml` and the `.ss/.workflows-installed`
marker. Both present means a refresh, which routes to the
refresh-only steps: confirm the installed set is the pinned release's,
re-apply the customisations a re-run wipes, and look for new knobs.
Neither means a first install. The installer is idempotent either way;
the skill's job is to know which questions to ask. (The demo has the
config but not the marker until you install, so on it the answer is a
first install.)

</details>

## Going further

- [Install the skills](../runbooks/INSTALL_SKILLS.md): the trigger
  table, what lands, and how to uninstall
- [The install skill](../../.claude/skills/slopstopper-install/SKILL.md)
  and [the triage skill](../../.claude/skills/slopstopper-triage/SKILL.md),
  the maps themselves
- Lesson 3 for the AGENTS.md-first model the skills assume, and lesson
  20 for the change map that keeps them true

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A red check. A prompt: "fix it". The agent runs
the shim, opens the report, moves the content, reruns. Green.

**Talking points.**

1. Why: built to be run by agents; AGENTS.md-first, one surface, red
   lines that name files; the skills close the loop.
2. Install them; what lands; project level and committed.
3. The triage map is lesson 2's loop written for an agent; the three
   kinds of finding.
4. The live run: break entry-files, prompt, watch it take the route;
   why it moves content rather than raising the budget.
5. The skills as a surface: docs-accuracy, the change map, the count.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/18.tape` for the install; a screen recording for the
agent run, with the transcript's tool calls visible.

**Chapters.** `0:00 Why` · `1:30 Install` · `3:00 The map` ·
`4:30 The run` · `7:30 A surface` · `9:00 Next lesson`.

</details>
