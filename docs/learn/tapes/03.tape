# Lesson 3: Entry files: the AGENTS.md-first model.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 03` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/03.mp4.
Output demos/.frames/03/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it green, and read the table
Type "task ss:hygiene:entry-files" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 2. Break it
Type "clear" Enter
Type "cat docs/README.md >> README.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. See it red
Type "clear" Enter
Type "task ss:hygiene:entry-files" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 4. Read the report
Type "clear" Enter
Type "sed -n '/How to fix/,$p' .ss/reports/entry-files/entry-file-size-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 5. Fix it
Type "clear" Enter
Type "git checkout README.md" Enter
Type "task ss:hygiene:entry-files" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Type "slopstopper run hygiene:entry-files | grep 'Every entry file'" Enter
Wait+Line@5m /^\$$/
Sleep 3s
