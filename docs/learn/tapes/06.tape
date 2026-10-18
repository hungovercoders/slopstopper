# Lesson 6: Secrets.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 06` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/06.mp4.
Output demos/.frames/06/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# You will need
Type "gitleaks version" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 1. See it green
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:secrets" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Write a fake key, and see that an uncommitted file is not scanned
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf 'AWS_ACCESS_KEY_ID=AKIA%s\n' LEARNSLOPSTOPPER > scratch/.env.example" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:secrets" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Commit it, and see it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git add scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'git commit -q -m "wip: config"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:secrets" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Rule/,/^$/p' .ss/reports/secrets/secrets-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Delete the file in a new commit, and see it still red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git rm -q scratch/.env.example" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'git commit -q -m "remove the key"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:secrets" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git reset -q --hard HEAD~2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:secrets" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:secrets >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
