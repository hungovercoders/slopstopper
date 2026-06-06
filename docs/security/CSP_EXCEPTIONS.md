# CSP exceptions

This file is the **single source of truth** for every per-path
Content-Security-Policy relaxation on the SlopStopper site. The
`ss:hygiene:csp-exceptions` check fails the build if `netlify.toml` and
this file disagree.

## Why this exists

The SlopStopper site ships a strict `default-src 'self'; script-src
'self'; style-src 'self'` CSP on every path. This is one of the security
properties the suite advertises, and the DAST workflow exercises it.

But almost every real-world adopter eventually needs to admit *something*
third-party: Google Tag Manager, Sentry, Intercom, an analytics tag, an
embedded video, a comments widget. Telling adopters "just don't" is
unhelpful. The honest answer is a pattern:

1. **Default to the strictest CSP you can.** Set it once for the whole
   site (`for = "/*"`).
2. **Relax per page, not site-wide.** When you need a third-party on one
   page, add a new `[[headers]]` block in `netlify.toml` scoped to that
   exact path. The rest of the site stays strict, so XSS or supply-chain
   issues stay contained.
3. **Pin external scripts with SRI** wherever the host supports it. SRI
   locks the relaxation to one exact bundle hash — a compromise of the
   third-party CDN can't ship new JavaScript to your visitors. The
   tradeoff: when the third-party releases a new version, your SRI hash
   stops matching and the widget silently breaks until you refresh it.
   Make sure there's a fallback link on the page so the page stays
   useful in that window.
4. **Document every exception here.** What origin you let in, on which
   page, what data leaves, who approved it, and how to refresh the SRI
   hash. The hygiene check verifies that what's in `netlify.toml`
   matches what's documented here.
5. **Let DAST keep flagging the relaxed pages.** A scanner flagging a
   documented exception is correct behaviour — that's how you find
   *un*documented relaxations later. The DAST workflow on this repo
   consults this file via [the DAST gate script](../../.ss/scripts/check-dast-alerts.py):
   ZAP CSP findings whose URL path is listed under `## Exceptions`
   below are reported separately and do **not** fail the build, while
   any non-CSP finding or any High-severity (riskcode 3) CSP finding
   still blocks. PR comments call out the swallowed findings so they
   stay visible in review.

This pattern is what this site does for Giscus. If you're adopting
SlopStopper and need to admit GTM or any other third-party, copy the
shape below.

## Schema

Each exception is a `## /path` heading followed by these fields:

| Field | Purpose |
| --- | --- |
| `**Origin allowed:**` | One or more origins added to the CSP for this path |
| `**Directives added:**` | Which CSP directives changed (script-src, frame-src, style-src, …) |
| `**Loader SRI:**` | `sha384-…` hash of the external script, or `n/a` if SRI is not applicable / unsupported |
| `**Why:**` | One sentence on what feature this enables and why a third-party is required |
| `**Approved by:**` | PR number where this was reviewed |
| `**Data leaving site:**` | What visitor data the third-party will receive (IP, UA, GitHub identity, page URL, etc.) |
| `**Refresh policy:**` | When and how to update the SRI hash |

The check parser is literal — keep the field labels exactly as above.

## Computing an SRI hash

```bash
curl -sSL https://giscus.app/client.js | openssl dgst -sha384 -binary | openssl base64 -A
# prepend "sha384-" to the output
```

Re-run when the widget breaks after a third-party release.

---

## Exceptions

### `/feedback.html`

- **Origin allowed:** `https://giscus.app`
- **Directives added:** `script-src https://giscus.app`, `frame-src https://giscus.app`, `style-src 'unsafe-inline'`
- **Loader SRI:** `sha384-UwLZGbJGvkTzz0719+xEzUm/idqwzs0yZN8aB9Se5vUXHbyRyDWw9yqZTIsOsJ7x` (last refreshed when this exception was added; see refresh policy below)
- **Why:** Embedded GitHub Discussions comments via [Giscus](https://giscus.app) so visitors can leave feedback directly on the page without leaving the site
- **Approved by:** PR introducing the feedback page (see `git log app/feedback.html`)
- **Data leaving site:**
  - For passive viewers: visitor IP, User-Agent and referrer go to `giscus.app` when the iframe is fetched
  - For commenters: GitHub identity (login, avatar URL) goes to `giscus.app` and back to `github.com` when posting
  - No analytics or telemetry from us — Giscus is the only third-party
- **Refresh policy:**
  - The SRI hash above must be refreshed when Giscus publishes a new release of their loader script. Refresh procedure:
    1. Recompute the hash with the `curl … openssl` command above
    2. Update the `integrity=` attribute in `app/feedback.html`
    3. Update the `**Loader SRI:**` line above to match
    4. Open a PR — the `ss:hygiene:csp-exceptions` check will green-light when both sides match
  - The COOP/COEP overrides on this path (`same-origin-allow-popups` / `unsafe-none`) are also part of this exception, so the GitHub OAuth popup can communicate back during sign-in
- **Fallback if Giscus is unavailable or SRI mismatch:** The page renders a static link to the Feedback discussion category (`https://github.com/hungovercoders/slopstopper/discussions/categories/feedback`) so visitors can still reach the same destination

---

## Adopters: how to use this in your own repo

1. Keep your own `[[headers]] for = "/*"` strict by default
2. Drop a new `[[headers]]` block per page that needs a relaxation; **list
   the full replacement directives**, not just additions
3. Add an entry to this file mirroring the schema above
4. Install `ss-hygiene-csp-exceptions-check.yml` via the SlopStopper
   installer — the check enforces drift between `netlify.toml` and this
   file
5. Keep DAST in your pipeline. The SlopStopper DAST gate
   (`.ss/scripts/check-dast-alerts.py`) already consults this file:
   Medium-severity CSP findings on documented paths are surfaced in the
   PR comment but do **not** block the build. Undocumented relaxations
   still fail DAST, as does any non-CSP finding or any High-severity
   finding (even CSP, even on a documented path)
6. If your repo has no third-party widgets, you can ignore this file
   entirely — the DAST gate handles its absence as "no exceptions" and
   blocks all riskcode ≥ 2 findings normally
