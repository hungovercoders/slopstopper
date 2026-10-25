# Lesson 2: Run your first check and read its report.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 02` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/02.mp4.
# Sandbox: demo
Output demos/.frames/02/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it red
Type "slopstopper run hygiene:complexity" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/High Complexity/,/Guidelines/p' .ss/reports/complexity/complexity-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See the raw exit code
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:complexity >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms "p = pathlib.Path('scripts/status.py'); s = p.read_text()" Enter
Type@8ms "start = s.index('def badge(status):'); end = s.index('\n\n\n', start)" Enter
Type@8ms `new = '''BADGES = {200: "ok", 201: "ok", 202: "ok", 204: "ok", 301: "ok", 302: "ok", 304: "ok",` Enter
Type@8ms '          400: "degraded", 401: "degraded", 403: "degraded", 404: "degraded", 408: "degraded", 429: "degraded",' Enter
Type@8ms '          500: "down", 502: "down", 503: "down"}' Enter
Enter
Enter
Type@8ms "def badge(status):" Enter
Type@8ms `    return BADGES.get(status, "unknown")'''` Enter
Type@8ms "p.write_text(s[:start] + new + s[end:])" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:complexity" Enter
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
Type 'slopstopper run hygiene:complexity >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
