# App

What the site does and how its pages are organised.

## Overview

SlopStopper is a static site promoting deterministic feedback for AI-driven development. It showcases the quality gates and tools available in this repo to keep a codebase healthy through high volumes of AI-assisted changes.

## Pages

The site is a three-page static app with shared navigation. Each page has its own HTML and CSS file, with TypeScript source compiled to JavaScript.

| Page | File | Title | Interactive Element |
| ---- | ---- | ----- | ------------------- |
| Home | `app/index.html` | SlopStopper | **Run Health Check** button — displays "✅ Repo is healthy!" |
| Features | `app/features.html` | Features | **Text input + Check** — confirms a feature is enabled |
| Tools | `app/tools.html` | Tools | **Counter** — increment, decrement, and reset buttons |

Every page includes a `<nav>` bar linking to all three pages.

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

server.js           ← Local dev server (reads headers from netlify.toml, serves app/)
netlify.toml        ← Netlify config: headers, routing, build settings (publish = "app")
tsconfig.json       ← TypeScript config: src/ → app/
```

## Build

TypeScript source in `src/` is compiled to JavaScript in `app/` using:

```bash
npm run build
```

Netlify runs `npm run build` automatically before deployment.

## Interaction Details

### Home — Run Health Check

Clicking the button sets the `#message` element's text to "✅ Repo is healthy!".

### Features — Feature Check

1. User types a feature name into the text input.
2. Clicking **Check** displays "Feature '{name}' is enabled!".
3. If the input is blank, it prompts "Please enter a feature name."

### Tools — Counter

- **+** increments the counter.
- **−** decrements the counter.
- **Reset** sets the counter back to 0.

The counter value is held in a TypeScript variable and rendered into the `#counter` element.
