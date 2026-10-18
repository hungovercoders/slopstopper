# Lesson 4: Docs structure: every doc has a route.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 04` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/04.mp4.
Output demos/.frames/04/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it green
Type "task ss:hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Break it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '# Hygiene notes\n\nScratch notes about the hygiene checks.\n' > docs/hygiene/NOTES.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Try a soft link, and see why it does not count
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nSee also [NOTES.md](NOTES.md).\n' >> docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Route it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nBefore you tune a hygiene threshold, read [NOTES.md](NOTES.md) for the reasoning behind each default.\n' >> docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Read the report, then put the checkout back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep NOTES .ss/reports/docs/docs-structure-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/hygiene/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm docs/hygiene/NOTES.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-structure | grep 'docs are routed'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
