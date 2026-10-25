# Lesson 7: Static analysis

<!-- learn-sandbox: demo -->

**Goal.** Find the one unsafe line in the demo's script, read the
finding Semgrep raised for it, and fix the code rather than the rule.

## Why this check

`security:sast` catches the patterns reviewers skim past. A shell
command assembled from a string that came from somewhere else. SQL built
with `+`. An `eval` on a value a request supplied. A hash function that
stopped being safe a decade ago. Generated code reproduces these because
they are everywhere in its training data, and they look fine in a diff:
the line is short, the test passes, the variable is called `cmd`. The
slop is not that the code is wrong today; it is that the shape of the
code is one that goes wrong the first time the input is not what the
author pictured.

The tool is [Semgrep](https://semgrep.dev/), which matches the **shape**
of code, not its text. A rule says "a call to `subprocess.run` with
`shell=True` whose first argument is not a literal", and it fires
whatever the variable is named and however the string was built. The
check runs it with `--config=auto`, so Semgrep picks rules for the
languages it finds in the repo, and every finding carries a rule id, a
severity and a message that says why the pattern is dangerous and what
to do instead.

The verdict lives in the check. Semgrep reports findings at ERROR,
WARNING and INFO; `security.sast.fail_on` in `.slopstopper.yml` names
the lowest severity that fails the run, default `error`, so warnings are
reported and do not block. Exit 0 is nothing at or above that line, exit
1 is a finding at or above it, and exit 2 is Semgrep missing, unable to
fetch its rules, or writing no report, because a scan that never
happened is not a clean scan.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `semgrep` on PATH. `pip install semgrep` or `brew install semgrep`;
  the check's own workflow installs it with pip, and this course's CI
  does the same. The first run fetches rules from the registry, so it
  needs the network.

<!-- learn -->
```sh
semgrep --version
```

```
1.176.0
```

## Steps

### 1. See it red

<!-- learn: fails 1 -->
```sh
slopstopper run security:sast
```

```
┌──────────────┐
│ Scan Summary │
└──────────────┘
✅ Scan completed successfully.
 • Findings: 3 (3 blocking)
 • Rules run: 338
 • Targets scanned: 22
🔍 Running SAST analysis…
⚠️  Found 3 finding(s): 1 error(s), 2 warning(s)
❌ 1 finding(s) at or above `fail_on: error`, so the check fails

📁 Reports saved to: .ss/reports/sast/
   • sast-report.md
```

Trimmed to the summary. Semgrep ran a few hundred rules over the
twenty-two files git tracks and found three things: one ERROR, which is
above the line and fails the check, and two WARNINGs, which are
reported and do not. Semgrep's own "3 blocking" is its word for "would
fail at its default setting"; the check's line underneath is the one
that counts.

### 2. Read the finding

<!-- learn -->
```sh
sed -n '/| Rule/,/^$/p' .ss/reports/sast/sast-report.md | head -3
```

```
| Rule | Severity | Location | Message |
|------|----------|----------|---------|
| python.lang.security.audit.subprocess-shell-true.subprocess-shell-true | ERROR | `scripts/status.py:80` | Found 'subprocess' function 'run' with 'shell=True'. This is dangerous becaus... |
```

Three things to read, in this order. The **rule id** is a path into
Semgrep's registry (`python.lang.security.audit.subprocess-shell-true`),
which is where you go to read the whole rule and its references. The
**location** is the file and line. And the **message** says why: with
`shell=True`, the string is handed to a shell, so anything in it that
the shell treats as syntax is executed. The full message in the report
also says what to do instead, which is the next step.

### 3. Read the line as a reviewer would

<!-- learn -->
```sh
sed -n '76,80p' scripts/status.py
```

```
        state = badge(probe(url))
        page = update(page, name, state)
        summary.append(f"{name}={state}")
    PAGE.write_text(page)
    subprocess.run("git commit -qam 'status: " + " ".join(summary) + "'", shell=True, check=False)
```

It does what it says: commit the refreshed page with a message built
from each service's state. Nothing in it is unusual. The states come
from `badge`, which today returns one of four words; the day it
returns something with a quote in it, the commit message is shell
syntax. A reviewer reading for intent passes this line every time.
Semgrep reads for shape.

### 4. Fix the code, not the rule

The fix the rule asks for: pass the command as a list and drop
`shell=True`. There is no shell, so there is no shell syntax, and a
message is only ever a message.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
p = pathlib.Path('scripts/status.py'); s = p.read_text()
old = '''    subprocess.run("git commit -qam 'status: " + " ".join(summary) + "'", shell=True, check=False)'''
p.write_text(s.replace(old, '''    subprocess.run(["git", "commit", "-qam", "status: " + " ".join(summary)], check=False)'''))
PY
slopstopper run security:sast
```

```
🔍 Running SAST analysis…
⚠️  Found 2 finding(s): 0 error(s), 2 warning(s)
ℹ️  none at or above `fail_on: error`, so the check does not fail

📁 Reports saved to: .ss/reports/sast/
   • sast-report.md
```

Green, and honest about it: the two warnings are still reported. The
other way out, when a pattern is genuinely safe where it stands, is a
suppression **with a reason** on the line itself:

```python
subprocess.run(cmd, shell=True, check=False)  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true -- cmd is a constant from the table above
```

The rule id is spelled out, so the suppression covers one rule on one
line and nothing else, and the reason sits where the next reader will
see it. That is the honest exception. Turning the rule off for the repo
is not; neither is lowering `fail_on` because one finding was
inconvenient.

### 5. Put the demo back

<!-- learn -->
```sh
git checkout scripts/status.py
```

## Checkpoint

<!-- learn: fails 1 -->
```sh
slopstopper run security:sast >/dev/null 2>&1; echo "exit $?"
```

```
exit 1
```

Red again, with the demo as it shipped: one ERROR on one line, and you
know the fix is a list.

## Exercise

Move the line. Make the two warnings block as well, read what they
are, and put the line back.

<details>
<summary>Solution</summary>

```sh
printf 'security:\n  sast:\n    fail_on: warning\n' >> .slopstopper.yml
slopstopper run security:sast; echo "exit $?"
sed -n '/| Rule/,/^$/p' .ss/reports/sast/sast-report.md | tail -4
git checkout .slopstopper.yml
```

The run ends `❌ 3 finding(s) at or above `fail_on: warning`, so the
check fails` and `exit 1`, with no change to the code. The two warnings
are `missing-integrity` on the two pages' stylesheet links: a
`<link rel="stylesheet">` with no `integrity` hash. For a stylesheet
served from the same origin that is noise; for one from a CDN it is
the thing that stops a tampered file loading. The knob is a policy
decision, so it lives in the one config file you own, and the same line
moves the pre-push hook and CI together, because the check is the gate
in all three places.

</details>

## Going further

- [SAST](../security/SAST.md): the severity table, `fail_on`, and the
  suppressions slopstopper's own repo carries with the reason for each
- [Semgrep's registry](https://semgrep.dev/r), where every rule id in a
  report resolves to the rule, its references and its fix guidance
- Lesson 6, the other static security check, which scans history rather
  than the tree
- Lesson 17 for what the check does on `main`: the tracking issue it
  opens for a blocking finding and closes when the finding goes

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** The five-line commit function in a diff. "LGTM."
Type a service state with a quote in it. Cut to the terminal doing
something else.

**Talking points.**

1. Why: the patterns reviewers skim past; shape, not text; why
   generated code reproduces them.
2. Red on the demo; one error above the line, two warnings below it;
   what "3 blocking" means and what the check's line means.
3. The finding: rule id, location, message; the registry.
4. The line as a reviewer reads it; the day the input changes.
5. Fix the code; the warnings stay; the suppression with a reason;
   what is not honest.
6. Exercise: move the line, read the warnings, put it back.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/07.tape`. Zoom on `1 error(s)` becoming `0 error(s)`,
and on the rule id in the report row.

**Chapters.** `0:00 Why` · `1:30 Red` · `2:30 The finding` ·
`4:00 The line` · `5:00 Fix` · `7:00 Exercise` · `8:40 Next lesson`.

</details>
