# Install the SlopStopper Claude Code skill trio

The companion to [`install.sh`](../../install.sh). Where `install.sh` drops the quality suite into a *repo*, [`install-skill.sh`](../../install-skill.sh) drops the SlopStopper [skill trio](../../.claude/skills/) into your Claude Code *user profile* so it's available in every project on this machine.

Run it once per machine; re-run any time to refresh. After that, Claude Code auto-discovers the right skill for any SlopStopper-related prompt:

| Skill | Triggered by prompts like… |
| ----- | -------------------------- |
| [`slopstopper-install`](../../.claude/skills/slopstopper-install/SKILL.md) | "add slopstopper to this repo", "install the slopstopper quality suite" |
| [`slopstopper-update`](../../.claude/skills/slopstopper-update/SKILL.md) | "refresh slopstopper", "upgrade slopstopper", "pull in new slopstopper checks" |
| [`slopstopper-triage`](../../.claude/skills/slopstopper-triage/SKILL.md) | "fix this failing slopstopper check", "the complexity check is failing", "diagnose this DAST alert" |

## What you need

- **Claude Code** — [claude.com/claude-code](https://claude.com/claude-code). The script can run before Claude Code is installed (it just writes files under `~/.claude/skills/`); Claude Code picks them up the first time it launches.
- **curl** — used to fetch each skill file from this repo.
- **Write access to `~/.claude/skills/`** — the script creates the directory if it doesn't exist.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
```

Or, two-step (review first):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
bash install-skill.sh
```

## What lands

Three files, one per skill:

```
~/.claude/skills/slopstopper-install/SKILL.md
~/.claude/skills/slopstopper-update/SKILL.md
~/.claude/skills/slopstopper-triage/SKILL.md
```

Nothing outside `~/.claude/skills/slopstopper-*/` is touched. The script is atomic per skill — it fetches to a temp file, validates the download looks like a Claude Code skill (frontmatter present), and only then overwrites the destination. An interrupted run cannot leave a half-file behind.

## Migration from the previous single-skill layout

If you previously ran an older version of this script that installed a single `install-slopstopper` skill, the trio installer removes the obsolete directory (`~/.claude/skills/install-slopstopper/`) automatically after the trio is in place. You'll see a one-line `ℹ  Removed obsolete skill: install-slopstopper (replaced by slopstopper-install)` notice in stdout.

The new `slopstopper-install` covers everything the old `install-slopstopper` did (install pre-flight, install command, post-install config, Map Pattern setup, badges, local-first verification loop). The per-check failure handling that used to live inside the install skill has moved to `slopstopper-triage`. The new `slopstopper-update` covers the refresh flow that wasn't previously a first-class skill.

## How the trio gets used

Claude Code auto-discovers skills under `~/.claude/skills/`. Each skill's `description` field in the SKILL frontmatter is what Claude matches against incoming prompts — so different prompt shapes trigger different skills automatically:

- A first-time install prompt loads only `slopstopper-install` (the install playbook).
- A "fix this failing check" prompt loads only `slopstopper-triage` (the diagnostic table).
- A "refresh slopstopper" prompt loads only `slopstopper-update` (the upgrade flow).

Per-invocation context stays small because Claude only loads the one skill that matches. The trio is a navigable mesh — each skill ends with a "When to hand off" pointer to the other two so the agent can escalate or jump between flows without you having to remember the names.

## Refresh

Re-run the same command any time. The script compares each downloaded SKILL.md against what's already installed and only writes if the content differs. Safe to put in a periodic update routine, or just run when you remember.

## Uninstall

```bash
rm -rf ~/.claude/skills/slopstopper-install ~/.claude/skills/slopstopper-update ~/.claude/skills/slopstopper-triage
```

Claude Code stops invoking the skills immediately on next prompt. No other state to clean up.

## Why the trio is shipped as a separate one-liner

The skills are *for* installing/updating/triaging SlopStopper in target repos. Committing them into target repos is circular (by the time the skills are there, the install they describe is already done). User-global is the right shape — install once, every project benefits.

Bundling the skills into `install.sh` was considered and rejected for the same reason: `install.sh` runs *inside* a target repo, but the skills need to be available *before* you're inside a target repo (you need them to know how to install). Two scripts, two scopes — `install.sh` for the suite-in-the-repo, `install-skill.sh` for the skills-on-the-machine.

## When this runbook needs updating

- A skill is added to or removed from `install-skill.sh`'s `SKILLS` array → update the table at the top and the "What lands" file list.
- A skill is renamed → update both lists plus the uninstall command.
- The migration cleanup mechanism changes → update the "Migration" section.
- The trio's mutual hand-off pattern changes → update the "How the trio gets used" section.

The AGENTS.md "When making changes" table in this repo cross-references this runbook for the relevant change classes.
