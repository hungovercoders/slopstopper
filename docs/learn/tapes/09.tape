# Lesson 9: Headers and CSP.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 09` (demos/render.sh), which
# starts the shell in a scratch clone of this repo with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/09.mp4.
# Sandbox: checkout
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
Type "curl -sI http://localhost:8099/ | grep -iE 'content-security|x-frame|nosniff|cross-origin'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 2. See the drift check green
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:csp-exceptions" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Relax one page without saying so
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import json, pathlib" Enter
Type@8ms 'path = pathlib.Path("worker/headers.json")' Enter
Type@8ms "rules = json.loads(path.read_text())" Enter
Type@8ms 'rules.append({"for": "/tools.html", "values": {' Enter
Type@8ms `    "Content-Security-Policy": "default-src 'self'; script-src 'self' https://widgets.example.com; style-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"}})` Enter
Type@8ms 'path.write_text(json.dumps(rules, indent=2) + "\n")' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:csp-exceptions" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Read the report
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/^## .* Errors/,/Mismatched origins/p' .ss/reports/csp/csp-exceptions-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 5. Document it
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import pathlib" Enter
Type@8ms 'doc = pathlib.Path("docs/security/CSP_EXCEPTIONS.md")' Enter
Type@8ms "text = doc.read_text()" Enter
Type@8ms 'entry = """### `/tools.html`' Enter
Enter
Type@8ms "- **Origin allowed:** `https://widgets.example.com`" Enter
Type@8ms "- **Directives added:** `script-src https://widgets.example.com`" Enter
Type@8ms "- **Loader SRI:** `n/a`" Enter
Type@8ms "- **Why:** A worked example for lesson 9 of the course" Enter
Type@8ms "- **Approved by:** nobody yet" Enter
Type@8ms "- **Data leaving site:** visitor IP and User-Agent when the script is fetched" Enter
Type@8ms "- **Refresh policy:** n/a" Enter
Enter
Type@8ms '"""' Enter
Type@8ms 'marker = "---\n\n## Adopters"' Enter
Type@8ms "doc.write_text(text.replace(marker, entry + marker, 1))" Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:csp-exceptions" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "git checkout worker/headers.json docs/security/CSP_EXCEPTIONS.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 6. Audit the site's headers as an API would be audited
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:security:api-headers -- http://localhost:8099 --path /" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/serve.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 7. Build an API with the commonest CORS mistake
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
Type "task ss:security:api-headers -- http://localhost:8765 --path /health" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 8. Fix the API
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
Type "task ss:security:api-headers -- http://localhost:8765 --path /health --allowed-origin https://app.example.com" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/api.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "slopstopper run hygiene:csp-exceptions | grep 'No drift'" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s
