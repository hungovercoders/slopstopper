# Lesson 7: Static analysis

**Goal.** Write one unsafe line, watch Semgrep flag it, read the
finding, and fix the code rather than the rule.

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

- The checkout from the [syllabus](README.md), with the CLI on PATH.
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

### 1. See it green

<!-- learn -->
```sh
task ss:security:sast
```

```
┌──────────────┐
│ Scan Summary │
└──────────────┘
✅ Scan completed successfully.
 • Findings: 15 (15 blocking)
 • Rules run: 508
 • Targets scanned: 283
🔍 Running SAST analysis…
⚠️  Found 15 finding(s): 0 error(s), 15 warning(s)
✅ No finding(s) at or above `fail_on: error`, so the check passes

📁 Reports saved to: .ss/reports/sast/
   • sast-report.md
```

Trimmed to the summary. Semgrep ran about five hundred rules over the
whole checkout and found fifteen things, all warnings, so the check
passes; Semgrep's own "15 blocking" is its word for "would fail at its
default setting", and the check's line underneath is the one that
counts. The warnings are real and worth a look later (the report lists
them); none is above the line.

### 2. Write the line that always looks fine

A script that renders a file to PDF by shelling out. It takes the path
from the command line, which is to say from wherever the command line
came from.

<!-- learn -->
```sh
mkdir -p scratch
cat > scratch/report.py <<'EOF'
import subprocess
import sys


def render(path):
    cmd = "wkhtmltopdf " + path + " out.pdf"
    subprocess.run(cmd, shell=True, check=True)


if __name__ == "__main__":
    render(sys.argv[1])
EOF
```

Read it once as a reviewer would. It does what it says. Nothing in it
is unusual. A path containing `; rm -rf ~` is also a path.

### 3. See it red

<!-- learn: fails -->
```sh
task ss:security:sast
```

```
🔍 Running SAST analysis…
⚠️  Found 16 finding(s): 1 error(s), 15 warning(s)
❌ 1 finding(s) at or above `fail_on: error`, so the check fails

📁 Reports saved to: .ss/reports/sast/
   • sast-report.md
task: Failed to run task "ss:security:sast": exit status 1
```

One new finding, and it is an ERROR, so the count above the line went
from zero to one and the check fails. The file was not committed; Semgrep
scans what is on disk and not ignored, so the finding arrives before the
commit does.

### 4. Read the finding

<!-- learn -->
```sh
sed -n '/| Rule/,/^$/p' .ss/reports/sast/sast-report.md | head -3
```

```
| Rule | Severity | Location | Message |
|------|----------|----------|---------|
| python.lang.security.audit.subprocess-shell-true.subprocess-shell-true | ERROR | `scratch/report.py:7` | Found 'subprocess' function 'run' with 'shell=True'. This is dangerous becaus... |
```

Three things to read, in this order. The **rule id** is a path into
Semgrep's registry (`python.lang.security.audit.subprocess-shell-true`),
which is where you go to read the whole rule and its references. The
**location** is the file and line. And the **message** says why: with
`shell=True`, the string is handed to a shell, so anything in it that
the shell treats as syntax is executed. The full message in the report
also says what to do instead, which is the next step.

### 5. Fix the code, not the rule

The fix the rule asks for: pass the command as a list and drop
`shell=True`. There is no shell, so there is no shell syntax, and a path
is only ever a path.

<!-- learn -->
```sh
cat > scratch/report.py <<'EOF'
import subprocess
import sys


def render(path):
    subprocess.run(["wkhtmltopdf", path, "out.pdf"], check=True)


if __name__ == "__main__":
    render(sys.argv[1])
EOF
```

The other way out, when a pattern is genuinely safe where it stands, is
a suppression **with a reason** on the line itself:

```python
subprocess.run(cmd, shell=True, check=True)  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true -- cmd is a constant from the table above
```

The rule id is spelled out, so the suppression covers one rule on one
line and nothing else, and the reason sits where the next reader will
see it. That is the honest exception. Turning the rule off for the repo
is not; neither is lowering `fail_on` because one finding was
inconvenient.

## Checkpoint

<!-- learn -->
```sh
slopstopper run security:sast >/dev/null 2>&1; echo "exit $?"
rm -rf scratch
```

```
exit 0
```

Back to the fifteen warnings and nothing above the line. The `rm` puts
the checkout back for the next lesson.

## Exercise

Move the line. Make the fifteen warnings block, see the check fail on the
checkout as it stands, and put the line back.

<details>
<summary>Solution</summary>

```sh
printf 'security:\n  sast:\n    fail_on: warning\n' >> .slopstopper.yml
task ss:security:sast; echo "exit $?"
git checkout .slopstopper.yml
```

The run ends `❌ 15 finding(s) at or above `fail_on: warning`, so the
check fails` and `exit 1`, with no change to the code. The knob is a
policy decision, so it lives in the one config file you own, and the
same line moves the pre-push hook and CI together, because the check is
the gate in all three places. Before you raise the bar for real, read
the fifteen: some want the suppression-with-a-reason from step 5, and
the rest want fixing.

</details>

## Going further

- [SAST](../security/SAST.md): the severity table, `fail_on`, and the
  suppressions this repo carries with the reason for each
- [Semgrep's registry](https://semgrep.dev/r), where every rule id in a
  report resolves to the rule, its references and its fix guidance
- Lesson 6, the other static security check, which scans history rather
  than the tree
- Lesson 17 for what the check does on `main`: the tracking issue it
  opens for a blocking finding and closes when the finding goes

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A ten-line script in a diff. "LGTM." Type a
filename with a semicolon in it. Cut to the terminal doing something
else.

**Talking points.**

1. Why: the patterns reviewers skim past; shape, not text; why
   generated code reproduces them.
2. Green on the checkout; what "15 blocking" means and what the check's
   line means.
3. The script; read it as a reviewer; red.
4. The finding: rule id, location, message; the registry.
5. Fix the code; the suppression with a reason; what is not honest.
6. Exercise: move the line, see the warnings block, put it back.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/07.tape`. Zoom on `0 error(s)` becoming `1 error(s)`,
and on the rule id in the report row.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 The line` ·
`3:30 Red` · `4:30 The finding` · `6:00 Fix` · `7:30 Exercise` ·
`8:40 Next lesson`.

</details>
