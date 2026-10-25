# Lesson 10: Dynamic scanning

**Goal.** Serve the site, run OWASP ZAP against it, read a baseline
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

- The checkout from the [syllabus](README.md), with the CLI on PATH.
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

### 1. Serve the site and scan it

The site is served on a port of its own, tracked by a pid file so a
later step can stop it. ZAP runs in a container, so the check rewrites
`localhost` to the address the container can reach the host on
(`host.docker.internal` on macOS, the bridge gateway `172.17.0.1`
everywhere else) and tells you.

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
task ss:security:dast -- http://localhost:8099
```

```
🌐 Running DAST baseline scan against http://localhost:8099…
📍 Using Docker-compatible target: http://host.docker.internal:8099
WARN-NEW: Storable and Cacheable Content [10049] x 4
WARN-NEW: CSP: style-src unsafe-inline [10055] x 1
	http://host.docker.internal:8099/feedback.html (200 OK)
WARN-NEW: Modern Web Application [10109] x 1
WARN-NEW: Cross-Origin-Embedder-Policy Header Missing or Invalid [90004] x 2
FAIL-NEW: 0	FAIL-INPROG: 0	WARN-NEW: 4	WARN-INPROG: 0	INFO: 0	IGNORE: 0	PASS: 64
⚠️  Found 1 high/medium alert(s) (total 5)
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 0
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 1
   🛡 /feedback.html: alert=10055-6 riskcode=2 'CSP: style-src unsafe-inline' ← CSP_EXCEPTIONS.md path `/feedback.html`
✅ No blocking findings.
```

Trimmed to the alerts and the gate. Sixty-four rules passed. ZAP raised
five alerts, one of them Medium: the feedback page's CSP allows inline
styles, which the Giscus widget needs. That is exactly the relaxation
lesson 9 put in the ledger, and the gate found the entry and accepted
the finding, naming the path that accepted it. Green, with the Medium
still visible.

### 2. Read the report

<!-- learn -->
```sh
sed -n '/^## Summary/,/Low Risk Alerts/p' .ss/reports/dast/dast-report.md
```

```
## Summary

| Risk Level | Count |
|------------|-------|
| 🔴 High | 0 |
| 🟡 Medium | 1 |
| 🔵 Low | 2 |
| ℹ️ Informational | 2 |
| **Total** | **5** |

## 🟡 Medium Risk Alerts

| Alert | Risk | Instances | Description |
|-------|------|-----------|-------------|
| CSP: style-src unsafe-inline | Medium | 1 | <p>Content Security Policy (CSP) is an added layer of security that helps to ... |

## 🔵 Low Risk Alerts
```

The report opens with the accepted findings and the entry behind each,
then the counts by risk, then a table per level. The two Lows are the
cross-origin isolation headers the feedback page relaxes for the same
widget; Low never blocks, so they are there to be read, not fixed
today. The JSON beside it has every instance and ZAP's `alertRef`
(`10055-6`), which is the id you will use in step 4.

### 3. Take the ledger away

The entry is what made the Medium acceptable. Remove the ledger and the
same scan is red.

<!-- learn -->
```sh
rm docs/security/CSP_EXCEPTIONS.md
```

<!-- learn: fails -->
```sh
task ss:security:dast -- http://localhost:8099
```

```
⚠️  Found 1 high/medium alert(s) (total 5)
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 1
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 0
❌ 1 blocking finding(s). See .ss/reports/dast/dast-report.md.
task: Failed to run task "ss:security:dast": exit status 1
```

Same site, same five alerts, one blocking; the report's Medium table
names it. Nothing about the response changed; what changed is that
nobody has said why it is acceptable. The gate blocks on a Medium until
someone does, in a place a reviewer reads.

### 4. Accept it with a reason, the other way

For a finding that is not a CSP relaxation on one path (a header a
static host cannot send, a rule that misreads a framework), the ledger
is the wrong instrument. `.zap/rules.tsv` is the right one: one line per
alert, tab-separated, with the reason as the third field.

<!-- learn -->
```sh
mkdir -p .zap
printf '10055-6\tIGNORE\t# inline styles on /feedback.html: the Giscus widget sets them; the page allows nothing else\n' > .zap/rules.tsv
task ss:security:dast -- http://localhost:8099
```

```
🕷️  DAST gate
   blocking alerts (riskcode >= 2): 0
   swallowed (rules.tsv IGNORE or documented CSP exceptions): 1
   🛡 /feedback.html: alert=10055-6 riskcode=2 'CSP: style-src unsafe-inline' ← .zap/rules.tsv entry `10055-6`
✅ No blocking findings.
```

Green again, and the gate names the line that did it. Two things about
the id. `10055-6` is the **alert ref**: plugin 10055 is ZAP's whole CSP
scanner and raises several unrelated alerts, so ignoring `10055` would
also hide a missing `frame-ancestors`; the ref accepts exactly the
inline-styles alert and nothing else. And the reason is not optional:
the file is read in review, and "IGNORE" with no `# why` is the quiet
relaxation this course exists to stop.

Put the ledger back and remove the rule, so the next lesson starts
clean:

<!-- learn -->
```sh
git checkout docs/security/CSP_EXCEPTIONS.md
rm -rf .zap
```

## Checkpoint

<!-- learn -->
```sh
slopstopper run security:dast -- http://localhost:8099 >/dev/null 2>&1; echo "exit $?"
kill "$(cat scratch/serve.pid)"
rm -rf scratch
```

```
exit 0
```

Green by the ledger again, server stopped, pid file gone.

## Exercise

Point the scan at the live site instead of the local one, and explain
the difference in what ZAP sees.

<details>
<summary>Solution</summary>

```sh
task ss:security:dast -- https://slopstopper.dev
```

No `📍` line, because there is nothing to rewrite, and the same gate
result. The response headers now come from the Cloudflare Worker that
serves the site rather than from `slopstopper serve` reading
`worker/headers.json`, so this is the run that would catch a header the
edge strips or adds. That is why the suite scans production after each
deploy and daily, and why a local build is enough for a pull request:
the two runs answer different questions.

</details>

## Going further

- [DAST](../security/DAST.md): the risk table, the gate's rules in
  full, `rules.tsv` by plugin id versus alert ref, static hosts that
  cannot send headers, and scanning an API through ZAP's OpenAPI mode
- [ZAP's alert registry](https://www.zaproxy.org/docs/alerts/), where
  every plugin id and alert ref resolves to its rule
- Lesson 9, whose ledger is what the gate read in step 1
- Lesson 17 for the post-deploy and scheduled runs against production,
  and the tracking issue a blocking alert on `main` opens

<details>
<summary>Episode script</summary>

**Length.** 10 to 12 minutes.

**Cold open (0:00).** `curl -I` against the deployed site: a header the
config file says is there, missing from the response. "The code is
right." Cut to a scan that reads responses, not code.

**Talking points.**

1. Why: the running thing; what a diff cannot show; baseline versus a
   full scan and why PRs get the cheap one.
2. Serve, scan, the Docker rewrite; sixty-four passes, five alerts, one
   Medium, accepted by the ledger and named.
3. The report: accepted first, counts, a table per level, the alert
   ref in the JSON.
4. Remove the ledger; red; nothing about the site changed.
5. `rules.tsv`: the alert ref, not the plugin; the reason field; green
   and named again.
6. Exercise: the live site; headers from the edge; two runs, two
   questions.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/10.tape`. Zoom on `← CSP_EXCEPTIONS.md path`, on
`blocking alerts: 1`, and on `← .zap/rules.tsv`.

**Chapters.** `0:00 Why` · `1:30 Scan` · `3:30 The report` ·
`5:00 Take the ledger away` · `7:00 rules.tsv` · `9:00 Exercise` ·
`10:30 Next lesson`.

</details>
