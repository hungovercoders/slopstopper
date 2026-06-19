# Install the SlopStopper Claude Code skills

The companion to [`install.sh`](../../install.sh). Where `install.sh` drops the whole quality suite into a repo, [`install-skill.sh`](../../install-skill.sh) targets just the Claude Code skill subset — useful for refreshing the playbooks without re-running the full installer.

Both scripts write skills at **project level** — into the adopter repo's `.claude/skills/` directory — so every contributor that clones the repo gets them automatically. Claude Code auto-discovers project-level skills the same way it does user-level ones.

After install, Claude Code auto-picks the right skill for any SlopStopper-related prompt:

| Skill | Triggered by prompts like… |
| ----- | -------------------------- |
| [`slopstopper-install`](../../.claude/skills/slopstopper-install/SKILL.md) | "add slopstopper to this repo", "install the slopstopper quality suite", "refresh slopstopper", "upgrade slopstopper", "pull in new slopstopper checks" |
| [`slopstopper-triage`](../../.claude/skills/slopstopper-triage/SKILL.md) | "fix this failing slopstopper check", "the complexity check is failing", "diagnose this DAST alert" |

`slopstopper-install` covers both first install and refresh — its mode-detection branch checks for `.slopstopper.yml` + `.ss/.workflows-installed` and routes to the right subset of steps. There's no separate `slopstopper-update` skill; the previous version was folded into `slopstopper-install` because install.sh is idempotent and the two flows shared 80% of their steps.

## What you need

- **Claude Code** — [claude.com/claude-code](https://claude.com/claude-code). Skills land at project level regardless of whether Claude Code is installed on the machine running the install; any contributor who has Claude Code will pick them up when they open the repo.
- **curl** — used to fetch each skill file from this repo.
- **Write access to the target repo** — the scripts create `.claude/skills/` under the repo root.

## Install

Skills are installed as part of `install.sh` automatically:

```bash
cd <your-repo>
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install.sh | bash
```

Pass `--no-skills` (or set `SLOPSTOPPER_NO_SKILLS=1`) to skip the skill subset.

To refresh just the skills without re-running the whole installer, use the standalone one-liner from inside the target repo:

```bash
cd <your-repo>
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh | bash
```

Or, two-step (review first):

```bash
curl -fsSL https://raw.githubusercontent.com/hungovercoders/slopstopper/main/install-skill.sh -o install-skill.sh
bash install-skill.sh
```

Or, explicit target directory:

```bash
bash install-skill.sh /path/to/repo
```

## What lands

Two files, one per skill, written under the target repo root:

```
<repo>/.claude/skills/slopstopper-install/SKILL.md
<repo>/.claude/skills/slopstopper-triage/SKILL.md
```

Nothing outside `<repo>/.claude/skills/slopstopper-*/` is touched. The script is atomic per skill — it fetches to a temp file, validates the download looks like a Claude Code skill (frontmatter present), and only then overwrites the destination. An interrupted run cannot leave a half-file behind.

**Commit the resulting files** alongside the workflows that `install.sh` lands. The `.gitignore` block that `install.sh` appends already includes a carve-out for `.claude/skills/` so repos with a blanket `.claude/*` ignore don't silently shadow them.

## Why project level (and what happened to user level)

A previous version of this script wrote skills to `~/.claude/skills/slopstopper-*`. That made the skills available globally on the installer's machine — but only on the installer's machine. Every other contributor cloning the repo would need to run the install themselves to get the playbooks. Asymmetric with how the workflows landed (project-level, committed, shared on clone), and a frequent source of "the suite is set up but Claude doesn't know about it" confusion.

The new model treats skills like every other slopstopper artefact: shipped into the repo, committed, shared by every contributor on git clone. Two scripts, one destination — no more user/project drift.

## What happened to `slopstopper-update`

The previous skill set was a trio: `slopstopper-install`, `slopstopper-update`, `slopstopper-triage`. The install and update skills overlapped heavily — install.sh is idempotent, the local-verify loop was identical, the "what just landed / what changed" inventory was the same surface. The genuinely-update-only content (re-applying customizations, diffing upstream for new knobs, spotting newly-shipped checks) has been folded into `slopstopper-install` as a "Refresh-only" section that the mode-detection branch routes to when `.slopstopper.yml` already exists. One skill, two flows, no churn maintaining two near-identical playbooks.

The old `slopstopper-update` directory is auto-removed by both `install.sh` and `install-skill.sh` (it's listed in the `OBSOLETE_SKILLS` array alongside the older single-skill `install-slopstopper` name).

## Migrating from the user-level install

If you previously ran `install-skill.sh` (older version) on this machine, you'll have stale copies at `~/.claude/skills/slopstopper-{install,update,triage}/SKILL.md`. Claude Code merges user-level and project-level skills, so the stale user-level copies will shadow the project-level ones until you remove them:

```bash
rm -rf ~/.claude/skills/slopstopper-install \
       ~/.claude/skills/slopstopper-update \
       ~/.claude/skills/slopstopper-triage
```

Both `install.sh` and `install-skill.sh` detect this scenario and print a one-line warning suggesting the cleanup. They don't execute the `rm` — deleting another contributor's user-level state without consent isn't something an installer should do silently — but they tell you exactly which command to run.

## How the skills get used

Claude Code auto-discovers skills under `.claude/skills/` in the project root. Each skill's `description` field in the SKILL frontmatter is what Claude matches against incoming prompts:

- A prompt about installing or refreshing slopstopper → `slopstopper-install` (its mode-detection branch handles the rest).
- A "fix this failing check" prompt → `slopstopper-triage` (the diagnostic table).

Per-invocation context stays small because Claude only loads the one skill that matches. Each skill ends with a "When to hand off" pointer to the other so the agent can escalate without you having to remember the names.

## Refresh

Re-run either script any time. Each compares the downloaded SKILL.md against what's installed and only writes if content differs.

## Uninstall

```bash
rm -rf .claude/skills/slopstopper-install .claude/skills/slopstopper-triage
```

Claude Code stops invoking the skills immediately on next prompt. No other state to clean up.

## When this runbook needs updating

- A skill is added to or removed from either script's `SKILLS` / `SKILL_NAMES` array → update the table at the top, the "What lands" file list, and the uninstall command.
- A skill is renamed → update all the above plus the migration sections.
- The migration cleanup mechanism changes → update the "What happened to slopstopper-update" and "Migrating from user-level" sections.
- The skills move back to user level (or a hybrid) → rewrite the "Why project level" section.

The AGENTS.md "When making changes" table in this repo cross-references this runbook for the relevant change classes.
