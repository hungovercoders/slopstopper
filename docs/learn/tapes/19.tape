# Lesson 19: Profiles and tailoring.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 19` (demos/render.sh), which
# starts the shell in a scratch clone of this repo with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/19.mp4.
# Sandbox: checkout
Output demos/.frames/19/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See what this repo resolves to, and why
Type "slopstopper profile show" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Ask for a suggestion
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile detect" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Read the whole mapping
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile list" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Switch the repo to the API profile
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -i 's/^profile: ui$/profile: api/' .slopstopper.yml" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile show" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Keep one of them
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms 'path = pathlib.Path(".slopstopper.yml")' Enter
Type@8ms "text = path.read_text()" Enter
Type@8ms 'path.write_text(text.replace("workflows:\n  disabled: []", "workflows:\n  disabled: []\n  enabled: [ss-reliability-broken-links-check.yml]"))' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile show" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout .slopstopper.yml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 6. Find the pin
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -A3 '^\[tools\]' mise.toml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper profile show | grep 'Profile: ui'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
