# Lesson 3: Entry files: the AGENTS.md-first model

**Goal.** Say why `AGENTS.md` has a token budget, blow it, and see that
the fix is to move content deeper and route it, never to raise the
budget.

## Why this check

`hygiene:entry-files` is the check that keeps a repo legible to an
agent. `AGENTS.md` (which `CLAUDE.md` includes) is loaded into every
agent conversation, so inlining what most tasks need is cheap: it is
prompt-cached, while every file an agent has to go and read costs a tool
turn. But instruction-following degrades as rules pile up. Past roughly
2,000 tokens, forty to sixty rules, an agent starts skipping some. So
the entry file carries what most tasks need and routes the rest with
explicit lines of the form "when you are X, read Y".

The slop this stops is the entry file that grows by accretion: every
incident adds a rule, every feature adds a paragraph, and six months on
the file that was meant to make the repo easy to work in is the reason
the agent ignores half of it. The same goes for `README.md`, which is
human orientation under a smaller budget, and for the docs map at
`docs/README.md`, the fallback routing table.

The check is stdlib Python. It estimates tokens as characters divided by
four, enforces the four budgets, insists `CLAUDE.md` is a pure
`@AGENTS.md` include so there is one entry point and nothing to drift,
and insists every `.md` link in `AGENTS.md` is an explicit route. It
prints the cold-start cost on every run so a creeping number is visible
before a budget trips.

## You will need

The checkout from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See it green, and read the table

<!-- learn -->
```sh
task ss:hygiene:entry-files
```

```
📏 Entry-file budget + AGENTS.md-first check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ README.md          529 tokens  (budget 600, headroom +71)  ✅ rules
  ✅ AGENTS.md         1626 tokens  (budget 2000, headroom +374)  ✅ rules
  ✅ CLAUDE.md            2 tokens  (budget 2000, headroom +1998)  ✅ rules
  ✅ docs/README.md     948 tokens  (budget 1000, headroom +52)  ✅ rules

  cold start: 1626 always loaded (AGENTS.md) + 948 fallback hop (docs/README.md) = 2574

✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
```

Four files, four budgets, and two columns of verdict: the size and the
rules. `CLAUDE.md` is two tokens because it is the one line
`@AGENTS.md`. The cold-start line is what an agent pays before doing
anything: the always-loaded file, plus the map if the task is not
covered.

### 2. Break it

Paste the docs map into the README. This is the commonest shape of entry
file slop: content that belongs one hop deeper, inlined "so people see
it".

<!-- learn -->
```sh
cat docs/README.md >> README.md
```

### 3. See it red

<!-- learn: fails -->
```sh
task ss:hygiene:entry-files
```

```
  ❌ README.md         1477 tokens  (budget 600, headroom -877)  ✅ rules
  ✅ AGENTS.md         1626 tokens  (budget 2000, headroom +374)  ✅ rules
  ✅ CLAUDE.md            2 tokens  (budget 2000, headroom +1998)  ✅ rules
  ✅ docs/README.md     948 tokens  (budget 1000, headroom +52)  ✅ rules

  cold start: 1626 always loaded (AGENTS.md) + 948 fallback hop (docs/README.md) = 2574

❌ An entry file is over its token budget, or breaks an AGENTS.md-first rule (see below).
task: Failed to run task "ss:hygiene:entry-files": exit status 1
```

The headroom went negative. The rules column is still green: nothing
about the file's form is wrong, there is just too much of it.

### 4. Read the report

The report carries a paste-ready fix for each violation.

<!-- learn -->
```sh
sed -n '/How to fix/,$p' .ss/reports/entry-files/entry-file-size-report.md
```

```
## How to fix violations

### `README.md` is over its token budget (1477 > 600)

Keep it to orientation and a quick start; everything else lives under `docs/` and is reachable from [`docs/README.md`](./docs/README.md).
```

### 5. Fix it

The fix is always the same direction: move the content that serves the
fewest tasks into a `docs/` topic doc and add a route to it. Here the
content already lives in `docs/README.md`, so the move is a revert.

<!-- learn -->
```sh
git checkout README.md
task ss:hygiene:entry-files
```

```
✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
```

What you never do is raise `readme_max_tokens`. The budgets are the
feature: they are the point at which an agent stays reliable, and they
do not move with the repo.

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:entry-files | grep 'Every entry file'
```

```
✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
```

## Exercise

Make the rules column go red instead of the size column, then put it
back.

<details>
<summary>Solution</summary>

Add a line to `CLAUDE.md` so it is no longer a pure include:

```sh
echo "Also read the wiki." >> CLAUDE.md
task ss:hygiene:entry-files
git checkout CLAUDE.md
```

The size is still tiny, but the `rules` column for `CLAUDE.md` fails,
because with two entry points there are two places for instructions to
drift apart. The report's fix is the one-line `@AGENTS.md` body.

</details>

## Going further

- [The entry-file budget](../hygiene/README.md#entry-file-budget) in the
  hygiene README: every rule and knob
- [The model](../README.md#the-model) at the bottom of the docs map:
  why AGENTS.md-first, in the repo's own words
- The four scaffolds `install.sh` seeds, under
  `cli/slopstopper/data/templates/entry-files/`

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** An `AGENTS.md` scrolling for ten seconds. "Which
of these rules does the agent actually follow?"

**Talking points.**

1. Why a budget: always loaded, prompt-cached, cheap to inline, but
   instruction-following degrades past about 2,000 tokens.
2. Green run; the four files; the cold-start line.
3. Paste the map in; red; the headroom goes negative, the rules stay
   green.
4. The report's paste-ready fix.
5. Revert; the direction of every fix is deeper and routed, never a
   bigger budget.
6. Exercise: break the rules column instead.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/03.tape`. Zoom on the headroom number.

**Chapters.** `0:00 Why` · `1:30 Green` · `3:00 Break it` ·
`4:00 The report` · `5:30 Fix` · `7:00 Exercise` · `8:30 Next lesson`.

</details>
