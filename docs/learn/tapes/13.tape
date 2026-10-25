# Lesson 13: Core Web Vitals.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 13` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/13.mp4.
# Sandbox: demo
Output demos/.frames/13/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Serve the demo and see it green
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:cwv -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the budget
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Add one blocking script
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'const until = Date.now() + 1500;\nwhile (Date.now() < until) {}\n' > app/slow.js" Enter
Wait+Line@5m /(^|\s)\$$/
Type `sed -i.bak 's|<link rel="stylesheet" href="style.css">|<script src="slow.js"></script>\n  <link rel="stylesheet" href="style.css">|' app/index.html && rm app/index.html.bak` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:cwv -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/index.html" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm app/slow.js" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run reliability:cwv -- http://localhost:8099 >/dev/null 2>&1" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep 'Core Web Vitals' .ss/reports/cwv/cwv-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
