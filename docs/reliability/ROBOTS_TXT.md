# robots.txt Discoverability Check

Audits your site's `/robots.txt`: a stray `Disallow: /` that would de-index the whole site fails, and a `Sitemap:` pointer is required. `/robots.txt` is the [Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) file every crawler reads first, and a `Disallow: /` leaked from a staging config silently removes a whole public site from search. It complements [`ss:reliability:seo`](SEO.md) (what human crawlers read) and [`ss:reliability:llms-txt`](LLMS_TXT.md) (what AI assistants read).

## What gets validated

The check fetches `/robots.txt` and asserts it is present and does not sabotage discoverability.

**Hard-fail (exit 1):**

- The file is reachable (HTTP 200)
- The body is non-empty
- The `User-agent: *` group has no blanket `Disallow: /`, unless `allow_disallow_all` says otherwise
- At least one `Sitemap:` directive is present

**Advisory (notes only):**

- Content-Type is `text/plain`
- No `Llms:` line. It is not a robots.txt directive: no crawler reads it, Lighthouse's `robots-txt` audit counts it as an unknown directive and scores the file 0 (which costs the Core Web Vitals SEO category), and `/llms.txt` is found at its own path, which the `llms-txt` check covers
- When `check_links` is on, the `Sitemap:` URLs are HEAD-verified as reachable (non-4xx/5xx)

Lighthouse's SEO audit (run by `ss:reliability:cwv`) already checks that robots.txt *parses*, but it buries accidental blanket blocking and a missing sitemap pointer. This check surfaces those two failures as a named, first-class gate.

## Configuration

Read from environment variables or `.slopstopper.yml`'s `reliability.robots_txt` block:

| Variable / key | Default | Purpose |
| --- | --- | --- |
| `ROBOTS_TXT_TEST_URL` | (none, required) | Base URL to audit |
| `ROBOTS_TXT_PATH` | `/robots.txt` | Path to the file |
| `reliability.robots_txt.allow_disallow_all` | `false` | Permit a blanket `Disallow: /` (`--allow-disallow-all`) |
| `reliability.robots_txt.check_links` | `false` | HEAD-verify Sitemap: URLs resolve (`--check-links`) |

A `require_llms` key is ignored with a note.

## Running it

```bash
# Audit a deployed site
task ss:reliability:robots-txt -- https://your-site.example.com

# Audit the local build and verify the referenced URLs resolve
ROBOTS_TXT_TEST_URL=http://localhost:8080 \
task ss:reliability:robots-txt -- --check-links
```

Generated reports are written to:

- `.ss/reports/robots-txt/robots-txt-report.md` (human-readable)
- `.ss/reports/robots-txt/robots-txt-report.json` (machine-readable)

## Authoring a robots.txt

A minimal, healthy file for a public site:

```
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```

This site's own file, [`app/robots.txt`](../../app/robots.txt), is the canonical example.

## Why this exists

A single wrong line in robots.txt can de-index a whole site, and the failure is silent, because nothing errors and traffic evaporates over the following weeks. A deploy-time gate turns that slow, invisible failure into a red check on the PR that introduced it. The sitemap-pointer assertion completes the picture: crawlers that read robots.txt find the URL inventory rather than guessing.

## CI integration

The [`ss-reliability-robots-txt-check.yml`](../../.github/workflows/ss-reliability-robots-txt-check.yml) workflow runs on every PR, every push to `main`, on `deployment_status` success, daily, and on a `url` dispatch (which is how `ss-cloudflare-deployed.yml` runs it after a Workers Builds deploy). PR runs comment back with pass/fail and a link to the artefact.
