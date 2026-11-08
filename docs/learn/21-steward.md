# Lesson 21: Across an organisation: the steward

<!-- learn-sandbox: demo -->

**Goal.** See what slopstopper-steward reads from a repo to find it,
judge its pin and work its findings, so that you can run one for your
organisation and know what it will and will not touch.

## Why this lesson

Everything so far is one repo at a time. A team with forty repos has
forty pins, and each one falls behind the day after a release; forty
sets of tracking issues, each waiting for someone to notice; and forty
copies of the skills, which fix a red check only when someone asks.
That is the slop of scale: nothing is wrong in any one repo, and the
whole estate drifts.

[slopstopper-steward](https://github.com/hungovercoders/slopstopper-steward)
is the operator for that. On a schedule, in your organisation's own
GitHub Actions, it finds every repo with slopstopper installed, moves
the pins that fell behind, and works the issues the checks raised, one
pull request each. It carries no check logic and no fix knowledge: the
pinned CLI rewrites and verifies the suite, and the `slopstopper-triage`
skill the install ships is what its agent works a finding with. Each
organisation runs its own copy; there is no service.

What makes that possible is a **contract**: a short list of things in an
adopter's repo and in the CLI that the steward reads, named in its
contract module and tested nightly against slopstopper's `main`. This
lesson walks that list from the adopter's side, in the demo, so every
surface the steward depends on is one you have seen.

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH.
Nothing in this lesson needs the steward installed or a token; running
one for real is the last section.

## Steps

### 1. Install the suite, and see what the steward can see

Install into the demo quietly, keeping the skills, so there is a suite
to discover. Then read the two files discovery is built on.

<!-- learn -->
```sh
slopstopper --quiet install --no-topic --no-hooks
grep slopstopper-cli mise.toml
cat .ss/.installed-from
```

```
"pipx:slopstopper-cli" = "0.29.0"
0.29.0
```

Three signals say "this repo has slopstopper": the `slopstopper` topic
the installer adds through `gh` (skipped here with `--no-topic`, because
the demo has no remote), the pin line in `mise.toml`, and
`.ss/.installed-from`, which the installer writes with its own version.
The pin is what runs; the marker is what wrote the suite. A pin below
the steward's target is an **upgrade order**: rewrite that one line,
run `slopstopper install` from the target CLI, and open the pull request
with the result.

### 2. The finding it works

A check that fails on `main` opens a tracking issue (lesson 17), and the
issue body carries a hidden marker naming the check. The steward reads
those issues, and when its agent reproduces one it asks the CLI for the
verdict as JSON rather than parsing the red line:

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:complexity --json
```

```
❌ 1 function(s) exceed CCN 15. Refactor them before merging.
{
  "check": "hygiene:complexity",
  "exit_code": 1,
  "status": "fail",
  "reports": [
    ".ss/reports/complexity/complexity-report.csv",
    ".ss/reports/complexity/complexity-report.md"
  ]
}
```

Trimmed to the verdict. The check, the exit code from lesson 0, and the
reports to read: that is what the agent is handed, and then it follows
the triage skill exactly as you did in lesson 18. A 2 here would be
"could not run", and the steward reports that as unverified rather than
as a finding.

### 3. The rest of the contract

Three more commands the steward calls, each with a `--json` form so it
never scrapes text meant for people:

<!-- learn -->
```sh
slopstopper profile expand library --json | head -4
slopstopper checks list --json | head -7
```

```
{
  "profile": "library",
  "workflows": [
    "ss-reliability-smoke-tests.yml",
[
  {
    "name": "hygiene:complexity",
    "summary": "Code complexity analyzer (Lizard wrapper).",
    "workflow": "ss-hygiene-complexity-check.yml",
    "disabled": false
```

`profile expand` is how it knows which workflows a repo of that shape
should carry after a refresh (lesson 19); `checks list` is how it names
a check from a workflow file. The third is `doctor --json`, whose
`needed_by` field says which check a missing tool belongs to:

<!-- learn -->
```sh
slopstopper doctor --json | python3 -c "
import json, sys
for t in json.load(sys.stdin)['tools']:
    if t['tool'] == 'semgrep': print(t['needed_by'], t['status'])"
```

```
security:sast missing
```

The steward runs in a bare clone with no Semgrep, Gitleaks or Trivy, so
without this it would report four checks red on every repo. With it,
they are reported as not verified here, which is true.

### 4. The marker a workaround leaves

When the triage skill works around a bug in slopstopper itself, it
leaves a marker on the workaround naming the upstream issue, in the
file's own comment syntax. The install skill's refresh step, and the
steward on an upgrade, collect on those: a pin moved, so the fix may
have shipped, and a workaround that outlives its bug keeps a check
degraded for nothing.

<!-- learn -->
```sh
grep -rho 'slopstopper-workaround: hungovercoders/slopstopper#<N>' .claude/skills | sort -u
```

```
slopstopper-workaround: hungovercoders/slopstopper#<N>
```

The two skills carry the convention byte for byte, because the steward
greps for exactly this string. It is also why lesson 20's change map
lists the skills as a surface: rename the marker in one place and the
steward stops finding workarounds everywhere.

### 5. What an upgrade order changes

Simulate a pin that fell behind, and read what the steward would open:

<!-- learn -->
```sh
sed -i.bak 's/"pipx:slopstopper-cli" = ".*"/"pipx:slopstopper-cli" = "0.28.0"/' mise.toml && rm mise.toml.bak
grep slopstopper-cli mise.toml
```

```
"pipx:slopstopper-cli" = "0.28.0"
```

The order is that one line rewritten to the target, then
`slopstopper install` run from the target version so the workflows,
shims, hook and skills are the ones that version ships, then the
repo's own `ss-*` checks on the pull request. The steward waits for
them. A check that goes red after the refresh is the one case where its
agent is called in on an upgrade; a green run is merged only when the
copy's `merge.auto` says so, and otherwise left for a person.

Running one is a copy of the steward repo in your organisation, with
your `orgs` in `steward.yml`, a GitHub App installed on the adopters,
and a first run in plan mode. The commands are the whole interface:

```sh
steward discover            # the adopters, and the evidence for each
steward plan                # the orders a run would open, nothing written
steward run --dry-run       # the same, as a report under .steward/reports/
steward contract ../slopstopper   # do the surfaces above still hold?
```

Everything it writes is a `steward/<order>` branch and a pull request;
it never pushes to a default branch, edits an issue or changes a
setting, and an issue labelled `steward:ignore` is left alone.

## Checkpoint

The checks the steward will report as unverified in a bare clone, read
the way it reads them:

<!-- learn -->
```sh
slopstopper doctor --json | python3 -c "
import json, sys
print(sorted({t['needed_by'] for t in json.load(sys.stdin)['tools'] if t['needed_by']}))"
```

```
['security:dast', 'security:sast', 'security:secrets', 'security:vulnerability:all']
```

Put the demo back:

<!-- learn -->
```sh
git checkout .gitignore package.json
git clean -fdq
```

## Exercise

Rename `.ss/.installed-from` in your head and list what breaks. Then
find the one place in this repository that names every surface the
steward reads, so a change there is reviewed as a contract change.

<details>
<summary>Solution</summary>

Discovery loses one of its three signals, so a repo with no topic and
a pin the steward cannot parse would be missed; nothing else breaks,
because the pin still says which version runs. The list is the steward
row of [the change map](../contributing/CHANGE_MAP.md), which points at
[STEWARD.md](../architecture/STEWARD.md); the steward's own CI checks
the same list against this repo's `main` nightly, so a rename here goes
red there within a day. Run `steward contract <this checkout>` from a
steward checkout before merging one.

</details>

## Going further

- [The steward and the suite](../architecture/STEWARD.md): the split of
  concerns, the full contract and the loop as a diagram
- [The steward's setup runbook](https://github.com/hungovercoders/slopstopper-steward/blob/main/docs/runbooks/SETUP.md):
  the fork, the GitHub App, the agent user and the first plan-only run
- Lesson 18 for the two skills the steward hands its agent, and lesson
  19 for the pin it moves

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** A GitHub organisation page, forty repos, each with
a slopstopper badge row. Click three: three different pin versions, two
with open tracking issues nobody has touched. "Nothing is wrong in any
one of them."

**Talking points.**

1. The slop of scale, and why the fix is an operator, not a bigger
   suite.
2. Discovery: the topic, the pin, the marker.
3. The finding as JSON, and the agent handed the triage skill.
4. The contract: three more commands, and the nightly test that keeps
   them true.
5. An upgrade order, line by line, and what the steward never does.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/21.tape`. Cut once to the steward doc's loop diagram
while talking point 1 lands, and once to a `steward/<order>` pull
request on a real adopter.

**Chapters.** `0:00 Forty repos` · `1:30 Discovery` · `3:00 The finding` ·
`4:30 The contract` · `6:30 An upgrade order` · `8:00 Running one` ·
`9:00 Next steps`.

</details>
