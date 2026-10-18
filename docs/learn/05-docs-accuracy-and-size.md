# Lesson 5: Docs accuracy and docs size

**Goal.** Watch a doc drift from the repo it describes, read the two
findings that catches, and then read the growth signal the size monitor
prints without ever failing a build.

## Why these checks

`hygiene:docs-accuracy` catches docs that describe last month's repo.
Every reference a doc makes is a promise: that `task ss:hygiene:tidy`
exists, that `ss-hygiene-tidy-check.yml` is a workflow, that `TIDY.md`
is a file, that a link into the GitHub repo lands on a path. Generated
docs break these promises constantly, because they are written from a
snapshot and nobody re-reads them when the task is renamed or the file
moves. An agent that reads the stale doc then runs the stale command,
and the first anyone hears of it is a confused transcript. The check is
stdlib Python: it reads every doc, resolves each reference against the
working tree, the Taskfiles and the workflows directory, and fails on
the first one that does not resolve.

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

The checkout from the [syllabus](README.md), with the CLI on PATH. Both
checks are stdlib Python, so nothing else.

## Steps

### 1. See docs-accuracy green

<!-- learn -->
```sh
task ss:hygiene:docs-accuracy
```

```
🔍 Checking documentation accuracy…
🚫 8 doc(s) excluded by hygiene.docs.exclude (listed in the report)
✅ Documentation accuracy checks passed

📁 Reports saved to: .ss/reports/docs/
   • docs-accuracy-report.md
```

The excluded line is this course: the lessons are left out of the three
docs checks, as lesson 4 explained.

### 2. Break it twice in one line

Append a sentence to the hygiene README that names a task which does
not exist and links a file which does not exist. Both are things a doc
written from memory does.

<!-- learn -->
```sh
printf '\nRun `task ss:hygiene:tidy` after editing, then open [the tidy guide](TIDY.md).\n' >> docs/hygiene/README.md
```

### 3. See it red

<!-- learn: fails -->
```sh
task ss:hygiene:docs-accuracy
```

```
🔍 Checking documentation accuracy…
🚫 8 doc(s) excluded by hygiene.docs.exclude (listed in the report)
⚠️  Found 2 accuracy issue(s)
  docs/hygiene/README.md:216: Broken link: [the tidy guide](TIDY.md) points to a path that does not exist
  docs/hygiene/README.md:216: Task reference `task ss:hygiene:tidy` not found in Taskfile.yml
task: Failed to run task "ss:hygiene:docs-accuracy": exit status 1
```

Two findings from one line, each with the file, the line and the
promise that was broken. The report groups them by kind.

### 4. Read the report

<!-- learn -->
```sh
sed -n '/## Issues/,/## Excluded/p' .ss/reports/docs/docs-accuracy-report.md
```

```
## Issues

### Broken Internal Links

- **docs/hygiene/README.md** (line 216): Broken link: [the tidy guide](TIDY.md) points to a path that does not exist

### Stale Taskfile References

- **docs/hygiene/README.md** (line 216): Task reference `task ss:hygiene:tidy` not found in Taskfile.yml


## Excluded
```

### 5. Fix it

The fix is to make the doc true: name the task that exists, link the
file that exists, or delete the sentence. Here it is the last.

<!-- learn -->
```sh
git checkout docs/hygiene/README.md
task ss:hygiene:docs-accuracy
```

```
✅ Documentation accuracy checks passed
```

A doc that names a file on purpose although no checkout holds it, such
as a report written at run time, goes in
`hygiene.docs_accuracy.ignore_refs` with a reason. That is the one
honest exception.

### 6. Read the size monitor

Now the advisory check. Run it and read the three numbers and the
three thresholds.

<!-- learn -->
```sh
task ss:hygiene:docs-size
```

```
📊 Documentation Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Files:        34
  Total Size:         211 KB
  Estimated Tokens:   ~54118
  Average File Size:  6 KB

📈 Largest Files:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs/reliability/README.md (16 KB)
docs/hygiene/README.md (14 KB)
docs/contributing/CHANGE_MAP.md (11 KB)
docs/architecture/README.md (10 KB)
docs/security/DAST.md (10 KB)

📋 Threshold Limits:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Max Total Size:     220 KB
  Max File Size:      20 KB
  Max File Count:     35

✅ Status: Within acceptable limits
```

This repo documents every check, so it sits above the defaults (150 KB,
25 files) and its `.slopstopper.yml` raises the totals with a comment
saying why. The per-file cap is untouched, because that one is about a
single doc staying readable.

### 7. See the advisory fire, and the exit code not move

Drop a 25 KB doc into the tree and run again.

<!-- learn -->
```sh
yes 'Notes on every default the hygiene checks ship with, and why.' | head -c 25000 > docs/hygiene/NOTES.md
task ss:hygiene:docs-size | sed -n '/Status/,/excluded/p'
```

```
❌ Status: THRESHOLDS EXCEEDED

⚠️ Alerts:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Total documentation size (235 KB) exceeds threshold (220 KB)
⚠️  Files exceeding 20 KB:
     - NOTES.md

🚫 8 doc(s) excluded by hygiene.docs.exclude (listed in the report)
```

The verdict is red in the output and in the report, and the exit code
is still 0: the shim ran clean, the hook would let you push, CI would
stay green. The PR summary comment carries the alert instead, where a
reviewer sees it. That is the design: a size is a reason to look, a
broken reference is a reason to stop.

<!-- learn -->
```sh
slopstopper run hygiene:docs-size >/dev/null; echo "exit $?"
rm docs/hygiene/NOTES.md
```

```
exit 0
```

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:docs-accuracy >/dev/null; echo "exit $?"
```

```
exit 0
```

## Exercise

Make docs-accuracy fail with a workflow reference instead of a task or
a link, then put it back.

<details>
<summary>Solution</summary>

```sh
printf '\nThe `ss-hygiene-tidy-check.yml` workflow runs it in CI.\n' >> docs/hygiene/README.md
task ss:hygiene:docs-accuracy
git checkout docs/hygiene/README.md
```

A backticked `ss-*.yml` name is resolved against `.github/workflows/`,
so the finding reads "Workflow reference … not found". The same goes
for a backticked file path: it must exist somewhere `git ls-files`
lists.

</details>

## Going further

- [Documentation accuracy](../hygiene/README.md#documentation-accuracy)
  in the hygiene README: every kind of reference it resolves,
  `extra_paths` for scanning the site and the skills, `ignore_refs`
- [Documentation size monitoring](../hygiene/README.md#documentation-size-monitoring):
  why it is advisory and where the verdict lives
- The `docs_size` comment in this repo's `.slopstopper.yml`, the worked
  example of raising a total in a commit that says why

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A doc that says `task ss:hygiene:tidy`. A
terminal that says "task: Task "ss:hygiene:tidy" does not exist". An
agent transcript trying it three times.

**Talking points.**

1. Every reference is a promise; generated docs break them silently.
2. Green run; the one-line break with two findings; the report groups
   by kind; revert.
3. `ignore_refs` is the honest exception.
4. The size monitor: three numbers, three thresholds, always exit 0.
   Why: under AGENTS.md-first size is a reason to look.
5. The 25 KB doc; the red verdict; the exit code still 0; where the
   alert goes instead.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/05.tape`. Zoom on the two findings, then on
`exit 0` under the red verdict.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 Two findings` ·
`4:00 Fix` · `5:00 The size monitor` · `6:30 Red but exit 0` ·
`8:00 Exercise` · `8:40 Next lesson`.

</details>
