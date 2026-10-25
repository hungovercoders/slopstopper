# Architecture

Lantern is two HTML pages, `app/index.html` and `app/history.html`,
with one stylesheet beside them, served as static assets. There is no
build step: what is committed is what is served.

## The page

Every service is one `<article>` inside `<main>`, with a heading, an
owner, a status badge and a link to the service's runbook. Styles live
in `app/style.css` and nothing is inlined, so the Content-Security-Policy
in `app/_headers` is strict for every path; the one relaxation it carries
is for the history page's chart.

## The service table

| Service   | Owner    | Runbook                                  |
| --------- | -------- | ---------------------------------------- |
| gateway   | platform | https://example.com/runbooks/gateway     |
| billing   | payments | https://example.com/runbooks/billing     |
| search    | discover | https://example.com/runbooks/search      |

The page and this table must agree; a pull request that changes one
without the other is sent back.
