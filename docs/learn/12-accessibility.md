# Lesson 12: Accessibility

<!-- learn-sandbox: demo -->

**Goal.** Audit both of the demo's pages with axe-core, find the one
attribute a screen reader depends on that the history page is missing,
and fix it.

## Why this check

Generated markup fails accessibility constantly, and the failures are
not exotic: an image without alternative text, a button that is a
`<div>`, the brand colour used for body text, a form field with no
label. Each is invisible to a sighted reviewer with a mouse and a
barrier to someone with a screen reader, a keyboard or low vision. They
are also cheap to catch before merge and expensive after, when the
page has been copied four times.

`reliability:accessibility` loads each page in `pages.accessibility`
in a real browser and runs [axe-core](https://github.com/dequelabs/axe-core)
against it, the same engine behind the browser extensions, checking
the WCAG 2.1 AA rules. axe grades each violation by impact: critical,
serious, moderate, minor. The check fails on any violation at or above
`serious`, the default, with a threshold of zero. Automated checks
cover roughly a third of WCAG, so a green run means "nothing a machine
can find", not "accessible"; it is the floor, and the point of a floor
is that nothing gets under it.

## You will need

- The demo repo from the [syllabus](README.md), with the CLI on PATH.
- `node`, and in the demo `npm install` then
  `npx playwright install chromium` (as in lesson 11).

## Steps

### 1. Serve the demo and see it red

<!-- learn: fails 1 -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
slopstopper run reliability:accessibility -- http://localhost:8099
```

```
♿ Accessibility violations on /history.html (1 at or above "serious" impact):
[CRITICAL] image-alt: Ensure <img> elements have alternative text or a role of none or presentation
  - img
  ✓  2 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › homepage meets accessibility threshold (944ms)
  ✘  1 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › /history.html meets accessibility threshold (957ms)
    Error: /history.html: expected ≤0 violations at "serious" impact or above, but found 1
  1 failed
  1 passed (1.2s)
```

The check prints each violation with its impact, its axe rule id and
the selector of each offending element before Playwright reports the
failed test. `image-alt` is critical: the history page's one image is
the uptime chart, and a screen reader user gets nothing at all for it.

### 2. Read the element

<!-- learn -->
```sh
grep -n '<img' app/history.html
```

```
26:    <img src="uptime.svg" width="480" height="60">
```

Dimensions, so the page does not jump when it loads, and no `alt`. It
is the shape a template that "cleans up" attributes leaves behind, and
the shape most image tags written in a hurry have.

### 3. Fix it

The fix is the attribute, with text that says what the image shows,
not that it is an image.

<!-- learn -->
```sh
sed -i.bak 's|<img src="uptime.svg" width="480" height="60">|<img src="uptime.svg" width="480" height="60" alt="Uptime over the last ninety days: a flat line at 100% with two dips">|' app/history.html && rm app/history.html.bak
slopstopper run reliability:accessibility -- http://localhost:8099
```

```
  ✓  1 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › /history.html meets accessibility threshold (784ms)
  ✓  2 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › homepage meets accessibility threshold (794ms)

  2 passed (1.1s)
```

### 4. Know the knobs

`ACCESSIBILITY_IMPACT` lowers the bar to `moderate` or `minor` for one
run, and `ACCESSIBILITY_THRESHOLD` allows a number of violations
through; both are for seeing the long tail, not for making a red run
green. `pages.accessibility` in `.slopstopper.yml` is the page list.
The spec is bundled and ejectable like the others; a page that needs
to be audited in a particular state, after a login or with a dialog
open, gets its own ejected copy.

## Checkpoint

<!-- learn -->
```sh
git checkout app/history.html
rm -rf test-results
out=$(slopstopper run reliability:accessibility -- http://localhost:8099 2>&1 || true)
kill "$(cat scratch/serve.pid)"
rm -rf scratch test-results
echo "$out" | grep 'CRITICAL'
```

```
[CRITICAL] image-alt: Ensure <img> elements have alternative text or a role of none or presentation
```

Red again, with the demo as it shipped, and the fix is one attribute
whose text you have now written once.

## Exercise

Find out what impact level axe gives a contrast failure, which is the
most common real-world violation.

<details>
<summary>Solution</summary>

Serve the demo again and make the body text the same colour as the
page's muted grey:

```sh
sed -i.bak 's|color: #1d1d1b;|color: #9a9a94;|' app/style.css && rm app/style.css.bak
slopstopper run reliability:accessibility -- http://localhost:8099
git checkout app/style.css
```

`color-contrast` fires at `serious`, which is why the default threshold
is set there: contrast is the violation most often argued away as a
design choice. If the stylesheet's colours differ from the ones above,
pick any text colour close to the background; the rule, not the
value, is the point.

</details>

## Going further

- [Accessibility monitoring](../reliability/ACCESSIBILITY.md): the
  impact levels, every variable, and what the workflow audits on each
  event
- [axe-core's rule descriptions](https://dequeuniversity.com/rules/axe/4.10),
  one page per rule id

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** The history page with a screen reader voicing
it: "image". Nothing else.

**Talking points.**

1. Why: the failures are ordinary and invisible to a mouse; a third of
   WCAG is automatable, and that third is the floor.
2. Serve; red on the history page; critical `image-alt`, with the rule
   and the selector; the threshold at serious and why.
3. The element: dimensions, no alt.
4. The attribute, with text that says what the chart shows; green.
5. Put the demo back. The knobs are for seeing the long tail.
6. Exercise: a contrast failure and its impact level.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/12.tape`. Zoom on `[CRITICAL] image-alt`.

**Chapters.** `0:00 Why` · `1:30 Red` · `3:00 The element` ·
`4:00 Fix` · `5:30 The knobs` · `6:30 Exercise` · `8:00 Next lesson`.

</details>
