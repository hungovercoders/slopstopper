# Lesson 5: Docs accuracy and docs size

<!-- learn-sandbox: demo -->

**Goal.** Find the doc in the demo that describes a command the repo
does not have, read the finding, make the doc true, and then read the
growth signal the size monitor prints without ever failing a build.

## Why these checks

`hygiene:docs-accuracy` catches docs that describe last month's repo.
Every reference a doc makes is a promise: that `task ss:hygiene:docs`
exists, that `.github/workflows/ss-hygiene-tidy-check.yml` is there,
that `TIDY.md` is a file, that a link into the GitHub repo lands on a
path. Generated docs break these promises constantly, because they are
written from a snapshot and nobody re-reads them when the task is
renamed or the file moves. An agent that reads the stale doc then runs
the stale command, and the first anyone hears of it is a confused
transcript. The check is stdlib Python: it reads every doc, resolves
each reference against the working tree, the Taskfiles and the
workflows directory, and fails on the first one that does not resolve.

`hygiene:docs-size` is the other half, and it is deliberately not a
gate. It always exits 0. What it does is measure: how many docs, how
big in total, how big the largest, and it prints a verdict against
three thresholds in `.slopstopper.yml`. The per-file cap is the one
that protects a reader, because a 20 KB doc is one nobody finishes.
The totals are a growth signal, sized to the repo, and moved only in a
commit that says why. Under AGENTS.md-first (lessons 3 and 4) only the
entry file is always loaded and everything else is opt-in behind a
route, so size is a thing to watch, not a thing to block on.

The two checks together say: every doc you keep must be true, and you
should notice when you are keeping too many.

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH. Both
checks are stdlib Python, so nothing else.

## Steps

### 1. See docs-accuracy red

<!-- learn: fails -->
```sh
slopstopper run hygiene:docs-accuracy
```

```
🔍 Checking documentation accuracy…
⚠️  Found 1 accuracy issue(s)
  docs/contributing.md:17: Task reference `task ss:hygiene:docs` not found in Taskfile.yml

📁 Reports saved to: .ss/reports/docs/
   • docs-accuracy-report.md
```

The file, the line and the promise that was broken. The demo has no
Taskfile at all, so there is no `task` target of any name, and the
contributing guide is telling every new contributor to run one.

### 2. Read the report, then the line

<!-- learn -->
```sh
sed -n '/## Issues/,/## Excluded/p' .ss/reports/docs/docs-accuracy-report.md
sed -n '17,18p' docs/contributing.md
```

```
## Issues

### Stale Taskfile References

- **docs/contributing.md** (line 17): Task reference `task ss:hygiene:docs` not found in Taskfile.yml

## How to Fix

1. Review each issue above.
2. Update the referenced docs to match the current project state.
3. Run `task ss:hygiene:docs-accuracy` locally to verify fixes.

## Excluded
Run `task ss:hygiene:docs` before you push; it is the two docs checks in
one, and the pull request will not be looked at until it is green.
```

The report groups findings by kind; a doc that also linked a missing
file or named a missing workflow would get a section each. This one is
a doc written from memory of another repo: the command was never
installed here, and the sentence beside it is confidently wrong.

### 3. Fix it

The fix is to make the doc true: name the commands that exist, link the
file that exists, or delete the sentence. Here the two checks the
sentence means do exist, as `slopstopper run` commands.

<!-- learn -->
```sh
sed -i.bak 's/Run `task ss:hygiene:docs` before you push; it is the two docs checks in/Run `slopstopper run hygiene:entry-files` and `slopstopper run hygiene:docs-structure` before you push; they are the two docs checks,/' docs/contributing.md && rm docs/contributing.md.bak
slopstopper run hygiene:docs-accuracy
```

```
🔍 Checking documentation accuracy…
✅ Documentation accuracy checks passed

📁 Reports saved to: .ss/reports/docs/
   • docs-accuracy-report.md
```

A doc that names a file on purpose although no checkout holds it, such
as a report written at run time, goes in
`hygiene.docs_accuracy.ignore_refs` with a reason. That is the one
honest exception.

### 4. Read the size monitor

Now the advisory check. Run it and read the three numbers and the
three thresholds.

<!-- learn -->
```sh
slopstopper run hygiene:docs-size
```

```
📊 Documentation Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Files:        5
  Total Size:         4 KB
  Estimated Tokens:   ~1176
  Average File Size:  0 KB

📈 Largest Files:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs/README.md (1 KB)
docs/security/CSP_EXCEPTIONS.md (1 KB)
docs/architecture.md (0 KB)
docs/contributing.md (0 KB)
docs/runbooks/RELEASE.md (0 KB)

📋 Threshold Limits:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Max Total Size:     150 KB
  Max File Size:      20 KB
  Max File Count:     25

✅ Status: Within acceptable limits
```

Five small docs against the defaults. A repo that documents a lot sits
above them and raises the totals in its `.slopstopper.yml` with a
comment saying why; the per-file cap stays, because that one is about
a single doc staying readable.

### 5. See the advisory fire, and the exit code not move

Drop a 160 KB doc into the tree and run again.

<!-- learn -->
```sh
yes 'Notes on every default the checks ship with, and why each is what it is.' | head -c 160000 > docs/notes.md
slopstopper run hygiene:docs-size | sed -n '/Status/,/Reports/p'
```

```
❌ Status: THRESHOLDS EXCEEDED

⚠️ Alerts:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Total documentation size (160 KB) exceeds threshold (150 KB)
⚠️  Files exceeding 20 KB:
     - notes.md


📁 Reports saved to: .ss/reports/docs/
```

The verdict is red in the output and in the report, and the exit code
is still 0: the hook would let you push, CI would stay green. The PR
summary comment carries the alert instead, where a reviewer sees it.
That is the design: a size is a reason to look, a broken reference is
a reason to stop.

<!-- learn -->
```sh
slopstopper run hygiene:docs-size >/dev/null; echo "exit $?"
rm docs/notes.md
git checkout docs/contributing.md
```

```
exit 0
```

The last line puts the demo back for the next lesson.

## Checkpoint

<!-- learn: fails -->
```sh
slopstopper run hygiene:docs-accuracy >/dev/null; echo "exit $?"
```

```
exit 1
```

Red again, with the demo as it shipped: one stale command, one finding,
and the fix is a sentence.

## Exercise

Make docs-accuracy fail with a broken link and a workflow reference as
well as the task, then put it back.

<details>
<summary>Solution</summary>

```sh
printf '\nThe `.github/workflows/ss-hygiene-tidy-check.yml` workflow runs it in CI; see [the tidy guide](TIDY.md).\n' >> docs/contributing.md
slopstopper run hygiene:docs-accuracy
git checkout docs/contributing.md
```

Three kinds of finding from two lines: the stale task from before, a
"Broken link" because `TIDY.md` is not a file, and a "Workflow
reference does not exist" from the rule that resolves every
`.github/workflows/<name>.yml` path. A bare `ss-hygiene-tidy-check.yml`
with no directory would pass that last rule, because prose names config
files loosely; write the path.

</details>

## Going further

- [Documentation accuracy](../hygiene/README.md#documentation-accuracy)
  in the hygiene README: every kind of reference it resolves,
  `extra_paths` for scanning a site or the skills, `ignore_refs`
- [Documentation size monitoring](../hygiene/README.md#documentation-size-monitoring):
  why it is advisory and where the verdict lives
- The `docs_size` comment in slopstopper's own `.slopstopper.yml`, the
  worked example of raising a total in a commit that says why

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A doc that says `task ss:hygiene:docs`. A
terminal that says "task: command not found". An agent transcript
trying it three times.

**Talking points.**

1. Every reference is a promise; generated docs break them silently.
2. Red on the demo; the report groups by kind; the sentence beside the
   command is confidently wrong.
3. The fix is to make the doc true. `ignore_refs` is the honest
   exception.
4. The size monitor: three numbers, three thresholds, always exit 0.
   Why: under AGENTS.md-first size is a reason to look.
5. The 160 KB doc; the red verdict; the exit code still 0; where the
   alert goes instead.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/05.tape`. Zoom on the finding, then on `exit 0`
under the red verdict.

**Chapters.** `0:00 Why` · `1:30 Red` · `2:30 The report` ·
`4:00 Fix` · `5:00 The size monitor` · `6:30 Red but exit 0` ·
`8:00 Exercise` · `8:40 Next lesson`.

</details>
