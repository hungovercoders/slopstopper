# Lesson 12: Accessibility

**Goal.** Audit every page with axe-core, remove one attribute that a
screen reader depends on, watch the audit fail at the strictest
threshold, and fix it.

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

The site has one rule of its own that axe enforces for it: the tomato
accent is below 4.5:1 against the cream background, so it is for
shapes only, and text on light backgrounds uses the deeper tomato. The
exercise shows what happens when that rule is broken.

## You will need

- The checkout from the [syllabus](README.md), with the CLI on PATH.
- `node`, the npm dependencies and Playwright's Chromium, from
  `task contributing:setup`.

## Steps

### 1. Serve the site and see it green

<!-- learn -->
```sh
mkdir -p scratch
PORT=8099 slopstopper serve >/dev/null 2>&1 & echo $! > scratch/serve.pid
sleep 2
task ss:reliability:accessibility -- http://localhost:8099
```

```
♿ Running accessibility audit against: http://localhost:8099
📜 pages.accessibility (4 path(s))

Running 4 tests using 2 workers

  ✓  2 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › homepage meets accessibility threshold (1.7s)
  ✓  1 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › /features.html meets accessibility threshold (2.2s)
  ✓  3 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › /tools.html meets accessibility threshold (1.5s)
  ✓  4 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › /feedback.html meets accessibility threshold (1.4s)

  4 passed (4.8s)
```

### 2. Remove the alternative text from the homepage image

The hero's terminal demo is an image with a long `alt` describing what
the terminal shows. Strip it, the way a template that "cleans up"
attributes would.

<!-- learn -->
```sh
sed -i 's/ alt="[^"]*"//' app/index.html
```

<!-- learn: fails -->
```sh
task ss:reliability:accessibility -- http://localhost:8099
```

```
♿ Accessibility violations on homepage (1 at or above "serious" impact):
[CRITICAL] image-alt: Ensure <img> elements have alternative text or a role of none or presentation
  - img
  ✘  2 [chromium] › .ss/.run/tests/accessibility.spec.ts:59:9 › Accessibility Audit › homepage meets accessibility threshold (1.5s)
    Error: homepage: expected ≤0 violations at "serious" impact or above, but found 1
  1 failed
  3 passed (5.2s)
task: Failed to run task "ss:reliability:accessibility": exit status 1
```

The check prints each violation with its impact, its axe rule id and
the selector of each offending element before Playwright reports the
failed test. `image-alt` is critical: a screen reader user gets
nothing at all for the one thing the page is showing off.

### 3. Fix it

The fix is the attribute, with text that says what the image shows,
not that it is an image. Here that is the text that was there:

<!-- learn -->
```sh
git checkout app/index.html
task ss:reliability:accessibility -- http://localhost:8099
```

```
  4 passed (4.8s)
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
out=$(task ss:reliability:accessibility -- http://localhost:8099 2>&1)
kill "$(cat scratch/serve.pid)"
rm -r scratch
echo "$out" | grep 'passed'
```

```
  4 passed (4.8s)
```

## Exercise

Break the site's own contrast rule and see which impact level axe
gives it.

<details>
<summary>Solution</summary>

Serve the site again, then use the accent for text everywhere the
stylesheet uses the deeper tomato:

```sh
sed -i 's/color: var(--accent-deep);/color: var(--accent);/' app/shared.css
task ss:reliability:accessibility -- http://localhost:8099
git checkout app/shared.css
```

`color-contrast` fires at `serious`, which is why the default threshold
is set there: contrast is the most common real-world violation and the
one most often argued away as a design choice. The fix is the one the
brand tokens already encode: `--accent` for shapes, `--accent-deep` for
text.

</details>

## Going further

- [Accessibility monitoring](../reliability/ACCESSIBILITY.md): the
  impact levels, every variable, and what the workflow audits on each
  event
- [axe-core's rule descriptions](https://dequeuniversity.com/rules/axe/4.10),
  one page per rule id
- The contrast rule and the brand tokens in [the app README](../app/README.md)

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** The homepage with a screen reader voicing it:
"image". Nothing else.

**Talking points.**

1. Why: the failures are ordinary and invisible to a mouse; a third of
   WCAG is automatable, and that third is the floor.
2. Serve; four pages green.
3. Strip the alt; critical `image-alt`, with the rule and the
   selector; the threshold at serious and why.
4. Put it back; green. The knobs are for seeing the long tail.
5. Exercise: break the contrast rule; `color-contrast` at serious.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/12.tape`. Zoom on `[CRITICAL] image-alt`.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 No alt` ·
`4:30 Fix` · `5:30 The knobs` · `6:30 Exercise` · `8:00 Next lesson`.

</details>
