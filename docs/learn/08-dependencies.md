# Lesson 8: Dependencies and licences

<!-- learn-sandbox: demo -->

**Goal.** Find the pinned package in the demo with a known CVE, read the
report's "Fixed In" column, take the fix, and see where the licence
gates sit.

## Why this check

`security:vulnerability:all` stops the slop you did not write: a
dependency with a published vulnerability. It arrives in ordinary ways.
An agent pins the version it remembers, which is the version from its
training data and a year or more old. A requirements file is copied
from another project along with its pins. A lock file is regenerated
and nobody reads the diff. None of these are mistakes in your code, and
no review of your code finds them, because the vulnerable lines are in
a package you never open. The only way to know is to look every
dependency up against the list of CVEs, and the only way to keep
knowing is to do it on every pull request and again on every push to
`main`, because the list grows after your code stops changing.

The tool is [Trivy](https://trivy.dev/), which scans the filesystem for
every dependency manifest and lock file it knows (npm, pip, Go, Cargo,
Maven and the rest), resolves each package to a version, and matches
them against a vulnerability database it downloads and caches for a
day. The check subprocess-invokes it with `node_modules` and `.git`
skipped, writes the report, and gates on severity: CRITICAL and HIGH
exit 1, MEDIUM and LOW are reported and exit 0. That threshold is in the
check, not the workflow, so the local run and CI agree. Exit 2 is Trivy
missing or its database download failing, because a scan that never
finished must not read as clean.

Two companion checks cover licences. The dependency review runs only
in CI: it is GitHub's own `dependency-review-action` on the pull
request's manifest diff, so it sees only what the PR adds, and fails a
new dependency under a licence outside the allowlist in
`.github/dependency-review-config.yml`. `security:licences` applies the
same allowlist to the whole resolved tree, locally and in CI, so a
transitive package under a denied licence cannot sit unseen. Neither
gates on a build tool's own dependencies, which is Dependabot's job;
the [vulnerability doc](../security/VULNERABILITY.md#what-it-does-not-cover-and-who-does)
has the table.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `trivy` on PATH. `brew install trivy`, or a release binary from
  [github.com/aquasecurity/trivy](https://github.com/aquasecurity/trivy/releases);
  the suite's own workflow installs it from the Trivy apt repository
  and this course's CI does the same. The first run downloads the
  vulnerability database, which takes a minute.

<!-- learn -->
```sh
trivy --version | head -1
```

```
Version: 0.74.0
```

## Steps

### 1. See it red

<!-- learn: fails -->
```sh
slopstopper run security:vulnerability:all
```

```
🔍 Scanning dependencies for vulnerabilities…
2026-10-25T16:52:46Z	INFO	Number of language-specific files	num=1
2026-10-25T16:52:46Z	INFO	[pip] Detecting vulnerabilities...
⚠️  Found 1 CRITICAL/HIGH vulnerability(ies) (total 5)

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
```

One manifest found, and it is red. The demo's script needs one
package, and whoever wrote the requirements file pinned the version
they remembered. It is from 2018.

<!-- learn -->
```sh
cat scripts/requirements.txt
```

```
requests==2.19.1
```

One line, five findings, none of them in anything you can read in this
repo.

### 2. Read the report

<!-- learn -->
```sh
sed -n '/^| Severity/,/^$/p; /^| CVE/,/^$/p' .ss/reports/vulnerability-all/vulnerability-all-report.md
```

```
| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 High | 1 |
| 🟡 Medium | 4 |
| 🔵 Low | 0 |
| **Total** | **5** |

| CVE | Package | Installed | Fixed In | Severity | Title |
|-----|---------|-----------|----------|----------|-------|
| CVE-2018-18074 | `requests` | 2.19.1 | 2.20.0 | HIGH | python-requests: Redirect from HTTPS to HTTP does not rem... |

| CVE | Package | Installed | Fixed In | Severity | Title |
|-----|---------|-----------|----------|----------|-------|
| CVE-2023-32681 | `requests` | 2.19.1 | 2.31.0 | MEDIUM | python-requests: Unintended leak of Proxy-Authorization h... |
| CVE-2024-35195 | `requests` | 2.19.1 | 2.32.0 | MEDIUM | requests: subsequent requests to the same host ignore cer... |
| CVE-2024-47081 | `requests` | 2.19.1 | 2.32.4 | MEDIUM | requests: Requests vulnerable to .netrc credentials leak ... |
| CVE-2026-25645 | `requests` | 2.19.1 | 2.33.0 | MEDIUM | requests: Requests: Security bypass due to predictable te... |
```

The column that matters is **Fixed In**. Every row names the first
version without the hole, so the report is its own fix list: the HIGH
needs 2.20.0, and the newest MEDIUM needs 2.33.0. The dates in the CVE
ids tell the other story, which is that a pin that was clean in 2018
has had a finding added to it roughly every year since. A dependency
you never touch still changes.

### 3. Take the fix the gate needs

<!-- learn -->
```sh
printf 'requests==2.20.0\n' > scripts/requirements.txt
slopstopper run security:vulnerability:all 2>/dev/null
```

```
🔍 Scanning dependencies for vulnerabilities…
ℹ️  Found 4 vulnerability(ies), none CRITICAL/HIGH

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
```

Trivy's log lines go to stderr, so dropping that stream leaves the
check's own verdict and keeps its exit code, which a pipe into `grep`
would replace. Green, and honest about it: four findings remain,
reported and not blocking. The threshold is where it is because a
MEDIUM is usually "needs a specific setup to exploit" and blocking on
it would make the gate something people route around, which lesson 19
has more to say about. It is still listed, so a reviewer who reads the
comment sees it.

### 4. Then take the fix you want

<!-- learn -->
```sh
printf 'requests==2.33.0\n' > scripts/requirements.txt
slopstopper run security:vulnerability:all 2>/dev/null
grep 'No vulnerabilities detected' .ss/reports/vulnerability-all/vulnerability-all-report.md
```

```
🔍 Scanning dependencies for vulnerabilities…
✅ No vulnerabilities detected

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
No vulnerabilities detected.
```

The `grep` is the assertion: exit 0 only says nothing blocking was
found, so a clean report is the thing to check for. 2.33.0 is the
current release as this lesson was written. When a later one carries a
CVE, the harness that checks this course goes red on this block, which
is the lesson in miniature: the pin did not change, the world did.

### 5. Put the demo back

<!-- learn -->
```sh
git checkout scripts/requirements.txt
```

### 6. When local and CI disagree

This is the one check where they legitimately can. Trivy caches its
database for a day, and CI starts cold and pulls the newest one, so a
CVE published this morning fails the PR and not your laptop.
`trivy clean --vuln-db` then a rerun reproduces CI; the binary version
in the workflow's "Install Trivy" step is the other thing to compare.
Treat CI as the verdict.

## Checkpoint

<!-- learn: fails -->
```sh
slopstopper run security:vulnerability:all >/dev/null 2>&1; echo "exit $?"
```

```
exit 1
```

Red again, with the demo as it shipped, and the fix is a version
number the report hands you.

## Exercise

The licence allowlist is a file `install.sh` seeds into every repo.
Seed one into the demo by hand, with the GPL family left out, and run
the licence inventory against the demo's one dependency.

<details>
<summary>Solution</summary>

```sh
mkdir -p .github
printf 'allow-licenses:\n  - MIT\n  - Apache-2.0\n  - BSD-3-Clause\n  - ISC\n' > .github/dependency-review-config.yml
slopstopper run security:licences; echo "exit $?"
rm -r .github
```

The inventory reads `scripts/requirements.txt`, finds that `requests`
is not installed in any interpreter beside it, and exits 2: a Python
tree that is not installed is a tree it cannot judge, and it refuses to
call that clean. `pip install -r scripts/requirements.txt` into a venv
beside the file and run it again to see `requests` (Apache-2.0) judged
against the four ids. The dependency review needs no such thing: it
reads GitHub's own dependency graph on the pull request, which is also
why it only ever runs in CI.

</details>

## Going further

- [Dependency vulnerability scanning](../security/VULNERABILITY.md):
  the dependency review, local/CI parity, and the fixed threshold
- [Licence inventory](../security/LICENCES.md): what each ecosystem is
  read from, the purl exemptions, and the exit-2 cases
- [Trivy's supported ecosystems](https://trivy.dev/latest/docs/coverage/language/),
  which is what "every manifest it knows" means
- Lesson 17 for the issue a red run on `main` opens, and lesson 20 for
  the licence boundary from the CLI's side

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `requests==2.19.1` in a requirements file. "The
assistant picked it." Cut to five CVE rows.

**Talking points.**

1. Why: slop you did not write; the version an agent remembers; a
   dependency changes after your code stops; every PR and every push.
2. Red on the demo; one manifest, one line, five findings in nothing
   you can read.
3. The report: Fixed In is the fix list; the dates in the ids.
4. The two fixes: what the gate needs, what you want; why MEDIUM does
   not block.
5. Put the demo back. Local versus CI: the day-old database; CI is the
   verdict.
6. Exercise: the allowlist, the inventory, and why it refuses an
   uninstalled tree.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/08.tape`. Zoom on the Fixed In column and on
"none CRITICAL/HIGH".

**Chapters.** `0:00 Why` · `1:30 Red` · `2:30 The report` ·
`4:00 Two fixes` · `6:00 Put it back` · `6:30 Local vs CI` ·
`7:30 Exercise` · `9:00 Next lesson`.

</details>
