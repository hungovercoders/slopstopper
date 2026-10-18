# Lesson 11: Smoke and end-to-end.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 11` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/11.mp4.
Output demos/.frames/11/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the site and see smoke green
Type "mkdir -p scratch" Enter
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Type "sleep 2" Enter
Type "task ss:reliability:smoke -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 2. Remove a page the list still names
Type "clear" Enter
Type "rm app/tools.html" Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:smoke -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/tools.html" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. See end-to-end green
Type "clear" Enter
Type "task ss:reliability:e2e -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 4. Point a navigation link at a page that does not exist
Type "clear" Enter
Type `sed -i 's|href="tools.html"|href="nope.html"|' app/index.html` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:e2e -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "git checkout app/index.html" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Type "out=$(task ss:reliability:smoke -- http://localhost:8099 2>&1)" Enter
Type 'kill "$(cat scratch/serve.pid)"' Enter
Type "rm -r scratch" Enter
Type `echo "$out" | grep 'passed'` Enter
Wait+Line@5m /^\$$/
Sleep 2s
