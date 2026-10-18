# Lesson 6: Secrets

**Goal.** Commit a fake key, watch Gitleaks catch it, see why deleting
it in a later commit does not help, and learn the fix that does.

## Why this check

`security:secrets` stops the single most expensive kind of slop: a
credential in the repo. It arrives in ordinary ways. An agent writes a
config file and fills the key field with something key-shaped "as an
example". A person commits `.env` because it was not in `.gitignore`
yet. A test fixture carries a token that was real once. The moment the
push lands, the credential is in a place it can be read from, and on a
public repo it is being read within minutes. Rotation is the only
remedy, and rotation is cheaper the sooner the leak is known. So the
check runs on every PR, before the push reaches anyone else, and it is
always blocking.

The tool is [Gitleaks](https://gitleaks.io/), which scans a repository's
**git history** for strings that match the shape of known credential
formats (an AWS access key starts `AKIA` and is twenty characters; a
GitHub token starts `ghp_`; a private key has a header) plus
high-entropy strings in the places secrets live. History is the point:
a secret removed in a later commit is still in the repository, and a
scan of the working tree alone would call that clean.

The check subprocess-invokes `gitleaks` with `--redact`, so the report
names the rule, the file, the line and the commit but never the value.
That matters because CI uploads the report as an artifact, and a check
whose job is to contain a leak must not widen its audience. Exit 0 is
no findings, exit 1 is findings, and exit 2 is Gitleaks not installed,
which `slopstopper doctor` reports with an install hint.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `gitleaks` on PATH. `brew install gitleaks`, or a release binary from
  [github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks/releases);
  the suite's own workflow pins one and this course's CI does the same.

<!-- learn -->
```sh
gitleaks version
```

```
8.30.1
```

## Steps

### 1. See it green

<!-- learn -->
```sh
task ss:security:secrets
```

```
🔑 Running secrets detection…
9:18AM INF 52 commits scanned.
9:18AM INF scanned ~2854337 bytes (2.85 MB) in 516ms
9:18AM INF no leaks found
✅ No secrets detected

📁 Reports saved to: .ss/reports/secrets/
   • secrets-report.md
```

Gitleaks says what it scanned: every commit, not the files on disk.

### 2. Write a fake key, and see that an uncommitted file is not scanned

The key below is built from two halves so that this page itself does
not trip the check when it is committed to this repository. The file
it writes holds a twenty-character `AKIA…` string, which is what the
`aws-access-token` rule matches. It is not a real key.

<!-- learn -->
```sh
mkdir -p scratch
printf 'AWS_ACCESS_KEY_ID=AKIA%s\n' LEARNSLOPSTOPPER > scratch/.env.example
task ss:security:secrets
```

```
9:18AM INF 52 commits scanned.
9:18AM INF no leaks found
✅ No secrets detected
```

Still green. The file is on disk but in no commit, and commits are what
the scanner reads. A secret becomes a finding the moment it is
committed, which is also the moment it starts to matter.

### 3. Commit it, and see it red

<!-- learn -->
```sh
git add scratch
git commit -q -m "wip: config"
```

<!-- learn: fails -->
```sh
task ss:security:secrets
```

```
9:18AM INF 53 commits scanned.
9:18AM WRN leaks found: 1
⚠️  Found 1 secret(s). Revoke and remove them immediately

📁 Reports saved to: .ss/reports/secrets/
   • secrets-report.md
task: Failed to run task "ss:security:secrets": exit status 1
```

### 4. Read the report

<!-- learn -->
```sh
sed -n '/| Rule/,/^$/p' .ss/reports/secrets/secrets-report.md
```

```
| Rule | Location | Commit | Description |
|------|----------|--------|-------------|
| aws-access-token | `scratch/.env.example:1` | c0597f9c | Identified a pattern that may indicate AWS credentials, r... |
```

The rule that matched, the file and line, and the commit. Not the
value: the report is written redacted, so nothing that reads it, a PR
comment, an artifact, a tracking issue, repeats the leak.

### 5. Delete the file in a new commit, and see it still red

This is what most people do first, and it is the step the lesson
exists for.

<!-- learn -->
```sh
git rm -q scratch/.env.example
git commit -q -m "remove the key"
```

<!-- learn: fails -->
```sh
task ss:security:secrets
```

```
9:19AM WRN leaks found: 1
⚠️  Found 1 secret(s). Revoke and remove them immediately
```

The key is gone from the working tree and present in the repository.
Anyone with a clone has it; `git log -p` shows it. The check is right
to stay red.

### 6. Fix it

The fix has two halves, in this order.

**Revoke the credential first.** Rotate the key, invalidate the token.
Nothing you do to the repository un-leaks a value that has been pushed,
so treat it as public from the moment the check went red. There is no
command for this step here; it happens wherever the key was issued.

**Then rewrite the history.** Here the two commits are local and were
never pushed, so dropping them is one line. On a pushed branch the same
job is `git filter-repo` or BFG followed by a force-push that the whole
team knows about.

<!-- learn -->
```sh
git reset -q --hard HEAD~2
task ss:security:secrets
```

```
9:19AM INF 52 commits scanned.
9:19AM INF no leaks found
✅ No secrets detected
```

Back to the commit count from step 1, and green.

## Checkpoint

<!-- learn -->
```sh
slopstopper run security:secrets >/dev/null; echo "exit $?"
```

```
exit 0
```

## Exercise

Commit the fake key again, and make the check pass with the commit
still in place, without touching the key.

<details>
<summary>Solution</summary>

A test fixture that looks like a secret and is not one is the honest
exception, and the honest way to say so is an allowlist in
`.gitleaks.toml` at the repo root:

```sh
mkdir -p scratch
printf 'AWS_ACCESS_KEY_ID=AKIA%s\n' LEARNSLOPSTOPPER > scratch/.env.example
git add scratch && git commit -q -m "wip: config"
printf '[extend]\nuseDefault = true\n\n[allowlist]\ndescription = "Fixtures for the course"\npaths = [ """scratch/.*""" ]\n' > .gitleaks.toml
task ss:security:secrets
```

Green, with the key committed. Two things to notice. `[extend]
useDefault = true` keeps every built-in rule; without it a custom
config replaces them and the check scans for nothing. And the allowlist
is by path with a description, which a reviewer can read; allowlisting
a specific value is for a documented example key, never for a real one
that was "already rotated". Clean up with `git reset -q --hard HEAD~1`
and `rm .gitleaks.toml`.

</details>

## Going further

- [Secrets detection](../security/SECRETS.md): the allowlist forms,
  what to do when a real secret is found, and how the report is kept
  redacted end to end
- [Gitleaks' rules](https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml),
  which is what "key-shaped" means in practice
- Lesson 17 for what the check does on `main`: the tracking issue it
  opens and closes

<details>
<summary>Episode script</summary>

**Length.** 9 to 11 minutes.

**Cold open (0:00).** A config file with `AWS_ACCESS_KEY_ID=AKIA…` in
a diff. "It's just an example." Cut to a cloud bill.

**Talking points.**

1. Why: ordinary ways a key lands in a repo; public within minutes;
   rotation is the only remedy; the earlier the cheaper.
2. Gitleaks scans history, not disk. Green run; the fake key
   uncommitted is still green.
3. Commit; red; the report without the value, and why.
4. Delete it in a new commit; still red; `git log -p` shows it.
5. The fix in order: revoke, then rewrite. Reset locally; filter-repo
   and a coordinated force-push on a shared branch.
6. Exercise: the allowlist, `useDefault = true`, path not value.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/06.tape`. Zoom on "52 commits scanned" versus "53",
and on the redacted report row.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 Uncommitted` ·
`3:30 Committed` · `5:00 Deleted, still red` · `6:30 Revoke, then
rewrite` · `8:30 Exercise` · `9:30 Next lesson`.

</details>
