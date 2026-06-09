# Install the install-slopstopper Claude Code skill

The companion to [`install.sh`](../../install.sh). Where `install.sh` drops the quality suite into a *repo*, [`install-skill.sh`](../../install-skill.sh) drops the install-slopstopper [skill](../../.claude/skills/install-slopstopper/SKILL.md) into your Claude Code *user profile* so it's available in every project on this machine.

Run it once per machine. After that, any Claude Code prompt asking to add SlopStopper (e.g. "install slopstopper", "add the slopstopper quality suite to this repo") invokes the skill automatically.

## What you need

- **Claude Code** — [claude.com/claude-code](https://claude.com/claude-code). The script can run before Claude Code is installed (it just creates `~/.claude/skills/install-slopstopper/SKILL.md`); the skill is picked up the first time Claude Code launches.
- **curl** — used to fetch the skill file from this repo.
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

A single file:

```
~/.claude/skills/install-slopstopper/SKILL.md
```

Nothing outside that path is touched. The script is atomic — it fetches to a temp file, validates the download looks like a Claude Code skill (frontmatter present), and only then overwrites the destination. An interrupted run cannot leave a half-file behind.

## How it gets used

Claude Code auto-discovers skills under `~/.claude/skills/`. The `description` field in the SKILL frontmatter is what Claude matches against incoming prompts — for this skill it covers "install slopstopper", "add the slopstopper quality suite", and any of the five loops (security, hygiene, reliability, runbooks, deployment).

You don't invoke the skill manually. Drop into any repo, ask Claude Code to add SlopStopper, and the skill activates and walks the install end-to-end: pre-flight checks, the install command, post-install URL config, a local-first verification loop, and a forward-looking gotcha table that handles predictable adoption issues during the local loop instead of after CI is red.

## Refresh

Re-run the same command any time. The script compares the downloaded SKILL.md against what's already installed and only overwrites if the content differs — safe to put in a periodic update routine, or just run when you remember.

## Uninstall

```bash
rm -rf ~/.claude/skills/install-slopstopper
```

Claude Code stops invoking the skill immediately on next prompt. No other state to clean up.

## Why this is shipped as a separate one-liner

The skill is *for installing SlopStopper into a target repo*. Committing it into target repos is circular (by the time the skill is there, you've done the install). User-global is the right shape — install once, every project benefits.

Bundling the skill into `install.sh` was considered and rejected for the same reason: `install.sh` runs *inside* a target repo, but the skill needs to be available *before* you're inside a target repo (you need it to know how to install). Two scripts, two scopes — clean separation.
