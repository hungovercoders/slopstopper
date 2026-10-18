# Lesson 11: Smoke and end-to-end

**Goal.** Serve the site, run the two browser checks that prove it
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
seconds, then checks the homepage links a stylesheet and the share
image answers with the one header that lets another site embed it.
It is the check that runs hourly against production, because "it
worked when we deployed" has a short shelf life.

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

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `node`, the npm dependencies and Playwright's Chromium, which
  `task contributing:setup` installs in one go.

## Steps

### 1. Serve the site and see smoke green

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
task ss:reliability:smoke -- http://localhost:8099
```

```
  ✓  1 [chromium] › .ss/.run/tests/smoke.spec.ts:46:9 › Smoke Tests › /features.html returns 200 and loads cleanly (953ms)
  ✓  2 [chromium] › .ss/.run/tests/smoke.spec.ts:46:9 › Smoke Tests › / returns 200 and loads cleanly (1.1s)
  ✓  3 [chromium] › .ss/.run/tests/smoke.spec.ts:46:9 › Smoke Tests › /tools.html returns 200 and loads cleanly (678ms)
  ✓  5 [chromium] › .ss/.run/tests/smoke.spec.ts:67:7 › Smoke Tests › homepage has at least one stylesheet linked (210ms)
  ✓  6 [chromium] › .ss/.run/tests/smoke.spec.ts:80:9 › Smoke Tests › og image (/og-image.png) is publicly shareable (22ms)
  ✓  4 [chromium] › .ss/.run/tests/smoke.spec.ts:46:9 › Smoke Tests › /feedback.html returns 200 and loads cleanly (853ms)

  6 passed (3.5s)
```

Four pages from `pages.smoke` in `.slopstopper.yml`, plus the
stylesheet and the share image. The `.ss/.run/` path is where the
bundled spec was staged for this run; the spec itself lives in the
wheel.

### 2. Remove a page the list still names

The commonest smoke failure is a rename: the page moved, the list did
not.

<!-- learn -->
```sh
rm app/tools.html
```

<!-- learn: fails -->
```sh
task ss:reliability:smoke -- http://localhost:8099
```

```
    Error: /tools.html should return 200

    Expected: 200
    Received: 404

      53 |
      54 |       expect(response, `${path}: navigation returned no response`).not.toBeNull();
    > 55 |       expect(response!.status(), `${path} should return 200`).toBe(200);

  1 failed
    [chromium] › .ss/.run/tests/smoke.spec.ts:46:9 › Smoke Tests › /tools.html returns 200 and loads cleanly
  5 passed (3.2s)
task: Failed to run task "ss:reliability:smoke": exit status 1
```

Playwright names the assertion and shows the line of the spec that
made it. The markdown report under `.ss/reports/reliability/` carries
the verdict and points at Playwright's own HTML report, which CI
uploads as an artifact, with a screenshot and the network log of the
failing test.

<!-- learn -->
```sh
git checkout app/tools.html
```

### 3. See end-to-end green

<!-- learn -->
```sh
task ss:reliability:e2e -- http://localhost:8099
```

```
  ✓  2 [chromium] › .ss/.run/tests/e2e.spec.ts:181:9 › E2E Journeys › /: in-page anchors resolve (220ms)
  ✓  3 [chromium] › .ss/.run/tests/e2e.spec.ts:210:9 › E2E Journeys › /: disclosure widgets open and close (1.1s)
  ✓  1 [chromium] › .ss/.run/tests/e2e.spec.ts:152:9 › E2E Journeys › /: primary navigation round trip (1.5s)
  ✓  4 [chromium] › .ss/.run/tests/e2e.spec.ts:243:9 › E2E Journeys › /: browser back returns to the start (385ms)
  ✓  6 [chromium] › .ss/.run/tests/e2e.spec.ts:181:9 › E2E Journeys › /features.html: in-page anchors resolve (200ms)
  ✓  5 [chromium] › .ss/.run/tests/e2e.spec.ts:152:9 › E2E Journeys › /features.html: primary navigation round trip (1.5s)
  ✓  8 [chromium] › .ss/.run/tests/e2e.spec.ts:243:9 › E2E Journeys › /features.html: browser back returns to the start (347ms)
  ✓  7 [chromium] › .ss/.run/tests/e2e.spec.ts:210:9 › E2E Journeys › /features.html: disclosure widgets open and close (3.6s)

  8 passed (6.6s)
```

Two start paths from `pages.e2e`, four journeys each. The disclosure
journey on the features page takes longest because that page has a
collapsible per check, and the spec clicks every one twice.

### 4. Point a navigation link at a page that does not exist

<!-- learn -->
```sh
sed -i 's|href="tools.html"|href="nope.html"|' app/index.html
```

<!-- learn: fails -->
```sh
task ss:reliability:e2e -- http://localhost:8099
```

```
  ✘  1 [chromium] › .ss/.run/tests/e2e.spec.ts:152:9 › E2E Journeys › /: primary navigation round trip (890ms)
    Error: nope.html: primary navigation should still be present
      172 |         await expect(page.locator('h1').first(), `${href}: page should have a heading`).toBeVisible();
      173 |         expect(await page.locator('nav a[href]').count(), `${href}: primary navigation should still be present`)
  1 failed
  7 passed (6.9s)
```

The other seven journeys still pass, including the round trip from the
features page, because its nav is a separate copy of the markup. That
is the slop this check exists for: a site with no build step has the
nav duplicated on every page, and a link fixed on one page stays
broken on the others until something walks all of them.

<!-- learn -->
```sh
git checkout app/index.html
```

### 5. Know the knobs

Both checks take the URL positionally and read their page lists from
`.slopstopper.yml`:

```yaml
pages:
  smoke: /,/features.html,/tools.html,/feedback.html
  e2e:   /,/features.html
smoke:
  og_image_path: /og-image.png
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
out=$(task ss:reliability:smoke -- http://localhost:8099 2>&1)
kill "$(cat scratch/serve.pid)"
rm -r scratch
echo "$out" | grep 'passed'
```

```
  6 passed (3.5s)
```

## Exercise

Make smoke fail without touching a page: add a path to the list that
the site does not serve.

<details>
<summary>Solution</summary>

Serve the site again, then override the list for one run:

```sh
SMOKE_PAGES='/,/pricing.html' task ss:reliability:smoke -- http://localhost:8099
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
2. Serve; smoke green; what the six tests are.
3. Remove the tools page; red; Playwright names the assertion and the
   line; the HTML report.
4. E2E green; the four journeys.
5. Break one nav link; one journey fails, seven pass; why the nav is
   duplicated and why that is the slop.
6. The page lists, `--ci`, ejecting the spec for your own journeys.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/11.tape`. Zoom on "Expected: 200 / Received: 404".

**Chapters.** `0:00 Why` · `1:30 Smoke` · `3:00 A missing page` ·
`4:30 E2E` · `6:00 A broken link` · `8:00 The knobs` · `9:30 Next
lesson`.

</details>
