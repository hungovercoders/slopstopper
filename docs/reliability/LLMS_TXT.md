# llms.txt AI-Discoverability Check

Audits your site's `/llms.txt`, the [llmstxt.org](https://llmstxt.org/) map that lets an AI assistant read your key pages without parsing HTML. It complements [`ss:reliability:seo`](SEO.md): SEO covers what human-facing crawlers read, this covers the surface an LLM reads.

## What gets validated

The check fetches `/llms.txt` and asserts a **well-formed** file per the convention.

**Hard-fail (exit 1):**

- The file is reachable (HTTP 200)
- The body is non-empty
- The first content line is an H1 (`# <name>`)
- At least one markdown inline link is present

**Advisory (notes only, unless escalated via config):**

- Content-Type is `text/plain` or `text/markdown`
- A `> summary` blockquote follows the H1, as the spec recommends. Escalate with `require_summary`
- When `check_links` is on, every link is HEAD-verified as reachable (non-4xx/5xx)

Because `llms.txt` is an *unratified* convention, the hard-fail bar is deliberately low. The check confirms the file exists and is structurally valid without imposing contested opinions.

## Configuration

Read from environment variables or `.slopstopper.yml`'s `reliability.llms_txt` block:

| Variable / key | Default | Purpose |
| --- | --- | --- |
| `LLMS_TXT_TEST_URL` | (none, required) | Base URL to audit |
| `LLMS_TXT_PATH` | `/llms.txt` | Path to the file |
| `reliability.llms_txt.check_links` | `false` | HEAD-verify every link inside llms.txt (`--check-links`) |
| `reliability.llms_txt.require_summary` | `false` | Fail if the `> summary` blockquote is missing (`--require-summary`) |

## Running it

```bash
# Audit a deployed site
task ss:reliability:llms-txt -- https://your-site.example.com

# Audit the local build and verify every link resolves
LLMS_TXT_TEST_URL=http://localhost:8080 \
task ss:reliability:llms-txt -- --check-links
```

Generated reports are written to:

- `.ss/reports/llms-txt/llms-txt-report.md` (human-readable)
- `.ss/reports/llms-txt/llms-txt-report.json` (machine-readable)

## Authoring an llms.txt

A minimal, valid file:

```markdown
# Your Project

> One-sentence summary of what this is.

## Docs
- [Getting started](https://example.com/start): how to install and run
- [Reference](https://example.com/reference): the full API

## Optional
- [Changelog](https://example.com/changelog): release history
```

This site's own file, [`app/llms.txt`](../../app/llms.txt), is the canonical example.

## Why this exists

A tool that promises quality for agents should be readable by agents. `llms.txt` gives an assistant a short, curated entry point, so you say what the project is instead of leaving it to scrape the HTML. Few crawlers read the file yet, so the check asks only that it exists and is well formed.

## CI integration

The [`ss-reliability-llms-txt-check.yml`](../../.github/workflows/ss-reliability-llms-txt-check.yml) workflow runs on every PR, every push to `main`, on `deployment_status` success, daily, and on a `url` dispatch (which is how `ss-cloudflare-deployed.yml` runs it after a Workers Builds deploy). PR runs comment back with pass/fail and a link to the artefact.
