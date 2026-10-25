# Lesson 10: Dynamic scanning

<!-- learn-sandbox: demo -->

**Goal.** Serve the demo, run OWASP ZAP against it, read a baseline
report, see what the gate accepts and why, and accept one finding with a
reason.

## Why this check

Everything before this lesson read the source. `security:dast` tests the
**running thing**. A header the host strips on the way out, a redirect
that leaks the path it came from, a page that caches when it should not,
a policy that is tighter in the config file than in the response: none
of that is visible in a diff, because all of it is about what a client
gets back. This is the one check whose findings a reviewer could not
have seen, however carefully they read.

The tool is [OWASP ZAP](https://www.zaproxy.org/), run from its official
Docker image so the CLI ships none of it. The check runs ZAP's
**baseline** scan: it spiders the site from the URL you give it and runs
the passive rules over every response, which is the cheap version of
dynamic testing and the right one for a pull request. A full active scan
sends attack payloads and takes an hour; that is a scheduled job against
production, not a PR gate. Each alert carries a risk (High, Medium, Low,
Informational), a plugin id, and the URLs it was seen on.

Then the **gate** decides. Medium and High block, with two narrow
exceptions. A CSP finding on a path documented in
`docs/security/CSP_EXCEPTIONS.md` (lesson 9's ledger) is accepted,
because the relaxation was reviewed and the ledger says why. And an
alert `.zap/rules.tsv` marks `IGNORE`, with a reason, is accepted. The
report lists what was accepted and names the entry that accepted it, so
nothing is quietly swallowed. Exit 0 is no blocking alert left, 1 is at
least one, and 2 is Docker missing, nothing listening at a localhost
target, or ZAP exiting without a report.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH,
  and `node` for `slopstopper serve`.
- Docker, running. `slopstopper doctor` says whether it is on PATH; the
  first scan pulls the ZAP image (about a gigabyte), so it needs the
  network once.

<!-- learn -->
```sh
docker --version
```

```
Docker version 29.5.3, build d1c06ef
```

## Steps

### 1. Relax one page, and write it down

The demo's policy is strict enough that ZAP's passive rules find
nothing above Low on it, so this lesson makes the relaxation that
lesson 9 only documented a little wider: the history page's chart sets
inline styles, so `style-src` admits `'unsafe-inline'` there. Both
halves at once, the header and the ledger entry, so the drift check
stays green.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
p = pathlib.Path('app/_headers'); text = p.read_text()
head, block = text.split('/history.html\n', 1)
block = block.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';", 1)
p.write_text(head + '/history.html\n' + block)
doc = pathlib.Path('docs/security/CSP_EXCEPTIONS.md'); t = doc.read_text()
entry = '''### `/history.html`

- **Origin allowed:** `https://charts.example.com`
- **Directives added:** `img-src https://charts.example.com`, `style-src 'unsafe-inline'`
- **Loader SRI:** `n/a`
- **Why:** the uptime chart is rendered by the charts service and sets inline styles on its container
- **Approved by:** nobody yet
- **Data leaving site:** visitor IP and User-Agent when the chart image is fetched
- **Refresh policy:** n/a
'''
doc.write_text(t.replace('None yet: every path serves the baseline policy.\n', entry, 1))
PY
slopstopper run hygiene:csp-exceptions | tail -1
```

```
✅ No drift detected.
```

### 2. Serve the demo and scan it

The site is served on a port of its own, tracked by a pid file so a
later step can stop it. The server reads `app/_headers` when it starts,
which is why the relaxation came first. ZAP runs in a container, so the
check rewrites `localhost` to the address the container can reach the
host on (`host.docker.internal` on macOS, the bridge gateway
`172.17.0.1` everywhere else) and tells you.

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
slopstopper run security:dast -- http://localhost:8099
```

```
🌐 Running DAST baseline scan against http://localhost:8099…
📍 Using Docker-compatible target: http://host.docker.internal:8099
WARN-NEW: Storable and Cacheable Content [10049] x 3
WARN-NEW: CSP: style-src unsafe-inline [10055] x 1
	http://host.docker.internal:8099/history.html (200 OK)
WARN-NEW: Permissions Policy Header Not Set [10063] x 4
WARN-NEW: Cross-Origin-Embedder-Policy Header Missing or Invalid [90004] x 15
FAIL-NEW: 0	FAIL-INPROG: 0	WARN-NEW: 4	WARN-INPROG: 0	INFO: 0	IGNORE: 0	PASS: 64
⚠️  Found 1 high/medium alert(s) (total 6)
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 0
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 1
   🛡 /history.html: alert=10055-6 riskcode=2 'CSP: style-src unsafe-inline' ← CSP_EXCEPTIONS.md path `/history.html`
✅ No blocking findings.
```

Trimmed to the alerts and the gate. Sixty-four rules passed. ZAP raised
six alerts, one of them Medium: the history page's CSP allows inline
styles. That is exactly the relaxation step 1 put in the ledger, and
the gate found the entry and accepted the finding, naming the path that
accepted it. Green, with the Medium still visible.

### 3. Read the report

<!-- learn -->
```sh
sed -n '/^# DAST/,/Low Risk Alerts/p' .ss/reports/dast/dast-report.md
```

```
# DAST Analysis Report

**Generated**: 2026-10-25 18:27:22 UTC

### 🛡 Accepted findings (swallowed by gate)

1 finding(s) accepted by `.zap/rules.tsv` or `docs/security/CSP_EXCEPTIONS.md` were filtered out:

- **/history.html**: alert `10055-6`, riskcode 2, _CSP: style-src unsafe-inline_, by CSP_EXCEPTIONS.md path `/history.html`

These do not block the build. They will block again if the entry is removed or if a higher-risk variant appears.

## Summary

| Risk Level | Count |
|------------|-------|
| 🔴 High | 0 |
| 🟡 Medium | 1 |
| 🔵 Low | 4 |
| ℹ️ Informational | 1 |
| **Total** | **6** |

## 🟡 Medium Risk Alerts

| Alert | Risk | Instances | Description |
|-------|------|-----------|-------------|
| CSP: style-src unsafe-inline | Medium | 1 | <p>Content Security Policy (CSP) is an added layer of security that helps to ... |

## 🔵 Low Risk Alerts
```

The report opens with the accepted findings and the entry behind each,
then the counts by risk, then a table per level. The Lows are the
cross-origin isolation and permissions-policy headers the demo's host
does not send; Low never blocks, so they are there to be read, not
fixed today. The JSON beside it has every instance and ZAP's `alertRef`
(`10055-6`), which is the id you will use in step 5.

### 4. Take the ledger away

The entry is what made the Medium acceptable. Remove it and the same
scan is red.

<!-- learn -->
```sh
git checkout docs/security/CSP_EXCEPTIONS.md
```

<!-- learn: fails -->
```sh
slopstopper run security:dast -- http://localhost:8099
```

```
⚠️  Found 1 high/medium alert(s) (total 6)
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 1
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 0
❌ 1 blocking finding(s). See .ss/reports/dast/dast-report.md.
```

Same site, same six alerts, one blocking; the report's Medium table
names it. Nothing about the response changed; what changed is that
nobody has said why it is acceptable. The gate blocks on a Medium until
someone does, in a place a reviewer reads.

### 5. Accept it with a reason, the other way

For a finding that is not a CSP relaxation on one path (a header a
static host cannot send, a rule that misreads a framework), the ledger
is the wrong instrument. `.zap/rules.tsv` is the right one: one line per
alert, tab-separated, with the reason as the third field.

<!-- learn -->
```sh
mkdir -p .zap
printf '10055-6\tIGNORE\t# inline styles on /history.html: the chart container sets them; the page allows nothing else\n' > .zap/rules.tsv
slopstopper run security:dast -- http://localhost:8099
```

```
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 0
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 1
   🛡 /history.html: alert=10055-6 riskcode=2 'CSP: style-src unsafe-inline' ← .zap/rules.tsv entry `10055-6`
✅ No blocking findings.
```

Green again, and the gate names the line that did it. Two things about
the id. `10055-6` is the **alert ref**: plugin 10055 is ZAP's whole CSP
scanner and raises several unrelated alerts, so ignoring `10055` would
also hide a missing `frame-ancestors`; the ref accepts exactly the
inline-styles alert and nothing else. And the reason is not optional:
the file is read in review, and "IGNORE" with no `# why` is the quiet
relaxation this course exists to stop.

### 6. Put the demo back

Remove the rule, restore the headers, and stop the server: it read the
relaxed headers when it started, so the clean run in the checkpoint
needs a fresh one.

<!-- learn -->
```sh
rm -rf .zap
git checkout app/_headers
kill "$(cat scratch/serve.pid)"
```

## Checkpoint

<!-- learn -->
```sh
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
slopstopper run security:dast -- http://localhost:8099 2>&1 | grep -E 'Found|No blocking'
kill "$(cat scratch/serve.pid)"
rm -rf scratch
```

```
ℹ️  Found 4 alert(s), but none are high/medium
✅ No blocking findings.
```

The demo as it shipped: four Lows, nothing to accept, server stopped,
pid file gone.

## Exercise

Point the scan at a live site instead of the local one, and explain
the difference in what ZAP sees.

<details>
<summary>Solution</summary>

```sh
slopstopper run security:dast -- https://slopstopper.dev
```

No `📍` line, because there is nothing to rewrite. The response headers
now come from the host's edge rather than from `slopstopper serve`
reading a file, so this is the run that would catch a header the edge
strips or adds. That is why the suite scans production after each
deploy and daily, and why a local build is enough for a pull request:
the two runs answer different questions.

</details>

## Going further

- [DAST](../security/DAST.md): the risk table, the gate's rules in
  full, `rules.tsv` by plugin id versus alert ref, static hosts that
  cannot send headers, and scanning an API through ZAP's OpenAPI mode
- [ZAP's alert registry](https://www.zaproxy.org/docs/alerts/), where
  every plugin id and alert ref resolves to its rule
- Lesson 9, whose ledger is what the gate read in step 2
- Lesson 17 for the post-deploy and scheduled runs against production,
  and the tracking issue a blocking alert on `main` opens

<details>
<summary>Episode script</summary>

**Length.** 10 to 12 minutes.

**Cold open (0:00).** `curl -I` against a deployed site: a header the
config file says is there, missing from the response. "The code is
right." Cut to a scan that reads responses, not code.

**Talking points.**

1. Why: the running thing; what a diff cannot show; baseline versus a
   full scan and why PRs get the cheap one.
2. The relaxation and its ledger entry, both at once; serve; scan; the
   Docker rewrite; sixty-four passes, six alerts, one Medium, accepted
   by the ledger and named.
3. The report: accepted first, counts, a table per level, the alert
   ref in the JSON.
4. Remove the ledger; red; nothing about the site changed.
5. `rules.tsv`: the alert ref, not the plugin; the reason field; green
   and named again.
6. Put the demo back and scan it clean. Exercise: a live site; headers
   from the edge; two runs, two questions.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/10.tape`. Zoom on `← CSP_EXCEPTIONS.md path`, on
`blocking alerts: 1`, and on `← .zap/rules.tsv`.

**Chapters.** `0:00 Why` · `1:30 Relax and record` · `2:30 Scan` ·
`4:30 The report` · `6:00 Take the ledger away` · `7:30 rules.tsv` ·
`9:30 Clean` · `10:30 Next lesson`.

</details>
