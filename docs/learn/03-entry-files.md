# Lesson 3: Entry files: the AGENTS.md-first model

<!-- learn-sandbox: demo -->

**Goal.** Say why `README.md` and `AGENTS.md` have token budgets, find
the demo's README over its budget, and see that the fix is to move
content deeper and route it, never to raise the budget.

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

The demo repo from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See it red, and read the table

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:entry-files
```

```
📏 Entry-file budget + AGENTS.md-first check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌ README.md          800 tokens  (budget 600, headroom -200)  ✅ rules
  ✅ AGENTS.md          709 tokens  (budget 2000, headroom +1291)  ✅ rules
  ✅ CLAUDE.md            2 tokens  (budget 2000, headroom +1998)  ✅ rules
  ✅ docs/README.md     301 tokens  (budget 1000, headroom +699)  ✅ rules

  cold start: 709 always loaded (AGENTS.md) + 301 fallback hop (docs/README.md) = 1010

❌ An entry file is over its token budget, or breaks an AGENTS.md-first rule (see below).
```

Four files, four budgets, and two columns of verdict: the size and the
rules. `CLAUDE.md` is two tokens because it is the one line
`@AGENTS.md`. The README is over by two hundred tokens, and its rules
column is still green: nothing about the file's form is wrong, there is
just too much of it. The cold-start line is what an agent pays before
doing anything: the always-loaded file, plus the map if the task is not
covered.

### 2. Read the report, then the file

The report carries a paste-ready fix for each violation.

<!-- learn -->
```sh
sed -n '/How to fix/,$p' .ss/reports/entry-files/entry-file-size-report.md | head -6
grep -n '^## ' README.md
```

```
## How to fix violations

### `README.md` is over its token budget (800 > 600)

Keep it to orientation and a quick start; everything else lives under `docs/` and is reachable from [`docs/README.md`](./docs/README.md).

9:## Quick start
20:## Docs
27:## Everything you need to know
```

The headings tell the story. Orientation, a quick start, a pointer to
the docs, and then the whole manual pasted in because "people read the
README". This is the commonest shape of entry-file slop: content that
belongs one hop deeper, inlined so it will be seen, which is exactly
what makes the file too long to be read.

### 3. Fix it: move the content deeper and route it

The fix is always the same direction: move the content that serves the
fewest tasks into a `docs/` topic doc and add a route to it from the
map. This cuts the manual out of the README into `docs/manual.md` and
adds one route line.

<!-- learn -->
```sh
python3 - <<'PY'
import pathlib
readme = pathlib.Path('README.md'); text = readme.read_text()
head, manual = text.split('## Everything you need to know\n', 1)
readme.write_text(head.rstrip() + '\n')
pathlib.Path('docs/manual.md').write_text('# The manual\n\n' + manual.lstrip())
PY
printf '\nBefore you look anything up beyond the quick start, read [manual.md](manual.md) for the whole manual.\n' >> docs/README.md
slopstopper run hygiene:entry-files
```

```
📏 Entry-file budget + AGENTS.md-first check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ README.md          225 tokens  (budget 600, headroom +375)  ✅ rules
  ✅ AGENTS.md          709 tokens  (budget 2000, headroom +1291)  ✅ rules
  ✅ CLAUDE.md            2 tokens  (budget 2000, headroom +1998)  ✅ rules
  ✅ docs/README.md     327 tokens  (budget 1000, headroom +673)  ✅ rules

  cold start: 709 always loaded (AGENTS.md) + 327 fallback hop (docs/README.md) = 1036

✅ Every entry file is within budget, CLAUDE.md is a pure include, and every route is explicit.
```

The README dropped to a third of its budget, the map grew by one line,
and the cold start barely moved: the manual now costs a tool turn only
for the task that needs it. The route line's form, a trigger, the word
"read", the file and what it holds, is the subject of lesson 4.

What you never do is raise `readme_max_tokens`. The budgets are the
feature: they are the point at which an agent stays reliable, and they
do not move with the repo.

### 4. Put the demo back

<!-- learn -->
```sh
git checkout README.md docs/README.md
rm docs/manual.md
```

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:entry-files | grep 'README.md'
```

```
  ❌ README.md          800 tokens  (budget 600, headroom -200)  ✅ rules
```

Red again, with the demo as it shipped, and you know the fix is a move
and a route, never a number.

## Exercise

Make the rules column go red instead of the size column, then put it
back.

<details>
<summary>Solution</summary>

Add a line to `CLAUDE.md` so it is no longer a pure include:

```sh
echo "Also read the wiki." >> CLAUDE.md
slopstopper run hygiene:entry-files
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
2. Red run on the demo; the four files; headroom negative, rules
   green; the cold-start line.
3. The report's paste-ready fix; the README's headings tell the story.
4. The move and the route; green; the cold start barely moves.
5. The direction of every fix is deeper and routed, never a bigger
   budget. Put the demo back.
6. Exercise: break the rules column instead.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/03.tape`. Zoom on the headroom number.

**Chapters.** `0:00 Why` · `1:30 Red` · `3:00 The report` ·
`4:00 Move and route` · `6:00 Put it back` · `7:00 Exercise` ·
`8:30 Next lesson`.

</details>
