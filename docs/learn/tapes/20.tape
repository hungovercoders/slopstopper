# Lesson 20: Inside slopstopper: add a check.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 20` (demos/render.sh), which
# starts the shell in a scratch clone of this repo with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/20.mp4.
# Sandbox: checkout
Output demos/.frames/20/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Read the registry
Type `sed -n '/^REGISTRY/,/^}/p' cli/slopstopper/checks/__init__.py | grep -c '": '` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 2. Add a check to the registry and nothing else
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed 's/smoke/probe/g; s/Smoke/Probe/g; s/SMOKE/PROBE/g' cli/slopstopper/checks/smoke.py > cli/slopstopper/checks/probe.py" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms 'path = pathlib.Path("cli/slopstopper/checks/__init__.py")' Enter
Type@8ms "text = path.read_text()" Enter
Type@8ms 'text = text.replace("    openapi,\n", "    openapi,\n    probe,\n", 1)' Enter
Type@8ms `text = text.replace('    "reliability:smoke": smoke.run,\n', '    "reliability:smoke": smoke.run,\n    "reliability:probe": probe.run,\n', 1)` Enter
Type@8ms "path.write_text(text)" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'grep -n "probe" cli/slopstopper/checks/__init__.py' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Let the registration test name every surface you missed
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task contributing:test -- -k registration -q" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the change map
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'grep -c "slopstopper-install\|slopstopper-triage" docs/contributing/CHANGE_MAP.md' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Remove the half-registered check
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout cli/slopstopper/checks/__init__.py" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm cli/slopstopper/checks/probe.py" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task contributing:test -- -k registration -o addopts= -q" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task contributing:test -- -k registration -o addopts= -q" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
