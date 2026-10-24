# Lantern agent guide

Open standard for agents, AI assistants and automation tools working in
this repo (conformant with [agents.md](https://agents.md)). `CLAUDE.md`
is `@AGENTS.md`. This file carries what most tasks need; the routes at
the end say when to open anything else.

## Ground rules

1. **The page is the product.** `app/index.html` is hand-written and
   reviewed like code; there is no build step and no JavaScript.
2. **Validate before committing.** `slopstopper run hygiene:entry-files`
   and `slopstopper run hygiene:docs-structure` are what CI runs on the
   docs; the browser checks run against `slopstopper serve`.
3. **Budgets are the feature.** When a docs check fails, move content
   deeper into `docs/` and route it; never raise the budget.

## Commands

| Command                                      | Does                                      |
| -------------------------------------------- | ----------------------------------------- |
| `slopstopper serve`                          | serve `app/` on port 8080                 |
| `slopstopper run hygiene:entry-files`        | the entry-file budgets and routes         |
| `slopstopper run hygiene:docs-structure`     | every doc under `docs/` has a route       |
| `slopstopper run reliability:smoke -- <url>` | the page loads and has its title          |

## Layout

```
AGENTS.md         this file (CLAUDE.md is @AGENTS.md)
app/index.html    the page
docs/             topic docs; docs/README.md is the map
.slopstopper.yml  slopstopper config: profile, pages, thresholds
```

## Conventions

- One service per `<article>`, one owner per service, owners are teams.
- A service whose team is gone moves to "unowned"; nothing is deleted.

## Routes: read before you act

| When you are…                                  | Do this                                                                          |
| ---------------------------------------------- | -------------------------------------------------------------------------------- |
| adding or changing a service on the page       | Read [docs/architecture.md](./docs/architecture.md) for the page's shape and the service table |
| opening a pull request                         | Read [docs/contributing.md](./docs/contributing.md) for the review rules and the checks that run |
| fixing a failing slopstopper check             | Read `.ss/reports/<check>/` first. The report names the finding and the fix         |
| doing any task not covered above               | Read [docs/README.md](./docs/README.md) before you start; do not guess a convention |

The `hygiene:entry-files` check keeps this file under its token budget
and every route above explicit, so don't remove either.
