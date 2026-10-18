# Lesson 18: Agents: the install and triage skills.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 18` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/18.mp4.
Output demos/.frames/18/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Install the skills into a repo
Type "mkdir -p scratch/repo" Enter
Type `SLOPSTOPPER_REPO_RAW="file://$PWD" bash install-skill.sh scratch/repo | grep -A3 'Skills installed'` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "find scratch/repo -type f | sort" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 2. Read the map of the triage skill
Type "clear" Enter
Type "grep '^## ' scratch/repo/.claude/skills/slopstopper-triage/SKILL.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 4. Why the skills are a surface
Type "clear" Enter
Type "grep -c 'task ss:' scratch/repo/.claude/skills/slopstopper-triage/references/reproduce.md" Enter
Type "rm -r scratch" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Type "grep -c '^name: slopstopper-' .claude/skills/*/SKILL.md | tr '\n' ' '" Enter
Wait+Line@5m /^\$$/
Sleep 2s
