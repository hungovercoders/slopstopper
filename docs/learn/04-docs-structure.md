# Lesson 4: Docs structure: every doc has a route

**Goal.** Add a doc nobody routes to, watch it fail, route it, and
understand the hop and line limits.

## Why this check

`hygiene:docs-structure` stops the most common documentation slop: a
page written once and never found again. An agent reads what it is
routed to. A doc with no explicit route is invisible, however good it
is, and a doc that is only "see also"-linked is skipped, because a link
without a trigger does not tell the agent when to spend a tool turn on
it. The model the check enforces is `AGENTS.md` → the map
(`docs/README.md`) → a directory README → the doc, with a route at every
step of the form "when you are X, read Y for Z".

The check also caps depth and length. A route more than three hops deep
costs a tool turn per hop, and a topic doc past 300 lines is one nobody
reads to the end; the fix for both is to split by concern and route each
part. It is stdlib Python, reads every `.md` under `docs/`, and writes a
report listing every reachable doc with its hop count.

The course you are reading lives under `docs/` but is listed in
`hygiene.docs.exclude`, so this check leaves it alone. Lessons are read
in order by people, not routed to by agents.

## You will need

The checkout from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See it green

<!-- learn -->
```sh
task ss:hygiene:docs-structure
```

```
🔍 Validating documentation structure…
✅ Documentation structure is valid: all 33 docs are routed (6 excluded by hygiene.docs.exclude)
```

### 2. Break it

Write a doc and route it from nowhere.

<!-- learn -->
```sh
printf '# Hygiene notes\n\nScratch notes about the hygiene checks.\n' > docs/hygiene/NOTES.md
```

### 3. See it red

<!-- learn: fails -->
```sh
task ss:hygiene:docs-structure
```

```
🔍 Validating documentation structure…
❌ Found 1 structure violation(s)
  - Unrouted doc: docs/hygiene/NOTES.md is not linked from AGENTS.md, the map, or a README above it. Add a route to docs/hygiene/README.md: 'Before you <do X>, read <doc> for <what it holds>'
task: Failed to run task "ss:hygiene:docs-structure": exit status 1
```

The red line names the file, says which README should route it, and
gives the route form. That is most of the fix.

### 4. Try a soft link, and see why it does not count

Add a "see also" to the hygiene README. This is what most people do
first.

<!-- learn: fails -->
```sh
printf '\nSee also [NOTES.md](NOTES.md).\n' >> docs/hygiene/README.md
task ss:hygiene:docs-structure
```

```
❌ Found 1 structure violation(s)
  - Unrouted doc: docs/hygiene/NOTES.md is linked from docs/hygiene/README.md without a trigger or 'read'. Add a route to docs/hygiene/README.md: 'Before you <do X>, read <doc> for <what it holds>'
```

Still unrouted, and the message changed: the check found the link and
is telling you it is soft. A link says a doc exists; a route says when
to read it.

### 5. Route it

Replace the soft link with a route: a trigger, the word "read", the
file, and what it holds.

<!-- learn -->
```sh
git checkout docs/hygiene/README.md
printf '\nBefore you tune a hygiene threshold, read [NOTES.md](NOTES.md) for the reasoning behind each default.\n' >> docs/hygiene/README.md
task ss:hygiene:docs-structure
```

```
✅ Documentation structure is valid: all 34 docs are routed (6 excluded by hygiene.docs.exclude)
```

### 6. Read the report, then put the checkout back

The report lists every doc and how many hops it costs. Your new doc is
two hops from `AGENTS.md`: the hygiene README is routed directly from
there, so anything it routes is one hop further.

<!-- learn -->
```sh
grep NOTES .ss/reports/docs/docs-structure-report.md
git checkout docs/hygiene/README.md
rm docs/hygiene/NOTES.md
```

```
| `docs/hygiene/NOTES.md` | 2 | `docs/hygiene/README.md` |
```

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:docs-structure | grep 'docs are routed'
```

```
✅ Documentation structure is valid: all 33 docs are routed (6 excluded by hygiene.docs.exclude)
```

## Exercise

Make the check fail with `doc_over_lines` instead of `unrouted_doc`,
without adding a file.

<details>
<summary>Solution</summary>

Pad an existing routed doc past 300 lines, run, and revert:

```sh
yes '' | head -300 >> docs/hygiene/DOC_UPDATER.md
task ss:hygiene:docs-structure
git checkout docs/hygiene/DOC_UPDATER.md
```

The violation names the doc and its line count. The real fix is a split
by concern, with a route to each part, never a bigger
`max_doc_lines`.

</details>

## Going further

- [Documentation structure validation](../hygiene/README.md#documentation-structure-validation)
  in the hygiene README: every violation kind
- [Excluding docs from the docs checks](../hygiene/README.md#excluding-docs-from-the-docs-checks):
  `hygiene.docs.exclude`, which is how this course sits under `docs/`
- Lesson 5 for the two checks that keep routed docs accurate and sized

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `ls docs/` showing thirty files. "Which of these
would an agent ever open?"

**Talking points.**

1. Why routes: an agent reads what it is routed to; a soft link is
   skipped; three hops; 300 lines.
2. Green run. Write `NOTES.md`; red; the message says which README and
   gives the form.
3. The soft link: still red, different message. A link says a doc
   exists; a route says when to read it.
4. The route; green; the report's hop count.
5. Clean up. Exercise: `doc_over_lines`.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/04.tape`. Zoom on the two different violation
messages.

**Chapters.** `0:00 Why` · `1:30 Green` · `2:30 Unrouted` ·
`4:00 The soft link` · `5:30 The route` · `7:00 Exercise` ·
`8:30 Next lesson`.

</details>
