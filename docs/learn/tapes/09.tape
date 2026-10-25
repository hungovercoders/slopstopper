# Lesson 9: Headers and CSP.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 09` (demos/render.sh), which
# starts the shell in the demo repo `slopstopper demo` writes with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/09.mp4.
# Sandbox: demo
Output demos/.frames/09/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. See the headers the site sends
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 2" Enter
Wait+Line@5m /(^|\s)\$$/
Type "curl -sI http://localhost:8099/ | grep -iE 'content-security|x-frame|nosniff|referrer'" Enter
Wait+Line@5m /(^|\s)\$$/
Type "curl -sI http://localhost:8099/history.html | grep -iE 'content-security'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 2. See the drift check red
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:csp-exceptions" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^## .* Errors/,/Mismatched origins/p' .ss/reports/csp/csp-exceptions-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 4. Document it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms "doc = pathlib.Path('docs/security/CSP_EXCEPTIONS.md')" Enter
Type@8ms "text = doc.read_text()" Enter
Type@8ms "entry = '''### `/history.html`" Enter
Enter
Type@8ms "- **Origin allowed:** `https://charts.example.com`" Enter
Type@8ms "- **Directives added:** `img-src https://charts.example.com`" Enter
Type@8ms "- **Loader SRI:** `n/a`" Enter
Type@8ms "- **Why:** the uptime chart on the history page is rendered by the charts service" Enter
Type@8ms "- **Approved by:** nobody yet" Enter
Type@8ms "- **Data leaving site:** visitor IP and User-Agent when the chart image is fetched" Enter
Type@8ms "- **Refresh policy:** n/a" Enter
Type@8ms "'''" Enter
Type@8ms "doc.write_text(text.replace('None yet: every path serves the baseline policy.\n', entry, 1))" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:csp-exceptions" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout docs/security/CSP_EXCEPTIONS.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Audit the site's headers as an API would be audited
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:api-headers -- http://localhost:8099 --path /" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 6. Build an API with the commonest CORS mistake
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/api.py <<'PY'" Enter
Type@8ms "from http.server import BaseHTTPRequestHandler, HTTPServer" Enter
Enter
Type@8ms "class Api(BaseHTTPRequestHandler):" Enter
Type@8ms "    def do_GET(self):" Enter
Type@8ms "        self.send_response(200)" Enter
Type@8ms '        self.send_header("Content-Type", "application/json")' Enter
Type@8ms '        self.send_header("Access-Control-Allow-Origin", "*")' Enter
Type@8ms '        self.send_header("Access-Control-Allow-Credentials", "true")' Enter
Type@8ms "        self.end_headers()" Enter
Type@8ms `        self.wfile.write(b'{"ok": true}')` Enter
Enter
Type@8ms "    def log_message(self, *args):" Enter
Type@8ms "        pass" Enter
Enter
Type@8ms 'HTTPServer(("127.0.0.1", 8765), Api).serve_forever()' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:api-headers -- http://localhost:8765 --path /health" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 7. Fix the API
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/api.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/api.py <<'PY'" Enter
Type@8ms "from http.server import BaseHTTPRequestHandler, HTTPServer" Enter
Enter
Type@8ms 'ALLOWED = {"https://app.example.com"}' Enter
Enter
Type@8ms "class Api(BaseHTTPRequestHandler):" Enter
Type@8ms "    def do_GET(self):" Enter
Type@8ms '        origin = self.headers.get("Origin", "")' Enter
Type@8ms "        self.send_response(200)" Enter
Type@8ms '        self.send_header("Content-Type", "application/json")' Enter
Type@8ms '        self.send_header("X-Content-Type-Options", "nosniff")' Enter
Type@8ms '        self.send_header("Vary", "Origin")' Enter
Type@8ms "        if origin in ALLOWED:" Enter
Type@8ms '            self.send_header("Access-Control-Allow-Origin", origin)' Enter
Type@8ms '            self.send_header("Access-Control-Allow-Credentials", "true")' Enter
Type@8ms "        self.end_headers()" Enter
Type@8ms `        self.wfile.write(b'{"ok": true}')` Enter
Enter
Type@8ms "    def log_message(self, *args):" Enter
Type@8ms "        pass" Enter
Enter
Type@8ms 'HTTPServer(("127.0.0.1", 8765), Api).serve_forever()' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 1" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run security:api-headers -- http://localhost:8765 --path /health --allowed-origin https://app.example.com" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/api.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'slopstopper run hygiene:csp-exceptions >/dev/null; echo "exit $?"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
