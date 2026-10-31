# slopstopper-steward: the org-wide operator

slopstopper is per-repo: it tells one repo what is wrong and ships how to
fix it. [`hungovercoders/slopstopper-steward`](https://github.com/hungovercoders/slopstopper-steward)
is the counterpart that works across an organisation. On a schedule it
finds every repo with slopstopper installed, moves CLI pins that fell
behind, and works the issues slopstopper raised, opening one pull request
per piece of work. It is a separate repo and package so an adopter's
install stays small and the cross-repo token stays out of every adopter.

## The split

| Concern | slopstopper (here) | steward |
| ------- | ------------------ | ------- |
| What is wrong in a repo | the checks, `emit`'s PR comments and issues, the failure tracker | reads the issues |
| How to fix it | the `slopstopper-triage` and `slopstopper-install` skills, shipped into every adopter | hands the agent the repo's own copy, or fetches them at the pinned release's tag |
| What a repo should carry | `slopstopper install` from the pinned CLI | runs it, from the target version |
| Which version | the `"pipx:slopstopper-cli"` pin in `mise.toml`, moved by `install.sh --cli-version` | picks the target (PyPI + its policy) and rewrites that one line |
| Which repos, when, how much | nothing | discovery, budgets, the schedule, the report |

The steward carries no check logic and no fix knowledge. Anything that
explains how a check works or how to fix it belongs in the two skills
here, which the steward then gets for free in every adopter.

## What the steward reads from this repo

These are the surfaces its [contract module](https://github.com/hungovercoders/slopstopper-steward/blob/main/steward/contract.py) names. The steward's CI
checks them against this repo's `main` on every steward PR and nightly;
nothing in this repo's own CI does, so the steward row in
[`docs/contributing/CHANGE_MAP.md`](../contributing/CHANGE_MAP.md) lists
them for anyone changing one:

- **Discovery:** the `slopstopper` repo topic the installer adds, the
  `"pipx:slopstopper-cli"` key in `mise.toml`, `.ss/.installed-from`.
- **Findings:** the `slopstopper` brand label, the
  `<!-- slopstopper:check=<name> -->` and `<!-- slopstopper:workflow=<file> -->`
  body markers `emit` writes, and the failure tracker's `workflow-failure`
  label and `❌ Workflow Failure: <name>` title.
- **Method:** `.claude/skills/slopstopper-triage/` and
  `.claude/skills/slopstopper-install/` (on a big upgrade the agent works
  the `## Refresh-only` section of its `references/refresh.md`), and the
  `slopstopper-workaround: hungovercoders/slopstopper#N` marker.
- **Commands:** `slopstopper install --no-topic`, `slopstopper run --json`,
  `slopstopper checks list --json`, `slopstopper profile expand <n> --json`
  and `slopstopper doctor --json` with its `needed_by` (the shapes in
  [`docs/contributing/README.md`](../contributing/README.md)).
- **Checks that need an installed environment:** `security:licences`,
  registered in `cli/slopstopper/checks/__init__.py`, inventories the
  interpreter's packages (`pip inspect` in `checks/licences.py`), so the
  steward reports it unverified in a bare clone instead of red.
- **Releases:** PyPI `slopstopper-cli` and the `v<version>` tag form
  (`include-v-in-tag` in `release-please-config.json`), so release notes
  and skills can be fetched for a pinned version.

Before merging a change to any of these, run `steward contract <path to
this checkout>` from a steward checkout, and open the matching steward PR
in the same change.

## What it never does

No merge, no push to a default branch, no change to repo settings, no
edit of an issue. Every write is a `steward/<order>` branch and a PR
carrying `<!-- steward:order=<id> -->`; an issue labelled `steward:ignore`
is left alone. Its agent runs boxed inside a clone with no push rights
and a dollar cap, and only for judgement calls: an open finding, or a
check that went red after a refresh. Moving a pin and rewriting the suite
is code.
