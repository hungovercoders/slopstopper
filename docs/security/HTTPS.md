# HTTPS Redirect and HSTS

Checks that a deployed site sends every visitor to `https://` and keeps them there. A site can answer `http://` with a page and nobody at a desk notices: the browser remembers the https URL, or the TLD is on the HSTS preload list. A link shortener that rewrites a link to `http://`, or an in-app browser that ignores the preload list, then gets the page in the clear or no page at all.

`security:https` makes two requests to the deployed origin and gives a verdict on each.

## What it checks

| Finding | Hard fail? | Why |
|---|---|---|
| `http://<host>/` answers anything but a `301`/`302`/`307`/`308` | yes | A `200` serves the page without TLS; a `4xx` means an `http://` link does not open |
| The redirect's `Location` is not `https://` | yes | The visitor is still on plain HTTP |
| The redirect goes to `https://` on another host | yes | The browser has to see https on this host before it can remember HSTS for it. Redirect to `https://<host>/` first, then on |
| `Strict-Transport-Security` missing from the https response | unless `require_hsts: false` | Without it every later visit can start on plain HTTP again |
| `Strict-Transport-Security` with no `max-age`, or `max-age=0` | unless `require_hsts: false` | Browsers ignore the first and the second switches HSTS off |
| Nothing answers on port 80 | note | There is no plain-HTTP page to redirect |
| The https URL is on a custom port | note | Port 80 on that host may be another service, so only HSTS is audited |

A target that is `localhost`, a loopback address or not https is skipped with exit 0: there is no edge to redirect there and HSTS has no effect. An https host that does not answer is exit 2, because the check could not run.

## Fixing a finding

- **No redirect.** Turn on the host's force-HTTPS setting. On Cloudflare it is SSL/TLS → Edge Certificates → **Always Use HTTPS**; other hosts and proxies have their own.
- **No HSTS.** Send `Strict-Transport-Security: max-age=15552000` on every response. That goes in `public/_headers` on Cloudflare Pages and Netlify (the baseline the installer seeds carries the line, commented), in `worker/headers.json` or whatever `headers.source` names, or in the server's own config. Add `includeSubDomains` and `preload` only once every subdomain serves https, because both are slow to undo.

## Configuration

```yaml
# .slopstopper.yml
security:
  https:
    require_hsts: true   # false → a missing header is a note, not a failure
```

The redirect has no knob: a site that serves plain HTTP on purpose turns the check off under `workflows.disabled`.

## Running locally

```bash
task ss:security:https -- https://your-site.example.com

task ss:security:https -- https://your-site.example.com --no-require-hsts

HTTPS_TEST_URL=https://your-site.example.com task ss:security:https
```

Report: `.ss/reports/https/https-report.{md,json}`.

In CI the workflow audits `urls.preview` on pull requests and `urls.production` on pushes to `main`, the daily schedule, `deployment_status` events and the Cloudflare post-deploy dispatch. It never builds and serves the repo, because the redirect and the header come from the edge. With neither URL configured it skips with a notice.

Env var: `HTTPS_TEST_URL` (base URL).
