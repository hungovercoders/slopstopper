# Lesson 17: CI: the workflows and the PR feedback loop.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 17` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/17.mp4.
Output demos/.frames/17/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Read one workflow
Type "sed -n '/^    steps:/,$p' .github/workflows/ss-hygiene-entry-files-check.yml | grep -E 'name:|uses:|run:'" Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 2. See every third-party action pinned to a commit
Type "clear" Enter
Type `grep -h "uses: " .github/workflows/ss-*.yml | grep -v "./.github/actions" | grep -v '@[0-9a-f]\{40\}' | wc -l` Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 3. The one summary comment
Type "clear" Enter
Type `grep -c '"SlopStopper' .github/workflows/ss-pr-summary.yml` Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 4. The issue a red check raises on main
Type "clear" Enter
Type `grep -n "conclusion == 'failure'" -A1 .github/workflows/ss-workflow-failure-issue.yml` Enter
Wait+Line@5m /^\$$/
Sleep 2s

# 5. The rest of the loop
Type "clear" Enter
Type 'grep -l "cron:" .github/workflows/ss-*.yml | wc -l' Enter
Type 'grep -n "cron:" .github/workflows/ss-reliability-smoke-tests.yml' Enter
Wait+Line@5m /^\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Type `grep -h "uses: " .github/workflows/ss-*.yml | grep -v "./.github/actions" | grep -v '@[0-9a-f]\{40\}' | wc -l` Enter
Wait+Line@5m /^\$$/
Sleep 2s
