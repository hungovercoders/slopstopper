# Lesson 10: Dynamic scanning.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 10` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/10.mp4.
# Sandbox: demo
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

# 1. Relax one page, and write it down
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms "p = pathlib.Path('app/_headers'); text = p.read_text()" Enter
Type@8ms "head, block = text.split('/history.html\n', 1)" Enter
Type@8ms `block = block.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';", 1)` Enter
Type@8ms "p.write_text(head + '/history.html\n' + block)" Enter
Type@8ms "doc = pathlib.Path('docs/security/CSP_EXCEPTIONS.md'); t = doc.read_text()" Enter
Type@8ms "entry = '''### `/history.html`" Enter
Enter
Type@8ms "- **Origin allowed:** `https://charts.example.com`" Enter
Type@8ms "- **Directives added:** `img-src https://charts.example.com`, `style-src 'unsafe-inline'`" Enter
Type@8ms "- **Loader SRI:** `n/a`" Enter
Type@8ms "- **Why:** the uptime chart is rendered by the charts service and sets inline styles on its container" Enter
Type@8ms "- **Approved by:** nobody yet" Enter
Type@8ms "- **Data leaving site:** visitor IP and User-Agent when the chart image is fetched" Enter
Type@8ms "- **Refresh policy:** n/a" Enter
Type@8ms "'''" Enter
Type@8ms "doc.write_text(t.replace('None yet: every path serves the baseline policy.\n', entry, 1))" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:csp-exceptions | tail -1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 2. Serve the demo and scan it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^# DAST/,/Low Risk Alerts/p' .ss/reports/dast/dast-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Take the ledger away
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/security/CSP_EXCEPTIONS.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Accept it with a reason, the other way
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "mkdir -p .zap" Enter
Wait+Line@5m /(^|\s)\$$/
Type "printf '10055-6\tIGNORE\t# inline styles on /history.html: the chart container sets them; the page allows nothing else\n' > .zap/rules.tsv" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:dast -- http://localhost:8099" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Put the demo back
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf .zap" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout app/_headers" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:dast -- http://localhost:8099 2>&1 | grep -E 'Found|No blocking'" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -rf scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
