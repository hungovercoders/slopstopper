# Lesson 10: Dynamic scanning.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 10` (demos/render.sh), which
# starts the shell in a scratch clone of this repo with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/10.mp4.
# Sandbox: checkout
Output demos/.frames/10/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# You will need
Type "docker --version" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 1. Serve the site and scan it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^## Summary/,/Low Risk Alerts/p' .ss/reports/dast/dast-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Take the ledger away
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm docs/security/CSP_EXCEPTIONS.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Accept it with a reason, the other way
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p .zap" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '10055-6\tIGNORE\t# inline styles on /feedback.html: the Giscus widget sets them; the page allows nothing else\n' > .zap/rules.tsv" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/security/CSP_EXCEPTIONS.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf .zap" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:dast -- http://localhost:8099 >/dev/null 2>&1; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
