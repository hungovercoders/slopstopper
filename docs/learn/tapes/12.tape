# Lesson 12: Accessibility.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 12` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/12.mp4.
# Sandbox: demo
Output demos/.frames/12/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the demo and see it red
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:accessibility -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the element
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -n '<img' app/history.html" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type `sed -i.bak 's|<img src="uptime.svg" width="480" height="60">|<img src="uptime.svg" width="480" height="60" alt="Uptime over the last ninety days: a flat line at 100% with two dips">|' app/history.html && rm app/history.html.bak` Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:accessibility -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/history.html" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf test-results" Enter
Wait+Line@5m /(^|\s)\$$/
Type "out=$(slopstopper run reliability:accessibility -- http://localhost:8099 2>&1 || true)" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf scratch test-results" Enter
Wait+Line@5m /(^|\s)\$$/
Type `echo "$out" | grep 'CRITICAL'` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
