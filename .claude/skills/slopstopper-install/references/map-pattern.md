# Step 5 — Set up the Map Pattern

> Part of the `slopstopper-install` skill. `SKILL.md` says when to read this; it is not loaded until then.

## Step 5 — Set up the Map Pattern (if keeping the docs-* checks)

**Why the Map Pattern is worth it beyond passing the check:** the map is a token-efficiency play, not just a docs-structure rule. When `README.md`, `AGENTS.md` and `CLAUDE.md` are thin pointers into a `docs/index.md` index — rather than three fat files each restating the project — an agent (or a human) reads the index and opens only the category files relevant to the task. That cuts the tokens pulled into context on every agent invocation, which is real money at scale. Frame it to the user as a cost/latency win for AI-assisted work, not paperwork the check demands.

The three docs-* workflows (`docs-accuracy`, `docs-structure`, `docs-size`) validate a `docs/` directory laid out per slopstopper's governance pattern. If you're keeping them, the target needs a `docs/` directory shaped like this:

```
docs/
  index.md                    The map — table of categories, each linked
  <category-a>/README.md      One README per category named in the index
  <category-b>/README.md
  …
```

The structure check parses the table in `docs/index.md` (pattern: `| [category/](category/) | … |`) and fails the build if any listed category lacks a directory or `README.md`, or if there's an undocumented directory inside `docs/`. The directory tree must conform to the index — not the reverse. The entry-files check enforces the reverse half: README.md and AGENTS.md must link to `docs/index.md`, and CLAUDE.md must be a thin pointer to AGENTS.md (`@AGENTS.md` directive or a link). A budget without the pointer is pointless; the map only works if the entry files defer to it.

**Auto-seeded scaffolds.** On a fresh install, `install.sh` writes minimal pointer-shaped versions of all four files (`README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/index.md`) from `cli/slopstopper/data/templates/entry-files/` when they don't already exist — so a greenfield clone is green on Step 7's local loop without manual work. If a file already exists, the installer leaves it alone; remediation runs through the check's report-driven path (next paragraph).

**Remediating existing files.** When the target already has entry files but they don't link the map, `task ss:hygiene:entry-files` fails and writes `.ss/reports/entry-files/entry-file-size-report.md` with a paste-ready snippet for each violation:

- For a missing map pointer on `README.md` / `AGENTS.md` — a `> 🗺️ **Documentation map.** ...` callout to paste near the top of the file.
- For a CLAUDE.md that isn't a thin pointer — the full canonical CLAUDE.md body to replace the file contents with.
- For a missing `docs/index.md` — a minimal map template with an empty categories table.

Read the report, confirm the placement with the user if the file is non-trivial, then paste the snippet at the top of the offending file. Re-run `task ss:hygiene:entry-files` to confirm green.

**Minimum `docs/index.md`:**

```markdown
# Documentation Index

This file is **the map** — every other entry point in the repo defers to it.

| Category | Purpose | README |
| -------- | ------- | ------ |
| [architecture/](architecture/) | System structure and boundaries | [README](architecture/README.md) |
| [content/](content/) | What this repo produces, and how | [README](content/README.md) |
| [deployment/](deployment/) | How it ships | [README](deployment/README.md) |
| [operations/](operations/) | Runbooks and on-call notes | [README](operations/README.md) |
```

Pick categories that fit the target. Four is usually enough; slopstopper itself uses ten because it ships a tool with many surfaces. A blog/site does fine with three or four.

**Each category README** needs at minimum a heading and a sentence describing the category's scope. Better: short, practical, actually-useful content. The `docs-size` check caps total docs/ size and per-file size — keep each README concise.

**Wire the three entry files to defer to the map.** The Map Pattern is only useful if the entry files actually point at it. Once `docs/index.md` exists, restructure `README.md`, `AGENTS.md` and `CLAUDE.md` as a chain — each thin, each deferring upstream — so a human, an automation tool, or Claude Code all converge on the same canonical map:

- **`README.md`** (humans) — short project intro, install/run commands, pipeline-status badges, then a pointer like `See [docs/index.md](./docs/index.md) for the full documentation map.`
- **`AGENTS.md`** (any automation, [agents.md](https://agents.md) standard) — opens with a Map Pattern callout linking `docs/index.md`. Keeps only what an agent needs up-front: coding conventions (indentation, language, naming patterns), a "where to look for what" table mapping change types to category READMEs, and any non-obvious project-wide rules. Everything else lives in `docs/<category>/README.md`.
- **`CLAUDE.md`** (Claude Code) — a 3-5 line file that names the canonical chain (CLAUDE.md → AGENTS.md → docs/index.md) and uses the `@AGENTS.md` directive to import the agent conventions. Don't duplicate content here; Claude Code resolves the directive automatically.

Example minimal `CLAUDE.md`:

```markdown
# Claude Code — project instructions

The canonical agent conventions for this repo live in [`AGENTS.md`](./AGENTS.md), which in turn defers to the documentation map at [`docs/index.md`](./docs/index.md). Claude Code imports `AGENTS.md` via the directive below — keep this file thin.

@AGENTS.md
```

The `ss:hygiene:entry-files` check enforces both the 1500-word budget on each of the three entry files AND the pointer rule above. Aim well under the budget — it's the ceiling, not the target. Knobs in `.slopstopper.yml` if you need to override:

```yaml
hygiene:
  entry_files:
    max_words: 1500
    require_map_pointer: true        # set to false to disable the pointer rule only
    map_path: docs/index.md          # override if your map lives elsewhere
```

**Cross-references in docs:** the `docs-accuracy` check scans for `` `backtick-quoted` `` filenames and broken markdown links. Use full repo-relative paths (`scripts/foo.sh`, not bare `foo.sh`) so the checker can resolve them.

If none of this fits the target — short-lived prototype, single-file tool, generated docs only — delete the three workflows instead. `.ss/.workflows-installed` will remember the deletion so re-installs don't bring them back.
