# Lesson 18: Agents: the install and triage skills.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 18` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/18.mp4.
# Sandbox: demo
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
Type "slopstopper install --no-topic --no-hooks | grep -A2 'Installing the SlopStopper Claude Code skills' | tail -1" Enter
Wait+Line@5m /(^|\s)\$$/
Type "find .claude -type f | sort" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the map of the triage skill
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep '^## ' .claude/skills/slopstopper-triage/SKILL.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Why the skills are a surface
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -c 'task ss:' .claude/skills/slopstopper-triage/references/reproduce.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -c '^name: slopstopper-' .claude/skills/*/SKILL.md | tr '\n' ' '" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout .gitignore package.json" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git clean -fdq" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
