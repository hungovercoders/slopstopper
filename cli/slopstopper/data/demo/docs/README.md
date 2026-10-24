# Docs index

The fallback routing table (a README so it renders in place when you
browse `docs/`). `AGENTS.md` carries what most tasks need and routes the
common cases directly; come here when your task is not covered there.
Read only the doc whose trigger matches; each row says when.

## Routes

| When you are…                                | Do this                                                                 |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| changing the page, or asking why it is one file | Read [architecture.md](architecture.md) for the page's shape and the service table |
| opening a pull request, or reviewing one     | Read [contributing.md](contributing.md) for the review rules and the checks that run |

Every doc under `docs/` needs a row here (or in a README above it) in the
form **trigger → "read" → file → what it holds**. The
`hygiene:docs-structure` check fails on a doc nothing routes to and on a
row that only says "see".
