# Lesson 13: Core Web Vitals.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 13` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/13.mp4.
Output demos/.frames/13/
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
Type "task ss:reliability:cwv -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# 2. Read the budget
Type "clear" Enter
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. Add one blocking script
Type "clear" Enter
Type "printf 'const until = Date.now() + 1500;\nwhile (Date.now() < until) {}\n' > app/slow.js" Enter
Type `sed -i 's|<link rel="stylesheet" href="shared.css">|<script src="slow.js"></script>\n    <link rel="stylesheet" href="shared.css">|' app/index.html` Enter
Wait+Line@5m /^\$$/
Sleep 2s

Type "clear" Enter
Type "task ss:reliability:cwv -- http://localhost:8099" Enter
Wait+Line@5m /^\$$/
Sleep 3s

Type "clear" Enter
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 4. Fix it
Type "clear" Enter
Type "git checkout app/index.html" Enter
Type "rm app/slow.js" Enter
Type "task ss:reliability:cwv -- http://localhost:8099 >/dev/null" Enter
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Type 'kill "$(cat scratch/serve.pid)"' Enter
Type "rm -r scratch" Enter
Type "grep 'Core Web Vitals' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /^\$$/
Sleep 2s
