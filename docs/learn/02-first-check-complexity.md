# Lesson 2: Run your first check and read its report

**Goal.** Run one check, break it, read the red line and the report it
points at, fix it. This is the loop every later lesson repeats.

## Why this check

`hygiene:complexity` is the simplest check to see fire: one function
with too many branches. It is also the check most directly about slop.
Generated code tends to be long and flat. It handles every case in one
function, passes every test, and nobody can follow it six weeks later,
which means nobody can change it safely. Cyclomatic complexity is the
measurable symptom: the number of independent paths through a function,
which is roughly its `if`s, loops, `and`s and `or`s plus one.

The tool is [Lizard](http://www.lizard.ws/), which counts that number
(CCN) per function across most languages without needing a build. The
check fails when any function's CCN is above `hygiene.complexity.max_ccn`
in `.slopstopper.yml`, default 15, which is Lizard's own warning line.
Test files by the common conventions and anything `.gitignore` ignores
are skipped, so a local run after a build sees what CI sees.

The gate lives in the CLI, so `task ss:hygiene:complexity` returns the
same verdict at your terminal, in the pre-push hook and in CI. There is
no separate CI-only threshold.

## You will need

The checkout from the [syllabus](README.md), with the CLI on PATH.
Lizard is a Python dependency of the CLI, so nothing else.

## Steps

### 1. See it green

<!-- learn -->
```sh
task ss:hygiene:complexity
```

```
task: [ss:hygiene:complexity] slopstopper run hygiene:complexity
🔍 Analyzing code complexity…

📁 Reports saved to: .ss/reports/complexity/
   • complexity-report.md
   • complexity-report.csv
✅ No high-complexity functions found (all CCN ≤ 15).
```

The first line is the shim telling you what it ran: the `task` target is
a thin wrapper over `slopstopper run`. The last line is the verdict. In
between is where the report went.

### 2. Break it

Write a function with sixteen branches. This is a flat dispatch, the
shape generated code falls into most often: correct, tested, and a
maintenance trap.

<!-- learn -->
```sh
mkdir -p scratch && cat > scratch/triage.py <<'PY'
def route(code):
    if code == 1: return "a"
    if code == 2: return "b"
    if code == 3: return "c"
    if code == 4: return "d"
    if code == 5: return "e"
    if code == 6: return "f"
    if code == 7: return "g"
    if code == 8: return "h"
    if code == 9: return "i"
    if code == 10: return "j"
    if code == 11: return "k"
    if code == 12: return "l"
    if code == 13: return "m"
    if code == 14: return "n"
    if code == 15: return "o"
    if code == 16: return "p"
    return "z"
PY
```

### 3. See it red

<!-- learn: fails -->
```sh
task ss:hygiene:complexity
```

```
task: [ss:hygiene:complexity] slopstopper run hygiene:complexity
🔍 Analyzing code complexity…

📁 Reports saved to: .ss/reports/complexity/
   • complexity-report.md
   • complexity-report.csv
❌ 1 function(s) exceed CCN 15. Refactor them before merging.
task: Failed to run task "ss:hygiene:complexity": exit status 1
```

The red line says how many functions failed and what to do. It does not
say which; that is the report's job.

### 4. Read the report

Every check writes under `.ss/reports/<check>/`, which is gitignored.
The markdown report names the function, its CCN and where it is.

<!-- learn -->
```sh
sed -n '/High Complexity/,/Guidelines/p' .ss/reports/complexity/complexity-report.md
```

```
## ⚠️ High Complexity Items (CCN > 15)

| NLOC | CCN | Tokens | Params | Length | Location |
|------|-----|--------|--------|--------|----------|
| 18 | 17 | 119 | 1 | 18 | `route@1-18@./scratch/triage.py` |
## Guidelines
```

CCN 17: sixteen `if`s plus one. The CSV beside it carries the same rows
for anything that wants to chart them.

### 5. See the raw exit code

The shim passes the failure on, which is what the hook and CI gate on.
Run the CLI directly once to see the contract from lesson 0: this is a
1, because the check ran and the repo failed it.

<!-- learn: fails -->
```sh
slopstopper run hygiene:complexity >/dev/null; echo "exit $?"
```

```
exit 1
```

### 6. Fix it

The fix the check asks for is a refactor: a lookup table makes `route`
one line with a CCN of 1. Here the function was scratch, so delete it.
Either way the check goes green and the checkout is back where it was.

<!-- learn -->
```sh
rm -r scratch
task ss:hygiene:complexity
```

```
✅ No high-complexity functions found (all CCN ≤ 15).
```

When a function trips the ceiling and is genuinely well-factored, a flat
dispatch or validation table, raising `max_ccn` with a note in
`.slopstopper.yml` is honest. Doing it to silence noise is not; the
threshold is the feature.

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:complexity >/dev/null; echo "exit $?"
```

```
exit 0
```

## Exercise

Put `scratch/triage.py` back and make the check pass without deleting
the function and without touching `.slopstopper.yml`.

<details>
<summary>Solution</summary>

Replace the sixteen `if`s with a dictionary:

```python
LETTERS = dict(zip(range(1, 17), "abcdefghijklmnop"))

def route(code):
    return LETTERS.get(code, "z")
```

`route` now has one path, so its CCN is 1. Delete `scratch/` again when
you are done so the next lesson starts clean.

</details>

## Going further

- [Code complexity analysis](../hygiene/README.md#code-complexity-analysis)
  in the hygiene README: what is measured, what is skipped,
  `hygiene.complexity.exclude`
- `hygiene.complexity.max_ccn` in `.slopstopper.yml.example`
- The exit-code contract in `cli/slopstopper/checks/__init__.py`

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `scratch/triage.py` scrolling: sixteen `if`s, all
green in the test runner. "Ship it?"

**Talking points.**

1. Why complexity: generated code is long and flat; CCN is the number.
2. Green run; the three lines: what ran, where the report went, the
   verdict.
3. Write the function; red run; the red line says how many, not which.
4. The report says which; CCN 17 is sixteen plus one.
5. The raw exit code is 1; the shim passes it on; that is what CI gates.
6. Delete it, green. When raising the threshold is honest.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/02.tape`. Zoom on the verdict line each run.

**Chapters.** `0:00 Why` · `1:00 Green` · `2:30 Break it` ·
`3:30 Red` · `4:30 The report` · `6:00 Exit codes` · `7:00 Fix` ·
`8:30 Next lesson`.

</details>
