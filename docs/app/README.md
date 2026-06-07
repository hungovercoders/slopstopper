# App

What the site does and how its pages are organised.

## Overview

SlopStopper is a static site promoting deterministic feedback for AI-driven development. It showcases the quality gates and tools available in this repo to keep a codebase healthy through high volumes of AI-assisted changes.

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
--accent: #E8512B;       /* tomato — for decorative shapes only */
--accent-deep: #B33A1A;  /* tomato for text-on-light or text-on-accent */
--mint: #2E8B6F;         /* "pass" indicator */
--sun: #F5C24C;          /* "warning" + highlighter underline */
```

**Contrast rule:** `--accent` (`#E8512B`) is below 4.5:1 against white.
For any text on a light background, or white text on coloured
backgrounds, use `--accent-deep`. axe-core catches violations at the
strictest `minor` threshold — keep that gate green.

Typography is system-only (no web fonts): `ui-rounded` cascading to
`system-ui` for sans, `ui-monospace` for mono. Do not add `@font-face`
or external font links.

## Content authoring rules

- Each HTML page links `app/shared.css` first, then its page-specific CSS.
- Header / nav / footer markup is duplicated across pages — there is
  no build step or SSI. Accept the duplication; if you change one,
  change all four.
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

The site is a four-page static app with shared navigation. Each page has its own HTML and CSS file.

| Page | File | Title | Interactive Element |
| ---- | ---- | ----- | ------------------- |
| Home | `app/index.html` | SlopStopper | **Run Health Check** button; **Copy** button on the install curl block |
| Features | `app/features.html` | Features | **Text input + Check** — confirms a feature is enabled |
| Tools | `app/tools.html` | Tools | **Counter** — increment, decrement, and reset buttons |
| Feedback | `app/feedback.html` | Feedback | GitHub Discussions comments via Giscus embed |

Every page includes a `<nav>` bar linking to all four pages.

## File Map

```
src/index.ts        ← Home TypeScript source (compiled → app/index.js)
src/features.ts     ← Features TypeScript source (compiled → app/features.js)
src/tools.ts        ← Tools TypeScript source (compiled → app/tools.js)

app/index.html      ← Home page
app/index.css       ← Home styles
app/index.js        ← Compiled from src/index.ts (gitignored, built by tsc)

app/features.html   ← Features page
app/features.css    ← Features styles
app/features.js     ← Compiled from src/features.ts (gitignored, built by tsc)

app/tools.html      ← Tools page
app/tools.css       ← Tools styles
app/tools.js        ← Compiled from src/tools.ts (gitignored, built by tsc)

app/feedback.html   ← Feedback page (Giscus comments embed)
app/feedback.css    ← Feedback styles

app/copy.js         ← Runtime copy-button script (hand-authored, NOT compiled
                       from src/; opt-in via data-copyable on codeblocks)

server.js           ← Local dev server (reads worker/headers.json, serves app/)
wrangler.jsonc      ← Cloudflare Worker config: [assets] binding, compatibility date
worker/index.ts     ← Worker entrypoint: fetches assets, applies headers
worker/headers.json ← Canonical header map (CSP + COOP/COEP + …)
tsconfig.json       ← TypeScript config: src/ → app/
```

## Build

TypeScript source in `src/` is compiled to JavaScript in `app/` using:

```bash
npm run build
```

Cloudflare Workers Builds runs `npm run build` automatically before
deploying the Worker.

## Interaction Details

### Home — Run Health Check

Clicking the button sets the `#message` element's text to "✅ Repo is healthy!".

The install `curl` block also has a **Copy** button (powered by `app/copy.js`).
Clicking it writes the exact one-liner to the clipboard; the label restores
after 1.5 s. Only codeblocks marked with `data-copyable` get a button — the
illustrative YAML snippets on other pages are intentionally excluded.

### Features — Feature Check

1. User types a feature name into the text input.
2. Clicking **Check** displays "Feature '{name}' is enabled!".
3. If the input is blank, it prompts "Please enter a feature name."

### Tools — Counter

- **+** increments the counter.
- **−** decrements the counter.
- **Reset** sets the counter back to 0.

The counter value is held in a TypeScript variable and rendered into the `#counter` element.

### Feedback — GitHub Discussions

The page embeds [Giscus](https://giscus.app/) to surface GitHub Discussions
comments directly on the page. The embed requires a per-path CSP relaxation
(see [`docs/security/CSP_EXCEPTIONS.md`](../security/CSP_EXCEPTIONS.md)) and
serves as the reference example of the documented CSP exceptions pattern.
