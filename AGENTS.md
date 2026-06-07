# Agent instructions — SlopStopper

Open standard for agents, AI assistants and automation tools working in this
repo. Conformant with [agents.md](https://agents.md).

> 🗺️ **Documentation map.** [`docs/index.md`](./docs/index.md) is the
> single index of all project documentation. This file, [`CLAUDE.md`](./CLAUDE.md)
> and [`README.md`](./README.md) are intentionally thin — they point at
> the map rather than duplicating its content. The
> [`ss:hygiene:entry-files`](./docs/hygiene/README.md) check enforces a
> <2k token cap on each of them; the
> [`ss:hygiene:docs-structure`](./docs/hygiene/README.md) check keeps the
> map honest against the directory tree.

> 🏗️ **Naming convention.** The categories in
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
`app/tools.html`) AND `README.md`. The
[`ss:hygiene:docs-accuracy`](./docs/hygiene/README.md) check catches drift
between these.

## Where to find detail

| What you need | Where to look |
| ------------- | ------------- |
| Task namespace, command reference, verification checklist, commit conventions | [`docs/contributing/README.md`](./docs/contributing/README.md) |
| Repo layout, C4 diagrams, request flow, inner/outer dev loops | [`docs/architecture/README.md`](./docs/architecture/README.md) |
| Brand tokens, contrast rule, page-authoring rules | [`docs/app/README.md`](./docs/app/README.md) |
| CSP defaults, per-page exceptions process | [`docs/security/CSP_EXCEPTIONS.md`](./docs/security/CSP_EXCEPTIONS.md) |
| Deployment lifecycle, Cloudflare integration, custom-domain config | [`docs/deployment/README.md`](./docs/deployment/README.md) |
| Hygiene checks (complexity, docs-accuracy, entry-files, csp-exceptions, doc-updater) | [`docs/hygiene/README.md`](./docs/hygiene/README.md) |
| Common pitfalls when extending the suite | [`docs/contributing/PITFALLS.md`](./docs/contributing/PITFALLS.md) |

## When making changes

| Change | Affects |
| ------ | ------- |
| Visual / brand | `app/shared.css` (tokens), then individual pages if they use new components |
| New quality check | Add workflow under `.github/workflows/ss-*.yml`, add `task ss:<category>:<action>` target, surface on `app/features.html` and `app/tools.html`, mention in `README.md` |
| New page | Add HTML + page-specific CSS in `app/`; link `app/shared.css` first; copy header/nav/footer; add to nav on the other pages; add to `tests/smoke.spec.ts` and `tests/accessibility.spec.ts` |
| Headers / CSP | `worker/headers.json` (single source of truth — CSP changes are blast-radius, touch DAST tests too) |
| Worker behaviour | `worker/index.ts` (path matching, redirects); `wrangler.jsonc` (assets binding, compatibility date) |
| Installer behaviour | `install.sh` (the REPO_URL must always match this repo's actual location) |

For the gotchas that have bitten people before, see
[`docs/contributing/PITFALLS.md`](./docs/contributing/PITFALLS.md).
