# Lesson 12: Accessibility.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 12` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/12.mp4.
Output demos/.frames/12/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the site and see it green
Type "mkdir -p scratch" Enter
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Type "sleep 2" Enter
Type "task ss:reliability:accessibility -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 2. Remove the alternative text from the homepage image
Type "clear" Enter
Type `sed -i 's/ alt="[^"]*"//' app/index.html` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:accessibility -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 3. Fix it
Type "clear" Enter
Type "git checkout app/index.html" Enter
Type "task ss:reliability:accessibility -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Type "out=$(task ss:reliability:accessibility -- http://localhost:8099 2>&1)" Enter
Type 'kill "$(cat scratch/serve.pid)"' Enter
Type "rm -r scratch" Enter
Type `echo "$out" | grep 'passed'` Enter
Wait+Line@5m /^\$$/
Sleep 2s
