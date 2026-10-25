# Lesson 5: Docs accuracy and docs size.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 05` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/05.mp4.
# Sandbox: demo
Output demos/.frames/05/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See docs-accuracy red
Type "slopstopper run hygiene:docs-accuracy" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the report, then the line
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/## Issues/,/## Excluded/p' .ss/reports/docs/docs-accuracy-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '17,18p' docs/contributing.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -i.bak 's/Run `task ss:hygiene:docs` before you push; it is the two docs checks in/Run `slopstopper run hygiene:entry-files` and `slopstopper run hygiene:docs-structure` before you push; they are the two docs checks,/' docs/contributing.md && rm docs/contributing.md.bak" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-accuracy" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the size monitor
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-size" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. See the advisory fire, and the exit code not move
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "yes 'Notes on every default the checks ship with, and why each is what it is.' | head -c 160000 > docs/notes.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-size | sed -n '/Status/,/Reports/p'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:docs-size >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm docs/notes.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/contributing.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:docs-accuracy >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
