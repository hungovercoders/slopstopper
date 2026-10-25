# Lantern

A static status page for a small team: which services exist, who owns
each one, and where to look when one is down. Two HTML pages under
`app/` with a stylesheet, a script that refreshes the badges, no build
step, served by any static host.

This repository is the demo fixture that `slopstopper demo` writes. It
is deliberately a little slopped: a handful of checks fail on it out of
the box, one finding each, and the fix for each is the kind of edit a
real repo needs. `slopstopper demo` lists them as it writes; run any
check with `slopstopper run <check>` to see its finding.

## Quick start

```bash
slopstopper serve            # serves app/ on http://localhost:8080
slopstopper checks list      # every check the suite has
```

## Docs

[`AGENTS.md`](./AGENTS.md) carries the conventions and commands most
work needs; [`docs/README.md`](./docs/README.md) routes to everything
else.

## Everything you need to know

This section is the slop. It started as a quick note and grew into the
whole manual, pasted here because "people read the README". Every
paragraph below belongs in a doc of its own, routed from the map, and the
entry-files check will say so: the README's job is orientation and a
quick start, under a small token budget, so a reader finds the map
instead of a wall.

### How the page is built

`app/index.html` is hand-written. Every service is one `<article>` with
a name, an owner, a status badge and a link to its runbook. There is no
templating and no JavaScript; a change to the list is a change to the
HTML, reviewed like any other. Styles live in `app/style.css`, the one
stylesheet, so the page needs no JavaScript and the CSP needs nothing
beyond its own origin.

### Adding a service

Copy an existing `<article>`, change the name, the owner and the runbook
link, and keep the status badge as `unknown` until the first health
check reports. Add the service to the table in `docs/architecture.md`
so the page and the doc agree. Open a pull request; the smoke and
accessibility checks run against the page on every one.

### Releasing

Releases are a tag. `git tag -a v1.2.0 -m "v1.2.0"` and `git push
--tags`; the host deploys the tag. There is no changelog file, the tag
message is the changelog, so write it as one: what changed for the
people who read the page, not which files moved. If the release has to
be rolled back, retag the previous commit as the next version rather
than deleting the tag, because the host caches by tag name.

### Ownership rules

Every service has exactly one owner, a team name, never a person. A
service whose team is disbanded is moved to the "unowned" section at
the bottom of the page within a week, not deleted, because the page is
also the record of what used to exist. The page lists owners in the
order they appear in the on-call rota so the first name is the one to
call first.

### Checks that run here

Smoke, accessibility, SEO and the two docs checks run on every pull
request. The page has one route, `/`, so the page lists in
`.slopstopper.yml` are all `/`. There is no API and no headers file, so
the API checks and the CSP-drift check stay off. If any of this changes,
change the config and the doc together.
