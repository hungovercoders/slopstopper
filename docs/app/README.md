# App

What the site does and how its pages are organised.

## Overview

slopstopper.dev is the reference install of SlopStopper: a Python CLI plus GitHub Actions workflows that run security, hygiene and reliability checks on every PR. One command to install into any repo. The site is built and deployed with the same suite it describes, and its pages show the checks, the tools behind them, and how to adopt them.

## Brand & Design System

The site is **indie-playful**: cream / peach background, tomato accent,
"Stoppy" mascot, sticker cards with offset shadows and tiny rotations,
sun-highlighter underlines, hand-drawn SVG arrows.

Brand tokens live in [`app/shared.css`](../../app/shared.css) on `:root`:

```css
--cream: #FBF5EC;        /* page background */
--peach: #FFD9B8;        /* secondary surface */
--peach-soft: #FFE9D4;
--ink: #2A2118;          /* primary text */
--ink-soft: #6B5B47;     /* secondary text */
--accent: #E8512B;       /* tomato, decorative shapes only */
--accent-deep: #B33A1A;  /* tomato for text-on-light or text-on-accent */
--mint: #2E8B6F;         /* "pass" indicator */
--sun: #F5C24C;          /* "warning" + highlighter underline */
```

**Contrast rule:** `--accent` (`#E8512B`) is below 4.5:1 against white.
For any text on a light background, or white text on coloured
backgrounds, use `--accent-deep`. axe-core catches violations at the
strictest `minor` threshold, so keep that gate green.

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
  one, change all five. The footer carries the privacy line, which must
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

Five static pages with shared navigation. Each page is one HTML file plus
one page-specific CSS file; there is no build step and no framework.

| Page | File | Interactive element |
| ---- | ---- | ------------------- |
| Home | `app/index.html` | **Copy** buttons on the install code blocks (`app/copy.js`); `<details>` collapsibles |
| Features | `app/features.html` | `<details>` workflow excerpt per check; an "On this page" jump row under the hero and two Back-to-top pills |
| Tools | `app/tools.html` | `<details>` config or workflow excerpt per tool |
| Feedback | `app/feedback.html` | GitHub Discussions comments via the Giscus embed, loaded on a button press (`app/feedback.js`) |
| Privacy | `app/privacy.html` | None. States what the site collects (nothing), what Cloudflare keeps, and which services the pages reach; linked from every footer rather than the nav |

Every page includes the same `<nav aria-label="Main">` in its header linking
to the four main pages (Privacy is reached from the footer). Features carries a second `<nav aria-label="On this page">`
for its jump row; the header rules in `app/shared.css` are scoped to
`header nav` so it styles itself, and the distinct labels keep the two
landmarks unique for the accessibility audit.

## File Map

```
app/index.html      ← Home page            app/index.css      ← Home styles
app/features.html   ← Features page        app/features.css   ← Features styles
app/tools.html      ← Tools page           app/tools.css      ← Tools styles
app/feedback.html   ← Feedback page        app/feedback.css   ← Feedback styles
app/privacy.html   ← Privacy page         app/privacy.css    ← Privacy styles
app/shared.css      ← Brand tokens, header/nav/footer, cards, code blocks
app/assets/demo.svg ← The hero's terminal demo, drawn from real CLI output by
                       scripts/shot.py (`task contributing:shots`); re-render
                       when a command's output changes
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
