# Lesson 0: What slop is, and the five loops.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 00` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/00.mp4.
Output demos/.frames/00/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See the whole suite once
Type "slopstopper checks list" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. See the exit-code contract
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:nope; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:docs-structure; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. See the one surface
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task --list | grep 'ss:hygiene'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper checks list | grep -c 'hygiene:'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
