# Adoption metrics

How to measure who is using SlopStopper, using only public GitHub signals.
No phone-home, no proxy install, no adopter-side instrumentation.

## TL;DR

```bash
task ss:meta:adoption
```

Prints a copy/pasteable Markdown block split into two sections —
**real-adopter signals** (trustworthy) and **clone signals** (heavily
contaminated by this repo's own CI; see below).

Needs `gh` authenticated with `repo` scope (`gh auth login` if you see
403s — the Traffic endpoints require it).

## The clone problem (read this first)

SlopStopper runs ~20 GitHub Actions workflows, most of them on every
push and every PR, plus several on schedules. Each run typically does
at least one `actions/checkout` — which **is a git clone** counted by
GitHub's Traffic API.

In practice, this repo's CI generates ~2,000 clones per 14-day window
all by itself. A real human installing SlopStopper adds 1 clone to
the same bucket. The raw clones number is therefore ≈ CI noise + a
sprinkling of real installs.

The task subtracts the workflow-run count from the clones total to
give a rough "install estimate." It's imperfect (some workflows do
zero checkouts, some do several), but it gets the order of magnitude
right and is far more useful than the raw clones number.

**Rule of thumb:** treat the `installs_est` figure as ±50%, and only
trust the trend (week-over-week direction), not the absolute number.

## What each signal means

### 📦 Public adopters — the most reliable signal

`gh api -X GET search/code -f q='filename:Taskfile.ss.yml'`

Counts public repos with `Taskfile.ss.yml` checked in — that file is
the SlopStopper marker (it wires the `ss:` namespace into the root
Taskfile). This is the strongest "real, persistent install" signal we
have because:

- It's a specific filename, not a pattern an unrelated repo would
  have by accident.
- Adopters keep it. If `Taskfile.ss.yml` is gone, SlopStopper has
  been ripped out.
- It isn't contaminated by CI activity, downloads, or curl runs.

**Limitations:**

- **Public repos only.** Private adopters are invisible by design.
- **Default branch only.** Code search ignores other branches.
- **Capped at 1,000 results** by the search API. Cross that bridge
  if we get there.
- **Excludes forks** — which is what we want; a fork isn't an
  install.

### ⭐ Stars and 🍴 forks

`gh api repos/hungovercoders/slopstopper`

Interest, not adoption. People star repos they want to bookmark.
Forks are a lighter signal of "I might do something with this" but
still usually exploratory.

### 👀 Views (14-day total + unique visitors)

`gh api repos/hungovercoders/slopstopper/traffic/views`

Page views on github.com/hungovercoders/slopstopper. A signal of
interest in the repo itself (README reading, file browsing). Doesn't
include visits to the live site at slopstopper.dev.

### 📥 Clones (raw, 14-day)

`gh api repos/hungovercoders/slopstopper/traffic/clones`

Returned as-is from GitHub for completeness — but **dominated by this
repo's CI** as explained above. Useful only when paired with the CI
count below.

### 🤖 Workflow runs (14-day)

`gh api -X GET repos/hungovercoders/slopstopper/actions/runs -f created='>=YYYY-MM-DD'`

Total Actions runs in the same window as the Traffic clones. Used as
a floor estimate of "how many CI checkouts of this repo happened."
Not exact — a workflow with multiple jobs does multiple checkouts;
some jobs don't check out at all — but close enough for subtraction.

### 🧮 Install estimate

`clones_total - workflow_runs`, floored at 0.

Best rough proxy for human installs we can derive from public
signals. Treat as a noisy trend indicator, not a precise number.

## How to read the output

```
## SlopStopper adoption — 2026-06-07

**Real-adopter signals (uncontaminated by this repo's CI):**
- 📦 Public adopters (Taskfile.ss.yml on default branch): 7
- ⭐ Stars: 12
- 🍴 Forks: 3
- 👀 Views (14-day): 1,203 total / 218 unique

**Clone signal (heavily polluted by this repo's CI):**
- 📥 Clones (14-day): 2,137 total / 315 unique
- 🤖 Workflow runs (14-day, ≈ CI checkouts): 2,005
- 🧮 Install estimate (clones − CI runs, floored at 0): 132
```

What "healthy" looks like:

- **Public adopters trending up** week over week — the real win.
- **Views with growing uniques** — top of funnel is filling.
- **Install estimate > workflow runs** would mean real human installs
  outpace CI activity. Aspirational; not realistic until SlopStopper
  is much more widely known than its own CI is busy.

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
  the failed clones still reach the Traffic endpoint and inflate it.
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

## If we ever need clean install numbers

Two real options, both more work than this PR is worth:

1. **Switch `install.sh` from `git clone` to a tarball download**
   (`https://github.com/.../archive/refs/heads/main.tar.gz`). Tarballs
   don't count in Traffic clones, so the clones number would shrink
   to "CI + maintainer + exploration" only. But installs would
   disappear from public signals entirely — adopter count via code
   search would become the only install proxy.

2. **Proxy the install URL through slopstopper.dev** (Netlify redirect
   to the raw GitHub file, with redirect counts in Netlify's logs).
   Gives a real install funnel, requires a documented privacy note,
   adds a small ongoing cost.

Neither is needed at launch. Reassess if the install-estimate becomes
the metric the maintainer wants to chase.
