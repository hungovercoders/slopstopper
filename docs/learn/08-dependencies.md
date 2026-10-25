# Lesson 8: Dependencies and licences

**Goal.** Pin a package with a known CVE, watch Trivy catch it, read
the report's "Fixed In" column, take the fix, and see where the licence
gate sits and why it never runs locally.

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

A companion check, the dependency review, runs only in CI. It is
GitHub's own `dependency-review-action` on the pull request's manifest
diff, so it sees only what the PR adds, and it carries the licence gate:
a new dependency under a licence outside the allowlist in
`.github/dependency-review-config.yml` fails the PR. The two split the
job between "everything you have" and "what this change brings in".

Neither gates on a build tool's own dependencies: Trivy scans production
scope, and the review fails only on runtime scope (dev findings are
listed, not failed). An advisory in a devDependency reaches GitHub's
Dependabot alerts and nothing else, which is the intended division (the runtime is what ships), so
keep Dependabot's alerts and security updates on. The
[vulnerability doc](../security/VULNERABILITY.md#what-it-does-not-cover-and-who-does)
has the three-way table.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
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
Version: 0.76.0
```

## Steps

### 1. See it green

<!-- learn -->
```sh
task ss:security:vulnerability:all
```

```
🔍 Scanning dependencies for vulnerabilities…
2026-10-18T13:26:54Z	INFO	[vuln] Vulnerability scanning is enabled
2026-10-18T13:27:08Z	INFO	[npm] Run "npm install" to collect the license information of packages	dir="node_modules"
2026-10-18T13:27:08Z	INFO	Suppressing dependencies for development and testing. To display them, try the '--include-dev-deps' flag.
2026-10-18T13:27:08Z	INFO	Number of language-specific files	num=1
✅ No vulnerabilities detected

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
```

One manifest found, `package.json`, and its development dependencies
suppressed: Trivy's default is that a package only a build machine
installs is not a package you ship. Nothing in it carries a CVE today.

### 2. Pin a package the way an agent would

A requirements file for a tool script, with the version of `requests`
an assistant is likely to remember. It is from 2018.

<!-- learn -->
```sh
mkdir -p scratch
printf 'requests==2.19.1\n' > scratch/requirements.txt
```

<!-- learn: fails -->
```sh
task ss:security:vulnerability:all
```

```
🔍 Scanning dependencies for vulnerabilities…
2026-10-18T13:27:18Z	INFO	Number of language-specific files	num=2
2026-10-18T13:27:18Z	INFO	[pip] Detecting vulnerabilities...
⚠️  Found 1 CRITICAL/HIGH vulnerability(ies) (total 5)

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
task: Failed to run task "ss:security:vulnerability:all": exit status 1
```

Two manifests now, and the second one is red. One line of yours, five
findings, none of them in anything you can read in this repo.

### 3. Read the report

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

### 4. Take the fix the gate needs

<!-- learn -->
```sh
printf 'requests==2.20.0\n' > scratch/requirements.txt
task ss:security:vulnerability:all 2>/dev/null
```

```
🔍 Scanning dependencies for vulnerabilities…
ℹ️  Found 4 vulnerability(ies), none CRITICAL/HIGH

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
```

Trivy's log lines go to stderr, so dropping that stream leaves the
check's own verdict and keeps its exit code, which a pipe into `grep`
would replace. Green, and honest about it: four findings remain, reported and not
blocking. The threshold is where it is because a MEDIUM is usually
"needs a specific setup to exploit" and blocking on it would make the
gate something people route around, which lesson 19 has more to say
about. It is still listed, so a reviewer who reads the comment sees it.

### 5. Then take the fix you want

<!-- learn -->
```sh
printf 'requests==2.33.0\n' > scratch/requirements.txt
task ss:security:vulnerability:all 2>/dev/null
grep 'No vulnerabilities detected' .ss/reports/vulnerability-all/vulnerability-all-report.md
rm -r scratch
```

```
🔍 Scanning dependencies for vulnerabilities…
✅ No vulnerabilities detected

📁 Reports saved to: .ss/reports/vulnerability-all/
   • vulnerability-all-report.md
No vulnerabilities detected.
```

The `grep` is the assertion: exit 0 only says nothing blocking was
found, so a clean report is the thing to check for. The current release
as this lesson was written. When a later one
carries a CVE the harness that checks this course goes red on this
block, which is the lesson in miniature: the pin did not change, the
world did.

### 6. The licence gate, and why it is CI-only

<!-- learn -->
```sh
grep -c '^  - ' .github/dependency-review-config.yml
grep -c 'GPL' .github/dependency-review-config.yml
```

```
28
2
```

Twenty-eight SPDX ids allowed, and the only mention of the GPL family
is the comment that says it is left out. The dependency review reads
this file on every pull request, and a manifest change that introduces
a package under any other licence fails the run. It cannot be run
locally because it is GitHub's own action reading GitHub's own
dependency graph, which is also why it does not need Trivy or a task
shim; `install.sh` seeds the file once and a refresh never overwrites
it, so the list is yours. A licence the action cannot detect is
reported and never fails the run, because an unknown is not a
violation.

### 7. When local and CI disagree

This is the one check where they legitimately can. Trivy caches its
database for a day, and CI starts cold and pulls the newest one, so a
CVE published this morning fails the PR and not your laptop.
`trivy clean --vuln-db` then a rerun reproduces CI; the binary version
in the workflow's "Install Trivy" step is the other thing to compare.
Treat CI as the verdict.

## Checkpoint

<!-- learn -->
```sh
slopstopper run security:vulnerability:all >/dev/null 2>&1; echo "exit $?"
```

```
exit 0
```

## Exercise

Semgrep, which `security:sast` runs, is LGPL, and lesson 20 calls it
the suite's licence boundary. Work out whether the licence gate would
ever see it, and why.

<details>
<summary>Solution</summary>

```sh
grep -c 'LGPL' .github/dependency-review-config.yml
grep -rn 'semgrep' cli/pyproject.toml || echo "not a dependency"
```

The allowlist does not permit the LGPL, and the CLI does not depend on
Semgrep: it subprocess-invokes a binary the adopter installs, and the
wheel ships none of its code. The dependency review inspects manifest
changes only, so a tool that is never in a manifest never reaches it.
That is the same boundary Gitleaks and Trivy sit behind, and it is
deliberate: the suite can use a copyleft tool without the suite, or any
repo that adopts it, taking on the licence.

</details>

## Going further

- [Dependency vulnerability scanning](../security/VULNERABILITY.md):
  the dependency review and licence allowlist, local/CI parity, and
  the fixed threshold
- [Trivy's supported ecosystems](https://trivy.dev/latest/docs/coverage/language/),
  which is what "every manifest it knows" means
- Lesson 17 for the issue a red run on `main` opens, and lesson 20 for
  the licence boundary from the CLI's side

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `requests==2.19.1` in a diff. "The assistant
picked it." Cut to five CVE rows.

**Talking points.**

1. Why: slop you did not write; the version an agent remembers; a
   dependency changes after your code stops; every PR and every push.
2. Green; one manifest, dev deps suppressed.
3. The 2018 pin; red; five findings in nothing you can read.
4. The report: Fixed In is the fix list; the dates in the ids.
5. The two fixes: what the gate needs, what you want; why MEDIUM does
   not block.
6. The licence gate: twenty-eight ids, no GPL, CI-only and why.
7. Local versus CI: the day-old database; CI is the verdict.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/08.tape`. Zoom on the Fixed In column and on
"none CRITICAL/HIGH".

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 The pin` ·
`3:30 The report` · `5:00 Two fixes` · `6:30 Licences` ·
`8:00 Local vs CI` · `9:00 Next lesson`.

</details>
