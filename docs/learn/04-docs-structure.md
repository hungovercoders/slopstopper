# Lesson 4: Docs structure: every doc has a route

<!-- learn-sandbox: demo -->

**Goal.** Find the doc in the demo that nothing routes to, see why a
"see also" link does not count, route it, and understand the hop and
line limits.

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

## You will need

The demo repo from the [syllabus](README.md), with the CLI on PATH.

## Steps

### 1. See it red

<!-- learn: fails 1 -->
```sh
slopstopper run hygiene:docs-structure
```

```
🔍 Validating documentation structure…
❌ Found 1 structure violation(s)
  - Unrouted doc: docs/runbooks/RELEASE.md is not linked from AGENTS.md, the map, or a README above it. Add a route to docs/README.md: 'Before you <do X>, read <doc> for <what it holds>'

📁 Reports saved to: .ss/reports/docs/
   • docs-structure-report.md
```

The red line names the file, says which file should route it, and
gives the route form. That is most of the fix. The runbook is a good
doc: it says how to cut a release, in two commands. Nobody will ever
read it, because nothing says when to.

### 2. Try a soft link, and see why it does not count

Add a "see also" to the map. This is what most people do first.

<!-- learn: fails 1 -->
```sh
printf '\nSee also [runbooks/RELEASE.md](runbooks/RELEASE.md).\n' >> docs/README.md
slopstopper run hygiene:docs-structure
```

```
🔍 Validating documentation structure…
❌ Found 2 structure violation(s)
  - Unrouted doc: docs/runbooks/RELEASE.md is linked from docs/README.md without a trigger or 'read'. Add a route to docs/README.md: 'Before you <do X>, read <doc> for <what it holds>'
  - docs/README.md line 21 → docs/runbooks/RELEASE.md: "See also [runbooks/RELEASE.md](runbooks/RELEASE.md)." is a soft route. A route agents follow names its trigger and says read: 'Before you <do X>, read <doc> for <what it holds>'.
```

Still unrouted, and now two findings instead of one: the check found
the link, is telling you it is soft, and quotes the line. A link says a
doc exists; a route says when to read it.

### 3. Route it

Replace the soft link with a route: a trigger, the word "read", the
file, and what it holds.

<!-- learn -->
```sh
git checkout docs/README.md
printf '\nBefore you cut a release, read [runbooks/RELEASE.md](runbooks/RELEASE.md) for the tag, the push and what the tag message is for.\n' >> docs/README.md
slopstopper run hygiene:docs-structure
```

```
🔍 Validating documentation structure…
✅ Documentation structure is valid: all 4 docs are routed
```

### 4. Read the report, then put the demo back

The report lists every doc and how many hops it costs. The runbook is
two hops from `AGENTS.md`: the map is routed directly from there, so
anything the map routes is one hop further.

<!-- learn -->
```sh
grep RELEASE .ss/reports/docs/docs-structure-report.md
git checkout docs/README.md
```

```
| `docs/runbooks/RELEASE.md` | 2 | `docs/README.md` |
```

## Checkpoint

<!-- learn -->
```sh
slopstopper run hygiene:docs-structure | grep 'Unrouted doc'
```

```
  - Unrouted doc: docs/runbooks/RELEASE.md is not linked from AGENTS.md, the map, or a README above it. Add a route to docs/README.md: 'Before you <do X>, read <doc> for <what it holds>'
```

Red again, with the demo as it shipped, and you can write the one line
that fixes it from memory.

## Exercise

Make the check fail with `doc_over_lines` instead of `unrouted_doc`,
without adding a file.

<details>
<summary>Solution</summary>

Pad a routed doc past 300 lines, run, and revert:

```sh
yes '' | head -300 >> docs/architecture.md
slopstopper run hygiene:docs-structure
git checkout docs/architecture.md
```

The violation names the doc and its line count, beside the unrouted
runbook. The real fix is a split by concern, with a route to each part,
never a bigger `max_doc_lines`.

</details>

## Going further

- [Documentation structure validation](../hygiene/README.md#documentation-structure-validation)
  in the hygiene README: every violation kind
- [Excluding docs from the docs checks](../hygiene/README.md#excluding-docs-from-the-docs-checks):
  `hygiene.docs.exclude`, which is how this course sits under
  slopstopper's own `docs/`
- Lesson 5 for the two checks that keep routed docs accurate and sized

<details>
<summary>Episode script</summary>

**Length.** 8 to 10 minutes.

**Cold open (0:00).** `ls docs/` on a repo with thirty files. "Which of
these would an agent ever open?"

**Talking points.**

1. Why routes: an agent reads what it is routed to; a soft link is
   skipped; three hops; 300 lines.
2. Red on the demo: the message says which file and gives the form.
3. The soft link: two findings now, and the line quoted. A link says a
   doc exists; a route says when to read it.
4. The route; green; the report's hop count. Put the demo back.
5. Exercise: `doc_over_lines`.

**Shot list.** One terminal, 100x30, font size 16, the site's theme.
`docs/learn/tapes/04.tape`. Zoom on the two different violation
messages.

**Chapters.** `0:00 Why` · `1:30 Unrouted` · `3:00 The soft link` ·
`4:30 The route` · `6:00 Put it back` · `7:00 Exercise` ·
`8:30 Next lesson`.

</details>
