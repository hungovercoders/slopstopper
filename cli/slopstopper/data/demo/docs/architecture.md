# Architecture

Lantern is one HTML file, `app/index.html`, served as static assets.
There is no build step: what is committed is what is served.

## The page

Every service is one `<article>` inside `<main>`, with a heading, an
owner, a status badge and a link to the service's runbook. Styles live
in a `<style>` block at the top of the page, so the page is one file and
the Content-Security-Policy needs no exceptions.

## The service table

| Service   | Owner    | Runbook                 |
| --------- | -------- | ----------------------- |
| gateway   | platform | runbooks/gateway.md     |
| billing   | payments | runbooks/billing.md     |
| search    | discover | runbooks/search.md      |

The page and this table must agree; a pull request that changes one
without the other is sent back.
