# The demo repo

`slopstopper demo` writes a small fixture repository, shipped in the CLI
wheel under `cli/slopstopper/data/demo/`, for anything that needs a repo
to run slopstopper against with no network and no clone of this one: the
course, the demo tapes, a triage walkthrough, the skill evals. It is
"Lantern", a static status page, laid out the AGENTS.md-first way.

```bash
slopstopper demo                 # writes slopstopper-demo/
slopstopper demo --out /tmp/lantern --force
slopstopper demo --json          # {out, written, skipped, failures}
```

Files already in the directory are left alone unless `--force` is
given, so a demo someone has started editing survives a second run.

## What it contains

| Path | Role |
| ---- | ---- |
| `README.md` | Orientation and a quick start, plus a pasted-in manual that puts it over budget |
| `AGENTS.md`, `CLAUDE.md` | The working layer with explicit routes; `@AGENTS.md` |
| `docs/README.md` | The map, routing `architecture.md`, `contributing.md` and `security/CSP_EXCEPTIONS.md` |
| `docs/runbooks/RELEASE.md` | A doc nothing routes to |
| `docs/security/CSP_EXCEPTIONS.md` | The CSP ledger: the schema and an empty `## Exceptions` section |
| `.slopstopper.yml` | `profile: ui`, two pages, `headers.source: app/_headers`; the smoke share-image assertion is off because the image is an SVG |
| `.env.example` | The values the script needs, blank; lesson 6 adds the fake key itself |
| `scripts/status.py`, `scripts/requirements.txt` | A script that refreshes the badges, and its one pinned dependency |
| `app/index.html`, `app/history.html`, `app/style.css`, `app/og-image.svg`, `app/uptime.svg` | The two pages with a nav between them, the stylesheet, the share image and the uptime chart |
| `app/_headers` | The host's headers: a strict baseline for `/*` and one relaxation for `/history.html` |
| `app/sitemap.xml`, `app/robots.txt`, `app/llms.txt` | The discovery files |
| `.gitignore` | `.ss/reports/`, `.env` and `node_modules/` |
| `package.json` | The devDependencies the browser checks need (Playwright, axe, Lighthouse CI); `npm install` once, then `npx playwright install chromium` |

Dotfiles are stored without the dot and renamed by `demo.write`; the
command's help and output come from `demo.FAILURES`.

## The findings it must keep

One check per lesson fails on the fresh fixture, each with exactly one
finding whose fix is the edit a real repo would make: a reader sees a
red check, reads the report, fixes the real thing, and sees it green.
Every other check passes or skips.

| Check | Finding | The fix |
| ----- | ------- | ------- |
| `hygiene:entry-files` | `README.md` is over its 600-token budget (the manual under "Everything you need to know"); every rule passes | Move that section into `docs/` and route it; never raise the budget |
| `hygiene:docs-structure` | `docs/runbooks/RELEASE.md` has no route | One row in `docs/README.md`: a trigger, then "read", then the link |
| `hygiene:docs-accuracy` | `docs/contributing.md` says to run a `task` target (`ss:hygiene:docs`) and the repo has no Taskfile | Name the `slopstopper run` commands that exist |
| `hygiene:complexity` | `badge()` in `scripts/status.py` maps sixteen HTTP statuses with sixteen `if`s: CCN 17 against the cap of 15 | A dict of the sixteen statuses and a one-line lookup, CCN 1 |
| `security:sast` | `scripts/status.py` builds a `git commit` command from a string and runs it with `shell=True`: `subprocess-shell-true`, at ERROR (two `missing-integrity` WARNINGs on the stylesheet links are reported and do not block) | A list, and no shell |
| `security:vulnerability:all` | `scripts/requirements.txt` pins `requests==2.19.1`: CVE-2018-18074 (HIGH), plus four MEDIUMs that are reported and do not block | The version the Fixed In column names, or the current release |
| `hygiene:csp-exceptions` | `app/_headers` lets `/history.html` load images from `https://charts.example.com`; the ledger has no entry | The entry with all seven fields, or drop the relaxation |
| `reliability:accessibility` | The uptime chart on `app/history.html` is an `<img>` with no `alt`: `image-alt`, critical | An `alt` that says what the chart shows |
| `reliability:seo` | `app/history.html` has no `<meta name="description">`; every other tag is present | The one line in its `<head>` |
| `reliability:sitemap` | `app/sitemap.xml` lists `/` only, and the status page links to `/history.html` | A `<url>` entry, or generate the file from the page list |

The last three need the page served (`slopstopper serve` in the demo,
then the check against `http://localhost:8080`). `index.html` passes
every browser check on its own; smoke, e2e, broken-links, robots-txt and
llms-txt pass on both pages, so a lesson that breaks one starts green.

`cli/tests/test_demo.py` runs every check on a written copy, asserts it
reports its one finding and nothing else, applies the fix, and asserts
green. The scanner-backed tests run the real tool and skip where it is
not on PATH; the Playwright-backed tests skip without the repo's
`node_modules`. `slopstopper/demo.py`'s `FAILURES` is what the command
prints after writing; keep it true to the fixture.

## The fixture's slop and this repo's own checks

The fixture lives inside this repository, so two of its findings are
excluded from slopstopper's own runs by path, with the reason beside
the exclusion: `.slopstopper.yml` (`hygiene.complexity.exclude`) and
`.semgrepignore`. The vulnerable pin is stored as
`scripts/requirements.demo` and becomes `requirements.txt` only when the
demo is written, so neither Trivy nor the dependency review reads it as
ours. The fixture carries no secret: a key-shaped string in this
repository's history would be found on every branch and reported to the
vendor whose shape it borrows, so lesson 6 adds its own fake private key.

## Changing it

Edit the files under `cli/slopstopper/data/demo/` and run
`task contributing:test -- -k demo`; a change that drops a finding, adds
a second, or breaks a rule the fixture should pass fails there. A new
finding is a row in `FAILURES`, a row in the table above, a test beside
the others and, if this repo's own run would see it, an exclusion.
