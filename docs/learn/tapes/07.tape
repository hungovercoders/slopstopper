# Lesson 7: Static analysis.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 07` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/07.mp4.
# Sandbox: demo
Output demos/.frames/07/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# You will need
Type "semgrep --version" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 1. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:sast" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the finding
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Rule/,/^$/p' .ss/reports/sast/sast-report.md | head -3" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. Read the line as a reviewer would
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '76,80p' scripts/status.py" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Fix the code, not the rule
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms "p = pathlib.Path('scripts/status.py'); s = p.read_text()" Enter
Type@8ms `old = '''    subprocess.run("git commit -qam 'status: " + " ".join(summary) + "'", shell=True, check=False)'''` Enter
Type@8ms `p.write_text(s.replace(old, '''    subprocess.run(["git", "commit", "-qam", "status: " + " ".join(summary)], check=False)'''))` Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:sast" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Put the demo back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout scripts/status.py" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:sast >/dev/null 2>&1; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
