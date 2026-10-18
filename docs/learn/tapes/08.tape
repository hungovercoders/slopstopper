# Lesson 8: Dependencies and licences.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 08` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/08.mp4.
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

# 1. See it green
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:vulnerability:all" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Pin a package the way an agent would
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'requests==2.19.1\n' > scratch/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:vulnerability:all" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^| Severity/,/^$/p; /^| CVE/,/^$/p' .ss/reports/vulnerability-all/vulnerability-all-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Take the fix the gate needs
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'requests==2.20.0\n' > scratch/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:vulnerability:all 2>/dev/null" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Then take the fix you want
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'requests==2.33.0\n' > scratch/requirements.txt" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:vulnerability:all 2>/dev/null" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep 'No vulnerabilities detected' .ss/reports/vulnerability-all/vulnerability-all-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. The licence gate, and why it is CI-only
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -c '^  - ' .github/dependency-review-config.yml" Enter
Wait+Line@5m /(^|\s)\$$/
Type "grep -c 'GPL' .github/dependency-review-config.yml" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:vulnerability:all >/dev/null 2>&1; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
