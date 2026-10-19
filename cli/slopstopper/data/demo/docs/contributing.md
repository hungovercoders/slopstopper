# Contributing

## Review rules

- One service per pull request, so a rollback is one revert.
- The owner named on the page is a team, never a person.
- A removed service moves to the "unowned" section; it is never deleted.

## The checks that run

Every pull request runs the slopstopper suite: smoke and accessibility
against the served page, SEO on its meta tags, and the two docs checks,
`hygiene:entry-files` and `hygiene:docs-structure`, on this repository's
entry files and `docs/`. A red check blocks the merge; its report under
`.ss/reports/<check>/` names the finding and the fix.
