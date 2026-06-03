# Agent instructions — SlopStopper

Open standard for agents, AI assistants and automation tools working in this
repo. Conformant with [agents.md](https://agents.md).

> 📚 **Documentation hub:** [`docs/index.md`](./docs/index.md) is the
> structured map of all project documentation.

> 🏗️ **Naming convention:** the categories in
> [`docs/index.md`](./docs/index.md) drive naming across the project — Task
> targets use `category:action` (e.g. `hygiene:complexity`), GitHub Actions
> use `category-action-check.yml` (e.g. `hygiene-complexity-check.yml`).

## What SlopStopper is

Two things at once:

1. **A portable suite** of GitHub Actions workflows, Task targets and
   analysis scripts that consumers install into their own repos via
   [`install.sh`](./install.sh).
2. **A live reference site** under [`app/`](./app/) that markets the suite
   and proves it works — built and deployed with the same suite it
   advertises.

Changes that affect both layers (e.g. adding a new quality check) must be
reflected in the workflows AND the site copy (`app/features.html`,
`app/tools.html`) AND `README.md`. The hygiene docs-accuracy workflow exists
specifically to catch drift between these.

## Canonical interface: Taskfile.yml

**Agents must use `task <name>` instead of raw commands** wherever possible.
The Taskfile is the single source of truth for build, test, lint and scan
operations so developers, AI agents and CI all run the same thing — no
drift, no version skew.

Examples (run `task --list` for the full set):

| Task | What it does |
| ---- | ------------ |
| `task hygiene:complexity` | Cyclomatic complexity check (Lizard) |
| `task security:sast` | Static security scan (Semgrep) |
| `task security:dast` | Dynamic security scan (OWASP ZAP) |
| `task security:secrets` | Secrets detection (Gitleaks) |
| `task security:vulnerability:all` | Dependency CVE scan (Trivy) |
| `task reliability:smoke` | Smoke tests against a URL |
| `task reliability:accessibility` | axe-core WCAG 2.1 AA audit |
| `task reliability:cwv` | Lighthouse CI / Core Web Vitals |
| `task contributing:build` | TypeScript build (`tsc`) |
| `task contributing:test` | Playwright suite |
| `task contributing:run` | Local dev server on port 8080 |

The `:ci` variants (e.g. `reliability:accessibility:ci`) just delegate to
the base task with CI-friendly output paths — same logic.

## Repo structure (current state)

```
slopstopper/
├── .github/workflows/        # 19 GitHub Actions workflows (see docs/)
├── .scripts/                 # Python/shell analysis scripts called by tasks
├── app/                      # Static site — Netlify publish dir
│   ├── index.html            # Hero + Get Started + capability grid
│   ├── features.html         # 5 category cards with YAML excerpts + mock reports
│   ├── tools.html            # 14 tool cards with YAML/config excerpts
│   ├── shared.css            # Brand system, components, layout primitives
│   ├── index.css             # Page-specific layout
│   ├── features.css          # Page-specific layout (loops, bridge, reports)
│   ├── tools.css             # Page-specific layout
│   └── favicon.svg           # Inline SVG favicon (CSP-safe)
├── docs/                     # Documentation hub — see docs/index.md
├── src/                      # TypeScript stubs (build target; no runtime JS)
├── tests/                    # Playwright smoke + accessibility specs
├── install.sh                # Adopter installer
├── netlify.toml              # Netlify config + strict CSP
├── server.js                 # Local dev server that parses netlify.toml headers
├── Taskfile.yml              # Single source of truth for commands
├── playwright.config.js
├── tsconfig.json
├── package.json
├── README.md                 # Consumer-focused
└── CONTRIBUTING.md → docs/contributing/README.md
```

## Visual / brand conventions (rebranded — keep in sync if you change them)

The site is **indie-playful**: cream / peach background, tomato accent,
"Stoppy" mascot, sticker cards with offset shadows and tiny rotations,
sun-highlighter underlines, hand-drawn SVG arrows.

Brand tokens live in [`app/shared.css`](./app/shared.css) on `:root`:

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

**Contrast rule:** `--accent` (`#E8512B`) is below 4.5:1 against white. For
any text on a light background, or white text on coloured backgrounds, use
`--accent-deep`. axe-core will catch violations at the strictest `minor`
threshold — keep that gate green.

Typography is system-only (no web fonts): `ui-rounded` cascading to
`system-ui` for sans, `ui-monospace` for mono. Do not add `@font-face` or
external font links.

## CSP — what you can and cannot load

[`netlify.toml`](./netlify.toml) ships a strict CSP:

```
default-src 'self'; script-src 'self'; style-src 'self';
base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

This is non-negotiable — the security headers are tested in DAST. Therefore:

- ✅ Local CSS, local JS, local images, local fonts (none currently)
- ❌ No CDN fonts, no Google Fonts
- ❌ No external images, no `shields.io` badges
- ❌ No third-party scripts, no analytics, no embeds (no GitHub iframe, no Lighthouse iframe)
- ❌ No `data:` URLs for images (blocked by `default-src 'self'` in most browsers)

Use inline SVG for any imagery. Mascots and mock report cards are inline
SVG; the favicon is `app/favicon.svg`.

## Pages — content authoring rules

- Each HTML page links `shared.css` first, then its page-specific CSS
- Header / nav / footer markup is duplicated across pages — there is no
  build step or SSI. Accept the duplication; if you change one, change all
  three
- Every external link uses `rel="noopener noreferrer"`. Avoid
  `target="_blank"` for predictable screen-reader behaviour
- `aria-current="page"` marks the active nav link
- Skip-to-content link is the first `<body>` child
- The `<details>` collapsibles use a custom `+` / `−` marker; do not add JS
- Workflow YAML excerpts inside `<details>` are **hand-curated illustrative
  excerpts**, not verbatim. Each block has an HTML comment
  `<!-- sync this excerpt if the workflow's first job step changes -->`.
  The visible "View source" link is the canonical reference

## Deployment

- **Production:** push to `main` → [`netlify-deploy.yml`](./.github/workflows/netlify-deploy.yml) → live site
- **Preview:** open PR → preview at `https://pr-{number}--{site-name}.netlify.app` → URL posted as PR comment
- **Cleanup:** PR closed → [`netlify-cleanup-preview.yml`](./.github/workflows/netlify-cleanup-preview.yml) deletes the preview deploy
- **Secrets required:** `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`

## Operational automation

- [`workflow-failure-issue.yml`](./.github/workflows/workflow-failure-issue.yml) — failed workflow runs on `main` raise (or update) a tracking issue labelled `workflow-failure`. Linked from the live site
- [`hygiene-auto-label-pr.yml`](./.github/workflows/hygiene-auto-label-pr.yml) — labels PRs by changed paths via [`labeler.yml`](./.github/labeler.yml)
- [`hygiene-doc-updater.md`](./.github/workflows/hygiene-doc-updater.md) — gh-aw agentic workflow; weekly scan of merged PRs + open `documentation` issues, opens sync PRs labelled `documentation, automation`. Requires `ANTHROPIC_API_KEY` secret

## Commit conventions

[Conventional Commits](https://www.conventionalcommits.org/):
`<type>(<scope>): <description>` where type is one of `feat`, `fix`,
`docs`, `style`, `test`, `chore`, `refactor`. Examples:

- `feat(site): add Taskfile bridge + live issue/PR links`
- `fix(install): correct REPO_URL after rename`
- `docs(agents): refresh visual conventions`

## When making changes

| Change | Affects |
| ------ | ------- |
| Visual / brand | `app/shared.css` (tokens), then individual pages if they use new components |
| New quality check | Add workflow under `.github/workflows/`, add Task target, surface on `app/features.html` and `app/tools.html`, mention in `README.md` |
| New page | Add HTML + page-specific CSS in `app/`; link `shared.css` first; copy header/nav/footer; add to nav on the other two pages; add to `tests/smoke.spec.ts` and `tests/accessibility.spec.ts` |
| Netlify behaviour | `netlify.toml` (CSP changes are blast-radius — touch DAST tests too) |
| Installer behaviour | `install.sh` (the REPO_URL must always match this repo's actual location) |

## Verifying changes locally

```bash
task contributing:build                  # TypeScript build
task contributing:run                    # server on :8080
task contributing:test                   # Playwright smoke + a11y
task reliability:accessibility           # axe-core audit
task reliability:cwv                     # Lighthouse CI
task hygiene:complexity                  # Lizard cap
task security:sast                       # Semgrep
```

Or run the underlying npm scripts if you don't have Task installed
(`npm start`, `npm run build`, `npm test`) — but **prefer `task`** so your
behaviour matches CI exactly.

## Integration points

- **Netlify:** deployment is driven by GitHub Actions (not Netlify's git
  integration). DNS is managed externally.
- **GitHub Actions:** workflows require `NETLIFY_AUTH_TOKEN`,
  `NETLIFY_SITE_ID`, and (for the agentic doc updater) `ANTHROPIC_API_KEY`.
- **Netlify API:** the cleanup workflow uses
  `https://api.netlify.com/api/v1/sites/{site_id}/deploys` to delete
  preview deployments.

## Common pitfalls

- Adding a quality check workflow but forgetting to add a matching Task
  target → CI and local diverge
- Editing `app/index.html` but forgetting `aria-current="page"` on the
  active nav link → a11y regression
- Adding any external resource → CSP blocks it silently in production; test
  in DevTools first
- Tweaking `--accent` to use it as text colour → AA contrast fail (use
  `--accent-deep` for text)
- Adding to one HTML page's header but not the other two → nav drifts
