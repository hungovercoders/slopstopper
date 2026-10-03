# PR feedback: one summary, compact detail

Every check writes a standalone report — an H1, an overall verdict,
per-item sections, folded evidence, a "How to Fix" section. That is the
right shape for a file you open deliberately. It is the wrong shape for
nineteen of them stacked on a pull request, which is what posting each
report verbatim produced: on an all-passing run the suite emitted ~390
lines of markdown across 19 comment cards, so the one thing a reviewer
wants — *did anything fail* — was the hardest thing to find.

Feedback now arrives in two layers.

**One summary comment.** [`ss-pr-summary.yml`](../../.github/workflows/ss-pr-summary.yml)
renders a single rolling comment covering every check:

```
## ❌ SlopStopper — 2 of 24 checks failed

| | Check | |
|---|---|---|
| ❌ | **Complexity** | logs → |
| ❌ | **SEO**        | logs → |

<details><summary>The other 22 checks</summary>…</details>
```

A green PR gets three lines and a group listing; a red one leads with
the failures and folds the rest away.

**Compact per-check comments.** `slopstopper emit <check> --target
pr-comment` no longer posts the report. It posts a verdict line, the
failing items, and the report folded into a `<details>`:

```
### ❌ SEO — 2 issues

- og:image is missing
- canonical points at another domain

<details><summary>Full report and evidence</summary>…</details>
<sub>slopstopper · `reliability:seo` · head `abc1234` · run →</sub>
```

With `--on-pass=delete` a passing check *removes* its comment, so on a
green PR the summary is the only thing there.

## Design decisions

**The summary reads GitHub, not the checks.** It is built from the
workflow runs already recorded against the head commit
(`GET /repos/{repo}/actions/runs?head_sha=…`), so it needs no
coordination with the 24 check workflows and cannot race them into a
half-written comment. The alternative — each check editing its own
section of one shared comment — is a read-modify-write on a single
resource from 24 concurrent jobs, where a lost update silently drops a
check's status. Reading the runs makes the comment a pure function of
state GitHub already holds, so every re-render converges on the truth
regardless of what order the checks finish in.

It fires on `workflow_run: completed` with `cancel-in-progress: false`,
so the last render — the one that sees every conclusion — is the one
that sticks. `workflow_run` only triggers for workflows on the default
branch and cannot glob, so the triggering workflow list is explicit and
has to grow when a check workflow is added.

**The verdict comes from the workflow, not from parsing the report.**
`--status pass|fail` is passed in, because where "did it pass" lives
is the workflow's knowledge, not the report's: every check's own step
carries the verdict as its exit code (0 / 1 / 2 — see
[contributing](../contributing/README.md#exit-codes)), except
`hygiene:docs-size`, which is advisory — it always exits 0 while its
report says `❌ Status: THRESHOLDS EXCEEDED`. Inferring a verdict from
report text would get that one wrong, in the direction that hides
failures. The
default is `fail`, so a miswired workflow over-reports rather than
silently greenwashing.

There is a third value, `warn`, for exactly the advisory case: it renders
`### ⚠️ Docs Size — has alerts` and keeps the comment, so the per-check
comment doesn't contradict the ✅ that check's green job gets in the
summary table. `--on-pass=delete` only fires on `pass`.

**Naming isn't re-declared.** A check's label in a comment comes from
`profiles.CHECK_WORKFLOWS` (check → workflow file) chained through
`badges.WORKFLOW_DISPLAY` (workflow file → human label), so the string
on a PR comment, a README badge and the summary table is the same string
from the same place.

**Comments are found by a hidden marker.** Bodies carry
`<!-- slopstopper:check=<name> -->`, so the upsert is exact rather than
"does the body still contain the report's H1". The old discriminator
substring is still tried as a fallback, so comments posted by an earlier
CLI are updated in place instead of duplicated.
