# Lesson 7: Static analysis.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 07` (demos/render.sh), which
# starts the shell in a scratch clone with the CLI on PATH, fills in
# the theme from demos/theme.json, and writes dist/learn/07.mp4.
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

# 1. See it green
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:sast" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Write the line that always looks fine
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/report.py <<'EOF'" Enter
Type@8ms "import subprocess" Enter
Type@8ms "import sys" Enter
Enter
Enter
Type@8ms "def render(path):" Enter
Type@8ms '    cmd = "wkhtmltopdf " + path + " out.pdf"' Enter
Type@8ms "    subprocess.run(cmd, shell=True, check=True)" Enter
Enter
Enter
Type@8ms 'if __name__ == "__main__":' Enter
Type@8ms "    render(sys.argv[1])" Enter
Type@8ms "EOF" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 3. See it red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:sast" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the finding
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/| Rule/,/^$/p' .ss/reports/sast/sast-report.md | head -3" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Fix the code, not the rule
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/report.py <<'EOF'" Enter
Type@8ms "import subprocess" Enter
Type@8ms "import sys" Enter
Enter
Enter
Type@8ms "def render(path):" Enter
Type@8ms '    subprocess.run(["wkhtmltopdf", path, "out.pdf"], check=True)' Enter
Enter
Enter
Type@8ms 'if __name__ == "__main__":' Enter
Type@8ms "    render(sys.argv[1])" Enter
Type@8ms "EOF" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run security:sast >/dev/null 2>&1; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
