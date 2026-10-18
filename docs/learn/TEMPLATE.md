# Writing a lesson

This page is the template every lesson in the course is copied from, and
the rules a lesson follows. Copy it to `docs/learn/<NN>-<slug>.md`, keep
the H1 as `Lesson N: <title>`, replace each section, and update the row
in the [syllabus](README.md).

## The rules

- **Second person, present tense.** "You run", not "we will run".
- **One concept per lesson.** One check, or one idea. If a step needs a
  second idea explained, that idea is its own lesson or belongs in Going
  further.
- **Say why before how.** The "Why this check" section names the slop
  the check stops and the tool behind it, in plain words, before the
  first command. A reader should be able to argue for the check after
  reading that section alone.
- **Every command is copy-pasteable and shows its output.** A reader
  compares what they see with what the page shows; never make them
  guess. Trim output to the lines that matter and say so.
- **Every step runs in the checkout from the syllabus** unless the
  lesson is explicitly about a real deployment. Nobody gets stuck at a
  login page. Steps that edit the checkout end by putting it back
  (`git checkout <file>`, `rm`), so the next lesson starts clean.
- **Mark runnable blocks** with an HTML comment on the line before the
  fence. `<!-- learn -->` means the block must exit 0; `<!-- learn: fails -->`
  means it must exit non-zero: the break-it step of most lessons, and
  any `cmd; echo "exit $?"` block that shows a non-zero code, since
  `sh -e` stops at the command. `task contributing:learn:check` runs the
  marked blocks of each lesson in order with `sh -e` in a scratch clone,
  and fails if a page leaves that clone dirty; the `learn` job in
  `ci-cli.yml` runs the same on every change to the course or the CLI,
  so a lesson cannot rot. Blocks that need credentials, an editor, a
  browser or a tool the harness does not have are left unmarked. Run
  `task contributing:learn:check -- --page NN` on a lesson before
  committing it.
- **A background server is tracked by a pid file** under `scratch/`
  (`PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid`),
  stopped with `kill "$(cat scratch/serve.pid)"` in a later block, and
  `scratch/` removed at the end. If a block fails before the kill, the
  harness stops every process named by a pid file under `scratch/`
  before it moves on, so one lesson's failure cannot hold a port for
  the next; a reader does the same by hand.
- **The checkpoint is one command** whose output settles whether the
  lesson took. Make it the last runnable block.
- **The episode script lives on the page**, collapsed at the end, so the
  video and the text never drift apart.

The rest of this page is the template.

---

# Lesson N: Title in sentence case

**Goal.** One sentence: what you can do when you finish. For example:
run one check, break it, read the report and fix it.

## Why this check

Two or three paragraphs. The class of slop this check stops, with one
concrete example of what it looks like in a diff. The tool behind it and
what the tool measures. What the check does with the result: the
threshold, the report, the exit code.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- Any tool beyond that (`gitleaks`, Docker), with the install hint
  `slopstopper doctor` prints.

## Steps

### 1. See it green

Say what the reader is about to do and why, in a sentence. Then the
command:

<!-- learn -->
```sh
task ss:hygiene:complexity
```

Then what they should see. Show the real output, trimmed to the lines
that matter:

```
✅ No high-complexity functions found (all CCN ≤ 15).
```

### 2. Break it

Each step ends with something the reader can see change. Point at it:
"the summary line now says one function exceeds the ceiling".

<!-- learn: fails -->
```sh
task ss:hygiene:complexity
```

### 3. Read the report

The red line says what failed; the report says where. Show the command
that opens the part that matters.

### 4. Fix it

The fix the check asks for, not a way round it. Then the green run
again, and the clean-up that puts the checkout back.

## Checkpoint

One command, one expected result. If it matches, the lesson took.

<!-- learn -->
```sh
slopstopper run hygiene:complexity; echo "exit $?"
```

```
exit 0
```

## Exercise

One task that uses what the lesson taught with a small twist. No new
concepts.

<details>
<summary>Solution</summary>

The solution, as a command or a snippet, with a line on why it works.

</details>

## Going further

- The docs page this lesson skimmed, for example
  [the hygiene README](../hygiene/README.md)
- The config knob, in `.slopstopper.yml.example`

<details>
<summary>Episode script</summary>

**Length.** 8 to 12 minutes.

**Cold open (0:00).** The one-line problem this lesson solves, shown not
said: the diff that looks fine, the red line it causes.

**Talking points.**

1. Why the check exists, in the words a viewer hears.
2. Step 1, step 2.
3. The checkpoint and what it proves.

**Shot list.** One terminal, 100x30, font size 16, the site's theme
(`demos/theme.json`). `docs/learn/tapes/NN.tape` drives it for b-roll
when a recording is needed. Zoom on the line that changed after each
step.

**Chapters.** `0:00 Why` · `1:00 Green` · `2:30 Break it` ·
`4:00 The report` · `6:00 Fix` · `7:30 Exercise` · `8:40 Next lesson`.

</details>
