# Lesson 16: API checks: health, latency and OpenAPI drift.
# The terminal parts of the episode, generated from the lesson's
# runnable blocks by scripts/learntapes.py: edit the lesson, then
# `task contributing:learn:tapes`. Record it with
# `task contributing:learn:record -- 16` (demos/render.sh), which
# starts the shell in a scratch clone of this repo with the CLI on PATH, fills
# in the theme from demos/theme.json, and writes dist/learn/16.mp4.
# Sandbox: checkout
Output demos/.frames/16/
Set Shell bash
Set FontSize 16
Set Width 1070
Set Height 620
Set Padding 20
Set TypingSpeed 40ms
Set Theme @theme.json
Set Framerate 50

# 1. Start a small API
Type "mkdir -p scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/api.py <<'PY'" Enter
Type@8ms "import json, os, time" Enter
Type@8ms "from http.server import BaseHTTPRequestHandler, HTTPServer" Enter
Enter
Type@8ms 'STATUS = os.environ.get("HEALTH_STATUS", "ok")' Enter
Type@8ms 'PORT = int(os.environ.get("PORT", "8765"))' Enter
Type@8ms 'SPEC = {"openapi": "3.0.0", "info": {"title": "Lesson API", "version": "1"},' Enter
Type@8ms '        "paths": {"/health": {"get": {}}, "/v1/items": {"get": {}}, "/v1/slow": {"get": {}}}}' Enter
Type@8ms "ROUTES = {" Enter
Type@8ms '    "/health": (200 if STATUS == "ok" else 503, {"status": STATUS, "deps": {"db": "ok"}}),' Enter
Type@8ms '    "/v1/items": (200, [{"id": 1, "name": "widget"}, {"id": 2, "name": "gadget"}]),' Enter
Type@8ms '    "/v1/slow": (200, {"ok": True}),' Enter
Type@8ms '    "/openapi.json": (200, SPEC),' Enter
Type@8ms "}" Enter
Enter
Type@8ms "class Api(BaseHTTPRequestHandler):" Enter
Type@8ms "    def do_GET(self):" Enter
Type@8ms '        if self.path == "/v1/slow":' Enter
Type@8ms "            time.sleep(0.3)" Enter
Type@8ms '        code, body = ROUTES.get(self.path, (404, {"error": "not found"}))' Enter
Type@8ms "        payload = json.dumps(body).encode()" Enter
Type@8ms "        self.send_response(code)" Enter
Type@8ms '        self.send_header("Content-Type", "application/json")' Enter
Type@8ms '        self.send_header("X-Content-Type-Options", "nosniff")' Enter
Type@8ms "        self.end_headers()" Enter
Type@8ms "        self.wfile.write(payload)" Enter
Enter
Type@8ms "    def log_message(self, *args):" Enter
Type@8ms "        pass" Enter
Enter
Type@8ms 'HTTPServer(("127.0.0.1", PORT), Api).serve_forever()' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 2. Audit the health endpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:reliability:api-health -- http://localhost:8765 --path /health --require-field status --require-field deps.db" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 3. Measure latency with no budget
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:reliability:api-latency -- http://localhost:8765 --path /health --path /v1/items" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 4. Set a budget the slow route cannot meet
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:reliability:api-latency -- http://localhost:8765 --path /v1/slow --median-ms 100" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 5. Commit a spec that describes one route too many
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "cat > scratch/openapi.json <<'JSON'" Enter
Type@8ms "{" Enter
Type@8ms '  "openapi": "3.0.0",' Enter
Type@8ms '  "info": {"title": "Lesson API", "version": "1"},' Enter
Type@8ms '  "paths": {' Enter
Type@8ms '    "/health": {"get": {}},' Enter
Type@8ms '    "/v1/items": {"get": {}},' Enter
Type@8ms '    "/v1/slow": {"get": {}},' Enter
Type@8ms '    "/v1/reports": {"get": {}}' Enter
Type@8ms "  }" Enter
Type@8ms "}" Enter
Type@8ms "JSON" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:openapi -- http://localhost:8765 --spec scratch/openapi.json --served-spec http://localhost:8765/openapi.json" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sed -n '/Probed paths/,/details>/p' .ss/reports/openapi/openapi-report.md" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

# 6. Fix the spec
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "python3 - <<'PY'" Enter
Type@8ms "import json, pathlib" Enter
Type@8ms 'path = pathlib.Path("scratch/openapi.json")' Enter
Type@8ms "spec = json.loads(path.read_text())" Enter
Type@8ms 'del spec["paths"]["/v1/reports"]' Enter
Type@8ms 'path.write_text(json.dumps(spec, indent=2) + "\n")' Enter
Type@8ms "PY" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:hygiene:openapi -- http://localhost:8765 --spec scratch/openapi.json --served-spec http://localhost:8765/openapi.json" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# 7. Degrade the health endpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "HEALTH_STATUS=degraded PORT=8766 python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/degraded.pid" Enter
Wait+Line@5m /(^|\s)\$$/
Type "sleep 1" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s

Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "task ss:reliability:api-health -- http://localhost:8766 --path /health --require-field status --require-field deps.db" Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 3s

# Checkpoint
Type "clear" Enter
Wait+Line@5m /(^|\s)\$$/
Type "out=$(task ss:reliability:api-health -- http://localhost:8765 --path /health 2>&1)" Enter
Wait+Line@5m /(^|\s)\$$/
Type 'kill "$(cat scratch/api.pid)" "$(cat scratch/degraded.pid)"' Enter
Wait+Line@5m /(^|\s)\$$/
Type "rm -r scratch" Enter
Wait+Line@5m /(^|\s)\$$/
Type `echo "$out" | grep 'matches its contract'` Enter
Wait+Line@5m /(^|\s)\$$/
Sleep 2s
