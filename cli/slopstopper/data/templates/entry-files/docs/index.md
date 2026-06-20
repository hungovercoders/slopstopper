# Documentation Index

This file is **the map** — every other entry point in the repo defers to it.

## The Map Pattern

The repo has three thin entry-point files —
[`README.md`](../README.md) (humans),
[`AGENTS.md`](../AGENTS.md) (automation, conformant with
[agents.md](https://agents.md)) and
[`CLAUDE.md`](../CLAUDE.md) (Claude Code) — and each one defers to this
index instead of duplicating documentation inline.

The `ss:hygiene:entry-files` check enforces that the three entry files
stay thin and link here. The `ss:hygiene:docs-structure` check keeps the
directory tree below honest against the categories table.

## Documentation Categories

Each category has a README that defines its purpose. Replace the example
row with the categories that make sense for this repo (architecture,
deployment, runbooks, contributing, etc.) and add one
`docs/<category>/README.md` per row.

| Category | Purpose | README |
| -------- | ------- | ------ |
| [example/](example/) | Replace with a real category | [README](example/README.md) |
