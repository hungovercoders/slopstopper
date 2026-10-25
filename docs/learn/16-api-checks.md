# Lesson 16: API checks: health, latency and OpenAPI drift

<!-- learn-sandbox: demo -->

**Goal.** Point the three API checks at a small API, see each one fail
on its own kind of drift, and understand why they exist alongside the
browser checks.

## Why these checks

On an API repo the browser checks mean nothing: there is no DOM to
audit for contrast, no page to score for layout shift. The `api`
profile drops them and keeps three checks that ask the API-shaped
versions of the same questions.

- **`reliability:api-health`** is the smoke test's analogue. It probes
  the one endpoint an API exposes for exactly this purpose and asserts
  the contract around it: the documented status code, a JSON content
  type, a body that parses, and the fields the repo says must be there.
  Pointing smoke at `/health` would not do: `{"status": "degraded"}`
  with HTTP 200 passes any reachability probe and is a failure here,
  which is the whole reason a health endpoint returns a body.
- **`reliability:api-latency`** is Core Web Vitals' analogue. Nothing
  renders, so the question narrows to how long an endpoint takes to
  answer and how much it sends back. It samples each path several
  times and reports the median, the slowest sample and the size.
  Budgets gate on the median, because one slow sample on a shared
  runner moves the maximum and not the middle, and it deliberately
  reports no p95: five samples cannot support one.
- **`hygiene:openapi`** is docs-accuracy's analogue. A spec that has
  stopped describing its API is documentation that became fiction,
  and an agent reading the spec will call routes that are not there.
  The check compares the committed spec against the one the running
  API serves, and probes every documented path that takes no
  parameters.

All three are stdlib Python, skip gracefully when nothing is
configured, and never build or serve the repo themselves: an API is
not a static bundle, and guessing a start command would be worse than
not guessing. The `ui` profile adds them only when the repo shows an
API: a spec, a server framework or an `api.*` key.

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH, or
any directory at all: the lesson's API is twenty lines of stdlib
Python and the checks read nothing from the repo.

## Steps

### 1. Start a small API

Three routes, a health endpoint, and the spec it serves for itself.
`HEALTH_STATUS` and `PORT` are there for later steps.

<!-- learn -->
```sh
mkdir -p scratch
cat > scratch/api.py <<'PY'
import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer

STATUS = os.environ.get("HEALTH_STATUS", "ok")
PORT = int(os.environ.get("PORT", "8765"))
SPEC = {"openapi": "3.0.0", "info": {"title": "Lesson API", "version": "1"},
        "paths": {"/health": {"get": {}}, "/v1/items": {"get": {}}, "/v1/slow": {"get": {}}}}
ROUTES = {
    "/health": (200 if STATUS == "ok" else 503, {"status": STATUS, "deps": {"db": "ok"}}),
    "/v1/items": (200, [{"id": 1, "name": "widget"}, {"id": 2, "name": "gadget"}]),
    "/v1/slow": (200, {"ok": True}),
    "/openapi.json": (200, SPEC),
}

class Api(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/slow":
            time.sleep(0.3)
        code, body = ROUTES.get(self.path, (404, {"error": "not found"}))
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass

HTTPServer(("127.0.0.1", PORT), Api).serve_forever()
PY
python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/api.pid
sleep 1
```

### 2. Audit the health endpoint

The flags are the `api.health` keys from the command line: the path,
and two fields the body must carry, one of them nested.

<!-- learn -->
```sh
slopstopper run reliability:api-health -- http://localhost:8765 --path /health --require-field status --require-field deps.db
```

```
🩺 API health audit against: http://localhost:8765/health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ http://localhost:8765/health  (HTTP 200)
      ⚠️  responded in 32ms (no api.health.max_response_ms budget set)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Health endpoint is reachable and matches its contract.
```

The timing is reported and not enforced, because no budget is set.
That is the pattern for every number in this lesson: measure first,
set the budget from what you measured.

### 3. Measure latency with no budget

<!-- learn -->
```sh
slopstopper run reliability:api-latency -- http://localhost:8765 --path /health --path /v1/items
```

```
⏱ API latency audit against: http://localhost:8765
   Paths: /health, /v1/items (5 sample(s) after 1 warmup)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ http://localhost:8765/health  median 0.9ms · slowest 1.0ms · 38 bytes
      ⚠️  `http://localhost:8765/health` median 0.9ms, slowest 1.0ms, 38 bytes (no budget set, so nothing is enforced)
  ✅ http://localhost:8765/v1/items  median 0.9ms · slowest 1.3ms · 58 bytes
      ⚠️  `http://localhost:8765/v1/items` median 0.9ms, slowest 1.3ms, 58 bytes (no budget set, so nothing is enforced)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Every endpoint is reachable and within budget.
```

One warmup request is thrown away before the five that count, because
the first hit pays for DNS, TLS and cold start, none of which is the
steady state a budget is about.

### 4. Set a budget the slow route cannot meet

<!-- learn: fails 1 -->
```sh
slopstopper run reliability:api-latency -- http://localhost:8765 --path /v1/slow --median-ms 100
```

```
  ❌ http://localhost:8765/v1/slow  median 301.5ms · slowest 302.0ms · 12 bytes
      - `http://localhost:8765/v1/slow` median 301.5ms is over the 100ms budget
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/api-latency/api-latency-report.md for full details.
```

### 5. Commit a spec that describes one route too many

The committed spec is what a client or an agent reads. Give it a route
the API does not serve.

<!-- learn -->
```sh
cat > scratch/openapi.json <<'JSON'
{
  "openapi": "3.0.0",
  "info": {"title": "Lesson API", "version": "1"},
  "paths": {
    "/health": {"get": {}},
    "/v1/items": {"get": {}},
    "/v1/slow": {"get": {}},
    "/v1/reports": {"get": {}}
  }
}
JSON
```

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:openapi -- http://localhost:8765 --spec scratch/openapi.json --served-spec http://localhost:8765/openapi.json
```

```
📘 OpenAPI drift audit (spec: scratch/openapi.json)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ 4 operation(s) declared
      - `GET /v1/reports` is in the committed spec but the live API doesn't serve it
      - `/v1/reports` is documented but the API returns 404, so the route is gone
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Drift detected. See .ss/reports/openapi/openapi-report.md for full details.
```

Two findings for one route, from the two directions the check can
answer honestly: the committed spec disagrees with the served one, and
the documented path answers 404. The report lists every probe:

<!-- learn -->
```sh
sed -n '/Probed paths/,/details>/p' .ss/reports/openapi/openapi-report.md
```

```
<details><summary>Probed paths</summary>

| Path | Status |
|---|---|
| `/health` | ✅ 200 |
| `/v1/items` | ✅ 200 |
| `/v1/reports` | ❌ 404 |
| `/v1/slow` | ✅ 200 |

</details>
```

Paths with parameters, `/users/{id}`, are counted and never probed: a
404 from one could mean the route is missing or merely that no such
record exists, and failing both would train people to ignore the
check. Undocumented routes are the other half of drift and out of
scope, because finding them needs framework-specific introspection.

### 6. Fix the spec

Drop the route that is gone, or ship it. Here it is gone.

<!-- learn -->
```sh
python3 - <<'PY'
import json, pathlib
path = pathlib.Path("scratch/openapi.json")
spec = json.loads(path.read_text())
del spec["paths"]["/v1/reports"]
path.write_text(json.dumps(spec, indent=2) + "\n")
PY
slopstopper run hygiene:openapi -- http://localhost:8765 --spec scratch/openapi.json --served-spec http://localhost:8765/openapi.json
```

```
  ✅ 3 operation(s) declared
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ The spec matches the API it documents.
```

When the framework generates the spec at build time, the durable fix
is to point `api.openapi.spec` at the served URL, so there is no
committed copy to drift.

### 7. Degrade the health endpoint

A second copy of the API on its own port, reporting itself degraded
with a 503. This is what a readiness endpoint does when a dependency
is down, and it is what the health check is for.

<!-- learn -->
```sh
HEALTH_STATUS=degraded PORT=8766 python3 scratch/api.py >/dev/null 2>&1 & echo $! > scratch/degraded.pid
sleep 1
```

<!-- learn: fails 1 -->
```sh
slopstopper run reliability:api-health -- http://localhost:8766 --path /health --require-field status --require-field deps.db
```

```
  ❌ http://localhost:8766/health  (HTTP 503)
      - returned HTTP 503, expected 200
      ⚠️  responded in 41ms (no api.health.max_response_ms budget set)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failures detected. See .ss/reports/api-health/api-health-report.md for full details.
```

In a real repo these flags live in `.slopstopper.yml` under `api`, and
`expect_fields` there pins a value too, so `{"status": "degraded"}`
with a 200 fails as well.

## Checkpoint

<!-- learn -->
```sh
out=$(slopstopper run reliability:api-health -- http://localhost:8765 --path /health 2>&1)
kill "$(cat scratch/api.pid)" "$(cat scratch/degraded.pid)"
rm -r scratch
echo "$out" | grep 'matches its contract'
```

```
✅ Health endpoint is reachable and matches its contract.
```

## Exercise

Make the latency check fail on size rather than time.

<details>
<summary>Solution</summary>

Start the API again and give the items route a budget it cannot meet:

```sh
slopstopper run reliability:api-latency -- http://localhost:8765 --path /v1/items --max-bytes 10
```

The route answers in under a millisecond and still fails, because its
58-byte body is over the 10-byte budget. Size is a budget for the same
reason time is: a list endpoint that quietly grows from two items to
two thousand is slop that no timing on a fast network will show.

</details>

## Going further

- [API health](../reliability/README.md#api-health-check),
  [API latency](../reliability/README.md#api-latency-check) and
  [OpenAPI drift](../hygiene/README.md#openapi-drift): every
  assertion, knob and the workflow each runs under
- [Profiles](../architecture/PROFILES.md) for when the `ui` profile adds
  these checks and when `api` drops the browser ones; lesson 19 walks
  through it
- Lesson 9 for `security:api-headers`, the fourth check of the API set

<details>
<summary>Episode script</summary>

**Length.** 9 to 11 minutes.

**Cold open (0:00).** `{"status": "degraded"}` with a 200 next to it.
A green uptime badge.

**Talking points.**

1. Why: the browser checks mean nothing on an API; three analogues,
   each asking the same question in API terms.
2. The twenty-line API; health green with its fields; timing reported,
   not enforced.
3. Latency with no budget; the warmup; one slow route against a 100 ms
   budget.
4. The committed spec with one route too many; two findings, two
   directions; the probe table; parameters are never probed.
5. Fix the spec; point at the served URL when it is generated.
6. The degraded copy; 503 fails; `expect_fields` for the 200 case.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/16.tape`. Zoom on "median 301.5ms is over the 100ms
budget" and on the two drift findings.

**Chapters.** `0:00 Why` · `1:30 The API` · `2:30 Health` ·
`3:30 Latency` · `5:30 Drift` · `8:00 Degraded` · `9:30 Next lesson`.

</details>
