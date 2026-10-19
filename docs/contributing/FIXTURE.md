# The demo repo

`slopstopper demo` writes a small fixture repository, shipped inside the
CLI wheel under `cli/slopstopper/data/demo/`, that anything needing a
repo to run slopstopper against can use with no network and no clone of
this one: the course, the demo tapes, a triage walkthrough, the skill
evals. It is "Lantern", a static status page, laid out the AGENTS.md-first
way.

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
| `AGENTS.md` | The working layer: ground rules, commands, layout, explicit routes |
| `CLAUDE.md` | `@AGENTS.md` |
| `docs/README.md` | The map, routing `architecture.md` and `contributing.md` |
| `docs/architecture.md`, `docs/contributing.md` | Two routed topic docs |
| `docs/runbooks/RELEASE.md` | A doc nothing routes to |
| `.slopstopper.yml` | `profile: ui`, one page, no share image, no headers file |
| `app/index.html`, `app/style.css`, `app/og-image.svg` | The page: three services, a stylesheet, a share image and the meta tags the SEO check wants, which `slopstopper serve` serves |
| `.gitignore` | `.ss/reports/` |

The two dotfiles are stored without their dot (`slopstopper.yml`,
`gitignore`) so the packaged tree carries none; `demo.write` renames
them.

## The two findings it must keep

Two hygiene checks fail on the fresh fixture, each with exactly one
finding whose fix is the edit a real repo would make. They are the
point: a reader sees a red check, reads the report, fixes the real
thing, and sees it green.

| Check | Finding | The fix |
| ----- | ------- | ------- |
| `hygiene:entry-files` | `README.md` is over its 600-token budget (the manual pasted under "Everything you need to know"); every rule passes | Move that section into `docs/` and route it from the map; never raise the budget |
| `hygiene:docs-structure` | `docs/runbooks/RELEASE.md` has no route | One row in `docs/README.md`: a trigger, then "read", then the link |

`cli/tests/test_demo.py` runs both checks on a written copy, asserts
each reports its one finding and nothing else, applies the fix, and
asserts green. `slopstopper/demo.py`'s `FAILURES` is what the command
prints after writing; keep it true to the fixture.

## Changing it

Edit the files under `cli/slopstopper/data/demo/` and run
`task contributing:test -- -k demo`. A change that drops a finding, adds
a second one, or breaks a rule the fixture is meant to pass (AGENTS.md
under budget with explicit routes, `CLAUDE.md` a pure include) fails
there. The browser checks are not pinned by a test, but the page is
meant to pass smoke, accessibility and SEO when served (`slopstopper
serve` in the demo, then each check against `http://localhost:8080`),
so keep it valid: a title, a meta description, `lang`, one `h1`,
landmarks, a linked stylesheet, the canonical, Open Graph and Twitter
tags, and the share image they name.

Adding a deliberate finding for another check (a function past the
complexity cap, a stale reference for docs-accuracy, a pinned dependency
with a CVE, a page with an axe violation) is how the course moves onto
the fixture; each one gets a row in the table above and a test beside
the two that exist.
