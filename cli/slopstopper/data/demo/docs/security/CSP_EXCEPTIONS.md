# CSP exceptions

The site-wide Content-Security-Policy in `app/_headers` allows nothing
from any other origin. A page that needs more gets its own block in that
file, scoped to its path, and an entry here saying what was allowed and
why. The `hygiene:csp-exceptions` check fails when the two disagree in
either direction.

## Schema

Each exception is a `### /path` heading under `## Exceptions`, followed
by these fields with the labels spelled exactly like this:

| Field | Purpose |
| --- | --- |
| `**Origin allowed:**` | The origins added to the policy for this path |
| `**Directives added:**` | Which directives changed (`img-src`, `script-src`, …) |
| `**Loader SRI:**` | The `sha384-…` hash of an external script, or `n/a` |
| `**Why:**` | One sentence on what the relaxation enables |
| `**Approved by:**` | The pull request where it was reviewed |
| `**Data leaving site:**` | What the third party receives (IP, User-Agent, page URL, …) |
| `**Refresh policy:**` | When and how the SRI hash is refreshed, or `n/a` |

## Exceptions

None yet: every path serves the baseline policy.
