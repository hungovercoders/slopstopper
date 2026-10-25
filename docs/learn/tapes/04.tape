# Lesson 4: Docs structure: every doc has a route.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 04` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/04.mp4.
# Sandbox: demo
Output demos/.frames/04/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it red
Type "slopstopper run hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Try a soft link, and see why it does not count
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nSee also [runbooks/RELEASE.md](runbooks/RELEASE.md).\n' >> docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Route it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '\nBefore you cut a release, read [runbooks/RELEASE.md](runbooks/RELEASE.md) for the tag, the push and what the tag message is for.\n' >> docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-structure" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the report, then put the demo back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep RELEASE .ss/reports/docs/docs-structure-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/README.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:docs-structure | grep 'Unrouted doc'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
