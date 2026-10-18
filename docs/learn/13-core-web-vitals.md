# Lesson 13: Core Web Vitals

**Goal.** Run Lighthouse against the site, read the budget it enforces,
add one blocking script, and watch the numbers move.

## Why this check

Performance slop never looks like a performance change. It is a
400 KB web font added for one heading, an image without dimensions,
an analytics snippet pasted into `<head>` because that is where the
vendor's instructions put it. Each is one line in a PR. Nobody notices
until the page feels slow on a phone, and by then there are a dozen
such lines and no way to tell which one did it.

`reliability:cwv` turns the feeling into a number with a threshold. It
runs [Lighthouse](https://developer.chrome.com/docs/lighthouse) three
times against each URL and asserts on the metrics Google calls Core
Web Vitals: Largest Contentful Paint (how long until the main content
is on screen), Total Blocking Time (how long the main thread is busy
and cannot respond), and Cumulative Layout Shift (how much the page
jumps around while loading), plus the overall performance and SEO
scores. Each assertion is judged on the best of the three runs, so one
slow run on a noisy CI machine does not fail the build.

The budgets are deliberately loose: a static site clears them easily,
and a budget that fires on runner noise is worse than none. They live
in Lighthouse's own config, bundled in the wheel, with a dev set for
local and pull-request runs and a stricter prod set for the live site.
Exit 0 is every assertion within budget, 1 is a budget missed, 2 is
Lighthouse could not run: no Chrome, no `npx`, the URL unreachable.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `node` and the npm dependencies from `task contributing:setup`.
- A Chrome or Chromium that Lighthouse can launch. It finds an
  installed Chrome on its own; `CHROME_PATH` points it at another, such
  as the Chromium Playwright installed.

## Steps

### 1. Serve the site and see it green

Three Lighthouse runs take about a minute.

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
task ss:reliability:cwv -- http://localhost:8099
```

```
🚦 Running Core Web Vitals audit against: http://localhost:8099
✅  .lighthouseci/ directory writable
✅  Configuration file found
✅  Chrome installation found
Healthcheck passed!
Running Lighthouse 3 time(s) on http://localhost:8099
Run #1...done.
Run #2...done.
Run #3...done.
Done running Lighthouse!
Checking assertions against 1 URL(s), 3 total run(s)
All results processed!
📁 Reports saved to: .ss/reports/cwv/
   • cwv-report.md
```

### 2. Read the budget

<!-- learn -->
```sh
sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md
```

```
| Metric | Threshold | Status |
|--------|-----------|--------|
| Performance score | ≥ 70 | ✅ 100/100 |
| LCP | ≤ 4 s | ✅ 1728 ms |
| TBT | ≤ 600 ms | ✅ 0 ms |
| CLS | ≤ 0.25 | ✅ 0.000 |
```

The site paints its main content in under two seconds, blocks the
main thread for no time at all, and nothing shifts. The full Lighthouse
HTML reports, one per run, are under `.ss/reports/cwv/lighthouse/`,
and CI uploads them as an artifact.

### 3. Add one blocking script

A script in `<head>` without `defer` runs before the browser renders
anything below it. This one does nothing but spin for a second and a
half, which is what a badly written tag manager does while it decides
what to load.

<!-- learn -->
```sh
printf 'const until = Date.now() + 1500;\nwhile (Date.now() < until) {}\n' > app/slow.js
sed -i 's|<link rel="stylesheet" href="shared.css">|<script src="slow.js"></script>\n    <link rel="stylesheet" href="shared.css">|' app/index.html
```

<!-- learn: fails -->
```sh
task ss:reliability:cwv -- http://localhost:8099
```

```
  ✘  largest-contentful-paint failure for maxNumericValue assertion
       Largest Contentful Paint
       https://developer.chrome.com/docs/lighthouse/performance/lighthouse-largest-contentful-paint/
        expected: <=4000
           found: 7115.1494
      all values: 7115.1494, 7146.7868, 7127.7963
Assertion failed. Exiting with status code 1.
task: Failed to run task "ss:reliability:cwv": exit status 1
```

Lighthouse names the audit, links its explanation, and shows all three
runs so you can see the miss is not noise. The report table says the
same in one line each:

<!-- learn -->
```sh
sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md
```

```
| Metric | Threshold | Status |
|--------|-----------|--------|
| Performance score | ≥ 70 | ❌ 59/100 |
| LCP | ≤ 4 s | ❌ 7128 ms |
| TBT | ≤ 600 ms | ✅ 12 ms |
| CLS | ≤ 0.25 | ✅ 0.000 |
```

One script, and the main content takes four times as long to appear.
TBT barely moved, because the spin happened before anything painted;
it is LCP that paid for it. That is the point of measuring more than
one thing: the same change shows up in a different metric depending on
where in the load it lands.

### 4. Fix it

The real fix for a script like this is `defer`, or loading it after
the content, or not loading it at all. Here it was scratch, so remove
it and run again.

<!-- learn -->
```sh
git checkout app/index.html
rm app/slow.js
task ss:reliability:cwv -- http://localhost:8099 >/dev/null
sed -n '/| Metric/,/CLS/p' .ss/reports/cwv/cwv-report.md
```

```
| Metric | Threshold | Status |
|--------|-----------|--------|
| Performance score | ≥ 70 | ✅ 100/100 |
| LCP | ≤ 4 s | ✅ 1728 ms |
| TBT | ≤ 600 ms | ✅ 0 ms |
| CLS | ≤ 0.25 | ✅ 0.000 |
```

### 5. Know the knobs

The budgets are in `lighthouserc.json` (dev) and `lighthouserc.prod.json`
(prod) inside the wheel. `slopstopper templates eject lighthouserc.json`
drops an editable copy into `.ss/`, which the check prefers. `--prod`
selects the stricter set, which the daily run against production and
the post-deploy trigger use. Nothing leaves your machine by default:
publishing a report to Lighthouse's public storage is opt-in through
`reliability.cwv.public_report`, and the report links it when on.

## Checkpoint

<!-- learn -->
```sh
kill "$(cat scratch/serve.pid)"
rm -r scratch
grep 'Core Web Vitals' .ss/reports/cwv/cwv-report.md
```

```
## 🚦 Core Web Vitals ✅ PASSED
```

## Exercise

Tighten one budget until the site, unchanged, fails it. Then put the
budget back.

<details>
<summary>Solution</summary>

Eject the dev config and lower the LCP budget below what the site
achieves:

```sh
slopstopper templates eject lighthouserc.json
sed -i 's/"maxNumericValue": 4000/"maxNumericValue": 1000/' .ss/lighthouserc.json
task ss:reliability:cwv -- http://localhost:8099
rm .ss/lighthouserc.json
```

LCP at around 1.7 s now fails a 1 s budget. The exercise is the honest
way to raise the bar: tighten one budget to just above what you have
measured for a few weeks, then another, rather than guessing at the
numbers on day one.

</details>

## Going further

- [Core Web Vitals](../reliability/CWV.md): every metric and budget,
  the dev and prod configs, reading a failure, and what the workflow
  audits on each event
- [Lighthouse's own guide](https://developer.chrome.com/docs/lighthouse/overview)
  for what each audit measures
- Lesson 14, the metatag half of what Lighthouse's SEO score covers

<details>
<summary>Episode script</summary>

**Length.** 9 to 11 minutes.

**Cold open (0:00).** A phone, a page that stays blank for seven
seconds. Cut to the diff: one `<script>` tag.

**Talking points.**

1. Why: performance slop never looks like a performance change; a
   number with a threshold.
2. Serve; three runs; the report table and what each metric means.
3. The spinning script; red; the assertion with all three values.
4. LCP paid, TBT barely moved; why measuring several things matters.
5. Remove it; green. The knobs: eject, `--prod`, public reports off by
   default.
6. Exercise: tighten a budget to what you measure.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/13.tape`. Zoom on "found: 7115" and on "59/100".

**Chapters.** `0:00 Why` · `1:30 Green` · `3:00 The budget` ·
`4:00 One script` · `6:30 Fix` · `8:00 The knobs` · `9:30 Next
lesson`.

</details>
