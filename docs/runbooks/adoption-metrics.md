# Adoption metrics

How to measure who is using SlopStopper, using only public GitHub signals.
No phone-home, no proxy install, no adopter-side instrumentation.

## TL;DR

```bash
task ss:meta:adoption
```

Prints a copy/pasteable Markdown block with the five signals below.
Needs `gh` authenticated with `repo` scope (`gh auth login` if you see
403s — the Traffic endpoints require it).

## What each signal means

### ⭐ Stars and 🍴 forks

`gh api repos/hungovercoders/slopstopper`

Interest, not adoption. People star repos they want to bookmark. Forks
are a lighter signal of "I might do something with this" but still
usually exploratory.

### 📥 Clones (14-day total + unique cloners)

`gh api repos/hungovercoders/slopstopper/traffic/clones`

This is the strongest install proxy we have. `install.sh` runs
`git clone --depth=1` of the repo, so each install attempt shows up
here. But so does anyone who clones the repo for any other reason
(reading the source, debugging an issue, mirroring). Treat it as
"installs + manual exploration" — a ceiling, not a floor.

**Window:** rolling 14 days. To track trends across longer periods,
take a snapshot weekly (see "Snapshotting" below).

### 👀 Views (14-day total + unique visitors)

`gh api repos/hungovercoders/slopstopper/traffic/views`

Page views on github.com/hungovercoders/slopstopper. A signal of
interest in the repo itself (README reading, file browsing). Doesn't
include visits to the live site at slopstopper.dev.

### 📦 Public adopters

`gh api -X GET search/code -f q='filename:Taskfile.ss.yml'`

Counts public repos with `Taskfile.ss.yml` checked in — that file is
the SlopStopper marker (it's how the `ss:` namespace is wired into the
root Taskfile). Strongest indicator of real, persistent installs.

**Limitations:**

- **Public repos only.** Private adopters are invisible by design;
  that's the trade-off of the public-signals-only posture.
- **Default branch only.** GitHub code search ignores non-default
  branches.
- **Capped at 1,000 results** by the search API. We'll worry about
  this when we get there.
- **Excludes forks** by default — which is what we want; a fork isn't
  an install.

## How to read the output

Most useful as a single snapshot you can paste into release notes, a
status update, or a tracking issue:

```
## SlopStopper adoption — 2026-06-07

- ⭐ Stars: 12
- 🍴 Forks: 3
- 📥 Clones (14-day): 487 total / 124 unique
- 👀 Views (14-day): 1,203 total / 218 unique
- 📦 Public adopters (Taskfile.ss.yml on default branch): 7
```

Healthy direction: clones-unique growing, public adopters growing,
forks > 0. Stars are vanity but track them anyway.

## Snapshotting (trend across the 14-day window)

The Traffic API only exposes the last 14 days, so trend lines need
the maintainer to snapshot the output. Until there's enough data to
justify a workflow, just run the task weekly and paste the result
into a discussion or a dated note. Once we have 6+ snapshots and know
what shape the trend data should take, formalise it as
`ss-meta-adoption-snapshot.yml`.

## Authentication

The Traffic endpoints (`/traffic/clones`, `/traffic/views`) require
push access to the repo, so `gh` needs to be authenticated as a
maintainer. `gh auth login --scopes repo` if the default token is too
narrow.

## What this does NOT measure

- **Private adopters.** No public signal; out of scope by design.
- **Installs that failed midway** (curl succeeded, git clone failed) —
  the failed clones don't reach the Traffic endpoint.
- **Anyone who downloaded a release tarball.** We don't cut releases
  today.
- **slopstopper.dev visitors.** The live site has no analytics
  (Netlify's privacy-respecting analytics is paid; we haven't enabled
  it). If we ever do, add a row here.

## Why not phone home?

SlopStopper positions itself as a security and privacy-respecting
tool. A phone-home in `install.sh` or the workflows would (rightly)
erode adopter trust and would be the first thing security-conscious
adopters strip out. Public signals are weaker but defensible.
