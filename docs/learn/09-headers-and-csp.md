# Lesson 9: Headers and CSP

<!-- learn-sandbox: demo -->

**Goal.** See the headers the demo's host sends, find the
Content-Security-Policy relaxation nobody wrote down, document it
properly, and then audit an API's CORS headers and fix the commonest
mistake.

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
live in one source (a Cloudflare or Netlify `_headers` file here, a
JSON rules file or per-page meta tags elsewhere), and every per-path
entry that admits an external origin must have a matching entry in
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

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `node`, which `slopstopper serve` uses to serve the site with its
  real headers.

## Steps

### 1. See the headers the site sends

Serve the demo locally. The server applies `app/_headers`, the file
the demo's `.slopstopper.yml` names as `headers.source`, exactly as
the host does in production.

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
curl -sI http://localhost:8099/ | grep -iE 'content-security|x-frame|nosniff|referrer'
curl -sI http://localhost:8099/history.html | grep -iE 'content-security'
```

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://charts.example.com; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

`'self'` everywhere on the status page: nothing loads from anywhere
else. The history page is different: its `img-src` admits
`https://charts.example.com`. That is the default policy relaxed for
one path, and the question the check asks is "did you say so?"

### 2. See the drift check red

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:csp-exceptions
```

```
🔐 CSP exceptions check
   source: app/_headers
   CSP exceptions in source: 1
   documented in CSP_EXCEPTIONS.md: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ❌ /history.html: `/history.html` in app/_headers allows external origins (https://charts.example.com) but has no entry in CSP_EXCEPTIONS.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Drift detected. See .ss/reports/csp/csp-exceptions-report.md for full details.
```

One exception in the headers, none in the ledger. This is exactly the
diff a "make the chart show" commit contains: one line in a config
file, reviewed as config.

### 3. Read the report

<!-- learn -->
```sh
sed -n '/^## .* Errors/,/Mismatched origins/p' .ss/reports/csp/csp-exceptions-report.md
```

```
## ❌ Errors

- **/history.html**: `/history.html` in app/_headers allows external origins (https://charts.example.com) but has no entry in CSP_EXCEPTIONS.md

## How to Fix

- **Missing doc entry** → add a `### \`/path\`` heading under `## Exceptions` in `docs/security/CSP_EXCEPTIONS.md` with all required fields.
- **Mismatched origins** → make `Origin allowed` / `Directives added` in the doc list every external origin in the corresponding `app/_headers` entry.
```

### 4. Document it

The fix is not to remove the relaxation, unless the page no longer
needs it. It is to write it down, with every field, under the
`## Exceptions` heading. The demo's ledger says "None yet"; this
replaces that line with the entry.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
doc = pathlib.Path('docs/security/CSP_EXCEPTIONS.md')
text = doc.read_text()
entry = '''### `/history.html`

- **Origin allowed:** `https://charts.example.com`
- **Directives added:** `img-src https://charts.example.com`
- **Loader SRI:** `n/a`
- **Why:** the uptime chart on the history page is rendered by the charts service
- **Approved by:** nobody yet
- **Data leaving site:** visitor IP and User-Agent when the chart image is fetched
- **Refresh policy:** n/a
'''
doc.write_text(text.replace('None yet: every path serves the baseline policy.\n', entry, 1))
PY
slopstopper run hygiene:csp-exceptions
```

```
🔐 CSP exceptions check
   source: app/_headers
   CSP exceptions in source: 1
   documented in CSP_EXCEPTIONS.md: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ No drift detected.
```

Both sides agree. Notice what the fields forced you to say: who
approved it (nobody, yet), and what data leaves the site. A reviewer
reading the diff now sees a decision, not a config change. Put the
demo back before moving on:

<!-- learn -->
```sh
git checkout docs/security/CSP_EXCEPTIONS.md
```

### 5. Audit the site's headers as an API would be audited

The API check skips when nothing is configured, because an
unconfigured check is not a failing check. Point it at the served site
with a path and it probes for real:

<!-- learn -->
```sh
slopstopper run security:api-headers -- http://localhost:8099 --path /
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

### 6. Build an API with the commonest CORS mistake

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

<!-- learn: fails 1 -->
```sh
slopstopper run security:api-headers -- http://localhost:8765 --path /health
```

```
  ❌ http://localhost:8765/health
      - `Access-Control-Allow-Origin: *` is sent with `Access-Control-Allow-Credentials: true`. Browsers reject this pair, so the policy you intended is not being enforced. Echo a specific allowed origin instead
      - `X-Content-Type-Options: nosniff` is missing. A JSON response that a browser sniffs as HTML is an XSS vector. Or set api.headers.require_nosniff: false
      ⚠️  HSTS not asserted because the target is http, where the header has no effect
      ⚠️  `Server: BaseHTTP/0.6 Python/3.13.16` includes a version, so consider trimming it to the product name
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/api-headers/api-headers-report.md for full details.
```

Two hard failures and two notes. The first failure is the one to
understand: the wildcard plus credentials is not a permissive policy,
it is a policy browsers refuse, so whatever the author meant to allow
is not being allowed, and the next person "fixes" it by reflecting
`Origin`, which is the real leak.

### 7. Fix the API

Validate `Origin` against an allowlist and echo the match, add
`nosniff`, and send `Vary: Origin` on every response, not only the
allowed ones: a shared cache keys on the headers named in `Vary`, so a
response without it, served to a request with no `Origin`, could be
handed back to the allowed frontend without its CORS headers.

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
        self.send_header("Vary", "Origin")
        if origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *args):
        pass

HTTPServer(("127.0.0.1", 8765), Api).serve_forever()
PY
python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid
sleep 1
slopstopper run security:api-headers -- http://localhost:8765 --path /health --allowed-origin https://app.example.com
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

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:csp-exceptions >/dev/null; echo "exit $?"
```

```
exit 1
```

Red again, with the demo as it shipped, and the entry that fixes it is
seven lines you can now write.

## Exercise

Make the drift check fail in the other direction: a documented
exception with no matching entry in the headers source.

<details>
<summary>Solution</summary>

Run the step 4 snippet, then take the relaxation out of `app/_headers`
instead of the ledger:

```sh
python3 - <<'PY'
import pathlib
p = pathlib.Path('app/_headers'); text = p.read_text()
p.write_text(text[:text.index('/history.html')].rstrip() + '\n')
PY
slopstopper run hygiene:csp-exceptions
git checkout app/_headers docs/security/CSP_EXCEPTIONS.md
```

The error reads "documented in CSP_EXCEPTIONS.md but has no entry in
app/_headers". A stale ledger entry is its own kind of drift: it says
a page admits an origin that it no longer does, and the next person to
touch the page will trust it.

</details>

## Going further

- [CSP exceptions](../security/CSP_EXCEPTIONS.md): the pattern, the
  schema, computing an SRI hash, and how DAST treats documented paths
- [API headers and CORS](../security/API_HEADERS.md): every finding,
  which are hard failures, and the `api.headers` knobs
- `headers.source` and `headers.format` in `.slopstopper.yml.example`,
  including `meta` for hosts that cannot send headers
- Lesson 10, where DAST looks at the same headers from the outside

### Why a cookieless site still needs a privacy statement

The CSP you just documented limits where resources come from, not who
sees the request. The host processes every visitor's IP before your
code runs, and every origin the policy allows sees that IP too the
moment a page fetches from it: here, the charts service, on every
visit to the history page. So the honest statement for a site with no
cookies and no analytics is short, and it is a function of two files:
the hosting config and the headers source. `hygiene:privacy` reads
both and asks the page to name the host, every allowed origin and a
date. The demo has no hosting config, so the check skips there; on a
repo with one, the ledger entry you wrote in step 4 is also a line on
the privacy page.

<details>
<summary>Episode script</summary>

**Length.** 10 to 12 minutes.

**Cold open (0:00).** A diff: one line in `_headers` adding
`https://charts.example.com`. "LGTM, it's just config."

**Talking points.**

1. Why headers: the control that works after everything else failed;
   the quiet relaxation is the slop.
2. The site's headers from `curl -I`; `'self'` everywhere, then the
   history page's one difference.
3. Red; one in the source, none in the ledger; the report's two fixes.
4. The ledger entry and what its fields force you to say; green; put
   the demo back.
5. The API half: the unconfigured skip, then the site passes.
6. The ten-line API with wildcard plus credentials; why browsers
   reject it and why "fixing" it by reflecting Origin is the real leak.
7. Allowlist, echo, Vary, nosniff; green; `--allowed-origin`.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/09.tape`. Zoom on "in source: 1 / documented: 0",
and on the wildcard-plus-credentials line.

**Chapters.** `0:00 Why` · `1:30 The headers` · `2:30 Drift` ·
`4:00 The ledger` · `6:00 The API check` · `7:30 Wildcard plus
credentials` · `9:30 The fix` · `11:00 Next lesson`.

</details>
