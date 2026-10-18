# Lesson 2: Run your first check and read its report.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 02` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/02.mp4.
Output demos/.frames/02/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See it green
Type "task ss:hygiene:complexity" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Break it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch && cat > scratch/triage.py <<'PY'" Enter
Type@8ms "def route(code):" Enter
Type@8ms '    if code == 1: return "a"' Enter
Type@8ms '    if code == 2: return "b"' Enter
Type@8ms '    if code == 3: return "c"' Enter
Type@8ms '    if code == 4: return "d"' Enter
Type@8ms '    if code == 5: return "e"' Enter
Type@8ms '    if code == 6: return "f"' Enter
Type@8ms '    if code == 7: return "g"' Enter
Type@8ms '    if code == 8: return "h"' Enter
Type@8ms '    if code == 9: return "i"' Enter
Type@8ms '    if code == 10: return "j"' Enter
Type@8ms '    if code == 11: return "k"' Enter
Type@8ms '    if code == 12: return "l"' Enter
Type@8ms '    if code == 13: return "m"' Enter
Type@8ms '    if code == 14: return "n"' Enter
Type@8ms '    if code == 15: return "o"' Enter
Type@8ms '    if code == 16: return "p"' Enter
Type@8ms '    return "z"' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:complexity" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/High Complexity/,/Guidelines/p' .ss/reports/complexity/complexity-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. See the raw exit code
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:complexity >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Fix it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:complexity" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:complexity >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
