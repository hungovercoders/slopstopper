# Lesson 20: Inside slopstopper: add a check

**Goal.** Register a new check in the CLI, let the test suite tell you
the other surfaces it must be wired into, and understand the shape
every check shares.

## Why this lesson

The last lesson is the one for contributors, and it is about the
repository's own slop guard. A check is one Python module, but a check
that ships needs a workflow, a task shim, a line in the installer, a
row in the profile map, a badge label, two trigger lists, a labeler
entry, a doc heading, a test file, and mentions in both skills and on
the site. The change map lists them. A list in a table cell is prose,
and prose does not fail a build; when two checks landed touching
twenty-four files against a thirteen-item list, one of them shipped
with a badge and a workflow and no documentation. So the list became a
test keyed off the registry: a check that exists in the CLI and is
missing from any surface fails with a message naming the surface.

Every check also keeps one shape. It is stdlib Python, it
subprocess-invokes its tool if it has one (the licence boundary:
Semgrep is LGPL, Gitleaks and Trivy are their own projects, and the
CLI ships none of their code), it writes under `.ss/reports/<check>/`,
it carries a Configuration block in its docstring for every config key
it reads, and it exits 0, 1 or 2 by the contract from lesson 0. The
four Playwright-backed checks share their whole flow through one
module and differ only in a spec name and some wording, which is why
copying `smoke.py` is the way to start one.

## You will need

The checkout from the [syllabus](README.md). `task contributing:test`
creates the CLI's test environment on first use.

## Steps

### 1. Read the registry

<!-- learn -->
```sh
sed -n '/^REGISTRY/,/^}/p' cli/slopstopper/checks/__init__.py | grep -c '": '
```

```
23
```

Twenty-three checks, each a `<category>:<name>` key mapped to a
module's `run`. The key is what `slopstopper run` and the `task ss:*`
shims use, so this dictionary is the one list every other surface is
checked against.

### 2. Add a check to the registry and nothing else

A copy of the smoke check under a new name, registered in the
dictionary. This is exactly how far a hurried pull request gets.

<!-- learn -->
```sh
sed 's/smoke/probe/g; s/Smoke/Probe/g; s/SMOKE/PROBE/g' cli/slopstopper/checks/smoke.py > cli/slopstopper/checks/probe.py
python3 - <<'PY'
import pathlib
path = pathlib.Path("cli/slopstopper/checks/__init__.py")
text = path.read_text()
text = text.replace("    openapi,\n", "    openapi,\n    probe,\n", 1)
text = text.replace('    "reliability:smoke": smoke.run,\n', '    "reliability:smoke": smoke.run,\n    "reliability:probe": probe.run,\n', 1)
path.write_text(text)
PY
grep -n "probe" cli/slopstopper/checks/__init__.py
```

```
50:    probe,
79:    "reliability:probe": probe.run,
```

### 3. Let the registration test name every surface you missed

<!-- learn: fails -->
```sh
task contributing:test -- -k registration -q
```

```
E       AssertionError: add a DOC_HEADINGS row for: ['reliability:probe']; remove: []
E       AssertionError: reliability:probe is not in profiles.CHECK_WORKFLOWS
E       AssertionError: Taskfile.ss.yml has no `reliability:probe:` target
E       AssertionError: None is not in suite.GENERIC_WORKFLOWS, so adopters never get reliability:probe
E       AssertionError: None has no badges.WORKFLOW_DISPLAY entry; its README badge would fall back to a title-cased filename
E       AssertionError: reliability:probe: add 'cli/slopstopper/checks/probe.py' under the `reliability:` label in .github/labeler.yml
E       AssertionError: reliability:probe (probe.py) has no cli/tests/checks/test_probe.py
```

Seven failures, each naming a file and what to add to it: the doc
heading the test looks for, the profile map, the task shim, the
installer's workflow list, the badge label, the labeler, the test
module. Fix one and run again, and the next failure is the next
surface. The two `workflow_run` trigger lists from lesson 17 are
covered by a sibling test, and the generated check tables and README
badges by another, which fails while they are stale until
`task contributing:tables` regenerates them.

### 4. Read the change map

The test enforces what a test can. The rest of the row is the site
pages, the install runbook and the two skills, which name specific
checks and silently rot when one is added without them.

<!-- learn -->
```sh
grep -c "slopstopper-install\|slopstopper-triage" docs/contributing/CHANGE_MAP.md
```

```
7
```

Seven mentions, because the skills are the surface an agent reads
first, and a skill that does not know a check exists will never
suggest it or fix it.

### 5. Remove the half-registered check

<!-- learn -->
```sh
git checkout cli/slopstopper/checks/__init__.py
rm cli/slopstopper/checks/probe.py
task contributing:test -- -k registration -o addopts= -q
```

```
…
185 passed, 1805 deselected in 0.54s
```

### 6. Know the conventions the rest of a change follows

- **Conventional Commits.** `feat:` and `fix:` cut a CLI release through
  release-please; `docs:` and `chore:` do not, which is why this course
  lands as `docs(learn):` commits.
- **Third-party actions pinned to a SHA**, as lesson 17 counted.
- **`task ss:hygiene:test` before a push**, which the pre-push hook
  runs, and `task contributing:test` whenever `cli/` changes.
- **Budgets are the feature.** When entry-files or docs-structure
  fails, content moves deeper and gets a route; the budgets do not
  move.

## Checkpoint

<!-- learn -->
```sh
task contributing:test -- -k registration -o addopts= -q
```

```
…
185 passed, 1805 deselected in 0.54s
```

## Exercise

Make the seven failures six by wiring the probe into one surface, then
put everything back.

<details>
<summary>Solution</summary>

Repeat step 2, then add a shim to `Taskfile.ss.yml` next to the smoke
one:

```yaml
  reliability:probe:
    desc: Probe (a copy of smoke, for lesson 20)
    cmds:
      - slopstopper run reliability:probe -- {{.CLI_ARGS}}
```

`task contributing:test -- -k registration -q` now fails six times,
and the Taskfile assertion is gone. Revert with `git checkout
Taskfile.ss.yml cli/slopstopper/checks/__init__.py` and
`rm cli/slopstopper/checks/probe.py`.

</details>

## Going further

- [The change map](../contributing/CHANGE_MAP.md): every surface for
  every kind of change, not only a new check
- [Pitfalls](../contributing/PITFALLS.md): what has bitten before
- [Contributing](../contributing/README.md): the exit codes, the
  commit conventions and the test suite
- The registration test itself, `cli/tests/test_check_registration.py`,
  whose docstring tells the story this lesson summarised

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A pull request adding a check: a badge, a
workflow, a marketing bullet. `docs/`: nothing.

**Talking points.**

1. Why: the change map as prose did not fail a build; now it is a test
   keyed off the registry.
2. The registry; twenty-three keys; the shape every check shares and
   the licence boundary.
3. Copy smoke, register it; seven failures, each naming a surface.
4. The surfaces a test cannot cover: the site, the runbook, the skills.
5. Remove it; green. The conventions: commits, pins, the hook, budgets.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/20.tape`. Zoom on the seven assertion messages.

**Chapters.** `0:00 Why` · `1:30 The registry` · `3:00 Half a check` ·
`5:00 The change map` · `6:30 Clean up` · `7:30 Conventions` ·
`9:00 The end`.

</details>
