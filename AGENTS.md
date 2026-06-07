# Agent instructions — SlopStopper

Open standard for agents, AI assistants and automation tools working in this
repo. Conformant with [agents.md](https://agents.md).

> 🗺️ **Documentation map.** [`docs/index.md`](./docs/index.md) is the
> single index of all project documentation. This file, [`CLAUDE.md`](./CLAUDE.md)
> and [`README.md`](./README.md) are intentionally thin — they point at
> the map rather than duplicating its content. When you need details on a
> check, a runbook, or a decision, navigate the map. The
> [hygiene docs-structure check](./docs/hygiene/README.md) keeps the map
> honest against the directory tree.

> 🏗️ **Naming convention:** the categories in
> [`docs/index.md`](./docs/index.md) drive naming across the project. Task
> targets are defined as `category:action` (e.g. `hygiene:complexity`) and
> invoked under the `ss` namespace (`task ss:hygiene:complexity`). GitHub
> Actions use `ss-category-action-check.yml` (e.g.
> `ss-hygiene-complexity-check.yml`).

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

## Canonical interface: Taskfile (the `ss` namespace)

**Agents must use `task ss:<name>` instead of raw commands** wherever
possible. SlopStopper's task definitions live in
[`Taskfile.ss.yml`](./Taskfile.ss.yml); the root
[`Taskfile.yml`](./Taskfile.yml) is a thin integration layer that imports
them under the `ss` namespace via `includes:`. This keeps SlopStopper's
tasks isolated from anything a consumer has in their own root Taskfile.

The Taskfile is the single source of truth for build, test, lint and scan
operations so developers, AI agents and CI all run the same thing — no
drift, no version skew.

Examples (run `task --list` for the full set):

| Task | What it does |
| ---- | ------------ |
| `task ss:hygiene:complexity` | Cyclomatic complexity check (Lizard) |
| `task ss:security:sast` | Static security scan (Semgrep) |
| `task ss:security:dast` | Dynamic security scan (OWASP ZAP) |
| `task ss:security:secrets` | Secrets detection (Gitleaks) |
| `task ss:security:vulnerability:all` | Dependency CVE scan (Trivy) |
| `task ss:reliability:smoke` | Smoke tests against a URL |
| `task ss:reliability:accessibility` | axe-core WCAG 2.1 AA audit |
| `task ss:reliability:cwv` | Lighthouse CI / Core Web Vitals |
| `task ss:contributing:build` | TypeScript build (`tsc`) |
| `task ss:contributing:test` | Playwright suite |
| `task ss:contributing:run` | Local dev server on port 8080 |

The `:ci` variants (e.g. `reliability:accessibility:ci`) just delegate to
the base task with CI-friendly output paths — same logic.

## Repo structure (current state)

```
slopstopper/
├── .github/workflows/        # All SlopStopper workflows are `ss-*.yml`
│                             #   (copilot-setup-steps.yml stays bare — platform-fixed)
├── .ss/                      # Everything SlopStopper owns lives here
│   ├── scripts/              # Python/shell analysis scripts called by tasks
│   └── reports/              # Generated report output (.gitignored)
│       ├── complexity/
│       ├── sast/
│       ├── dast/
│       ├── secrets/
│       ├── dependencies/
│       └── docs/
├── app/                      # Static site — bound as the [assets] dir on the Worker
│   ├── index.html            # Hero + Get Started + capability grid
│   ├── features.html         # 5 category cards with YAML excerpts + mock reports
│   ├── tools.html            # 15 tool cards with YAML/config excerpts
│   ├── shared.css            # Brand system, components, layout primitives
│   ├── index.css             # Page-specific layout
│   ├── features.css          # Page-specific layout (loops, bridge, reports)
│   ├── tools.css             # Page-specific layout
│   ├── copy.js               # Progressive-enhancement copy button for [data-copyable] codeblocks; only runtime JS
│   ├── favicon.svg           # Inline SVG favicon (CSP-safe)
│   ├── apple-touch-icon.svg  # Source for the 180×180 iOS home-screen icon
│   ├── apple-touch-icon.png  # Rendered via task ss:contributing:assets
│   ├── og-image.svg          # Source for the 1200×630 OpenGraph card
│   ├── og-image.png          # Rendered via task ss:contributing:assets
│   ├── manifest.webmanifest  # PWA manifest (name, icons, theme colour)
│   ├── robots.txt            # Allows all, points at the sitemap
│   └── sitemap.xml           # Lists the three indexable pages
├── docs/                     # Documentation hub — see docs/index.md
├── src/                      # TypeScript stubs (build target; runtime JS is limited to app/copy.js)
├── tests/                    # Playwright smoke + accessibility specs
├── install.sh                # Adopter installer
├── wrangler.jsonc            # Cloudflare Worker + [assets] binding (Workers Builds reads this)
├── worker/                   # Cloudflare Worker — applies headers to every response
│   ├── index.ts              # fetch handler: env.ASSETS.fetch + per-path headers
│   └── headers.json          # canonical header map (CSP, COOP/COEP, X-Frame-Options …)
├── server.js                 # Local dev server — reads worker/headers.json for parity
├── Taskfile.yml              # Thin root with `includes: { ss: ./Taskfile.ss.yml }`
├── Taskfile.ss.yml           # SlopStopper task definitions
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

## CSP — strict by default, documented per-page exceptions

[`worker/headers.json`](./worker/headers.json) is the single source of
truth for response headers. The `/*` entry ships a strict default CSP
applied to every path:

```
default-src 'self'; script-src 'self'; style-src 'self';
base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

The Cloudflare Worker (`worker/index.ts`) imports this JSON and
applies the matching headers to every response. `server.js` (local
dev / DAST) reads the same file so prod and local stay identical.
Defaults are tested in DAST. **Do not weaken the default `/*` entry.**

For pages that genuinely need a vetted third-party widget (e.g.
`/feedback.html` embeds Giscus for GitHub Discussions comments) we
allow per-path CSP exceptions via additional entries scoped to a
single path. Every exception MUST:

1. **Be scoped to a single path** in `worker/headers.json` — never widen `/*`
2. **Be documented** in [`docs/security/CSP_EXCEPTIONS.md`](./docs/security/CSP_EXCEPTIONS.md)
   with origin, directives, SRI hash, why, data leaving, refresh policy
3. **SRI-pin external scripts** wherever the host supports it
4. **Provide a fallback** so the page is still useful if the third-party
   is down or the SRI hash goes stale

The [`ss:hygiene:csp-exceptions`](./Taskfile.ss.yml) check fails the
build if `worker/headers.json` and `CSP_EXCEPTIONS.md` disagree.

Default rules for any new resource (use these unless you're explicitly
opening a documented exception):

- ✅ Local CSS, local JS, local images, local fonts (none currently)
- ✅ Inline SVG for imagery — mascots, mock report cards, favicon
- ❌ No CDN fonts, no Google Fonts
- ❌ No external images, no `shields.io` badges
- ❌ No third-party scripts on `/*` — open a per-path exception instead
- ❌ No `data:` URLs for images (blocked by `default-src 'self'` in most
  browsers)

If you're adopting SlopStopper and your site needs GTM, Sentry,
Intercom, etc., copy the pattern from `CSP_EXCEPTIONS.md`. That doc
exists for adopters as much as for this repo.

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

Cloudflare Workers Builds is connected to the repo via the Cloudflare
GitHub App and handles the whole lifecycle. **No GitHub Action
workflow ships deploys; do not add one.**

- **Production:** push to `main` → Workers Builds runs `npm run build` → `wrangler deploy` → live site at the custom domain
- **Preview:** open PR → Workers Builds creates a version with a `<hash>-slopstopper.workers.dev` URL → posted as a commit check on the PR
- **Cleanup:** PR closed → Cloudflare retires the preview version automatically
- **Visibility:** `README.md` shows a shields.io GitHub-Deployments badge for per-deploy status; `ss-reliability-smoke-tests.yml` runs hourly *and* on every `deployment_status` event for ongoing health
- **GitHub secrets required:** none. (Locally, `wrangler dev` needs a `CLOUDFLARE_API_TOKEN` in your `.zshrc.local` to authenticate.)

## Operational automation

- [`workflow-failure-issue.yml`](./.github/workflows/ss-workflow-failure-issue.yml) — failed workflow runs on `main` raise (or update) a tracking issue labelled `workflow-failure`. Linked from the live site
- [`hygiene-auto-label-pr.yml`](./.github/workflows/ss-hygiene-auto-label-pr.yml) — labels PRs by changed paths via [`labeler.yml`](./.github/labeler.yml)
- [`hygiene-doc-updater.md`](./.github/workflows/ss-hygiene-doc-updater.md) — gh-aw agentic workflow; weekly scan of merged PRs + open `documentation` issues, opens sync PRs labelled `documentation, automation`. Requires `COPILOT_GITHUB_TOKEN` secret AND the "Allow GitHub Actions to create and approve pull requests" repo setting. After editing the `.md`, recompile with `gh aw compile ss-hygiene-doc-updater`. Full runbook: [`docs/hygiene/DOC_UPDATER.md`](./docs/hygiene/DOC_UPDATER.md)

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
| Headers / CSP | `worker/headers.json` (single source of truth — CSP changes are blast-radius, touch DAST tests too) |
| Worker behaviour | `worker/index.ts` (path matching, redirects); `wrangler.jsonc` (assets binding, compatibility date) |
| Installer behaviour | `install.sh` (the REPO_URL must always match this repo's actual location) |

## Verifying changes locally

```bash
task ss:contributing:build                  # TypeScript build
task ss:contributing:run                    # server on :8080
task ss:contributing:test                   # Playwright smoke + a11y
task ss:reliability:accessibility           # axe-core audit
task ss:reliability:cwv                     # Lighthouse CI
task ss:hygiene:complexity                  # Lizard cap
task ss:security:sast                       # Semgrep
```

Or run the underlying npm scripts if you don't have Task installed
(`npm start`, `npm run build`, `npm test`) — but **prefer `task`** so your
behaviour matches CI exactly.

## Integration points

- **Cloudflare:** deployment is driven by Workers Builds (Cloudflare's
  Git integration via the Cloudflare GitHub App). DNS is managed
  through Cloudflare's dashboard; the custom domain is attached to
  the Worker directly. No GitHub secret involved.
- **GitHub Actions:** workflows require `COPILOT_GITHUB_TOKEN` (for the
  agentic doc updater). No deploy secrets.
- **Local dev:** `wrangler dev` needs `CLOUDFLARE_API_TOKEN` set as
  an env var (e.g. in `.zshrc.local`). `server.js` does not need it.

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
- Invoking `task hygiene:complexity` (or any task) without the `ss:`
  prefix → "task not found". All SlopStopper tasks live under the `ss`
  namespace via the root `Taskfile.yml`'s `includes:` block. Use
  `task ss:hygiene:complexity`
- Creating a new workflow file without the `ss-` prefix → it won't get
  grouped with the rest in the Actions UI, and consumers risk a clash
  when they install. Always name new workflows `ss-<category>-<action>.yml`
  (exception: `copilot-setup-steps.yml`, whose name is fixed by the
  platform)
- Putting analysis output anywhere other than under `.ss/reports/<category>/`
  → it won't be `.gitignore`d and could pollute the consumer's repo
