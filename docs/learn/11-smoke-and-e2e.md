# Lesson 11: Smoke and end-to-end

<!-- learn-sandbox: demo -->

**Goal.** Serve the demo, run the two browser checks that prove it
works for a visitor, break each one the way a real change would, and
read what the browser saw.

## Why these checks

A green build is not a working site. The deploy can succeed and serve
a page with a JavaScript error that blanks it, a stylesheet that 404s,
a share image that social networks cannot fetch, or a navigation link
to a page that was renamed last week. None of that is visible to the
static checks, because all of it is about what a browser gets back.

`reliability:smoke` answers the first question after any deploy: does
it serve? For every path in `pages.smoke` it loads the page in a real
browser and asserts a 200, no JavaScript errors, and a load under five
seconds, then checks the homepage links a stylesheet and, when the
site has one, that the share image answers with the header that lets
another site embed it. It is the check that runs hourly against
production, because "it worked when we deployed" has a short shelf
life.

`reliability:e2e` answers the second: can a visitor get around? From
every path in `pages.e2e` it walks the primary navigation and asserts
each destination answers, has a heading and still carries the nav;
follows every in-page anchor to an element that exists; toggles every
disclosure widget open and closed; and presses the back button. It
names no selector of this site, so it runs unchanged on any site with
a `<nav>`.

Both are bundled Playwright specs inside the CLI's wheel, staged next
to your `node_modules` on each run. Exit 0 is every test passed, 1 is a
test failed, and 2 is the suite never ran to a verdict: no browser, no
`npx`, a config error.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `node`, and in the demo: `npm install` (its `package.json` lists the
  three packages the browser checks need) then
  `npx playwright install chromium`, once.

## Steps

### 1. Serve the demo and see smoke green

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
slopstopper run reliability:smoke -- http://localhost:8099
```

```
  ✓  3 [chromium] › .ss/.run/tests/smoke.spec.ts:102:7 › Smoke Tests › homepage has at least one stylesheet linked (288ms)
  ✓  2 [chromium] › .ss/.run/tests/smoke.spec.ts:71:9 › Smoke Tests › / returns 200 and loads cleanly (747ms)
  ✓  1 [chromium] › .ss/.run/tests/smoke.spec.ts:71:9 › Smoke Tests › /history.html returns 200 and loads cleanly (750ms)

  3 passed (1.4s)
```

Two pages from `pages.smoke` in `.slopstopper.yml`, plus the
stylesheet. There is no share-image test because the demo's
`smoke.og_image_path` is empty: its image is an SVG, and the assertion
is about the PNG a preview card can embed. The `.ss/.run/` path is
where the bundled spec was staged for this run; the spec itself lives
in the wheel.

### 2. Remove a page the list still names

The commonest smoke failure is a rename: the page moved, the list did
not.

<!-- learn -->
```sh
rm app/history.html
```

<!-- learn: fails -->
```sh
slopstopper run reliability:smoke -- http://localhost:8099
```

```
  ✘  1 [chromium] › .ss/.run/tests/smoke.spec.ts:71:9 › Smoke Tests › /history.html returns 200 and loads cleanly (105ms)
    Error: /history.html should return 200
    Expected: 200
    Received: 404

  1 failed
  2 passed (1.2s)
```

Playwright names the assertion and shows the line of the spec that
made it. The markdown report under `.ss/reports/reliability/` carries
the verdict and points at Playwright's own HTML report, which CI
uploads as an artifact, with a screenshot and the network log of the
failing test.

<!-- learn -->
```sh
git checkout app/history.html
rm -rf test-results
```

### 3. See end-to-end green

<!-- learn -->
```sh
slopstopper run reliability:e2e -- http://localhost:8099
```

```
  ✓  3 [chromium] › .ss/.run/tests/e2e.spec.ts:243:9 › E2E Journeys › /: browser back returns to the start (207ms)
  ✓  2 [chromium] › .ss/.run/tests/e2e.spec.ts:152:9 › E2E Journeys › /: primary navigation round trip (279ms)

  2 passed (710ms)
```

One start path from `pages.e2e`, and two of the four journeys: the
demo has no in-page anchors and no disclosure widgets, so those two
are skipped rather than failed, which is the spec's rule for a journey
the page gives it nothing to do.

### 4. Point a navigation link at a page that does not exist

<!-- learn -->
```sh
sed -i.bak 's|href="history.html"|href="nope.html"|' app/index.html && rm app/index.html.bak
```

<!-- learn: fails -->
```sh
slopstopper run reliability:e2e -- http://localhost:8099
```

```
  ✘  1 [chromium] › .ss/.run/tests/e2e.spec.ts:152:9 › E2E Journeys › /: primary navigation round trip (275ms)
    Error: nope.html: primary navigation should still be present
  1 failed
  1 passed (644ms)
```

The round trip fails at the destination: the page the link reaches has
no nav, because it is a 404 page. The other journey still passes. On a
site with no build step the nav is duplicated on every page, so a link
fixed on one page stays broken on the others until something walks
all of them; that is the slop this check exists for.

<!-- learn -->
```sh
git checkout app/index.html
rm -rf test-results
```

### 5. Know the knobs

Both checks take the URL positionally and read their page lists from
`.slopstopper.yml`:

```yaml
pages:
  smoke: /,/history.html
  e2e:   /
smoke:
  og_image_path: ''
```

`--ci` adds retries, a single worker and the HTML report, and is what
the workflows pass. `SMOKE_PAGES` and `E2E_PAGES` override the lists
for one run. Assertions specific to your site, a login or a basket,
belong in an ejected copy of the spec: `slopstopper templates eject
tests/e2e.spec.ts` drops one into `.ss/` and the CLI picks it up from
there.

## Checkpoint

<!-- learn -->
```sh
out=$(slopstopper run reliability:smoke -- http://localhost:8099 2>&1)
kill "$(cat scratch/serve.pid)"
rm -r scratch
echo "$out" | grep 'passed'
```

```
  3 passed (1.4s)
```

## Exercise

Make smoke fail without touching a page: add a path to the list that
the site does not serve.

<details>
<summary>Solution</summary>

Serve the demo again, then override the list for one run:

```sh
SMOKE_PAGES='/,/pricing.html' slopstopper run reliability:smoke -- http://localhost:8099
```

`/pricing.html should return 200` fails with a 404. The same happens
when a page is added to `pages.smoke` before it ships, which is the
right order: list it, watch it go red, then ship it and watch it go
green.

</details>

## Going further

- [Smoke tests](../reliability/README.md#smoke-tests) in the
  reliability README: every assertion, the config, adding pages
- [E2E journeys](../reliability/E2E.md): the four journeys in detail,
  what is skipped rather than failed, and adding your own
- Lesson 17 for the hourly production run and the issue it opens when
  the site stops serving

<details>
<summary>Episode script</summary>

**Length.** 9 to 11 minutes.

**Cold open (0:00).** A green deploy badge. Cut to the site: a blank
page and a console error.

**Talking points.**

1. Why: a green build is not a working site; the two questions, does
   it serve and can a visitor get around.
2. Serve; smoke green; what the three tests are and why there is no
   share-image test here.
3. Remove the history page; red; Playwright names the assertion and
   the line; the HTML report.
4. E2E green; two journeys run, two skipped.
5. Break the nav link; the round trip fails at the destination; why
   the nav is duplicated and why that is the slop.
6. The page lists, `--ci`, ejecting the spec for your own journeys.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/11.tape`. Zoom on "Expected: 200 / Received: 404".

**Chapters.** `0:00 Why` · `1:30 Smoke` · `3:00 A missing page` ·
`4:30 E2E` · `6:00 A broken link` · `8:00 The knobs` · `9:30 Next
lesson`.

</details>
