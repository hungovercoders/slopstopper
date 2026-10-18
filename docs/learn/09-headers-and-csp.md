# Lesson 9: Headers and CSP

**Goal.** Add a Content-Security-Policy exception without writing it
down, watch the drift check fail, document it properly, and then audit
an API's CORS headers and fix the commonest mistake.

## Why these checks

A site's security headers are one of the few controls that work even
after everything else has gone wrong. A strict Content-Security-Policy
means an injected script does not run; `frame-ancestors 'none'` means
the page cannot be framed for clickjacking; `nosniff` means a JSON
response is never executed as HTML. The slop is the quiet relaxation:
`'unsafe-inline'` added to make one widget render, a third-party origin
allowed site-wide because it was quicker than scoping it to one page.
Each one is a line in a diff that looks like configuration, and each
one removes a layer of defence for every page.

`hygiene:csp-exceptions` makes relaxation a documented act. The headers
live in one source (`worker/headers.json` here, a `_headers` file or
per-page meta tags elsewhere), and every per-path entry that admits an
external origin must have a matching entry in
`docs/security/CSP_EXCEPTIONS.md` with seven fields: what origin, which
directives, the loader's integrity hash, why, who approved it, what data
leaves the site and how the hash is refreshed. The check reads both
sides and fails on drift in either direction. It is stdlib Python and
needs no server.

`security:api-headers` is the same idea for an API, where CSP has no
document to protect and CORS is the control that decides who may read
a response. It probes live endpoints and hard-fails on the pair that
browsers reject but servers happily send (`Access-Control-Allow-Origin:
*` with credentials), on an arbitrary origin reflected back with
credentials, on a missing `nosniff`, and on a configured origin that is
no longer allowed. Version-leaking headers and a missing `Vary: Origin`
are advisory.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `node`, which `slopstopper serve` uses to serve the site with its
  real headers. `mise install` in the checkout provides it.

## Steps

### 1. See the headers the site sends

Serve the site locally. The server applies `worker/headers.json`
exactly as the Cloudflare Worker does in production.

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
curl -sI http://localhost:8099/ | grep -iE 'content-security|x-frame|nosniff|cross-origin'
```

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
```

`'self'` everywhere: nothing loads from anywhere else. That is the
default for every path, and the question the check asks is "where did
you relax it, and did you say so?"

### 2. See the drift check green

<!-- learn -->
```sh
task ss:hygiene:csp-exceptions
```

```
🔐 CSP exceptions check
   source: worker/headers.json
   CSP exceptions in source: 1
   documented in CSP_EXCEPTIONS.md: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ No drift detected.
```

One exception on each side: the feedback page, which embeds Giscus.
Read its entry in `docs/security/CSP_EXCEPTIONS.md` once; it is the
worked example every other entry copies.

### 3. Relax one page without saying so

Allow a widget's origin on the tools page. This is exactly the diff a
"make the widget work" commit contains.

<!-- learn -->
```sh
python3 - <<'PY'
import json, pathlib
path = pathlib.Path("worker/headers.json")
rules = json.loads(path.read_text())
rules.append({"for": "/tools.html", "values": {
    "Content-Security-Policy": "default-src 'self'; script-src 'self' https://widgets.example.com; style-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"}})
path.write_text(json.dumps(rules, indent=2) + "\n")
PY
```

<!-- learn: fails -->
```sh
task ss:hygiene:csp-exceptions
```

```
   CSP exceptions in source: 2
   documented in CSP_EXCEPTIONS.md: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ❌ /tools.html: `/tools.html` in worker/headers.json allows external origins (https://widgets.example.com) but has no entry in CSP_EXCEPTIONS.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Drift detected. See .ss/reports/csp/csp-exceptions-report.md for full details.
task: Failed to run task "ss:hygiene:csp-exceptions": exit status 1
```

### 4. Read the report

<!-- learn -->
```sh
sed -n '/## ❌ Errors/,/Mismatched origins/p' .ss/reports/csp/csp-exceptions-report.md
```

```
## ❌ Errors

- **/tools.html**: `/tools.html` in worker/headers.json allows external origins (https://widgets.example.com) but has no entry in CSP_EXCEPTIONS.md

## How to Fix

- **Missing doc entry** → add a `### \`/path\`` heading under `## Exceptions` in `docs/security/CSP_EXCEPTIONS.md` with all required fields.
- **Mismatched origins** → make `Origin allowed` / `Directives added` in the doc list every external origin in the corresponding `worker/headers.json` entry.
```

### 5. Document it

The fix is not to remove the relaxation. It is to write it down, with
every field, under the `## Exceptions` heading. The entry below goes in
just above the Adopters section, which is where the parser stops
reading.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
doc = pathlib.Path("docs/security/CSP_EXCEPTIONS.md")
text = doc.read_text()
entry = """### `/tools.html`

- **Origin allowed:** `https://widgets.example.com`
- **Directives added:** `script-src https://widgets.example.com`
- **Loader SRI:** `n/a`
- **Why:** A worked example for lesson 9 of the course
- **Approved by:** nobody yet
- **Data leaving site:** visitor IP and User-Agent when the script is fetched
- **Refresh policy:** n/a

"""
marker = "---\n\n## Adopters"
doc.write_text(text.replace(marker, entry + marker, 1))
PY
task ss:hygiene:csp-exceptions
```

```
   CSP exceptions in source: 2
   documented in CSP_EXCEPTIONS.md: 2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ No drift detected.
```

Both sides agree again. Notice what the fields forced you to say: who
approved it (nobody, yet), and what data leaves the site. A reviewer
reading the diff now sees a decision, not a config change. Put the
checkout back before moving on:

<!-- learn -->
```sh
git checkout worker/headers.json docs/security/CSP_EXCEPTIONS.md
```

### 6. Audit the site's headers as an API would be audited

The API check skips when nothing is configured, because an
unconfigured check is not a failing check. Point it at the served site
with a path and it probes for real:

<!-- learn -->
```sh
task ss:security:api-headers -- http://localhost:8099 --path /
kill "$(cat scratch/serve.pid)"
```

```
🛡 API header + CORS audit against: http://localhost:8099
   Paths: /
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ http://localhost:8099/
      ⚠️  HSTS not asserted because the target is http, where the header has no effect
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Every probed endpoint passes the API header contract.
```

### 7. Build an API with the commonest CORS mistake

A ten-line server that sends the wildcard origin together with
credentials, and forgets `nosniff`. Generated API scaffolds do both.

<!-- learn -->
```sh
cat > scratch/api.py <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer

class Api(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args):
        pass

HTTPServer(("127.0.0.1", 8765), Api).serve_forever()
PY
python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid
sleep 1
```

<!-- learn: fails -->
```sh
task ss:security:api-headers -- http://localhost:8765 --path /health
```

```
  ❌ http://localhost:8765/health
      - `Access-Control-Allow-Origin: *` is sent with `Access-Control-Allow-Credentials: true`. Browsers reject this pair, so the policy you intended is not being enforced. Echo a specific allowed origin instead
      - `X-Content-Type-Options: nosniff` is missing. A JSON response that a browser sniffs as HTML is an XSS vector. Or set api.headers.require_nosniff: false
      ⚠️  HSTS not asserted because the target is http, where the header has no effect
      ⚠️  `Server: BaseHTTP/0.6 Python/3.13.16` includes a version, so consider trimming it to the product name
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/api-headers/api-headers-report.md for full details.
task: Failed to run task "ss:security:api-headers": exit status 1
```

Two hard failures and two notes. The first failure is the one to
understand: the wildcard plus credentials is not a permissive policy,
it is a policy browsers refuse, so whatever the author meant to allow
is not being allowed, and the next person "fixes" it by reflecting
`Origin`, which is the real leak.

### 8. Fix the API

Validate `Origin` against an allowlist, echo the match, send `Vary:
Origin` so caches keep origins apart, and add `nosniff`.

<!-- learn -->
```sh
kill "$(cat scratch/api.pid)"
cat > scratch/api.py <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOWED = {"https://app.example.com"}

class Api(BaseHTTPRequestHandler):
    def do_GET(self):
        origin = self.headers.get("Origin", "")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        if origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args):
        pass

HTTPServer(("127.0.0.1", 8765), Api).serve_forever()
PY
python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid
sleep 1
task ss:security:api-headers -- http://localhost:8765 --path /health --allowed-origin https://app.example.com
kill "$(cat scratch/api.pid)"
rm -r scratch
```

```
  ✅ http://localhost:8765/health
      ⚠️  HSTS not asserted because the target is http, where the header has no effect
      ⚠️  `Server: BaseHTTP/0.6 Python/3.13.16` includes a version, so consider trimming it to the product name
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Every probed endpoint passes the API header contract.
```

`--allowed-origin` is the `api.headers.allowed_origins` knob from the
command line: the check sends that origin and insists it comes back
allowed, which catches an allowlist that silently stopped matching
after a frontend moved domains. In a real repo these live in
`.slopstopper.yml` under `api.headers`, and the check runs after every
deploy against the real edge, because the headers that matter usually
come from the proxy in front of the app, not the app.

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:csp-exceptions | grep 'No drift'
```

```
✅ No drift detected.
```

## Exercise

Make the drift check fail in the other direction: a documented
exception with no matching entry in the headers source.

<details>
<summary>Solution</summary>

Run the step 5 snippet on its own, without the step 3 one, so the ledger
gains `/tools.html` while `worker/headers.json` does not:

```sh
task ss:hygiene:csp-exceptions
git checkout docs/security/CSP_EXCEPTIONS.md
```

The error reads "documented in CSP_EXCEPTIONS.md but has no entry in
worker/headers.json". A stale ledger entry is its own kind of drift: it
says a page admits an origin that it no longer does, and the next
person to touch the page will trust it.

</details>

## Going further

- [CSP exceptions](../security/CSP_EXCEPTIONS.md): the pattern, the
  schema, computing an SRI hash, and how DAST treats documented paths
- [API headers and CORS](../security/API_HEADERS.md): every finding,
  which are hard failures, and the `api.headers` knobs
- `headers.source` and `headers.format` in `.slopstopper.yml.example`,
  including `meta` for hosts that cannot send headers
- Lesson 10, where DAST looks at the same headers from the outside

<details>
<summary>Episode script</summary>

**Length.** 10 to 12 minutes.

**Cold open (0:00).** A diff: one line in `headers.json` adding
`https://widgets.example.com`. "LGTM, it's just config."

**Talking points.**

1. Why headers: the control that works after everything else failed;
   the quiet relaxation is the slop.
2. The site's headers from `curl -I`; `'self'` everywhere.
3. Green; relax the tools page; red; the report's two fixes.
4. The ledger entry and what its fields force you to say; green.
5. The API half: the unconfigured skip, then the site passes.
6. The ten-line API with wildcard plus credentials; why browsers
   reject it and why "fixing" it by reflecting Origin is the real leak.
7. Allowlist, echo, Vary, nosniff; green; `--allowed-origin`.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/09.tape`. Zoom on "in source: 2 / documented: 1",
and on the wildcard-plus-credentials line.

**Chapters.** `0:00 Why` · `1:30 The headers` · `2:30 Drift` ·
`4:30 The ledger` · `6:00 The API check` · `7:30 Wildcard plus
credentials` · `9:30 The fix` · `11:00 Next lesson`.

</details>
