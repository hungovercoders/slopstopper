---
title: Agent Instructions Pointer
description: Pointer to canonical agent instructions at the repo root for AI assistants and automation tools.
status: maintained
date: 2026-03-02
---

# Agent instructions — pointer

The canonical agent instructions for this repo now live at the repo root:

→ [`../AGENTS.md`](../AGENTS.md)

This file is kept as a thin pointer so that existing references (in
workflows, README files, and external documentation) continue to resolve.
Do not duplicate content here — update [`../AGENTS.md`](../AGENTS.md)
instead.

## Why

The [agents.md](https://agents.md) open standard expects `AGENTS.md` at the
repo root, alongside `README.md` and `CONTRIBUTING.md`. Agents (Claude
Code, GitHub Copilot, Cursor, etc.) look for it there first. The root
[`CLAUDE.md`](../CLAUDE.md) imports it via Claude Code's `@AGENTS.md`
directive so all agents converge on the same source of truth.

## Quick map of related files

- [`../README.md`](../README.md) — consumer-facing project overview and install
- [`../AGENTS.md`](../AGENTS.md) — canonical agent conventions
- [`../CLAUDE.md`](../CLAUDE.md) — Claude Code entry point (imports `AGENTS.md`)
- [`../docs/contributing/README.md`](contributing/README.md) — contributor workflow
- [`index.md`](index.md) — documentation hub and naming governance
