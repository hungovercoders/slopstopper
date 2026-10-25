# Lesson 8: Dependencies and licences.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 08` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/08.mp4.
# Sandbox: demo
Output demos/.frames/08/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# You will need
Type "trivy --version | head -1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 1. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:vulnerability:all" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat scripts/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 2. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^| Severity/,/^$/p; /^| CVE/,/^$/p' .ss/reports/vulnerability-all/vulnerability-all-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Take the fix the gate needs
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'requests==2.20.0\n' > scripts/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:vulnerability:all 2>/dev/null" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Then take the fix you want
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'requests==2.33.0\n' > scripts/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:vulnerability:all 2>/dev/null" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep 'No vulnerabilities detected' .ss/reports/vulnerability-all/vulnerability-all-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Put the demo back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout scripts/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:vulnerability:all >/dev/null 2>&1; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
