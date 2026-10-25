# Lesson 1: Install slopstopper into a repo.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 01` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/01.mp4.
# Sandbox: demo
Output demos/.frames/01/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Run the installer with a profile
Type "slopstopper install --profile ui --no-topic | grep -v '^ ' | grep -E 'installed|pinned|refreshed|seeded|skipping|already|Added|appended'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Tour what landed
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git status --short" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat mise.toml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "wc -l < .ss/.workflows-installed" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat .ss/.installed-from" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See what the profile decided
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile show" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. See everything runnable
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type `slopstopper checks list --json | grep -c '"disabled": true'` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:entry-files | tail -1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout .gitignore package.json" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git clean -fdq" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
