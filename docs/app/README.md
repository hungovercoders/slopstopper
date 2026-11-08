# App

What the site does and how its pages are organised.

## Overview

slopstopper.dev is the reference install of SlopStopper: a Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo. The site is built and deployed with the same suite it describes, and its pages show the checks, the tools behind them, and how to adopt them.

## Brand & Design System

The site is **indie-playful**: cream / peach background, tomato accent,
"Stoppy" mascot, sticker cards with tinted offset shadows and small
rotations, sun-highlighter underlines, hand-drawn SVG arrows. It ships
in a light and a dark theme. The dark theme is not an inversion: ink
outlines would glare on a dark ground, so there the borders go
low-contrast, depth comes from tonal surfaces and soft shadows, the
highlighter becomes a marker underline and the tomato carries the
emphasis. The shapes, rotations, bubble and mascot are the same in both.

Brand tokens live in [`app/shared.css`](../../app/shared.css) on `:root`,
light first, then the dark palette:

```css
--cream: #FBF5EC;        /* page background        dark: #131110 */
--peach: #FFD9B8;        /* secondary surface      dark: #3A2E27 */
--peach-soft: #FFE9D4;   /*                        dark: #231D19 */
--ink: #2A2118;          /* primary text           dark: #EFE7DC */
--ink-soft: #6B5B47;     /* secondary text         dark: #AEA192 */
--accent: #E8512B;       /* tomato, decorative shapes only   dark: #FF6A3D */
--accent-deep: #B33A1A;  /* tomato for text and links        dark: #FFA073 */
--mint: #2E8B6F;         /* "pass" indicator       dark: #5FCBA2 */
--sun: #F5C24C;          /* "warning" + sticker surfaces     dark: #E5B547 */
--paper: #FFFFFF;        /* card surface           dark: #1C1815 */
```

Semantic tokens sit on top, and components are written against these,
never against a swatch: `--line` (every border: ink in light, muted in
dark), the `--shadow-*` set (offsets in a paper tint in light, soft
drops in dark),
`--rule` (dashed dividers), `--code-bg` / `--code-fg` / `--code-accent`
(code blocks stay dark in both themes), `--emphasis-bg` / `--emphasis-fg`
(the active nav pill, step numbers, report toolbars), `--on-sun` (text
on a sun sticker), `--highlight` with `--highlight-from` / `--highlight-to`
(the stripe: behind the lower half of the word in light, an underline in
dark) and `--btn-primary-bg` / `--btn-primary-fg`. **Write every colour
as a token**, in CSS and in the inline SVGs (`fill="var(--ink)"` works
in a presentation attribute); a hex literal will not follow the theme.
The mascot is the one exception: Stoppy is a sticker, cream-faced in
both themes.

**Dark theme mechanics.** The dark palette is declared twice in
`app/shared.css`, under `@media (prefers-color-scheme: dark)` and under
`:root[data-theme="dark"]` for an explicit choice; the two blocks must
match. `app/theme.js` is the first script in every `<head>`, so it runs
before first paint: it applies the choice stored in `localStorage`
(`theme`: `light` or `dark`) as `data-theme`, adds the `js` class that
shows the toggle, and keeps the toggle's label and the `theme-color`
metas in step. Choosing the theme the OS already prefers clears the
stored value. `app/privacy.html` names that value; keep it true. Giscus
takes the site's theme on load and follows the toggle (`app/feedback.js`).

**Contrast rule:** `--accent` is below 4.5:1 against the page in either
theme; text, links and buttons use `--accent-deep`, and sun surfaces
take `--on-sun`. axe-core gates at the strictest `minor` threshold, so
run the audit with the OS set to dark as well as light.

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
  one, change all seven, then run `task contributing:learn:site` and
  `task contributing:docs:site`, which copy the Learn and Docs pages'
  chrome into every generated page. The footer carries the privacy line, which must
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

Seven static pages with shared navigation, plus a generated page per
lesson of the course and per reference doc. Each hand-written page is one
HTML file plus one page-specific CSS file; there is no build step and no
framework.

| Page | File | Interactive element |
| ---- | ---- | ------------------- |
| Home | `app/index.html` | Hero with the copy beside the terminal demo from 980px; **Copy** buttons on the install code blocks (`app/copy.js`); `<details>` collapsibles |
| Features | `app/features.html` | The five loops as tabs (`app/tabs.js`: one panel at a time, arrow keys, the hash follows the tab so `#hygiene` deep-links; every panel shows without script); `<details>` workflow excerpt per check; a jump row to the sections below and a Back-to-top pill |
| Tools | `app/tools.html` | The tool groups as tabs (`app/tabs.js`, as on Features); `<details>` config or workflow excerpt per tool |
| Learn | `app/learn.html` | **Copy** button on the demo setup block (`app/copy.js`). Lists the course's lessons and links each to its page under `app/learn/`; `cli/tests/test_learn_page.py` keeps the list identical to `docs/learn/README.md` |
| Lessons | `app/learn/NN-slug.html` | Generated from `docs/learn/NN-slug.md` by `scripts/learnsite.py` (`task contributing:learn:site`), never edited by hand. The chrome is read from `app/learn.html`; **Copy** buttons on the command blocks; `<details>` for solutions and episode scripts; previous and next links |
| Docs | `app/docs.html` | The landing page for the reference docs: three hand-written doors in, then the section list between `<!-- docs:begin -->` and `<!-- docs:end -->`, which `scripts/docsite.py` owns |
| Doc pages | `app/docs/<dir>/<name>.html` | Generated from `docs/<dir>/<NAME>.md` by `scripts/docsite.py` (`task contributing:docs:site`), never edited by hand: a README becomes its directory's `index.html`, any other doc its name in lower case with hyphens. The chrome is read from `app/docs.html`; a breadcrumb, the section's other pages, and the file each page is rendered from. The lessons stay under `app/learn/` |
| Feedback | `app/feedback.html` | GitHub Discussions comments via the Giscus embed, loaded on a button press (`app/feedback.js`) |
| Privacy | `app/privacy.html` | None. States what the site collects (nothing), what Cloudflare keeps, which services the pages reach, and the one value the theme toggle stores in the browser; linked from every footer rather than the nav |

Every page includes the same `<nav aria-label="Main">` in its header linking
to the six main pages (Privacy is reached from the footer). Features carries a second `<nav aria-label="On this page">`
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
                                              app/lesson.css     ← Article typography, shared with the doc pages
app/docs.html       ← Docs page             app/docs.css       ← Docs page and doc page styles
app/docs/**/*.html  ← Doc pages, generated (task contributing:docs:site)
app/feedback.html   ← Feedback page        app/feedback.css   ← Feedback styles
app/privacy.html   ← Privacy page         app/privacy.css    ← Privacy styles
app/shared.css      ← Brand tokens, header/nav/footer, cards, code blocks
app/assets/demo.svg, demo-dark.svg
                    ← The hero's terminal demo in each theme, drawn from real
                       CLI output by scripts/shot.py (`task contributing:shots`);
                       re-render when a command's output changes
app/theme.js        ← Light/dark theme: first script in every <head>, the header toggle
app/copy.js         ← Copy buttons, opt-in via data-copyable
app/tabs.js         ← The tab sets on Features and Tools
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
