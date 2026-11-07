# App

What the site does and how its pages are organised.

## Overview

slopstopper.dev is the reference install of SlopStopper: a Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo. The site is built and deployed with the same suite it describes, and its pages show the checks, the tools behind them, and how to adopt them.

## Brand & Design System

The site is **indie-playful**: cream / peach background, tomato accent,
"Stoppy" mascot, sticker cards with offset shadows and tiny rotations,
sun-highlighter underlines, hand-drawn SVG arrows. It ships in a light
and a dark theme; the dark one is the same warm family on espresso, so
the stickers, highlighter and mascot carry over rather than giving way
to a generic grey.

Brand tokens live in [`app/shared.css`](../../app/shared.css) on `:root`,
light first, then the dark palette:

```css
--cream: #FBF5EC;        /* page background        dark: #1B1612 */
--peach: #FFD9B8;        /* secondary surface      dark: #4A3426 */
--peach-soft: #FFE9D4;   /*                        dark: #33261E */
--ink: #2A2118;          /* primary text           dark: #F3EAE0 */
--ink-soft: #6B5B47;     /* secondary text         dark: #BDAE9A */
--accent: #E8512B;       /* tomato, decorative shapes only   dark: #FF6B3D */
--accent-deep: #B33A1A;  /* tomato for text, links, buttons  dark: #FF9B78 */
--mint: #2E8B6F;         /* "pass" indicator       dark: #5CC29E */
--sun: #F5C24C;          /* "warning" + highlighter underline  dark: #7A5C12 */
--paper: #FFFFFF;        /* card surface           dark: #27201A */
```

Semantic tokens sit on top: `--line` draws every border and sticker
shadow, `--rule` the dashed dividers, and `--code-bg` / `--code-fg` /
`--code-accent` keep code blocks dark in both themes instead of inverting
with the page. **Write every colour as a token**, in CSS and in the
inline SVGs (`fill="var(--ink)"` works in a presentation attribute);
a hex literal is a colour that will not follow the theme. The mascot is
the one exception: Stoppy is a sticker, cream-faced in both themes.

**Dark theme mechanics.** The dark palette is declared twice in
`app/shared.css`, under `@media (prefers-color-scheme: dark)` for the OS
preference and under `:root[data-theme="dark"]` for an explicit choice,
and the two blocks must stay identical. `app/theme.js` is the first
script in every `<head>` so it runs before first paint: it reads the
visitor's choice from `localStorage` (`theme`: `light` or `dark`), sets
`data-theme` on `<html>`, adds the `js` class that shows the toggle, and
keeps the toggle's label and the `theme-color` metas in step. The toggle
is the icon pill after GitHub in every header; choosing the theme the OS
already prefers clears the stored value, so the page follows the OS
again. `app/privacy.html` names the stored value; keep that paragraph
true. Giscus takes the site's theme on load and follows the toggle
through its `postMessage` API (`app/feedback.js`).

**Contrast rule:** `--accent` is below 4.5:1 against the page in
either theme. For any text, link or button, use `--accent-deep`; `--sun`
surfaces take full `--ink` text, never faded. axe-core catches
violations at the strictest `minor` threshold, so keep that gate green
in both themes (run the accessibility audit with the OS set to dark as
well as light).

Typography is one self-hosted face: Nunito (SIL OFL 1.1, licence in
`app/fonts/OFL.txt`) as a single variable WOFF2, latin subset, at
`app/fonts/nunito-latin.woff2`. `app/shared.css` declares it with
`@font-face` (`font-display: swap`, a `unicode-range` so glyphs outside
the subset fall through to the system stack) and every page preloads it.
Mono stays `ui-monospace` cascading to the system. It is same-origin, so
the CSP needs no font-src exception; do not add external font links.

## Content authoring rules

- The one-sentence identity ("A Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo.") appears verbatim in the home hero, the home meta/OpenGraph/Twitter descriptions, the web manifest, `app/llms.txt`, `README.md`, `cli/README.md`, `cli/pyproject.toml` and the install skill. `cli/tests/test_site_identity.py` fails if any copy drifts, so change them all, or change the constant in the test with them.
- Each HTML page links `app/shared.css` first, then its page-specific CSS.
- Header / nav / footer markup is duplicated across pages because
  there is no build step or SSI. Accept the duplication; if you change
  one, change all six, then run `task contributing:learn:site`, which
  copies the Learn page's chrome into every lesson page. The footer carries the privacy line, which must
  stay true: see `app/privacy.html` and the CSP pitfall in
  `docs/contributing/PITFALLS.md`.
- Every external link uses `rel="noopener noreferrer"`. Avoid
  `target="_blank"` for predictable screen-reader behaviour.
- `aria-current="page"` marks the active nav link.
- Skip-to-content link is the first `<body>` child.
- The `<details>` collapsibles use a custom `+` / `−` marker; do not
  add JS.
- Workflow YAML excerpts inside `<details>` are **hand-curated
  illustrative excerpts**, not verbatim. Each block has an HTML
  comment `<!-- sync this excerpt if the workflow's first job step
  changes -->`. The visible "View source" link is the canonical
  reference.

## Pages

Six static pages with shared navigation, plus a generated page per lesson
of the course. Each hand-written page is one HTML file plus one
page-specific CSS file; there is no build step and no framework.

| Page | File | Interactive element |
| ---- | ---- | ------------------- |
| Home | `app/index.html` | **Copy** buttons on the install code blocks (`app/copy.js`); `<details>` collapsibles |
| Features | `app/features.html` | `<details>` workflow excerpt per check; an "On this page" jump row under the hero and two Back-to-top pills |
| Tools | `app/tools.html` | `<details>` config or workflow excerpt per tool |
| Learn | `app/learn.html` | **Copy** button on the demo setup block (`app/copy.js`). Lists the course's lessons and links each to its page under `app/learn/`; `cli/tests/test_learn_page.py` keeps the list identical to `docs/learn/README.md` |
| Lessons | `app/learn/NN-slug.html` | Generated from `docs/learn/NN-slug.md` by `scripts/learnsite.py` (`task contributing:learn:site`), never edited by hand. The chrome is read from `app/learn.html`; **Copy** buttons on the command blocks; `<details>` for solutions and episode scripts; previous and next links |
| Feedback | `app/feedback.html` | GitHub Discussions comments via the Giscus embed, loaded on a button press (`app/feedback.js`) |
| Privacy | `app/privacy.html` | None. States what the site collects (nothing), what Cloudflare keeps, which services the pages reach, and the one value the theme toggle stores in the browser; linked from every footer rather than the nav |

Every page's header also carries the theme toggle (`app/theme.js`), after the GitHub button.

Every page includes the same `<nav aria-label="Main">` in its header linking
to the five main pages (Privacy is reached from the footer). Features carries a second `<nav aria-label="On this page">`
for its jump row; the header rules in `app/shared.css` are scoped to
`header nav` so it styles itself, and the distinct labels keep the two
landmarks unique for the accessibility audit.

## File Map

```
app/index.html      ← Home page            app/index.css      ← Home styles
app/features.html   ← Features page        app/features.css   ← Features styles
app/tools.html      ← Tools page           app/tools.css      ← Tools styles
app/learn.html      ← Learn page           app/learn.css      ← Learn styles
app/learn/*.html    ← Lesson pages, generated (task contributing:learn:site)
                                              app/lesson.css     ← Lesson page styles
app/feedback.html   ← Feedback page        app/feedback.css   ← Feedback styles
app/privacy.html   ← Privacy page         app/privacy.css    ← Privacy styles
app/shared.css      ← Brand tokens, header/nav/footer, cards, code blocks
app/assets/demo.svg ← The hero's terminal demo, drawn from real CLI output by
                       scripts/shot.py (`task contributing:shots`); re-render
                       when a command's output changes
app/theme.js        ← Light/dark theme: first script in every <head>, the header toggle
app/copy.js         ← Copy buttons, opt-in via data-copyable
app/feedback.js     ← Inserts the Giscus loader when the visitor asks; holds its SRI pin
app/llms.txt, robots.txt, sitemap.xml, manifest.webmanifest, og-image.png,
favicon.svg, apple-touch-icon.png
                    ← Discoverability and share assets the reliability checks audit

slopstopper serve   ← Local dev server (bundled in slopstopper-cli;
                       applies worker/headers.json, serves app/)
wrangler.jsonc      ← Cloudflare Worker config: [assets] binding, compatibility date
worker/index.ts     ← Worker entrypoint: fetches assets, applies headers
worker/headers.json ← Canonical header map (CSP, COOP/COEP, …)
```

## Build

There is none. `npm run build` is a no-op echo kept because Cloudflare
Workers Builds runs it before `wrangler deploy`; Wrangler bundles
`worker/index.ts` itself. Edit the HTML and CSS under `app/` and they ship
as-is.

## Interaction Details

### Theme toggle

`app/theme.js` runs before first paint, applies a stored choice of
`light` or `dark` as `data-theme` on `<html>`, and binds the header
toggle. With no stored choice the page follows the OS; a choice that
matches the OS is not stored. The icon shows the theme you would switch
to and is chosen by CSS (`--show-sun` / `--show-moon` in the palette),
so it is right even before the script has bound the button.


### Copy buttons

`app/copy.js` adds a **Copy** button to every code block marked
`data-copyable`. Clicking it writes the block's exact text to the
clipboard; the label restores after 1.5 s. The illustrative YAML excerpts
on Features and Tools are deliberately not copyable.

### Collapsibles

`<details>` elements carry the custom `+` / `−` marker from
`app/shared.css` and need no script.

### Feedback via GitHub Discussions

The page offers [Giscus](https://giscus.app/) comments from GitHub Discussions,
loaded by `app/feedback.js` only when the visitor presses the button, so reading
the page sends nothing to giscus.app. The embed requires a per-path CSP relaxation
(see [`docs/security/CSP_EXCEPTIONS.md`](../security/CSP_EXCEPTIONS.md)) and
serves as the reference example of the documented CSP exceptions pattern.
