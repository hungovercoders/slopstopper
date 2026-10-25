# Lesson 2: Run your first check and read its report

<!-- learn-sandbox: demo -->

**Goal.** Run one check against the demo repo, read the red line and the
report it points at, fix what it names, and see it go green. This is the
loop every later lesson repeats.

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

The gate lives in the CLI, so `slopstopper run hygiene:complexity`
returns the same verdict at your terminal, in the pre-push hook and in
CI, where the `task ss:hygiene:complexity` shim and the workflow both
call it. There is no separate CI-only threshold.

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH.
Lizard is a Python dependency of the CLI, so nothing else.

## Steps

### 1. See it red

The demo ships with this finding in it. Run the check and read the
three parts of what it prints.

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:complexity
```

```
🔍 Analyzing code complexity…

📁 Reports saved to: .ss/reports/complexity/
   • complexity-report.md
   • complexity-report.csv
❌ 1 function(s) exceed CCN 15. Refactor them before merging.
```

The first line says what is running. The middle says where the report
went. The last line is the verdict: how many functions failed and what
to do. It does not say which; that is the report's job.

### 2. Read the report

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
| 34 | 17 | 119 | 1 | 34 | `badge@31-64@./scripts/status.py` |
## Guidelines
```

CCN 17: sixteen `if`s plus one. Open the function and you will
recognise the shape. `badge` maps an HTTP status to a word, one `if`
per status, which is the flat dispatch generated code falls into most
often: correct, tested, and a maintenance trap. The CSV beside the
report carries the same rows for anything that wants to chart them.

### 3. See the raw exit code

The verdict is also an exit code, which is what the hook and CI gate
on. This is the contract from lesson 0: a 1, because the check ran and
the repo failed it.

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:complexity >/dev/null; echo "exit $?"
```

```
exit 1
```

### 4. Fix it

The fix the check asks for is a refactor, not a bigger threshold. A
lookup table makes `badge` one line with a CCN of 1. This replaces the
function in place:

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
p = pathlib.Path('scripts/status.py'); s = p.read_text()
start = s.index('def badge(status):'); end = s.index('\n\n\n', start)
new = '''BADGES = {200: "ok", 201: "ok", 202: "ok", 204: "ok", 301: "ok", 302: "ok", 304: "ok",
          400: "degraded", 401: "degraded", 403: "degraded", 404: "degraded", 408: "degraded", 429: "degraded",
          500: "down", 502: "down", 503: "down"}


def badge(status):
    return BADGES.get(status, "unknown")'''
p.write_text(s[:start] + new + s[end:])
PY
slopstopper run hygiene:complexity
```

```
🔍 Analyzing code complexity…

📁 Reports saved to: .ss/reports/complexity/
   • complexity-report.md
   • complexity-report.csv
✅ No high-complexity functions found (all CCN ≤ 15).
```

Same behaviour, one path through the function. When a function trips
the ceiling and is genuinely well-factored, a flat dispatch or
validation table, raising `max_ccn` with a note in `.slopstopper.yml` is
honest. Doing it to silence noise is not; the threshold is the feature.

### 5. Put the demo back

The lessons promise each one starts from the demo as written, so undo
the fix with git. The next lesson's finding is a different file.

<!-- learn -->
```sh
git checkout scripts/status.py
```

## Checkpoint

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:complexity >/dev/null; echo "exit $?"
```

```
exit 1
```

Red again, because the demo is back to how it shipped, and you know
exactly which function and which line the 1 is about.

## Exercise

Make the check pass without replacing the function and without touching
`.slopstopper.yml`.

<details>
<summary>Solution</summary>

Split the chain by outcome. Three small functions, each a handful of
`if`s, and `badge` becomes a call to each in turn:

```python
def is_ok(status):
    return status in (200, 201, 202, 204, 301, 302, 304)

def is_degraded(status):
    return status in (400, 401, 403, 404, 408, 429)

def badge(status):
    if is_ok(status):
        return "ok"
    if is_degraded(status):
        return "degraded"
    return "down" if status >= 500 else "unknown"
```

No function has more than three paths. It is the same fix as the
table, seen from the other side: the branches did not go away, they
stopped living in one place. Put the demo back with
`git checkout scripts/status.py` when you are done.

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

**Cold open (0:00).** `scripts/status.py` scrolling: sixteen `if`s, all
green in the test runner. "Ship it?"

**Talking points.**

1. Why complexity: generated code is long and flat; CCN is the number.
2. Red run on the demo; the three lines: what ran, where the report
   went, the verdict. The red line says how many, not which.
3. The report says which; CCN 17 is sixteen plus one.
4. The raw exit code is 1; that is what the hook and CI gate on.
5. The table; green. When raising the threshold is honest.
6. Put the demo back; the exercise splits instead of tabling.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/02.tape`. Zoom on the verdict line each run.

**Chapters.** `0:00 Why` · `1:00 Red` · `2:30 The report` ·
`4:00 Exit codes` · `5:00 Fix` · `7:00 Exercise` · `8:30 Next lesson`.

</details>
