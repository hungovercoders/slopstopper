# Lesson 5: Docs accuracy and docs size.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 05` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/05.mp4.
Output demos/.frames/05/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See docs-accuracy green
Type "task ss:hygiene:docs-accuracy" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Break it twice in one line
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nRun `task ss:hygiene:tidy` after editing, then open [the tidy guide](TIDY.md).\n' >> docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-accuracy" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/## Issues/,/## Excluded/p' .ss/reports/docs/docs-accuracy-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-accuracy" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Read the size monitor
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-size" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 7. See the advisory fire, and the exit code not move
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "yes 'Notes on every default the hygiene checks ship with, and why.' | head -c 25000 > docs/hygiene/NOTES.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-size | sed -n '/Status/,/excluded/p'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:docs-size >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm docs/hygiene/NOTES.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:docs-accuracy >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
